import {useEffect,useState} from 'react';
export type OllamaDiscovery={status:'found'|'unavailable';url:string;models:string[];saved:boolean;configured_url:string};
export async function discoverOllama():Promise<OllamaDiscovery>{
  const response=await fetch('/api/admin/ollama-discover',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  if(!response.ok)throw Error('Could not check Ollama. Try again or configure its URL in Admin.');
  return response.json();
}
export function OllamaGuidance({result}:{result:OllamaDiscovery}){
  if(result.status==='unavailable')return <span>Ollama isn’t reachable. <a href="https://ollama.com/download" target="_blank" rel="noreferrer">Install Ollama</a> if needed, open it on this computer, then check again. Local AI writing and planning need Ollama; manual writing and mock production remain available.</span>;
  if(!result.models.length)return <span>Ollama found at {result.url}, but no local models are installed. Download a local model in Ollama, then check again.</span>;
  return <span>Ollama found at {result.url} · {result.models.length} local models. {result.saved?'The server URL is configured. Choose your writing and planning models in Admin.':'Your saved URL was preserved. Use the detected URL in Admin to switch servers.'}</span>;
}
export function OllamaSetup({onConfigure,onDetected}:{onConfigure:()=>void;onDetected:()=>void}){
  const [result,setResult]=useState<OllamaDiscovery|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function check(){setBusy(true);setError('');try{const found=await discoverOllama();setResult(found);onDetected();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  useEffect(()=>{void check();},[]);
  return <aside className="note" aria-label="Local AI setup"><p role={result?.status==='unavailable'||error?'alert':'status'}>{busy?'Searching this host for Ollama…':error|| (result&&<OllamaGuidance result={result}/>)}</p><button disabled={busy} onClick={()=>void check()}>Check Ollama again</button> <button onClick={onConfigure}>Configure local AI</button></aside>;
}
