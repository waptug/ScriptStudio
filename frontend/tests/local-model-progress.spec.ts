import {test,expect} from '@playwright/test';

test('installation shows stage progress, heartbeat, disconnection and persisted readiness',async({page})=>{
 page.setDefaultTimeout(15000);
 page.on('pageerror',error=>console.error(error.message));
 const now=Date.now()/1000;
 let model={id:'kokoro',name:'Kokoro-82M',kind:'narration',license:'Apache-2.0',url:'https://example.invalid',preset:'CPU',state:'not_installed',ready:false,supported:true,installable:true,progress:null as number|null,download_bytes:1024**3,installed_bytes:2*1024**3,guidance:'Install local model',phase:'preparing',detail:'',completed_bytes:0,total_bytes:null as number|null,heartbeat:now,started_at:now,progress_updated:now,cancel:false};
 let disconnected=false,requests=0;
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/admin/local-models'){
   if(disconnected)return route.fulfill({status:503,json:{detail:'Unavailable'}});
   return route.fulfill({json:{models:[model],hardware:{gpus:[],guidance:'CPU'}}});
  }
  if(path==='/api/admin/local-models/kokoro/install'){
   requests++;model={...model,state:'installing',detail:'Preparing files'};
   return route.fulfill({json:model});
  }
  if(path==='/api/admin/local-models/kokoro/cancel'){
   model={...model,cancel:true};return route.fulfill({json:model});
  }
  if(path==='/api/projects')return route.fulfill({json:[]});
  if(path==='/api/providers')return route.fulfill({json:{}});
  if(path==='/api/admin/ollama-discover')return route.fulfill({json:{status:'unavailable',models:[],configured_url:''}});
  return route.fulfill({json:{values:{},credentials:{RUNWAY_API_KEY:{configured:false},ELEVENLABS_API_KEY:{configured:false},HF_TOKEN:{configured:false}},paid_generation:{enabled:false},live_enabled:false}});
 });
 await page.goto('/');
 await page.getByRole('button',{name:'Admin',exact:true}).click();
 const card=page.locator('article').filter({has:page.getByRole('heading',{name:'Kokoro-82M · narration'})});
 await card.getByRole('button',{name:'Install',exact:true}).click();
 await expect(card.getByRole('progressbar')).not.toHaveAttribute('value');
 await expect(card).toContainText('Installer responding');
 model={...model,state:'downloading',phase:'downloading',detail:'model/weights.bin',progress:.25,completed_bytes:1024**3/4,total_bytes:1024**3};
 await expect(card.getByRole('progressbar')).toHaveAttribute('value','0.25',{timeout:8000});
 await expect(card).toContainText('25%');
 model={...model,state:'installing',phase:'extracting',detail:'runtime/torch.whl',progress:.6};
 await expect(card.getByRole('progressbar')).toHaveAccessibleName('Kokoro-82M: Unpacking runtime',{timeout:8000});
 await expect(card).toContainText('60%');
 model={...model,state:'verifying',phase:'probing',progress:null,total_bytes:null};
 await expect(card.getByRole('progressbar')).not.toHaveAttribute('value',{timeout:8000});
 model={...model,heartbeat:now-30,progress_updated:now-30};
 await expect(card).toContainText('No recent installer response',{timeout:8000});
 disconnected=true;
 await expect(card).toContainText('Connection lost',{timeout:8000});
 disconnected=false;model={...model,heartbeat:Date.now()/1000};
 await expect(card).toContainText('Installer responding',{timeout:8000});
 await card.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(card).toContainText('Cancel requested');
 model={...model,state:'ready',ready:true,phase:'complete',progress:1,cancel:false};
 await expect(card.getByRole('button',{name:'Installed',exact:true})).toBeDisabled({timeout:8000});
 await expect(card.getByRole('progressbar')).toHaveCount(0);
 await page.reload();await page.getByRole('button',{name:'Admin',exact:true}).click();
 await expect(card.getByRole('button',{name:'Installed',exact:true})).toBeDisabled();
 expect(requests).toBe(1);
});
