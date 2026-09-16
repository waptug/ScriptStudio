// Rasterize the canonical SVG with Chromium and package PNG frames into an ICO.
// Uses the existing frontend Playwright dependency; no image/font dependency.
import {readFile,writeFile} from 'node:fs/promises';
import {chromium} from '../frontend/node_modules/playwright/index.mjs';

const root=new URL('../frontend/public/',import.meta.url);
const svg=await readFile(new URL('logo.svg',root),'utf8');
const sizes=[16,24,32,48,64,128,256];
const browser=await chromium.launch({headless:true});
try {
  const page=await browser.newPage();
  const frames=await page.evaluate(async({svg,sizes})=>{
    const image=new Image();
    image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
    await image.decode();
    return sizes.map(size=>{
      const canvas=document.createElement('canvas');
      canvas.width=canvas.height=size;
      const context=canvas.getContext('2d');
      context.drawImage(image,0,0,size,size);
      return canvas.toDataURL('image/png').split(',')[1];
    });
  },{svg,sizes});
  const header=Buffer.alloc(6+16*sizes.length);
  header.writeUInt16LE(1,2);
  header.writeUInt16LE(sizes.length,4);
  const images=frames.map(frame=>Buffer.from(frame,'base64'));
  let offset=header.length;
  images.forEach((image,index)=>{
    const entry=6+16*index;
    header[entry]=header[entry+1]=sizes[index]===256?0:sizes[index];
    header.writeUInt16LE(1,entry+4);
    header.writeUInt16LE(32,entry+6);
    header.writeUInt32LE(image.length,entry+8);
    header.writeUInt32LE(offset,entry+12);
    offset+=image.length;
  });
  await writeFile(new URL('favicon.ico',root),Buffer.concat([header,...images]));
  console.log(`Generated favicon.ico: ${sizes.join(', ')} pixel frames from logo.svg`);
} finally {
  await browser.close();
}
