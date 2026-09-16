import {useEffect, useState} from 'react';

type Theme = 'dark' | 'light';
const storageKey = 'scriptstudio-theme';

export function ThemeToggle() {
  const [theme,setTheme] = useState<Theme>(()=>document.documentElement.dataset.theme==='light'?'light':'dark');
  function apply(next:Theme) {
    document.documentElement.dataset.theme=next;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content',next==='light'?'#f4f6f3':'#101419');
    setTheme(next);
  }
  useEffect(()=>{
    const sync=(event:StorageEvent)=>{
      if(event.key===storageKey||event.key===null)apply(event.newValue==='light'?'light':'dark');
    };
    window.addEventListener('storage',sync);
    return()=>window.removeEventListener('storage',sync);
  },[]);
  function toggle() {
    const next=theme==='dark'?'light':'dark';
    apply(next);
    try {localStorage.setItem(storageKey,next);} catch { /* Keep working for this visit. */ }
  }
  return <button className="theme-toggle" onClick={toggle} aria-label={`Switch to ${theme==='dark'?'light':'dark'} mode`} title={`Switch to ${theme==='dark'?'light':'dark'} mode`}>
    <span aria-hidden="true">{theme==='dark'?'☀':'☾'}</span> {theme==='dark'?'Light mode':'Dark mode'}
  </button>;
}
