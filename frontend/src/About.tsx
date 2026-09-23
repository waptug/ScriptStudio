import {ThemeToggle} from './ThemeToggle';
import {ReplicationPrompt} from './ReplicationPrompt';
import {useEffect, useRef, useState} from 'react';

type Component = {name:string;version:string;group:string;license:string;url:string;role:string;evidence?:string;notice?:string};
type Inventory = {runtime?:string;scope:string;components:Component[]};
let notices:Promise<Record<string,string>>|undefined;
function LicenseNotice({id}:{id:string}) {
  const [text,setText]=useState(''),[error,setError]=useState('');
  async function load(open:boolean) {
    if(!open||text)return;
    try {
      notices??=fetch('/credits/notices.json').then(async response=>{
        if(!response.ok)throw Error('Could not load license notices.');
        return response.json();
      }).catch(error=>{notices=undefined;throw error;});
      const all=await notices;
      if(!all[id])throw Error('This notice is unavailable.');
      setText(all[id]);setError('');
    } catch(e){setError((e as Error).message);}
  }
  return <details onToggle={e=>void load(e.currentTarget.open)}><summary>Read copyright & license notice</summary>{error?<p role="alert">{error} <button onClick={()=>void load(true)}>Retry notice</button></p>:<pre>{text||'Loading notice…'}</pre>}</details>;
}
const foundations = [
  {name:'OpenShot',credit:'OpenShot developers & contributors',role:'The visual foundation: libopenshot composes frames, animates clips, and creates editable native project handoffs.',license:'libopenshot: LGPL-3.0-or-later · desktop editor: GPL-3.0-or-later',url:'https://www.openshot.org/libopenshot/'},
  {name:'FFmpeg',credit:'The FFmpeg community',role:'Media inspection, normalization, audio mixing, and final video encoding.',license:'GPL build; the installed package and component-specific notices are listed below.',url:'https://ffmpeg.org/legal.html'},
  {name:'React & TypeScript',credit:'Meta, Microsoft & open-source contributors',role:'The interactive editor, timeline controls, and typed browser interface. Vite builds the frontend.',license:'React & Vite: MIT · TypeScript: Apache-2.0',url:'https://github.com/facebook/react/blob/main/LICENSE'},
  {name:'Python & FastAPI',credit:'Python Software Foundation & Python package maintainers',role:'The API and services, with Pydantic validation, SQLAlchemy, Alembic, and Psycopg.',license:'Python: PSF-2.0 · FastAPI: MIT · package-specific terms below',url:'https://docs.python.org/3.12/license.html'},
  {name:'PostgreSQL & job workers',credit:'PostgreSQL Global Development Group & Celery contributors',role:'Durable projects and job state. Linux uses Celery; standalone Windows uses a native PostgreSQL polling worker.',license:'PostgreSQL License · Celery: BSD-3-Clause',url:'https://www.postgresql.org/about/licence/'},
  {name:'Qt, PyQt5 & eSpeak NG',credit:'Qt, Riverbank Computing & eSpeak NG contributors',role:'Native rendering support, text overlays, and local demo narration. DejaVu fonts supply the render typefaces.',license:'Qt: module-specific LGPL/GPL · PyQt5: GPL v3 distribution · eSpeak NG: GPL-3.0-or-later · fonts: see notices',url:'https://www.riverbankcomputing.com/software/pyqt/intro'},
];

