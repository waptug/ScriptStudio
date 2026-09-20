import {useEffect,useState} from 'react';
import './queue-progress.css';
export type QueuePhase='queued'|'prepare'|'generate'|'transfer'|'validate'|'ready';
export type QueueProgressData={phases:QueuePhase[];completed:QueuePhase[];phase:QueuePhase;fraction:number|null;detail?:string;phase_started_at?:number;last_activity_at?:number;last_contact_at?:number};
export type QueueResult={elapsed_seconds?:number;steps?:{current:number;total:number};queue_progress?:QueueProgressData;retry_state?:string};
export type QueueJob={id:string;kind:string;provider:string;state:string;progress:number;result:QueueResult};
const colors:Record<QueuePhase,string>={queued:'#64748b',prepare:'#2563eb',generate:'#7c3aed',transfer:'#0891b2',validate:'#d97706',ready:'#16a34a'};
const terminal=['ready','failed','canceled','submission_outcome_unknown'];
const localModels=['wan','kokoro','ace_step','stable_audio'];
const duration=(n:number)=>`${Math.floor(Math.max(0,n)/60)}m ${Math.floor(Math.max(0,n)%60)}s`;
export function phaseSequence(job:QueueJob):QueuePhase[]{
 return job.provider==='mock'?['queued','generate','validate','ready']:['queued','prepare','generate','transfer','validate','ready'];
}
export function phaseLabel(phase:QueuePhase,job:QueueJob){
 if(phase==='prepare')return localModels.includes(job.provider)?'Load model':'Prepare';
 if(phase==='generate')return job.kind==='render'?'Render':'Generate';
 if(phase==='transfer')return job.kind==='render'?'Encode':job.provider==='runway'?'Download':'Save file';
 return {queued:'Queued',validate:'Check',ready:'Ready'}[phase];
}
function legacyPhase(job:QueueJob):QueuePhase|undefined{
 if(job.state==='queued'||job.state==='waiting_for_gpu')return 'queued';
 if(job.state==='loading')return 'prepare';
 if(job.state==='submitting')return job.provider==='mock'?'generate':'prepare';
 if(job.state==='submitted'||job.state==='generating')return 'generate';
 if(job.state==='downloading')return job.provider==='mock'?'validate':'transfer';
 if(job.state==='validating')return 'validate';
 if(job.state==='ready')return 'ready';
}
export function QueueProgress({job,connected=true}:{job:QueueJob;connected?:boolean}){
 const [now,setNow]=useState(Date.now()/1000);
 const stopped=terminal.includes(job.state),bad=['failed','submission_outcome_unknown'].includes(job.state);
 useEffect(()=>{if(stopped)return;const timer=setInterval(()=>setNow(Date.now()/1000),1000);return()=>clearInterval(timer);},[stopped]);
 const data=job.result.queue_progress;
 const phases=data?.phases?.length?data.phases.filter(p=>p in colors):phaseSequence(job);
 const current=data?.phase||legacyPhase(job);
 const currentIndex=current?phases.indexOf(current):-1;
 const completed=job.state==='ready'?phases:data?.completed||phases.slice(0,Math.max(0,currentIndex));
 const measured=data?data.fraction:job.state==='generating'&&job.progress>0&&job.progress<1?job.progress:null;
 const fraction=measured!==null&&Number.isFinite(measured)?Math.max(0,Math.min(1,measured)):null;
 const heading=job.state==='failed'?'Failed':job.state==='canceled'?'Canceled':job.state==='submission_outcome_unknown'?'Needs attention':job.state==='waiting_for_gpu'?'Waiting for GPU':current?phaseLabel(current,job):job.state.replaceAll('_',' ');
 const lastActivity=data?.last_activity_at===undefined?undefined:Math.max(0,now-data.last_activity_at);
 const lastContact=data?.last_contact_at===undefined?undefined:Math.max(0,now-data.last_contact_at);
 const stale=lastContact!==undefined&&lastContact>30;
 const animate=!stopped&&connected&&!stale&&current!=='queued';
 const step=job.result.steps;
 return <section className={`queue-progress${bad?' queue-progress-error':''}${job.state==='canceled'?' queue-progress-canceled':''}`} aria-label={`${job.kind} job phases`}>
  <div className="queue-progress-heading"><strong>{heading}</strong>{!stopped&&fraction!==null&&<span>{Math.floor(fraction*100)}% of phase</span>}</div>
  <ol className="queue-phase-bar" aria-label="Phase sequence">
   {phases.map((phase,index)=>{
    const done=completed.includes(phase),active=phase===current&&!done;
    const status=done?'completed':active?stopped?'stopped':'current':'remaining';
    const label=phaseLabel(phase,job);
    return <li key={phase} className={`queue-phase ${status}${active&&animate&&fraction===null?' indeterminate':''}`} style={{'--phase-color':colors[phase]} as React.CSSProperties} aria-current={active?'step':undefined} title={`${label}: ${status}`} aria-label={`${index+1}. ${label}: ${status}`}>
     <span className="queue-phase-fill" style={{width:done?'100%':active&&fraction!==null?`${fraction*100}%`:'0%'}}/>
     <span className="queue-phase-mark" aria-hidden="true">{done?'✓':active?stopped?'×':'▶':index+1}</span>
    </li>;
   })}
  </ol>
  <div className="queue-phase-legend">{phases.map((p,i)=><span key={p}><i style={{background:colors[p]}} aria-hidden="true"/>{i+1}. {phaseLabel(p,job)}</span>)}</div>
  {!stopped&&current&&current!=='queued'&&<div role="progressbar" aria-label={`${heading} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={fraction===null?undefined:Math.floor(fraction*100)} aria-valuetext={fraction===null?'Progress percentage unavailable':`${Math.floor(fraction*100)} percent of current phase`}/>}
  {data?.detail&&<p className="queue-activity">{data.detail}</p>}
  {step&&step.total>0&&!stopped&&<p>Step {step.current} / {step.total}</p>}
  {job.result.elapsed_seconds!==undefined&&<p>{duration(job.result.elapsed_seconds)} elapsed</p>}
  {data?.phase_started_at!==undefined&&!stopped&&<p>{duration(now-data.phase_started_at)} in this phase</p>}
  {!stopped&&<p className="queue-contact" role="status">{!connected?'Connection lost — reconnecting; job may still be running.':stale?'No recent process/provider contact.':lastContact!==undefined?'Process/provider contact received.':fraction===null&&current!=='queued'?'Working — percentage unavailable.':current==='queued'?'Waiting to start.':'Receiving job status.'}{connected&&lastActivity!==undefined&&lastActivity>=15?` Last reported activity ${duration(lastActivity)} ago.`:''}</p>}
  <p className="queue-sequence-note">Segments show stages, not time remaining.</p>
 </section>;
}
