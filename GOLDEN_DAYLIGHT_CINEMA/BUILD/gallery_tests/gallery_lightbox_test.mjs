import { JSDOM } from "jsdom";
import fs from "fs";
const html = fs.readFileSync(new URL("../../GALLERY/index.html", import.meta.url),"utf8");
const dom = new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/GALLERY/index.html"});
const {window}=dom, doc=window.document;
await new Promise(r=>setTimeout(r,300));
const ok=[],bad=[];
const t=(c,n)=>(c?ok:bad).push(n);

const lb=doc.getElementById("lb");
const body=doc.getElementById("lb-body");

// card notes rendered
const notes=doc.querySelectorAll(".card .note");
t(notes.length===8, `8 card notes rendered (${notes.length})`);
t(notes[0].textContent.includes("Bright buildings"), "note text reached the card");

// open, then tap the backdrop
doc.querySelector(".card .expand").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
t(lb.hasAttribute("open"),"lightbox open");
t(doc.body.style.position==="fixed","iOS scroll lock applied (body position:fixed)");
// click the backdrop itself
body.dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
t(!lb.hasAttribute("open"),"backdrop tap closes the lightbox");
t(doc.body.style.position==="","scroll lock released");
t(doc.body.style.top==="","body top offset cleared");

// reopening and tapping the image must NOT close
doc.querySelector(".card .expand").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
const img=body.querySelector("img");
if (img){ img.dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
  t(lb.hasAttribute("open"),"tapping the image does not close"); }
else bad.push("no image in lightbox to test");

// contact sheet viewer locks/unlocks too
window.document.dispatchEvent(new window.KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
t(doc.body.style.position==="","closed via Escape, lock released");
doc.getElementById("sheet-btn").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
t(doc.body.style.position==="fixed","contact sheet locks scroll");
window.document.dispatchEvent(new window.KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
t(doc.body.style.position==="","contact sheet unlock on close");

console.log(ok.map(x=>"  PASS  "+x).join("\n"));
if(bad.length) console.log(bad.map(x=>"  FAIL  "+x).join("\n"));
console.log(`\n${ok.length} passed, ${bad.length} failed`);
process.exit(bad.length?1:0);
