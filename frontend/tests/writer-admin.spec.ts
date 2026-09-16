import {test,expect} from '@playwright/test';

test('admin model selection and reviewable AI script without overwriting manual writing',async({page})=>{
  // Fixed model output makes this browser contract deterministic. Live local inference
  // is verified separately through the actual draft endpoint.
  const original=await (await page.request.get('/api/admin/settings')).json();
  try {
  await page.route('**/api/admin/ollama-models',route=>route.fulfill({json:{models:['gemma3:4b','qwen3:8b']}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Models & credentials'})).toBeVisible();
  await page.getByLabel('Local Ollama server URL').fill('http://host.docker.internal:11434');
  await page.getByRole('button',{name:'List installed models'}).click();
  await expect(page.getByRole('status')).toContainText('Found 2');
  await page.getByLabel('Script writing model',{exact:true}).fill('gemma3:4b');
  await page.getByLabel('Scene planning model',{exact:true}).fill('gemma3:4b');
  await page.getByRole('button',{name:'Save admin settings'}).click();
  await expect(page.getByRole('status')).toContainText('Admin settings saved');
  await page.reload();
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await expect(page.getByLabel('Script writing model',{exact:true})).toHaveValue('gemma3:4b');
  await expect(page.getByLabel('Runway API key',{exact:true})).toHaveValue('');
  await page.getByRole('button',{name:'Back to workspace'}).click();
  await page.getByRole('button',{name:'New project'}).click();
  await page.getByLabel('Script',{exact:true}).fill('My original manual script.');
  await page.getByRole('button',{name:'Write with AI',exact:true}).click();
  await page.getByLabel('Video idea').fill('A tour of a small garden');
  await page.route('**/api/projects/*/script-draft',async route=>{
    await route.fulfill({json:{script:'[A garden] Small gardens bring big possibilities.',model:'gemma3:4b',estimated_seconds:30}});
  });
  await page.getByRole('button',{name:'Generate script',exact:true}).click();
  await expect(page.getByLabel('Generated script',{exact:true})).toHaveValue(/Small gardens/);
  await expect(page.getByLabel('Script',{exact:true})).toHaveValue('My original manual script.');
  await page.getByLabel('Generated script',{exact:true}).fill('[A garden] My reviewed AI draft.');
  await page.getByRole('button',{name:'Replace script with this draft'}).click();
  await expect(page.getByLabel('Script',{exact:true})).toHaveValue('[A garden] My reviewed AI draft.');
  await page.getByRole('button',{name:'Save script',exact:true}).click();
  await page.getByRole('button',{name:'Plan scenes & shots'}).click();
  await expect(page.getByRole('heading',{name:/Storyboard/})).toBeVisible();
  await page.getByRole('button',{name:'Script',exact:true}).click();
  await expect(page.getByLabel('Video idea')).toHaveValue('A tour of a small garden');
  await expect(page.getByLabel('Generated script',{exact:true})).toHaveValue('[A garden] My reviewed AI draft.');
  await page.screenshot({path:'test-results/script-writer.png',fullPage:true});
  } finally {await page.request.put('/api/admin/settings',{data:{values:original.values}});}
});