export function About({onClose}:{onClose:()=>void}) {
  const [inventory,setInventory]=useState<Inventory|null>(null),[error,setError]=useState('');
  const [query,setQuery]=useState(''),[group,setGroup]=useState('All components'),[limit,setLimit]=useState(40);
  const heading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{
    heading.current?.focus();
    const controller=new AbortController();
    fetch('/credits/components.json',{signal:controller.signal}).then(async r=>{
      if(!r.ok)throw Error('Component inventory could not be loaded.');
      setInventory(await r.json());
    }).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return()=>controller.abort();
  },[]);
  useEffect(()=>{const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')onClose();};window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);},[onClose]);
  const rows=inventory?.components.filter(c=>(group==='All components'||c.group===group)&&`${c.name} ${c.license} ${c.role}`.toLowerCase().includes(query.toLowerCase()))||[];
  const groups=[...new Set(inventory?.components.map(c=>c.group)||[])];
  return <div className="dashboard about">
    <header><strong className="brand"><img className="brand-logo" src="/logo.svg" alt="" width="32" height="32"/>ScriptStudio</strong><span className="spacer"/><ThemeToggle/><button onClick={onClose}>Back to workspace</button></header>
    <main>
      <div className="eyebrow">BUILT ON SHARED WORK</div>
      <h1 tabIndex={-1} ref={heading}>About this project</h1>
      <p className="lead">From a written idea to an editable film, powered by the work of open-source communities.</p>
      <section className="about-license" aria-labelledby="project-license">
        <div><span className="badge">SCRIPTSTUDIO · 0.1.0</span><h2 id="project-license">Free software. A shared foundation.</h2>
        <p>ScriptStudio is a local script-to-video workspace created by ScriptStudio contributors. Copyright 2026 ScriptStudio contributors. Its source is licensed under <strong>GNU GPL version 3 or later (GPL-3.0-or-later)</strong>.</p>
        <p>Third-party components retain their own copyrights and licenses. The project license does not replace those terms.</p></div>
        <div className="about-links"><a href="/credits/LICENSE.txt" target="_blank" rel="noreferrer">Read the project license ↗</a><a href="/credits/NOTICE.txt" target="_blank" rel="noreferrer">Read third-party notices ↗</a><a href="/credits/components.json" download>Download component inventory ↓</a><a href="/credits/notices.json" download>Download collected license texts ↓</a></div>
      </section>
      <p className="about-brand-downloads">ScriptStudio brand assets: <a href="/logo.svg" download>Download SVG logo</a> · <a href="/favicon.ico" download>Download ICO icon</a></p>
      <section aria-labelledby="user-documentation"><h2 id="user-documentation">User documentation</h2><p>Learn the complete workflow, troubleshoot generation, or read setup and project details.</p><div className="about-links"><a href="/user-manual.html" target="_blank" rel="noreferrer">Read the user manual ↗</a><a href="/ScriptStudio-User-Manual.docx" download>Download user manual (.docx) ↓</a><a href="/README.html" target="_blank" rel="noreferrer">Read the README ↗</a><a href="/README.md" download>Download README.md ↓</a></div></section>
      <ReplicationPrompt/>
      <section aria-labelledby="foundation-credits"><h2 id="foundation-credits">Foundation credits</h2><p>Thank you to the maintainers, designers, translators, testers, and contributors who make these tools possible.</p>
      <div className="foundation-grid">{foundations.map(f=><article className="foundation-card" key={f.name}><h3><a href={f.url} target="_blank" rel="noreferrer">{f.name} ↗</a></h3><small>{f.credit}</small><p>{f.role}</p><p className="foundation-license">{f.license}</p></article>)}</div></section>
      <section className="about-context" aria-labelledby="license-boundaries"><h2 id="license-boundaries">Other tools & license boundaries</h2>
        {inventory?.runtime==='native-windows'?<p><strong>Standalone Windows runtime</strong> bundles Python, PostgreSQL, OpenShot, FFmpeg, and offline speech. A native worker polls durable PostgreSQL jobs. <a href="/credits/native-files.json" download>Download runtime file checksums</a>.</p>:<><p><strong>Redis server 7.4.2</strong> runs separately for job wakeups and is source-available under <a href="https://redis.io/legal/licenses/" target="_blank" rel="noreferrer">RSALv2 or SSPLv1</a>. It is not listed here as an OSI-approved open-source release. The Python Redis client has its own MIT license.</p>
        <p><strong>nginx, Debian, Alpine Linux, Node.js, and container tooling</strong> support delivery and development. Their packages, versions, and notices appear in the inventory below.</p></>}
        <p><strong>Ollama and OpenShot desktop</strong> are optional external tools. Ollama software is MIT-licensed; model weights have their own licenses. Runway, ElevenLabs, and Suno are proprietary service integrations, not open-source dependencies; their account and content terms apply separately. Suno generation is not enabled.</p>
        <p>Project names and marks identify their respective owners. No affiliation or endorsement is implied.</p>
      </section>
      <section aria-labelledby="component-inventory"><h2 id="component-inventory">Components & licenses</h2>
        <p>Search direct and transitive dependencies, build and test tools, container packages, and the available full copyright notices. License labels are package metadata; expand a notice for its terms.</p>
        {inventory&&<details className="inventory-scope"><summary>Inventory scope & provenance</summary><p>{inventory.scope}</p><p>This is a snapshot of the packaged build. Refresh it after dependency or image changes using the repository’s credits generator. A missing embedded notice is identified explicitly; upstream links and installed package notices remain available.</p></details>}
        <div className="about-filters"><label>Search components<input type="search" value={query} onChange={e=>{setQuery(e.target.value);setLimit(40);}} placeholder="Name, license, or purpose"/></label><label>Component group<select value={group} onChange={e=>{setGroup(e.target.value);setLimit(40);}}><option>All components</option>{groups.map(g=><option key={g}>{g}</option>)}</select></label></div>
        {error?<p role="alert">{error} <a href="/credits/components.json">Open inventory directly</a></p>:!inventory?<p role="status">Loading component inventory…</p>:<>
          <p role="status">{rows.length} matching records · {inventory.components.length} total</p>
          <div className="component-table"><table><caption>Component versions, licenses, and notices</caption><thead><tr><th scope="col">Component</th><th scope="col">License & notice</th></tr></thead><tbody>{rows.slice(0,limit).map((c,i)=><tr key={`${c.group}-${c.name}-${i}`}><td><a href={c.url} target="_blank" rel="noreferrer">{c.name} ↗</a><span>{c.version}</span><small>{c.group} · {c.role}</small></td><td><strong>{c.license}</strong>{c.notice?<LicenseNotice id={c.notice}/>:<p className="muted">Full notice not embedded; see the upstream license or installed distribution.</p>}{c.evidence&&<small>{c.evidence}</small>}</td></tr>)}</tbody></table></div>
          {!rows.length&&<p>No components match your search.</p>}
          {rows.length>limit&&<button onClick={()=>setLimit(limit+40)}>Show more components</button>}
        </>}
      </section>
    </main>
  </div>;
}
