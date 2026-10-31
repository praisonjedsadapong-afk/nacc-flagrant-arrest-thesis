#!/usr/bin/env python3
"""แปลงไฟล์ร่าง HTML เป็นหน้าเว็บแบบเรียบ (docs/index.html)
ใช้: python3 -I tools/make_page.py draft/original.html docs/index.html
- ตัดแถบข้าง สคริปต์ ฟอนต์ภายนอก คลาสทั้งหมด
- ใส่ป้าย (รอตรวจสอบ) ตาม tools/pending.json
"""
import sys, re, json, pathlib
from bs4 import BeautifulSoup

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
cfg = json.loads((pathlib.Path(__file__).parent / "pending.json").read_text(encoding="utf-8"))
soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")
main = soup.find("main")

# ลบส่วนที่ไม่ใช้บนเว็บ
for sel in ["div.folio", "div.covgap", "div[class^=gap]"]:
    for t in main.select(sel): t.decompose()
toc = main.find(id="toc")
if toc: toc.decompose()
for t in main.find_all("colgroup"): t.decompose()
for t in main.select("a.back"): t.decompose()

def retag(el, name, prefix=None):
    el.name = name
    if prefix: el.insert(0, prefix)

for el in main.select("p.secheadctr"): retag(el, "h2")
for el in main.select("p.secheadl"): retag(el, "h3")
for el in main.select("h2.chtitle"):
    txt = " ".join(s.get_text(strip=True) for s in el.find_all("span"))
    el.clear(); el.string = txt
for el in main.select("div.fld"):
    lab, val = el.select_one(".fl"), el.select_one(".fv")
    el.clear(); b = soup.new_tag("strong"); b.string = lab.get_text() + ": "
    el.append(b); el.append(val.get_text()); el.name = "p"
for el in main.select("p.li"):
    mk, tx = el.select_one(".mk"), el.select_one(".tx")
    if mk and tx:
        t = soup.new_tag("span"); t.string = mk.get_text() + " "
        for c in list(tx.contents): t.append(c.extract())
        el.clear(); el.append(t); t.unwrap()
for el in main.select("p.quote"): 
    p = soup.new_tag("p")
    for c in list(el.contents): p.append(c.extract())
    el.clear(); el.name = "blockquote"; el.append(p)
for el in main.select("div.tw"): el.unwrap()
for el in main.select("div.cover"): el.unwrap()

# ป้ายรอตรวจสอบ
def tag(el, reason, before=None):
    s = soup.new_tag("span", attrs={"class": "pending"})
    s.string = f" (รอตรวจสอบ: {reason})"
    if before is not None: before.insert_after(s)
    else: el.append(s)

fns = {re.sub(r"\D", "", li["id"]): li for li in main.select("ol.fnlist li")}
marked = dict(cfg["footnotes"])
if cfg.get("propagate_ah_laew"):
    changed = True
    while changed:
        changed = False
        for n, li in fns.items():
            if n in marked: continue
            m = re.search(r"อ้างแล้วเชิงอรรถที่ (\d+)", li.get_text())
            if m and m.group(1) in marked:
                marked[n] = f"อ้างอิงต่อจากเชิงอรรถที่ {m.group(1)} ซึ่งยังไม่ยืนยัน"; changed = True
for n, reason in marked.items():
    if n in fns: tag(fns[n], reason)
for sup in main.select("sup"):          # ป้ายในเนื้อหา: ต่อท้ายตัวเลขเชิงอรรถที่ยังรอตรวจ
    n = re.sub(r"\D", "", sup.get("id", ""))
    if n in marked: tag(None, marked[n], before=sup)
sec = main.find(id="biblio")
nb = 0
for p in sec.select("p.bib"):
    t = p.get_text().strip()
    for pre, why in cfg["bibliography"].items():
        if t.startswith(pre):
            tag(p, why); nb += 1; break

# ล้าง attribute ที่ไม่จำเป็น
KEEP = {"id", "href", "colspan", "rowspan", "class"}
for el in main.find_all(True):
    for a in list(el.attrs):
        if a not in KEEP: del el[a]
        elif a == "class" and "pending" not in el.get("class", []): del el[a]
for el in main.find_all(["section", "span"]):
    if el.name == "section" and not el.get("id"): el.unwrap()
    elif el.name == "span" and "pending" not in (el.get("class") or []): el.unwrap()

# สารบัญแบบสั้น (ไม่มีเลขหน้า)
nav = ["<nav><p><strong>สารบัญ</strong></p><ul>"]
for h in main.find_all("h2"):
    sid = h.get("id") or (h.parent.get("id") if h.parent and h.parent.name == "section" else None)
    name = h.get_text(strip=True)
    if sid and name != "สารบัญ":
        nav.append(f'<li><a href="#{sid}">{name}</a></li>')
nav.append("</ul></nav>")

CSS = """body{font-family:"TH Sarabun New","Angsana New","Sarabun",serif;font-size:20px;line-height:1.5;max-width:46rem;margin:1rem auto;padding:0 1rem;color:#000;background:#fff}
h2{font-size:1.3em;margin:1.6em 0 .4em}h3{font-size:1.15em;margin:1.2em 0 .3em}h4{font-size:1.05em;margin:1em 0 .2em}
p{margin:.5em 0;text-align:justify}blockquote{margin:.5em 0 .5em 2em}
table{border-collapse:collapse;margin:.8em 0;width:100%}th,td{border:1px solid #000;padding:.2em .4em;vertical-align:top}
sup a{text-decoration:none}.pending{background:#ffe27a}.clean .pending{display:none}.tools{user-select:none;border:1px solid #999;padding:.5em;margin:0 0 1em;font-size:.85em;font-family:sans-serif}.tools button{font:inherit;padding:.3em .8em;cursor:pointer}@media print{.tools{display:none}}nav ul{columns:2}"""
TOOLS = ('<div class="tools"><button id="cl" type="button">ซ่อนป้าย (รอตรวจสอบ) — สำหรับ copy ลง Word</button> '
         '<span>ป้ายสีเหลืองคือแหล่งที่ยังไม่ยืนยัน กดปุ่มเพื่อซ่อนก่อน copy; กดอีกครั้งเพื่อแสดง</span></div>\n'
         '<script>var b=document.getElementById("cl");b.onclick=function(){var c=document.body.classList.toggle("clean");'
         'b.textContent=c?"แสดงป้าย (รอตรวจสอบ)":"ซ่อนป้าย (รอตรวจสอบ) — สำหรับ copy ลง Word"}</script>\n')
title = soup.title.get_text()
html = (f'<!doctype html>\n<html lang="th"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="noindex,nofollow"><title>{title}</title><style>{CSS}</style></head><body>\n'
        + TOOLS + "".join(nav) + "\n" + main.decode_contents() + "\n</body></html>\n")
html = re.sub(r"\n{2,}", "\n", html)
out.write_text(html, encoding="utf-8")
print(f"wrote {out} {len(html):,} chars | footnotes tagged {len([n for n in marked if n in fns])}/{len(fns)} | bibliography tagged {nb}")
