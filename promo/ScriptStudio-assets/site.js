'use strict';
const viewer=document.querySelector('dialog');
const viewerImage=document.querySelector('#viewer-image');
document.querySelectorAll('[data-image]').forEach(button=>button.addEventListener('click',()=>{viewerImage.src=button.dataset.image;viewerImage.alt=button.querySelector('img').alt;document.querySelector('#viewer-caption').textContent=viewerImage.alt;viewer.showModal();}));
document.querySelector('.close').addEventListener('click',()=>viewer.close());
viewer.addEventListener('click',event=>{if(event.target===viewer){const r=viewer.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)viewer.close();}});

const socialStatus=document.querySelector('.social-status');
const copyButton=document.querySelector('.copy-link');
if(navigator.clipboard&&window.isSecureContext){copyButton.hidden=false;copyButton.addEventListener('click',async()=>{try{await navigator.clipboard.writeText('https://geekstreaming.com/ScriptStudio.html?utm_source=copy_link&utm_medium=referral&utm_campaign=scriptstudio&utm_content=copy_link');socialStatus.textContent='Link copied. Ready to share!';document.dispatchEvent(new Event('scriptstudio:link-copied'));}catch{socialStatus.textContent='Copy this link: https://geekstreaming.com/ScriptStudio.html?utm_source=copy_link&utm_medium=referral&utm_campaign=scriptstudio&utm_content=copy_link';}});}
