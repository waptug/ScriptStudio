import {useEffect, useRef, useState} from 'react';

export function ReplicationPrompt() {
  const [prompt,setPrompt]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [open,setOpen]=useState(false),[attempt,setAttempt]=useState(0);
  const text=useRef<HTMLTextAreaElement>(null);
  useEffect(()=>{
    const controller=new AbortController();
    setError('');
    fetch('/codex-goal.txt',{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw Error('The replication prompt could not be loaded.');
      const value=await response.text();
      if(!value.startsWith('/goal '))throw Error('The replication prompt is unavailable.');
      setPrompt(value);
    }).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return()=>controller.abort();
  },[attempt]);
  function select() {
    setOpen(true);
    requestAnimationFrame(()=>{text.current?.focus();text.current?.select();});
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(prompt);
      setNotice('Goal prompt copied. Paste it into Codex in your chosen workspace.');
    } catch {
      select();
      setNotice('Automatic copying is unavailable. The prompt is selected; press Ctrl+C or ⌘C, or download the text file.');
    }
  }
  return <section className="replication-prompt" aria-labelledby="replication-title">
    <h2 id="replication-title">Recreate ScriptStudio with Codex</h2>
    <p>A self-contained <code>/goal</code> prompt covering the application, architecture, provider safeguards, editor, branding, themes, credits, and acceptance checks. Open Codex in the workspace where you want to build, then paste the complete prompt.</p>
    <p>This is a specification for a functional recreation, not a byte-for-byte copy. Copying or downloading it does not start a build. See <a href="https://learn.chatgpt.com/use-cases/follow-goals" target="_blank" rel="noreferrer">OpenAI’s guide to goals ↗</a> for command availability and usage.</p>
    <div className="prompt-actions"><button disabled={!prompt} onClick={()=>void copy()}>Copy /goal prompt</button><button disabled={!prompt} onClick={select}>Select prompt</button><a href="/codex-goal.txt" download="ScriptStudio-codex-goal.txt">Download prompt (.txt)</a></div>
    {error?<p role="alert">{error} <button onClick={()=>setAttempt(attempt+1)}>Retry prompt</button></p>:!prompt?<p>Loading prompt…</p>:null}
    {notice&&<p role="status">{notice}</p>}
    <details open={open} onToggle={e=>setOpen(e.currentTarget.open)}><summary>Read the complete replication prompt</summary><textarea ref={text} aria-label="Codex replication goal prompt" value={prompt} readOnly spellCheck={false}/></details>
  </section>;
}
