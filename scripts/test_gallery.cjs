// JSDOM interaction smoke test; pass a path to an installed jsdom, no actual browser rendering.
const fs=require('fs'); const assert=require('assert');const {JSDOM}=require(process.argv[2] || 'jsdom');
const html=fs.readFileSync('GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html','utf8');
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost:8000/GALLERY/index.html',beforeParse(window){window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')}}});
const d=dom.window.document;assert.equal(d.querySelectorAll('.card').length,8);assert.equal(d.querySelectorAll('.card input[type=range]').length,8);
let first=d.querySelector('.comparison input');first.value='73';first.dispatchEvent(new dom.window.Event('input',{bubbles:true}));assert.equal(first.parentNode.style.getPropertyValue('--pos'),'73%');
d.querySelector('.open').click();assert(d.querySelector('dialog').hasAttribute('open'));assert(d.querySelector('#modal-title').textContent.includes('Harsh midday'));let modal=d.querySelector('#modal-content input');modal.value=21;modal.dispatchEvent(new dom.window.Event('input'));assert.equal(modal.parentNode.style.getPropertyValue('--pos'),'21%');d.querySelector('#close').click();assert(!d.querySelector('dialog').hasAttribute('open'));
console.log('PASS: 8 cards, slider events, modal open/close and modal slider (JSDOM, dialog shim; not a browser).');
