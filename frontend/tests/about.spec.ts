import {test,expect} from '@playwright/test';

test('About credits, searchable notices, downloads, and return to unsaved editor',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  await expect(page.getByRole('heading',{name:'About this project',exact:true})).toBeFocused();
  await expect(page.getByRole('heading',{name:'Foundation credits'})).toBeVisible();
  await expect(page.getByText('GNU GPL version 3 or later', {exact:false})).toBeVisible();
  const inventory=await (await page.request.get('/credits/components.json')).json();
  if(inventory.runtime==='native-windows')await expect(page.getByText('Standalone Windows runtime',{exact:true})).toBeVisible();
  else await expect(page.getByText('RSALv2 or SSPLv1',{exact:true})).toBeVisible();
  await expect(page.getByRole('status')).toContainText('matching records');
  await page.getByRole('searchbox',{name:'Search components'}).fill('react');
  await page.getByLabel('Component group').selectOption('JavaScript');
  const row=page.getByRole('row').filter({has:page.getByRole('link',{name:'react ↗',exact:true})});
  await expect(row).toContainText('19.1.0');
  await expect(row).toContainText('MIT');
  await row.getByText('Read copyright & license notice').click();
  await expect(row.locator('pre')).toContainText('Permission is hereby granted');
  for(const path of ['LICENSE.txt','NOTICE.txt','components.json','notices.json']){
    const response=await page.request.get(`/credits/${path}`);
    expect(response.ok()).toBeTruthy();
    expect(response.headers()['content-type']).not.toContain('text/html');
  }
  const download=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download component inventory'}).click();
  expect((await download).suggestedFilename()).toBe('components.json');
  await page.getByRole('searchbox',{name:'Search components'}).fill('no-such-package-xyz');
  await expect(page.getByText('No components match your search.')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'About this project',exact:true})).toBeFocused();
  await page.getByRole('button',{name:'New project'}).click();
  await page.getByLabel('Script',{exact:true}).fill('Keep this unsaved script.');
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('heading',{name:'About this project',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/about-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Back to workspace'}).click();
  await expect(page.getByLabel('Script',{exact:true})).toHaveValue('Keep this unsaved script.');
});
