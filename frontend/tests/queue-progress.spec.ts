import {test,expect} from '@playwright/test';

test('queue shows colored completed, current and remaining phases without new API fields',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
 await page.addInitScript(()=>{
  (window as any).EventSource=class{
   onopen:any;onerror:any;handler:any;
   constructor(){(window as any).queueStream=this;setTimeout(()=>this.onopen?.(),0);}
   addEventListener(_name:string,handler:any){this.handler=handler;}
   close(){}
  };
 });
 const settings={width:1280,height:720,fps_num:24,fps_den:1,aspect:'landscape',target_duration:5,spending_limit:0,video_provider:'wan',voice_provider:'kokoro',voice_id:'af_heart',voice_settings:{},reference_assets:[]};
 const job:any={id:'wan-job',kind:'video',provider:'wan',state:'loading',progress:0,estimated_cost:0,attempts:1,inputs:{},result:{elapsed_seconds:751}};
 const project:any={id:'queue-fixture',name:'Queue fixture',script:'A quiet park.',settings,revision:1,script_revision:1,storyboard:{scenes:[]},assets:[],jobs:[job],timeline:{items:[]},reserved_cost:0,undo:[],redo:[]};
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/projects')return route.fulfill({json:[project]});
  if(path==='/api/projects/queue-fixture')return route.fulfill({json:project});
  if(path==='/api/providers')return route.fulfill({json:{paid_generation:{enabled:false},local_models:[]}});
  if(path==='/api/admin/ollama-discover')return route.fulfill({json:{status:'unavailable',models:[],configured_url:''}});
  if(path==='/api/script-analysis')return route.fulfill({json:{word_count:3,estimated_seconds:2}});
  return route.fulfill({json:{configured:false}});
 });
 await page.goto('/');await page.getByRole('button',{name:/Queue fixture/}).click();
 await page.locator('.inspector-panel').getByRole('button',{name:/^Queue/}).click();
 const bar=page.getByRole('region',{name:'video job phases'});
 await expect(bar.getByLabel('1. Queued: completed',{exact:true})).toBeVisible();
 await expect(bar.getByLabel('2. Load model: current',{exact:true})).toHaveCSS('outline-color','rgb(37, 99, 235)');
 await expect(bar.getByLabel('3. Generate: remaining',{exact:true})).toBeVisible();
 await expect(bar.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow');
 await expect(bar).toContainText('12m 31s elapsed');
 async function emit(){await page.evaluate(p=>(window as any).queueStream.handler({data:JSON.stringify(p)}),project);}
 job.state='generating';job.progress=19/30;job.result.steps={current:19,total:30};await emit();
 await expect(bar.getByLabel('2. Load model: completed',{exact:true})).toBeVisible();
 await expect(bar.getByLabel('3. Generate: current',{exact:true})).toHaveCSS('outline-color','rgb(124, 58, 237)');
 await expect(bar.getByRole('progressbar')).toHaveAttribute('aria-valuenow','63');
 await expect(bar).toContainText('Step 19 / 30');
 await page.evaluate(()=>(window as any).queueStream.onerror());
 await expect(bar).toContainText('Connection lost');
 await expect(bar.locator('.indeterminate')).toHaveCount(0);
 await page.evaluate(()=>(window as any).queueStream.onopen());
 job.state='validating';job.result={elapsed_seconds:900};await emit();
 await expect(bar.getByLabel('5. Check: current',{exact:true})).toBeVisible();
 job.state='ready';await emit();await expect(bar.locator('.completed')).toHaveCount(6);
 job.state='failed';job.result={};await emit();await expect(bar.locator('.completed')).toHaveCount(0);
 await expect(bar).toContainText('Failed');
 job.state='loading';job.result={queue_progress:{phases:['queued','prepare','generate','transfer','validate','ready'],completed:['queued'],phase:'prepare',fraction:null,detail:'Checkpoint 2 / 5',phase_started_at:Date.now()/1000-80,last_activity_at:Date.now()/1000-20,last_contact_at:Date.now()/1000}};await emit();
 await expect(bar).toContainText('Checkpoint 2 / 5');await expect(bar).toContainText('Last reported activity');
 await page.emulateMedia({reducedMotion:'reduce'});expect(await bar.locator('.indeterminate').evaluate(e=>getComputedStyle(e,'::before').animationName)).toBe('none');
 await page.getByRole('button',{name:'Switch to light mode'}).click();
 await expect(bar).toBeVisible();
 await page.screenshot({path:'test-results/queue-progress-light.png',fullPage:true});
 job.state='canceled';await emit();await expect(bar.locator('.stopped')).toHaveCount(1);await expect(bar).toContainText('Canceled');
 job.state='submission_outcome_unknown';await emit();await expect(bar).toContainText('Needs attention');
 expect(errors).toEqual([]);
});
