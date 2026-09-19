import {test,expect} from '@playwright/test';

test('speech estimates exclude visual notes and preserve saved writing',async({page})=>{
 const name='Speech estimate '+Date.now();
 await page.request.post('/api/projects',{data:{name,script:''}});
 await page.goto('/');
 await page.getByRole('button').filter({has:page.getByRole('heading',{name,exact:true})}).click();
 const script=page.getByLabel('Script',{exact:true});
 const estimate=page.getByLabel('Speech estimate');
 const park='[A man and woman on a summer park bench. [Wide shot]\n\nLeaves rustle.] Isn’t it just lovely out here today? Absolutely. This cool breeze is really refreshing.';
 await script.fill(park);
 await expect(estimate).toContainText('14 spoken words');
 await expect(estimate).toContainText('~6 seconds of speech');
 const saved=page.waitForResponse(r=>r.url().includes('/api/projects/')&&r.request().method()==='PUT');
 await page.getByRole('button',{name:'Save script',exact:true}).click();
 const project=await (await saved).json();
 await page.reload();
 await page.getByRole('button').filter({has:page.getByRole('heading',{name:project.name,exact:true})}).first().click();
 await expect(script).toHaveValue(park);
 await expect(estimate).toContainText('14 spoken words');
 await script.fill('[Visuals only [nested notes]]');
 await expect(estimate).toContainText('0 spoken words');
 await script.fill('Hello there. [A very long unfinished direction\n\nthat is still not speech');
 await expect(estimate).toContainText('2 spoken words');
 await expect(estimate.getByRole('status')).toContainText('unfinished');
 await script.fill('Read \\[this\\] aloud.');
 await expect(estimate).toContainText('3 spoken words');
 await script.fill('');
 await expect(estimate).toContainText('0 spoken words');
});

test('an old analysis response cannot replace the current estimate',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'New project'}).click();
 let release!:()=>void;
 const pending=new Promise<void>(resolve=>{release=resolve;});
 let started!:()=>void;
 const arrived=new Promise<void>(resolve=>{started=resolve;});
 await page.route('**/api/script-analysis',async route=>{
  if(route.request().postDataJSON().script==='Old words here.'){
   started();await pending;
   await route.fulfill({json:{word_count:999,estimated_seconds:999,unclosed_direction:false}}).catch(()=>{});
  }else await route.continue();
 });
 const script=page.getByLabel('Script',{exact:true});
 await script.fill('Old words here.');
 await arrived;
 await script.fill('[New visual] Latest speech.');
 await expect(page.getByLabel('Speech estimate')).toContainText('2 spoken words');
 release();
 await page.waitForTimeout(250);
 await expect(page.getByLabel('Speech estimate')).toContainText('2 spoken words');
});
