import {test,expect} from '@playwright/test';

test('admin paid generation switches save, reload, and show master override',async({page})=>{
  const config=await (await page.request.get('/api/admin/settings')).json();
  config.paid_generation={enabled:false,text:false,video:false,audio:false,speech:false,music:false};
  // Do not enable real paid workers while testing the Admin UI. API persistence and
  // enforcement are independently exercised against isolated databases in pytest.
  await page.route('**/api/admin/settings',async route=>{
    if(route.request().method()==='PUT'){
      const body=route.request().postDataJSON();
      expect(typeof body.paid_generation.enabled).toBe('boolean');
      config.paid_generation=body.paid_generation;
      config.live_enabled=body.paid_generation.enabled;
    }
    await route.fulfill({json:config});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  const master=page.getByRole('switch',{name:'Allow paid AI generation',exact:true});
  await expect(master).not.toBeChecked();
  await master.check();
  for(const type of ['text','video','audio','speech','music'])
    await page.getByRole('switch',{name:`Paid ${type} generation`,exact:true}).check();
  await page.getByRole('button',{name:'Save admin settings'}).click();
  await expect(page.getByRole('status').filter({hasText:'Admin settings saved'})).toContainText('Admin settings saved');
  await page.reload();
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await expect(master).toBeChecked();
  for(const type of ['text','video','audio','speech','music'])
    await expect(page.getByRole('switch',{name:`Paid ${type} generation`,exact:true})).toBeChecked();
  await master.uncheck();
  await page.getByRole('button',{name:'Save admin settings'}).click();
  await expect(page.getByRole('status').filter({hasText:'Admin settings saved'})).toContainText('Admin settings saved');
  expect(config.paid_generation.video).toBe(true);
  expect(config.paid_generation.enabled).toBe(false);
  await expect(page.locator('.admin-section').filter({has:page.getByRole('heading',{name:'Paid AI generation',exact:true})})).toContainText('Blocked.');
  await page.screenshot({path:'test-results/paid-permissions.png',fullPage:true});
});
