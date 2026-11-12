"""Read-only retrospective temperature comparison; never changes live scorer rules."""
from __future__ import annotations
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import database
from dashboard_scores import load_forecast_rows
from backfill_weathernext_temperature import validate_metadata

from dashboard_scores import HORIZONS, horizon_pairs


def analyze(manifest, cutoff, output):
    cutoff=pd.Timestamp(cutoff)
    if cutoff.tzinfo is None: raise ValueError('UTC cutoff required')
    with closing(sqlite3.connect(database.DB_PATH.resolve().as_uri()+'?mode=ro',uri=True)) as con:
        con.execute('BEGIN')
        rows=load_forecast_rows(con,'air_temperature',end=cutoff)
        o=pd.read_sql_query('SELECT location_id,observed_at AS valid_at,air_temperature AS actual FROM observations WHERE air_temperature IS NOT NULL',con)
        o.valid_at=pd.to_datetime(o.valid_at,utc=True,format='mixed')
        observed=o.groupby(['location_id','valid_at']).actual.agg(['min','max']).reset_index()
        observed=observed[observed['min']==observed['max']].rename(columns={'min':'actual'})[['location_id','valid_at','actual']]
        assets=pd.read_sql_query("SELECT run_id,valid_at,asset_id FROM weathernext_samples WHERE metric='air_temperature' AND statistic='mean'",con)
        assets.valid_at=pd.to_datetime(assets.valid_at,utc=True,format='mixed')
        rows=rows.merge(assets,on=['run_id','valid_at'],how='left')
        duplicate_counts={
            'forecast_runs':con.execute('SELECT count(*) FROM (SELECT provider,location_id,issued_at FROM forecast_runs GROUP BY 1,2,3 HAVING count(*)>1)').fetchone()[0],
            'forecast_points':con.execute('SELECT count(*) FROM (SELECT run_id,valid_at FROM forecasts GROUP BY 1,2 HAVING count(*)>1)').fetchone()[0],
            'statistic_values':con.execute('SELECT count(*) FROM (SELECT run_id,valid_at,metric,statistic FROM weathernext_samples GROUP BY 1,2,3,4 HAVING count(*)>1)').fetchone()[0]}
    metadata=[]
    for issued,items in manifest['image_metadata'].items():
        validate_metadata(issued,manifest['plan'][issued],items)
        for item in items:
            metadata.append({'issued_at':pd.Timestamp(issued),'valid_at':pd.Timestamp(item['end_time']),
                             'asset_index':item['system:index'],
                             'original_available_at':pd.to_datetime(item['ingestion_time_utc'],unit='s',utc=True)})
    # Operational samples store system:index; also accept older full asset paths.
    rows['asset_index']=rows.asset_id.str.rsplit('/',n=1).str[-1]
    rows=rows.merge(pd.DataFrame(metadata),on=['issued_at','valid_at','asset_index'],how='left',validate='many_to_one')
    rows['available_at']=rows.original_available_at.fillna(rows.retrieved_at)
    derived=(rows.valid_at-rows.issued_at).dt.total_seconds()/3600
    assert ((derived-rows.lead_hours).abs()<1e-7).all(),'Stored lead differs from original timestamps'
    summaries=[];frames=[];examples=[];used_stations=set()
    preferred=['SN68860','SN18700','SN50540','SN90450']
    for horizon,station in zip(HORIZONS,preferred):
        pairs=horizon_pairs(rows,observed,horizon,cutoff)
        operational=horizon_pairs(rows,observed,horizon,cutoff,operational=True)
        entry={'horizon':horizon,'shared_samples':len(pairs),'operational_samples':len(operational)}
        if len(pairs):
            entry.update({'yr_mae':float(pairs.met_abs_error.mean()),'weathernext_mae':float(pairs.wn_abs_error.mean()),
                          'yr_bias':float(pairs.met_error.mean()),'weathernext_bias':float(pairs.wn_error.mean()),
                          'mae_difference_wn_minus_yr':float(pairs.wn_abs_error.mean()-pairs.met_abs_error.mean()),
                          'stations':int(pairs.location_id.nunique())})
            for prefix in ['met','wn']:
                for stat,value in pairs[prefix+'_lead_hours'].agg(['min','median','mean','max']).items():
                    entry[prefix+'_lead_'+stat]=float(value)
            entry['lead_gap_mean']=float(pairs.lead_gap.mean());entry['lead_gap_max']=float(pairs.lead_gap.max())
            subset=pairs[pairs.station_id==station]
            if subset.empty: subset=pairs[~pairs.station_id.isin(used_stations)]
            example=subset.sort_values(['station_id','valid_at']).iloc[0]
            used_stations.add(example.station_id);examples.append(example.to_dict());frames.append(pairs)
        summaries.append(entry)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result={'cutoff':cutoff.isoformat(),'comparison':'retrospective; verified original Earth Engine ingestion before valid time, actual local retrieval unchanged',
            'horizons':summaries,'duplicate_counts':duplicate_counts,'examples':examples}
    (output/'historical-temperature-results.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    pd.DataFrame(summaries).to_csv(output/'historical-temperature-summary.csv',index=False)
    pd.DataFrame(examples).to_csv(output/'historical-temperature-examples.csv',index=False)
    if frames: pd.concat(frames,ignore_index=True).to_csv(output/'historical-temperature-matches.csv',index=False)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--cutoff',required=True)
    parser.add_argument('--output',default='outputs/temperature-backfill')
    args=parser.parse_args()
    result=analyze(json.loads(Path(args.manifest).read_text(encoding='utf-8')),args.cutoff,args.output)
    print(json.dumps(result,indent=2,default=str))
