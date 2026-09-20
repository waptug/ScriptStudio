import {useEffect,useState} from 'react';
export type LocalModel={id:string;name:string;kind:string;license:string;url:string;preset:string;state:string;ready:boolean;supported:boolean;installable:boolean;progress:number|null;download_bytes:number|null;installed_bytes:number|null;guidance:string;error?:string;gated?:boolean;voices?:string[];phase?:string;detail?:string;completed_bytes?:number;total_bytes?:number|null;started_at?:number;heartbeat?:number;progress_updated?:number;cancel?:boolean};
const active=(m:LocalModel)=>['downloading','installing','verifying'].includes(m.state);
const size=(n:number|null)=>n===null?'Not yet pinned':`${(n/1024**3).toFixed(2)} GiB`;
const duration=(seconds:number)=>seconds<60?`${Math.floor(seconds)}s`:`${Math.floor(seconds/60)}m ${Math.floor(seconds%60)}s`;
const phases:Record<string,string>={preparing:'Preparing installation',downloading:'Downloading files',checking_download:'Checking downloaded file',extracting:'Unpacking runtime',verifying:'Verifying files',inventory:'Scanning installed runtime',probing:'Testing model runtime'};
function InstallationProgress({model:m,now,disconnected}:{model:LocalModel;now:number;disconnected:boolean}){
 const known=typeof m.progress==='number'&&!!m.total_bytes;
 const age=(timestamp?:number)=>timestamp?Math.max(0,now-timestamp):null;
 const heartbeatAge=age(m.heartbeat),progressAge=age(m.progress_updated),elapsed=age(m.started_at);
 const label=phases[m.phase||'']||'Installing model';
 const status=disconnected?'Connection lost — reconnecting; installation may still be running.':heartbeatAge===null?'Waiting for installer status…':heartbeatAge>10?'No recent installer response — checking again…':'Installer responding';
 return <div className="model-install-progress" aria-busy="true">
  <div className="model-progress-heading"><strong>{m.cancel?'Cancel requested — waiting for current step':label}</strong><span>{known?`${Math.floor(m.progress!*100)}%`:'Working…'}</span></div>
  <progress aria-label={`${m.name}: ${label}`} max={1} value={known?m.progress!:undefined}/>
  <p className="model-progress-detail" title={m.detail}>{m.detail||'Preparing files…'}</p>
  {known&&<p>{size(m.completed_bytes||0)} / {size(m.total_bytes!)} · current stage</p>}
  <p role="status" className={disconnected||(heartbeatAge!==null&&heartbeatAge>10)?'error':'note'}>{status}{elapsed!==null&&` · Elapsed ${duration(elapsed)}`}{progressAge!==null&&progressAge>=10&&` · Last progress ${duration(progressAge)} ago`}</p>
  {!known&&<p className="note">This step has no measured percentage yet. Large files and runtime checks can take several minutes.</p>}
 </div>;
}
export function LocalModels(){
 const [models,setModels]=useState<LocalModel[]>([]),[hardware,setHardware]=useState(''),[error,setError]=useState(''),[connectionError,setConnectionError]=useState(''),[accepted,setAccepted]=useState(false),[busy,setBusy]=useState(false),[pending,setPending]=useState<string|null>(null),[now,setNow]=useState(Date.now()/1000);
 async function refresh(){const response=await fetch('/api/admin/local-models');if(!response.ok)throw Error('Could not load local models');const data=await response.json();setModels(data.models);setHardware(data.hardware.gpus.map((g:{name:string;total_mib:number;free_mib:number})=>`${g.name}: ${g.free_mib} / ${g.total_mib} MiB free`).join(' · ')+' '+data.hardware.guidance);setConnectionError('');}
 useEffect(()=>{
  let stopped=false;
  let timer:ReturnType<typeof setTimeout>;
  async function poll(){try{await refresh();}catch(e){if(!stopped)setConnectionError((e as Error).message);}finally{if(!stopped)timer=setTimeout(()=>void poll(),2000);}}
  void poll();
  const clock=setInterval(()=>setNow(Date.now()/1000),1000);
  return()=>{stopped=true;clearTimeout(timer);clearInterval(clock);};
 },[]);
 async function action(id:string,action:string){setBusy(true);setPending(id);setError('');try{const response=await fetch(`/api/admin/local-models/${id}/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accept_license:accepted})});const data=await response.json();if(!response.ok)throw Error(data.detail);setModels(models=>models.map(m=>m.id===id?{...m,...data,ready:data.state==='ready'}:m));await refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);setPending(null);}}
 const installing=models.some(active);
 return <section className="admin-section"><h2>Local models</h2><p>Generate media on this workstation with no provider charges. Install downloads the selected model and its isolated Windows runtime. Installed models work offline and stay installed after you close or restart ScriptStudio. Generation loads the selected model from disk into memory; it does not reinstall it.</p><p className="note">{hardware}</p><p>Keep the EXE and ScriptStudioNative folder together. Downloads, models, caches and scratch files stay inside that folder. Each install reserves expanded space plus 2 GiB for working files.</p>{error&&<p role="alert" className="error">{error}</p>}{connectionError&&<p role="alert" className="error">{connectionError}. Reconnecting automatically.</p>}{models.map(m=><article className="credential" key={m.id}><h3>{m.name} · {m.kind}</h3><p>{m.preset}</p><p><a href={m.url} target="_blank" rel="noreferrer">{m.license}</a></p><p>Download: {size(m.download_bytes)} · Expanded runtime allowance: {size(m.installed_bytes)}</p><p role="status">{m.ready?'Ready':m.state.replaceAll('_',' ')} · {m.guidance}</p>{active(m)?<InstallationProgress model={m} now={now} disconnected={!!connectionError}/>:pending===m.id&&<div className="model-install-progress"><progress aria-label={`${m.name}: Sending request`}/><p role="status">Sending request…</p></div>}<p>{m.error}</p>{m.gated&&<><p>Accept the upstream license and commercial conditions on Hugging Face, then save an authorized Hugging Face token below. The token is encrypted and never returned.</p><label className="check"><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/>I accepted the upstream license and applicable commercial-use conditions</label></>}<div className="row">{(['install','cancel','resume','verify','uninstall'] as const).map(a=><button key={a} disabled={busy||(a==='cancel'?(!active(m)||m.cancel):installing)||(a==='install'&&(m.ready||!m.supported||!m.installable||(m.gated&&!accepted)))} onClick={()=>void action(m.id,a)}>{a==='install'&&m.ready?'Installed':a==='resume'&&m.ready?'Repair':a[0].toUpperCase()+a.slice(1)}</button>)}</div></article>)}</section>;
}
