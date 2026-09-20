import {useState} from 'react';
export function ClipName({name,busy,onRename}:{name:string;busy:boolean;onRename:(name:string)=>Promise<void>}){
 const [editing,setEditing]=useState(false),[value,setValue]=useState(name);
 return editing?<form className="clip-name" onSubmit={async e=>{e.preventDefault();if(!value.trim())return;try{await onRename(value.trim());setEditing(false);}catch{/* parent displays save error */}}}><label>Clip name<input aria-label="Clip name" autoFocus maxLength={200} value={value} onChange={e=>setValue(e.target.value)}/></label><button disabled={busy||!value.trim()}>Save name</button><button type="button" disabled={busy} onClick={()=>setEditing(false)}>Cancel</button></form>:<div className="clip-name"><strong>{name}</strong><button disabled={busy} onClick={()=>{setValue(name);setEditing(true);}}>Rename clip</button></div>;
}
