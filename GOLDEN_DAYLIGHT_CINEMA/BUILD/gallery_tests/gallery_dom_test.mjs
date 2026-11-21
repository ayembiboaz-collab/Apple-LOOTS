import { JSDOM } from "jsdom";
import fs from "fs";

const html = fs.readFileSync(new URL("../../GALLERY/index.html", import.meta.url),"utf8");
const fails = [], passes = [];
const ok  = (n,d="")=>passes.push(`${n}${d?" — "+d:""}`);
const bad = (n,d="")=>fails.push(`${n}${d?" — "+d:""}`);

const dom = new JSDOM(html, { runScripts:"dangerously", pretendToBeVisual:true,
                              url:"http://localhost:8080/GALLERY/index.html" });
const { window } = dom;
const doc = window.document;

// wait a tick for the IIFE
await new Promise(r=>setTimeout(r,300));

/* 1. cards built */
const cards = doc.querySelectorAll(".card");
cards.length === 8 ? ok("8 comparison cards built", `${cards.length}`)
                   : bad("expected 8 cards", `got ${cards.length}`);

/* 2. every image referenced exists on disk */
const imgs = [...doc.querySelectorAll("img")].map(i=>i.getAttribute("src"));
const missing = imgs.filter(s=>{
  // this file lives in BUILD/gallery_tests/, the document in GALLERY/,
  // so "img/x.jpg" resolves to ../../GALLERY/img/x.jpg
  const clean = s.replace(/^\.\//, "");
  return !fs.existsSync(new URL("../../GALLERY/" + clean, import.meta.url));
});
missing.length===0 ? ok("all <img> sources exist", `${imgs.length} checked`)
                   : bad("missing images", missing.join(", "));

/* 3. sliders initialised and respond to pointer + keyboard */
const first = cards[0];
const cmp = first.querySelector(".cmp");
const after = first.querySelector(".after");
const handle = first.querySelector(".handle");
after.style.clipPath && after.style.clipPath.includes("50") ? ok("slider initialised at 50%", after.style.clipPath)
                                                            : bad("slider not initialised", after.style.clipPath||"(empty)");
// jsdom lacks PointerEvent + getBoundingClientRect sizes, so drive via keyboard
cmp.dispatchEvent(new window.KeyboardEvent("keydown",{key:"ArrowRight",bubbles:true}));
after.style.clipPath.includes("54") ? ok("keyboard ArrowRight moves divider", after.style.clipPath)
                                    : bad("keyboard did not move divider", after.style.clipPath);
cmp.dispatchEvent(new window.KeyboardEvent("keydown",{key:"ArrowLeft",bubbles:true}));
cmp.dispatchEvent(new window.KeyboardEvent("keydown",{key:"ArrowLeft",bubbles:true}));
after.style.clipPath.includes("46") ? ok("keyboard ArrowLeft moves divider", after.style.clipPath)
                                    : bad("ArrowLeft failed", after.style.clipPath);
handle.style.left === after.style.clipPath ? ok("noop") : null;

/* 4. aria wiring */
cmp.getAttribute("role")==="slider" && cmp.hasAttribute("aria-valuenow")
  ? ok("comparison exposes slider role + aria-valuenow", cmp.getAttribute("aria-valuenow"))
  : bad("aria missing on comparison");

/* 5. lightbox opens, renders, navigates, toggles, closes */
const lb = doc.getElementById("lb");
const expand = first.querySelector(".expand");
expand.dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
lb.hasAttribute("open") ? ok("lightbox opens from EXPAND") : bad("lightbox did not open");
doc.getElementById("lb-body").innerHTML.includes("scene01_AFTER.jpg")
  ? ok("lightbox renders the AFTER layer") : bad("lightbox body empty");
doc.getElementById("lb-title").textContent.includes("1 / 8")
  ? ok("lightbox shows position", doc.getElementById("lb-title").textContent)
  : bad("lightbox position wrong", doc.getElementById("lb-title").textContent);

doc.getElementById("lb-next").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
doc.getElementById("lb-title").textContent.includes("2 / 8")
  ? ok("next scene works") : bad("next scene failed", doc.getElementById("lb-title").textContent);

doc.getElementById("lb-toggle").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
doc.getElementById("lb-body").innerHTML.includes("scene02_BEFORE.jpg")
  ? ok("toggle switches to BEFORE-only view") : bad("toggle view failed");

doc.getElementById("lb-range").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
doc.getElementById("lb-prev").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
doc.getElementById("lb-title").textContent.includes("1 / 8")
  ? ok("previous scene works") : bad("prev failed");

doc.dispatchEvent(new window.KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
!lb.hasAttribute("open") ? ok("Escape closes lightbox") : bad("Escape did not close");
doc.body.style.overflow==="" ? ok("scroll lock released on close") : bad("body still scroll-locked");

/* 6. contact sheet opens */
doc.getElementById("sheet-btn").dispatchEvent(new window.MouseEvent("click",{bubbles:true}));
lb.hasAttribute("open") && doc.getElementById("lb-body").innerHTML.includes("contact_sheet.jpg")
  ? ok("contact sheet opens full screen") : bad("contact sheet did not open");
window.document.dispatchEvent(new window.KeyboardEvent("keydown",{key:"Escape",bubbles:true}));

/* 7. download link resolves */
const dl = doc.getElementById("dl-lut").getAttribute("href");
fs.existsSync(new URL("../../LUT/" + dl.split("/").pop(), import.meta.url))
  ? ok("download link points at the real .cube", dl) : bad("download link broken", dl);
doc.getElementById("dl-lut").hasAttribute("download")
  ? ok("download attribute present") : bad("no download attribute");

/* 8. no duplicate ids */
const ids = [...doc.querySelectorAll("[id]")].map(e=>e.id);
(new Set(ids)).size===ids.length ? ok("no duplicate element ids", `${ids.length} ids`)
                                 : bad("duplicate ids");

/* 9. viewport + touch friendly declarations */
const vp = doc.querySelector('meta[name="viewport"]').content;
vp.includes("width=device-width") ? ok("viewport meta present") : bad("viewport meta missing");
const css = doc.querySelector("style").textContent;
/touch-action:\s*pan-y/.test(css) ? ok("vertical page scroll allowed over sliders (touch-action:pan-y)")
                      : bad("touch-action:pan-y missing");
/min-height:44px|min-height:52px/.test(css) ? ok("interactive targets >= 44px")
                                            : bad("targets too small for touch");
css.includes("aspect-ratio") ? ok("comparison keeps aspect ratio (no layout shift)")
                             : bad("no aspect ratio reserved");
css.includes("env(safe-area-inset") ? ok("safe-area insets respected") : bad("no safe-area insets");

console.log(passes.map(p=>"  PASS  "+p).join("\n"));
if (fails.length){ console.log("\n"+fails.map(f=>"  FAIL  "+f).join("\n")); }
console.log(`\n${passes.length} passed, ${fails.length} failed`);
process.exit(fails.length?1:0);
