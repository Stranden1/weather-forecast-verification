import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from collectors.weathernext import collect


def main():
    load_dotenv(Path(__file__).resolve().parent/'.env')
    parser=argparse.ArgumentParser(description='WeatherNext: preview unless --save is specified')
    parser.add_argument('--issued-at',help='Explicit UTC initialization; default latest complete synoptic run')
    parser.add_argument('--hours',type=int,default=1)
    parser.add_argument('--stations',type=int,default=1,help='Station count; 0 means all active stations')
    parser.add_argument('--station-id',action='append')
    parser.add_argument('--metrics',nargs='+')
    parser.add_argument('--save',action='store_true')
    args=parser.parse_args()
    try:
        report=collect(os.getenv('EARTH_ENGINE_PROJECT','weatherapp-508323'),args.issued_at,
            args.hours,args.stations or None,args.save,station_ids=args.station_id,
            metrics=args.metrics,progress=lambda msg: print(msg,flush=True))
        print(json.dumps(report,indent=2))
        return 0
    except Exception as exc:
        print(f'WeatherNext failed: {type(exc).__name__}: {exc}',flush=True)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
