import {ThemeToggle} from './ThemeToggle';
import {useEffect, useState} from 'react';

type PaidPermissions = {enabled:boolean;text:boolean;video:boolean;audio:boolean;speech:boolean;music:boolean};
type Configuration = {values:Record<string,string>;credentials:Record<string,{configured:boolean;source:string}>;live_enabled:boolean;paid_generation:PaidPermissions};
const paidCategories: {key:Exclude<keyof PaidPermissions,'enabled'>;label:string;description:string}[] = [
  {key:'text',label:'Paid text generation',description:'Controls the optional operator-configured planning gateway. No direct paid text provider is connected. Local Ollama stays free.'},
  {key:'video',label:'Paid video generation',description:'Runway video generation.'},
  {key:'audio',label:'Paid audio generation',description:'General audio and sound effects. Permission is saved; no paid audio adapter is connected yet.'},
  {key:'speech',label:'Paid speech generation',description:'ElevenLabs narration. This is separate from general audio.'},
  {key:'music',label:'Paid music generation',description:'Permission is saved; no paid music adapter is connected yet. Suno remains unavailable.'},
];
const keys=['RUNWAY_API_KEY','ELEVENLABS_API_KEY'];
const labels:Record<string,string>={
  OLLAMA_URL:'Local Ollama server URL',SCRIPT_WRITER_MODEL:'Script writing model',
  OLLAMA_MODEL:'Scene planning model',RUNWAY_MODEL:'Video model · Runway',
  ELEVENLABS_MODEL:'Narration model · ElevenLabs',RUNWAY_USD_PER_SECOND:'Runway estimate · USD per second',
  ELEVENLABS_USD_PER_CHARACTER:'ElevenLabs estimate · USD per character',
};

