import {useEffect, useRef, useState} from 'react';

type Draft = {script:string;model:string;estimated_seconds:number};
type Props = {projectId:string;configured:boolean;productionStarted:boolean;
  targetSeconds:number;hasScript:boolean;onUse:(script:string)=>void};

export function ScriptWriter({projectId,configured,productionStarted,targetSeconds,hasScript,onUse}:Props) {
  const key=`scriptstudio-writer-${projectId}`;
  const [open,setOpen]=useState(false);
  const [prompt,setPrompt]=useState('');
  const [audience,setAudience]=useState('General audience');
  const [tone,setTone]=useState('Conversational');
  const [seconds,setSeconds]=useState(Math.min(300,Math.max(30,targetSeconds)));
  const [draft,setDraft]=useState<Draft|null>(null);
  const [working,setWorking]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const controller=useRef<AbortController|null>(null);
  const ready=useRef(false);

  useEffect(()=>{
    try {
      const saved=JSON.parse(localStorage.getItem(key)||'null');
      if(saved){setPrompt(saved.prompt||'');setAudience(saved.audience||'General audience');
        setTone(saved.tone||'Conversational');setSeconds(saved.seconds||60);
        setDraft(saved.draft||null);setOpen(true);}
    } catch { /* Browser storage is optional; manual writing still works. */ }
    ready.current=true;
    return ()=>{controller.current?.abort();};
  },[key]);

  useEffect(()=>{
    if(!ready.current)return;
    try {localStorage.setItem(key,JSON.stringify({prompt,audience,tone,seconds,draft}));}
    catch { /* A full or disabled browser store must not break generation. */ }
  },[key,prompt,audience,tone,seconds,draft]);

  async function generate() {
    setWorking(true);setError('');setNotice('');
    controller.current=new AbortController();
    try {
      const response=await fetch(`/api/projects/${projectId}/script-draft`,{
        method:'POST',headers:{'Content-Type':'application/json'},signal:controller.current.signal,
        body:JSON.stringify({prompt,audience,tone,target_seconds:seconds}),
      });
      const result=await response.json();
      if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Check your prompt and duration, then try again.');
      setDraft(result);
    } catch(e) {
      if((e as Error).name!=='AbortError')setError((e as Error).message);
    } finally {setWorking(false);}
  }

  return <section className="script-writer" aria-label="AI script writer">
    <button className="wide" aria-expanded={open} onClick={()=>setOpen(!open)}>
      {open?'Hide AI writer':'Write with AI'}
    </button>
    {open&&<div>
      <p className="muted">Describe your video. Review the draft, then use it in the script editor below.</p>
      {productionStarted?<p className="note">Production has started. Create a new project to generate a new script.</p>:
        !configured?<p className="note">Local AI setup required: configure OLLAMA_URL and OLLAMA_MODEL on the server. You can still write your script below.</p>:null}
      <fieldset disabled={working||productionStarted||!configured}>
        <label>Video idea<textarea aria-label="Video idea" maxLength={10000} value={prompt}
          onChange={e=>setPrompt(e.target.value)} placeholder="A 60-second introduction to urban gardening for beginners. Cover containers, sunlight, and a simple first step."/></label>
        <label>Audience<input value={audience} maxLength={200} onChange={e=>setAudience(e.target.value)}/></label>
        <label>Tone<input value={tone} maxLength={200} onChange={e=>setTone(e.target.value)}/></label>
        <label>Draft target seconds<input type="number" min={30} max={300} step={1} value={seconds}
          onChange={e=>setSeconds(Number(e.target.value))}/></label>
        <button className="primary wide" disabled={!prompt.trim()||!Number.isInteger(seconds)||seconds<30||seconds>300}
          onClick={()=>void generate()}>{working?'Writing draft…':draft?'Generate another draft':'Generate script'}</button>
      </fieldset>
      {working&&<p role="status">Writing with your local AI model. This can take a few minutes. Your current script is unchanged.</p>}
      {error&&<p role="alert" className="error">{error}</p>}
      {draft&&<div className="draft-review">
        <p className="muted">Local AI · {draft.model} · Review facts and wording before use. Timing is an estimate.</p>
        <label>Generated script<textarea aria-label="Generated script" value={draft.script} maxLength={50000}
          onChange={e=>setDraft({...draft,script:e.target.value})}/></label>
        <button className="primary wide" disabled={working||productionStarted||!draft.script.trim()} onClick={()=>{
          onUse(draft.script);setNotice('Draft copied to the script editor. Save it or choose Plan scenes & shots to continue.');
        }}>{hasScript?'Replace script with this draft':'Use this script'}</button>
        <button disabled={working} onClick={()=>{setDraft(null);setNotice('Draft discarded. Your script is unchanged.');}}>Discard draft</button>
      </div>}
      {notice&&<p role="status">{notice}</p>}
    </div>}
  </section>;
}
