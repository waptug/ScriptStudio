import {test,expect} from '@playwright/test';

test('theme switches across the workspace, persists, and syncs between tabs',async({page,context})=>{
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  const light=page.getByRole('button',{name:'Switch to light mode',exact:true});
  await light.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await expect(page.locator('html')).toHaveCSS('background-color','rgb(244, 246, 243)');
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content','#f4f6f3');
  await page.reload();
  await expect(page.getByRole('button',{name:'Switch to dark mode',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'New project'}).click();
  await page.getByLabel('Script',{exact:true}).fill('My unsaved script survives theme changes.');
  await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
  await expect(page.getByLabel('Script',{exact:true})).toHaveValue('My unsaved script survives theme changes.');
  await page.getByRole('button',{name:'Switch to light mode',exact:true}).click();
  await expect(page.locator('.source-panel')).toHaveCSS('background-color','rgb(255, 255, 255)');
  await page.getByRole('button',{name:'＋ Title',exact:true}).click();
  await page.locator('.clip.title').click();
  await expect(page.locator('.clip.title')).toHaveCSS('background-color','rgb(244, 224, 201)');
  await page.screenshot({path:'test-results/theme-editor-light.png',fullPage:true});
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  await expect(page.getByRole('button',{name:'Switch to dark mode',exact:true})).toBeVisible();
  await page.screenshot({path:'test-results/theme-about-light.png'});
  await page.getByRole('button',{name:'Back to workspace'}).click();
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await expect(page.getByRole('button',{name:'Switch to dark mode',exact:true})).toBeVisible();
  await expect(page.locator('.admin-section').first()).toHaveCSS('background-color','rgb(255, 255, 255)');
  const second=await context.newPage();
  await second.goto('/');
  await expect(second.locator('html')).toHaveAttribute('data-theme','light');
  await second.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.getByRole('button',{name:'Switch to light mode',exact:true})).toBeVisible();
  await second.close();
});

test('theme remains usable when browser storage is unavailable',async({page})=>{
  await page.addInitScript(()=>{
    Storage.prototype.getItem=()=>{throw new DOMException('Storage blocked','SecurityError');};
    Storage.prototype.setItem=()=>{throw new DOMException('Storage blocked','SecurityError');};
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Switch to light mode',exact:true}).click();
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await expect(page.getByRole('button',{name:'Switch to dark mode',exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});
