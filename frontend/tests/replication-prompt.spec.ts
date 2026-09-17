import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('About displays, copies, and downloads the same complete goal prompt',async({page,context})=>{
  await page.goto('/');
  await context.grantPermissions(['clipboard-read','clipboard-write'],{origin:new URL(page.url()).origin});
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  const section=page.getByRole('region',{name:'Recreate ScriptStudio with Codex'});
  const response=await page.request.get('/codex-goal.txt');
  expect(response.ok()).toBeTruthy();
  expect(response.headers()['content-type']).toContain('text/plain');
  const prompt=await response.text();
  expect(prompt).toMatch(/^\/goal Recreate ScriptStudio/);
  for(const requirement of ['USD 0','PostgreSQL','FrameMapper','Light mode','GPL-3.0-or-later','ACCEPTANCE AND EVIDENCE'])expect(prompt).toContain(requirement);
  await section.getByText('Read the complete replication prompt',{exact:true}).click();
  await expect(section.getByRole('textbox')).toHaveValue(prompt);
  await section.getByRole('button',{name:'Copy /goal prompt',exact:true}).click();
  await expect(section.getByRole('status')).toContainText('Goal prompt copied');
  // Windows clipboard text convention is CRLF; compare the complete text after newline normalization.
  expect((await page.evaluate(()=>navigator.clipboard.readText())).replace(/\r\n/g,'\n')).toBe(prompt);
  const pending=page.waitForEvent('download');
  await section.getByRole('link',{name:'Download prompt (.txt)',exact:true}).click();
  const download=await pending;
  expect(download.suggestedFilename()).toBe('ScriptStudio-codex-goal.txt');
  expect(await readFile((await download.path())!,'utf8')).toBe(prompt);
});

test('clipboard denial selects the prompt for manual copying',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async()=>{throw new Error('Clipboard denied');}}}));
  await page.goto('/');
  await page.getByRole('button',{name:'About this project',exact:true}).click();
  const section=page.getByRole('region',{name:'Recreate ScriptStudio with Codex'});
  await section.getByRole('button',{name:'Copy /goal prompt',exact:true}).click();
  await expect(section.getByRole('status')).toContainText('Automatic copying is unavailable');
  const text=section.getByRole('textbox');
  await expect(text).toBeFocused();
  expect(await text.evaluate((element:HTMLTextAreaElement)=>element.selectionStart===0&&element.selectionEnd===element.value.length&&element.value.startsWith('/goal '))).toBeTruthy();
});
