/* This script receives private values from the loopback server only. */
'use strict';
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const units = {t:'°C',w:'m/s',p:'mm'};
const names = {t:'Temperature',w:'Wind speed',p:'Hourly precipitation'};
let data, variable='t', hours=48, chosenTime=null;
let theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
let requestNumber=0;
const timeFmt = new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Oslo',hour:'2-digit',minute:'2-digit'});
const dayFmt = new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Oslo',weekday:'short',day:'numeric',month:'short'});
const fullTime = iso => `${dayFmt.format(new Date(iso))}, ${timeFmt.format(new Date(iso))}`;
const value = (p,provider) => p?.[provider]?.[variable==='p'&&provider==='wn'?'p_p50':variable] ?? null;
const fmt = v => v===null || v===undefined ? '—' : `${v.toFixed(variable==='p'?2:1)} ${units[variable]}`;
const text = (id,v) => { $(id).textContent=v; };
function svg(tag,attrs={},content=''){
  const el=document.createElementNS(NS,tag);
  for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,v);
  if(content) el.textContent=content;
  return el;
}
function station(){return data?.stations.find(s=>s.id===$('station').value);}
function points(){
  const end=Date.parse(data.loaded)+hours*3600000;
  return (station()?.points??[]).filter(p=>Date.parse(p.time)<=end);
}
function setTheme(){
  document.documentElement.dataset.theme=theme;
  text('theme',theme==='dark'?'Light theme':'Dark theme');
  if(data) render();
}
$('theme').addEventListener('click',()=>{theme=theme==='dark'?'light':'dark';setTheme();});
setTheme();
function setPressed(selector,attribute,selected){
  document.querySelectorAll(selector).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset[attribute]===String(selected))));
}
document.querySelectorAll('[data-variable]').forEach(b=>b.addEventListener('click',()=>{
  variable=b.dataset.variable;setPressed('[data-variable]','variable',variable);render();
}));
document.querySelectorAll('[data-hours]').forEach(b=>b.addEventListener('click',()=>{
  hours=Number(b.dataset.hours);setPressed('[data-hours]','hours',hours);render();
}));
$('station').addEventListener('change',()=>{chosenTime=null;render();});
$('reload').addEventListener('click',load);
$('largest-gap').addEventListener('click',()=>{
  const paired=points().filter(p=>value(p,'yr')!==null&&value(p,'wn')!==null);
  if(!paired.length)return;
  chosenTime=paired.reduce((a,b)=>Math.abs(value(b,'wn')-value(b,'yr'))>Math.abs(value(a,'wn')-value(a,'yr'))?b:a).time;
  render();$('selected-heading').scrollIntoView({block:'nearest'});
});
async function load(){
  const request=++requestNumber;
  $('reload').disabled=true;
  try{
    const r=await fetch('/api/forecasts',{cache:'no-store'});
    if(!r.ok) throw new Error('Cannot read the fetched cloud state. Check PRIVATE_FORECAST.md.');
    const fresh=await r.json();
    if(request!==requestNumber)return;
    const prior=$('station').value;
    data=fresh;
    $('station').replaceChildren(...data.stations.map(s=>{
      const opt=document.createElement('option');opt.value=s.id;opt.textContent=s.name;return opt;
    }));
    $('station').value=data.stations.some(s=>s.id===prior)?prior:(data.stations.find(s=>s.id==='SN68860')?.id??data.stations[0]?.id);
    const age=(Date.parse(data.loaded)-Date.parse(data.collected))/3600000;
    text('status',`Cloud snapshot: ${fullTime(data.collected)} Oslo · ${age.toFixed(1)} hours old.${age>8?' This snapshot is old; refresh the fetched state before comparing.':''}`);
    $('status').classList.toggle('warning',age>8);
    $('notices').replaceChildren(...data.notices.map(n=>{const p=document.createElement('p');p.textContent=n;return p;}));
    render();
  }catch(e){if(request===requestNumber){text('status',e.message);$('status').classList.add('warning');}}
  finally{if(request===requestNumber)$('reload').disabled=false;}
}
function story(ps){
  const paired=ps.filter(p=>value(p,'yr')!==null&&value(p,'wn')!==null);
  if(!paired.length)return 'No shared forecast hours are saved in this window.';
  const diffs=paired.map(p=>Math.abs(value(p,'wn')-value(p,'yr'))).sort((a,b)=>a-b);
  const middle=(diffs[Math.floor((diffs.length-1)/2)]+diffs[Math.ceil((diffs.length-1)/2)])/2;
  const threshold=variable==='t'?0:variable==='w'?10:.1;
  const event=v=>variable==='t'?v<threshold:variable==='p'?v>threshold:v>=threshold;
  const differing=paired.filter(p=>event(value(p,'yr'))!==event(value(p,'wn'))).length;
  const eventName=variable==='t'?'whether it falls below freezing':variable==='w'?'whether wind reaches 10 m/s':'whether the hour is wet (>0.1 mm)';
  return `Typical gap: ${fmt(middle)} across ${paired.length} shared hours. ${differing?'Their main forecasts differ on '+eventName+' at '+differing+' hours.':'Their main forecasts agree on '+eventName+'.'}`;
}
function render(){
  if(!data)return;
  const ps=points();
  if(!ps.some(p=>p.time===chosenTime))chosenTime=ps[0]?.time??null;
  text('place-name',station()?.name??'');text('chart-heading',names[variable]);text('story',story(ps));
  $('range-key').hidden=variable==='p';
  const shared=ps.filter(p=>value(p,'yr')!==null&&value(p,'wn')!==null).length;
  $('largest-gap').disabled=shared===0;
  text('coverage',`${shared} shared hours saved in this ${hours}-hour window. Gaps are uncollected hours—not forecasts of zero. ${variable==='p'?'Bars show the hour ending at each time; WeatherNext uses the median.':'Bands cover the middle 80% of forecast possibilities; lines and bands stop at gaps.'}`);
  draw(ps);
  $('hours').replaceChildren(...ps.map(p=>{
    const b=document.createElement('button');b.type='button';b.dataset.time=p.time;b.setAttribute('aria-pressed',String(p.time===chosenTime));
    const small=document.createElement('small');small.textContent=dayFmt.format(new Date(p.time));
    b.append(small,document.createTextNode(timeFmt.format(new Date(p.time))));
    b.addEventListener('click',()=>{chosenTime=p.time;render();$('hours').querySelector(`[data-time="${chosenTime}"]`)?.focus({preventScroll:true});});
    return b;
  }));
  selected(ps.find(p=>p.time===chosenTime));
  text('table-caption',`${names[variable]} · Oslo time · WeatherNext ${variable==='p'?'median':'average'}`);
  $('table-body').replaceChildren(...ps.map(p=>{
    const tr=document.createElement('tr');tr.classList.toggle('selected-row',p.time===chosenTime);
    const y=value(p,'yr'),w=value(p,'wn');
    [fullTime(p.time),fmt(y),fmt(w),y!==null&&w!==null?fmt(w-y):'—'].forEach((v,i)=>{
      const c=document.createElement(i===0?'th':'td');if(i===0)c.scope='row';c.textContent=v;tr.append(c);
    });return tr;
  }));
}
function selected(p){
  text('selected-heading',p?fullTime(p.time)+' Oslo':'No saved future hours');
  const y=value(p,'yr'),w=value(p,'wn');
  text('difference',y!==null&&w!==null?`WeatherNext − Yr: ${fmt(w-y)}`:'A comparison needs both forecasts.');
  for(const provider of ['yr','wn']){
    const row=p?.[provider];const v=value(p,provider);
    text(provider+'-value',fmt(v));
    const lo=row?.[variable+'_p10'],hi=row?.[variable+'_p90'];
    text(provider+'-range',variable!=='p'&&lo!==null&&lo!==undefined&&hi!==null&&hi!==undefined?`Middle 80%: ${fmt(lo)} to ${fmt(hi)}`:variable==='p'?(provider==='wn'?'Middle outcome (median)':'Hourly amount'):'No range saved');
    text(provider+'-extra',variable==='p'?(provider==='yr'&&row?.p_prob!==null&&row?.p_prob!==undefined?`Yr precipitation probability: ${Math.round(row.p_prob)}%`:provider==='wn'&&row?.p_p90!==null&&row?.p_p90!==undefined?`9 in 10 model outcomes are at or below ${fmt(row.p_p90)}`:''):'');
    const age=row?.issued?(Date.parse(data.loaded)-Date.parse(row.issued))/3600000:null;
    text(provider+'-issued',row?.issued?`Issued ${fullTime(row.issued)} Oslo · ${age.toFixed(1)} hours old`:'No issue time saved');
  }
  text('interval-note',variable==='p'&&p?`Precipitation covers ${timeFmt.format(new Date(Date.parse(p.time)-3600000))}–${timeFmt.format(new Date(p.time))} Oslo, including snow as water equivalent.`:'Temperature is at 2 m; wind is the mean speed at 10 m, not a gust.');
}
function segments(ps,provider,range=false){
  const groups=[];let group=[];
  for(const p of ps){
    const r=p[provider];const valid=value(p,provider)!==null&&(!range||(r?.[variable+'_p10']!=null&&r?.[variable+'_p90']!=null));
    if(!valid||(group.length&&Date.parse(p.time)-Date.parse(group.at(-1).time)>3601000)){
      if(group.length)groups.push(group);group=[];
    }
    if(valid)group.push(p);
  }
  if(group.length)groups.push(group);return groups;
}
function draw(ps){
  const chart=$('chart');chart.replaceChildren();
  const width=Math.max(260,$('plot').clientWidth),height=width<600?280:310;
  chart.setAttribute('viewBox',`0 0 ${width} ${height}`);
  chart.setAttribute('aria-label',`${names[variable]} at ${station()?.name}. ${ps.length} saved hours. See the numbers table for exact values.`);
  const css=getComputedStyle(document.documentElement),colour=n=>css.getPropertyValue(n).trim();
  const left=44,right=width-12,top=20,bottom=height-38;
  const start=Date.parse(data.loaded),end=start+hours*3600000;
  const x=t=>left+(Date.parse(t)-start)/(end-start)*(right-left);
  const vals=[];
  ps.forEach(p=>['yr','wn'].forEach(provider=>{
    const v=value(p,provider);if(v!==null)vals.push(v);
    if(variable!=='p')for(const k of ['_p10','_p90'])if(p[provider]?.[variable+k]!=null)vals.push(p[provider][variable+k]);
  }));
  if(variable==='p')vals.push(0);
  let min=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):1;
  const pad=Math.max(variable==='p'?.05:1,(max-min)*.12);min=variable==='p'?0:min-pad;max+=pad;
  const y=v=>bottom-(v-min)/(max-min)*(bottom-top);
  // Mark hours without either provider's selected variable. Never interpolate gaps.
  const relevant=ps.filter(p=>value(p,'yr')!==null||value(p,'wn')!==null);
  const windows=relevant.map(p=>[Math.max(left,x(p.time)-(right-left)/hours/2),Math.min(right,x(p.time)+(right-left)/hours/2)]);
  let cursor=left;
  for(const [a,b] of [...windows,[right,right]]){
    if(a>cursor+2)chart.append(svg('rect',{x:cursor,y:top,width:a-cursor,height:bottom-top,fill:colour('--gap')}));cursor=Math.max(cursor,b);
  }
  for(let i=0;i<5;i++){
    const v=min+(max-min)*i/4,yy=y(v);
    chart.append(svg('line',{x1:left,y1:yy,x2:right,y2:yy,stroke:colour('--line'),'stroke-width':1}));
    chart.append(svg('text',{x:left-8,y:yy+4,'text-anchor':'end',fill:colour('--muted'),'font-size':11},v.toFixed(variable==='p'||max-min<4?1:0)));
  }
  chart.append(svg('text',{x:left,y:11,fill:colour('--muted'),'font-size':11},units[variable]));
  const threshold=variable==='t'?0:variable==='w'?10:.1;
  if(threshold>=min&&threshold<=max){
    chart.append(svg('line',{x1:left,y1:y(threshold),x2:right,y2:y(threshold),stroke:colour('--muted'),'stroke-dasharray':'3 5','stroke-width':1}));
  }
  const step=width<600?12:6;
  const tick=new Date(start);tick.setUTCMinutes(0,0,0);tick.setUTCHours(tick.getUTCHours()+1);
  for(let t=tick.getTime();t<=end;t+=step*3600000){
    const xx=x(new Date(t).toISOString());
    chart.append(svg('text',{x:Math.max(left+18,Math.min(right-18,xx)),y:bottom+20,'text-anchor':'middle',fill:colour('--muted'),'font-size':11},timeFmt.format(t)));
    chart.append(svg('text',{x:Math.max(left+18,Math.min(right-18,xx)),y:bottom+34,'text-anchor':'middle',fill:colour('--muted'),'font-size':9},dayFmt.format(t)));
  }
  for(const provider of ['yr','wn']){
    const colourLine=colour('--'+provider);
    if(variable!=='p'){
      for(const group of segments(ps,provider,true)){
        if(group.length<2)continue;
        const coords=[...group.map(p=>[x(p.time),y(p[provider][variable+'_p90'])]),...group.slice().reverse().map(p=>[x(p.time),y(p[provider][variable+'_p10'])])];
        chart.append(svg('polygon',{points:coords.map(p=>p.join(',')).join(' '),fill:colour('--'+provider+'-fill')}));
      }
      for(const group of segments(ps,provider)){
        chart.append(svg('polyline',{points:group.map(p=>`${x(p.time)},${y(value(p,provider))}`).join(' '),fill:'none',stroke:colourLine,'stroke-width':2.5,'stroke-dasharray':provider==='wn'?'6 3':'none'}));
      }
      ps.forEach(p=>{const v=value(p,provider);if(v!==null)chart.append(svg('circle',{cx:x(p.time),cy:y(v),r:p.time===chosenTime?5:2.5,fill:colourLine}));});
    }else{
      const bw=Math.min(12,Math.max(3,(right-left)/hours*.32));
      ps.forEach(p=>{const v=value(p,provider);if(v!==null)chart.append(svg('rect',{x:x(p.time)+(provider==='yr'?-bw-1:1),y:y(v),width:bw,height:Math.max(1,bottom-y(v)),fill:colourLine,rx:1}));});
    }
  }
  if(chosenTime)chart.append(svg('line',{x1:x(chosenTime),y1:top,x2:x(chosenTime),y2:bottom,stroke:colour('--ink'),'stroke-dasharray':'2 5','stroke-width':1}));
  if(!vals.length)chart.append(svg('text',{x:(left+right)/2,y:height/2,'text-anchor':'middle',fill:colour('--muted'),'font-size':12},'No saved values in this window'));
  chart.onclick=e=>{
    if(!ps.length)return;
    const at=(e.clientX-chart.getBoundingClientRect().left-left)/(right-left)*(end-start)+start;
    chosenTime=ps.reduce((a,b)=>Math.abs(Date.parse(a.time)-at)<Math.abs(Date.parse(b.time)-at)?a:b).time;render();
  };
}
new ResizeObserver(()=>{if(data)draw(points());}).observe($('plot'));
load();
// Re-evaluate ages and expired targets locally; this never fetches from GitHub.
setInterval(()=>{if(data&&!$('reload').disabled)load();},60000);
