import {useEffect,useState} from 'react';

type Analysis={word_count:number;estimated_seconds:number;unclosed_direction:boolean};

export function ScriptEstimate({script}:{script:string}){
 const [result,setResult]=useState<{script:string;analysis?:Analysis;error?:boolean}|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  const timer=setTimeout(async()=>{
   try{
    const response=await fetch('/api/script-analysis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({script}),signal:controller.signal});
    if(!response.ok)throw Error('Speech estimate unavailable');
    const analysis:Analysis=await response.json();
    if(!controller.signal.aborted)setResult({script,analysis});
   }catch{
    if(!controller.signal.aborted)setResult({script,error:true});
   }
  },150);
  return()=>{clearTimeout(timer);controller.abort();};
 },[script]);
 const current=result?.script===script?result:null;
 return <div aria-label="Speech estimate" aria-live="polite">
  {current?.analysis?<><div className="row muted"><span>{current.analysis.word_count} spoken words</span><span>~{current.analysis.estimated_seconds} seconds of speech</span></div>
   {current.analysis.unclosed_direction&&<p role="status">Close the unfinished [visual direction]. Its text is excluded from speech.</p>}</>
   :<p className="muted">{current?.error?'Speech estimate unavailable.':'Calculating speech…'}</p>}
 </div>;
}
