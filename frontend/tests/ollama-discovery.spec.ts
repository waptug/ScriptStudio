import {test,expect} from '@playwright/test';

test('automatically populates detected URL and installed models',async({page})=>{
  const config=await (await page.request.get('/api/admin/settings')).json();
  config.values.OLLAMA_URL='';
  await page.route('**/api/admin/settings',r=>r.fulfill({json:config}));
  await page.route('**/api/admin/ollama-discover',r=>r.fulfill({json:{status:'found',url:'http://127.0.0.1:11434',configured_url:'http://127.0.0.1:11434',saved:true,models:['local:4b']}}));
  await page.goto('/');
  await expect(page.getByLabel('Local AI setup')).toContainText('Ollama found');
  await page.getByRole('button',{name:'Configure local AI'}).click();
  await expect(page.getByLabel('Local Ollama server URL')).toHaveValue('http://127.0.0.1:11434');
  await expect(page.locator('#local-models option')).toHaveAttribute('value','local:4b');
});

test('missing Ollama shows install guidance and retry discovers an empty server',async({page})=>{
  let found=false;
  await page.route('**/api/admin/ollama-discover',r=>r.fulfill({json:{status:found?'found':'unavailable',url:found?'http://127.0.0.1:11434':'',configured_url:'',saved:found,models:[]}}));
  await page.goto('/');
  const setup=page.getByLabel('Local AI setup');
  await expect(setup.getByRole('alert')).toContainText('Ollama isn’t reachable');
  await expect(setup.getByRole('link',{name:'Install Ollama'})).toHaveAttribute('href','https://ollama.com/download');
  await page.screenshot({path:'test-results/ollama-setup.png',fullPage:true});
  found=true;await setup.getByRole('button',{name:'Check Ollama again'}).click();
  await expect(setup).toContainText('no local models are installed');
});