export function Admin({onClose}:{onClose:()=>void}) {
  const [config,setConfig]=useState<Configuration|null>(null);
  const [credentials,setCredentials]=useState<Record<string,string>>({});
  const [clear,setClear]=useState<string[]>([]);
  const [models,setModels]=useState<string[]>([]);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  async function request(path:string,method='GET',body?:unknown) {
    const response=await fetch('/api/admin/'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    const result=await response.json();
    if(!response.ok)throw Error(result.detail||'Admin request failed');
    return result;
  }
  useEffect(()=>{request('settings').then(setConfig).catch(e=>setError(e.message));},[]);
  async function run(action:()=>Promise<void>) {
    setBusy(true);setError('');setNotice('');
    try{await action();}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <div className="dashboard admin"><header><strong className="brand"><img className="brand-logo" src="/logo.svg" alt="" width="32" height="32"/>ScriptStudio · Admin</strong><span className="spacer"/><ThemeToggle/><button onClick={onClose}>Back to workspace</button></header>
    <main><h1>Models & credentials</h1><p>Choose the models used by each workflow. Changes apply to new requests; queued generation jobs keep their captured model.</p>
      {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="note">{notice}</p>}
      {config&&<fieldset disabled={busy}>
        <section className="admin-section"><h2>Paid AI generation</h2>
          <label className="check"><input type="checkbox" role="switch" checked={config.paid_generation.enabled} onChange={e=>setConfig({...config,paid_generation:{...config.paid_generation,enabled:e.target.checked}})}/>Allow paid AI generation</label>
          <p className="note">Saving an enabled master switch and category authorizes new paid requests in that category. Credentials, compatible models, and project budgets are still required. Saving these switches does not start generation.</p>
          {paidCategories.map(({key,label,description})=><div key={key} className="credential">
            <label className="check"><input type="checkbox" role="switch" checked={config.paid_generation[key]} onChange={e=>setConfig({...config,paid_generation:{...config.paid_generation,[key]:e.target.checked}})}/>{label}</label>
            <p className="muted">{description} {config.paid_generation.enabled&&config.paid_generation[key]?'Permission on.':'Blocked.'}</p>
          </div>)}
          <p className="muted">Changes take effect when you save. Turning off blocks queued requests before submission. Already-submitted jobs can finish, and charges already incurred are not reversed. Local models, mock generation, imports, previews, and exports stay available.</p>
        </section>
        <section className="admin-section"><h2>Writing & planning · Local AI</h2>
          <label>{labels.OLLAMA_URL}<input value={config.values.OLLAMA_URL} placeholder="http://host.docker.internal:11434" onChange={e=>setConfig({...config,values:{...config.values,OLLAMA_URL:e.target.value}})}/></label>
          <button disabled={!config.values.OLLAMA_URL} onClick={()=>void run(async()=>{
            const result=await request('ollama-models','POST',{url:config.values.OLLAMA_URL});setModels(result.models);
            setNotice(`Found ${result.models.length} installed local models. Choose one below and save.`);
          })}>List installed models</button>
          <datalist id="local-models">{models.map(m=><option key={m} value={m}/>)}</datalist>
          {['SCRIPT_WRITER_MODEL','OLLAMA_MODEL'].map(key=><label key={key}>{labels[key]}<input list="local-models" value={config.values[key]} placeholder={key==='SCRIPT_WRITER_MODEL'?'Uses scene planning model if blank':'Select or enter an installed model'} onChange={e=>setConfig({...config,values:{...config.values,[key]:e.target.value}})}/></label>)}
          <p className="muted">Local models only. Listing models checks connectivity without generating content or downloading a model. Manual writing and deterministic scene planning remain available.</p>
        </section>
        <section className="admin-section"><h2>Video & narration</h2>
          {['RUNWAY_MODEL','RUNWAY_USD_PER_SECOND','ELEVENLABS_MODEL','ELEVENLABS_USD_PER_CHARACTER'].map(key=><label key={key}>{labels[key]}<input value={config.values[key]} onChange={e=>setConfig({...config,values:{...config.values,[key]:e.target.value}})}/></label>)}
          <p className="muted">Choose models compatible with the configured Runway image-to-video and ElevenLabs timestamped speech adapters and your account. Voice IDs and provider choices are set per project. Update estimates when changing models.</p>
          <p className="note">Paid requests require the master permission and the matching category above. Saving credentials alone does not authorize spending. Music supports local synthesis and imports; Suno API access remains unavailable.</p>
        </section>
        <section className="admin-section"><h2>API credentials</h2>
          <p>Keys are encrypted on the server and never returned to the browser. Leave a field blank to keep its current key.</p>
          {keys.map(key=><div key={key} className="credential">
            <label>{key==='RUNWAY_API_KEY'?'Runway API key':'ElevenLabs API key'}<input type="password" autoComplete="new-password" maxLength={4096} value={credentials[key]||''} disabled={clear.includes(key)} placeholder="Enter a replacement key" onChange={e=>setCredentials({...credentials,[key]:e.target.value})}/></label>
            <p className="muted">{config.credentials[key].configured?'Configured':'Not configured'} · {config.credentials[key].source==='admin'?'Saved in Admin':'Server environment'}</p>
            <label className="check"><input type="checkbox" checked={clear.includes(key)} onChange={e=>{
              setClear(e.target.checked?[...clear,key]:clear.filter(k=>k!==key));setCredentials({...credentials,[key]:''});
            }}/>Clear stored {key==='RUNWAY_API_KEY'?'Runway':'ElevenLabs'} credential on save</label>
          </div>)}
        </section>
        <button className="primary" onClick={()=>void run(async()=>{
          const next=await request('settings','PUT',{values:config.values,credentials,clear_credentials:clear,paid_generation:config.paid_generation});
          setConfig(next);setCredentials({});setClear([]);setNotice('Admin settings saved. New requests will use these settings.');
        })}>{busy?'Saving…':'Save admin settings'}</button>
      </fieldset>}
    </main>
  </div>;
}
