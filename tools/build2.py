#!/usr/bin/env python3
"""สร้างบทที่เขียนแล้ว (ไฟล์ /tmp/new2/chN.txt) ลงใน draft/original.html ส่วนบทที่ยังไม่มีไฟล์คงเป็น [รอเขียนใหม่]"""
import re, json, html
from pathlib import Path
NEW=Path("/tmp/new2"); REPO=Path("/home/user/nacc-flagrant-arrest-thesis"); ORIG=REPO/"draft/original.html"
MACROS={
 "pg":"เลขหน้า/ส่วนของเล่มอ่านจากไฟล์ PDF ที่ผู้ใช้อัปโหลด ยังไม่ตรวจกับเล่มพิมพ์ และเนื้อหาเป็นการสรุปจากแหล่งรอง ยังไม่ตรวจต้นฉบับของแหล่งที่เล่มนั้นอ้างถึง",
 "stat":"ฉบับชำระของสำนักงานคณะกรรมการกฤษฎีกา หรือสำเนาที่ผู้ช่วยอ่านเอง ผู้ใช้ยังไม่ยืนยันถ้อยคำ",
 "foreign":"ยังไม่ได้ตรวจเลขมาตรากับตัวบททางการ และยังไม่ยืนยันว่าเป็นฉบับล่าสุดหรือไม่",
 "circ":"เอกสารภายในของสำนักงาน ป.ป.ช. ได้มาจากไฟล์ที่แชร์ผ่าน Google Drive ยังไม่ยืนยันที่มาและการเผยแพร่ต่อสาธารณะ; ข้อความอ่านจาก OCR ยังไม่เทียบภาพ PDF; วันที่ เลขที่ และข้อความ \"48 ชั่วโมง\" ต้องตรวจกับต้นฉบับ",
 "sg":"ผู้ช่วยอ่านจากไฟล์ที่ผู้ใช้อัปโหลด (sources/Prevention of Corruption Act 1960.pdf, 2020 Revised Edition รวมแก้ไขถึง 1 ธันวาคม 2021) ผู้ใช้ยังไม่ยืนยันถ้อยคำ และยังไม่ตรวจการแก้ไขภายหลัง",
 "hk":"ผู้ช่วยอ่านจากไฟล์ที่ผู้ใช้อัปโหลด (sources/Cap 204 PDF (24-06-2021) (English).pdf, Last updated date 24.6.2021) ผู้ใช้ยังไม่ยืนยันถ้อยคำ และยังไม่ตรวจการแก้ไขภายหลัง",
 "cpc":"ผู้ช่วยอ่านจากไฟล์ที่ผู้ใช้อัปโหลด (sources/Criminal Procedure Code 2010.pdf; ฉบับรวบรวมไม่เป็นทางการ Informal Consolidation ที่มีผลถึง 15/9/2026 ไม่ใช่ฉบับ official และไม่ตรงกับ PCA ฉบับ 2020 Rev. Ed.) ผู้ใช้ยังไม่ยืนยันถ้อยคำ",
 "case":"ยังไม่ระบุแหล่งตีพิมพ์ของฎีกา (เนติ./ศาลยุติธรรม เล่ม ตอน หน้า) สาระของฎีกาสรุปจากข้อความเต็มในระบบสืบค้นผ่านเครื่องมือ Thai Legal MCP ยังไม่เทียบกับรายงานฎีกาฉบับพิมพ์ (ดู sources/excerpts/th-deka-checked.md)",
 "regs":"ข้อ 45 และข้อ 48 ผู้ใช้ยืนยันถ้อยคำแล้ว 2026-11-02; ข้อ 46 และข้อ 47 อ่านจากสำเนาราชกิจจาฯ เล่ม 139 ตอนที่ 21 ก ที่ผู้ใช้อัปโหลด (sources/จับ ค้น ปปช.pdf) ผ่าน pdftotext แล้ว ยังไม่ได้เทียบภาพกับต้นฉบับ รอผู้ใช้ยืนยันถ้อยคำ",
 "reg":"ข้อ 36 ถึงข้อ 39 ผู้ใช้ยืนยันถ้อยคำแล้ว 2026-11-02; ข้อ 31 ผู้ใช้ยืนยันถ้อยคำแล้ว 2026-11-02; ข้อ 32 อ่านจากสำเนาราชกิจจาฯ เล่ม 139 ตอนที่ 21 ก ที่ผู้ใช้อัปโหลด (sources/จับ ค้น ปปช.pdf) ผ่าน pdftotext แล้ว รอผู้ใช้ยืนยันถ้อยคำเทียบต้นฉบับ ข้อวิเคราะห์ว่าปลายทางตามข้อ 39 (2) ต่างจากมาตรา 39 วรรคสี่ อิงข้อ 32",
}
FN_RE=re.compile(r"\[\[fn(p)?(?:@(\w+))?(?:#(\w+))?:\s*(.*?)\]\]",re.S)
footnotes=[]; keys={}
def inline(t):
    t=html.escape(t,quote=False)
    t=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",t)
    return re.sub(r"//(.+?)//",r"<em>\1</em>",t)
def render(t):
    out=[];pos=0
    for m in FN_RE.finditer(t):
        out.append(inline(t[pos:m.start()])); pend,macro,key,body=m.groups(); reason=None
        if pend:
            if macro: reason=MACROS[macro]
            else: reason,body=[x.strip() for x in body.split(" :: ",1)]
        n=len(footnotes)+1; footnotes.append(dict(n=n,text=body.strip(),reason=reason,key=key))
        if key: keys[key]=n
        out.append(f'<sup class="fnref" id="fnref-{n}"><a href="#fn-{n}">{n}</a></sup>'); pos=m.end()
    out.append(inline(t[pos:])); return "".join(out)
def slug(t): return "s-"+t.replace("“","").replace("”","").replace(" ","-")
def parse(path):
    lines=path.read_text(encoding="utf-8").split("\n"); parts=[]; heads=[]; ch=None; i=0
    while i<len(lines):
        ln=lines[i]
        if not ln.strip(): i+=1; continue
        if ln.startswith("# "):
            no,name=[x.strip() for x in ln[2:].split("|")]; n=re.search(r"\d+",no).group()
            ch=dict(no=no,n=n,name=name,id=f"ch{n}")
            parts.append(f'<section class="sheet chapter"><h2 class="chtitle" id="ch{n}"><span class="chno">{no}</span><span class="chname">{name}</span></h2>')
        elif ln.startswith("### "):
            t=ln[4:].strip(); heads.append((2,t,slug(t))); parts.append(f'<h4 class="hB" id="{slug(t)}">{t}</h4>')
        elif ln.startswith("## "):
            t=ln[3:].strip(); heads.append((1,t,slug(t))); parts.append(f'<h3 class="hA" id="{slug(t)}">{t}</h3>')
        elif ln.startswith(">>"):
            parts[-1]=parts[-1][:-4]+f"<br>{inline(ln[2:].strip())}</p>"
        elif ln.startswith("> "):
            parts.append(f'<p class="quote">{render(ln[2:].strip())}</p>')
        elif ln.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split(" | ")]); i+=1
            i-=1
            cell=lambda c:"<br>".join(render(x.strip()) for x in c.split(" ¶ "))
            th="".join(f"<th>{cell(c)}</th>" for c in rows[0])
            body="".join("<tr>"+"".join(f"<td>{cell(c)}</td>" for c in r)+"</tr>" for r in rows[1:])
            parts.append(f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>")
        elif re.match(r"\d+\. ",ln):
            mk,tx=ln.split(" ",1); parts.append(f'<p class="li num"><span class="mk">{mk}</span><span class="tx">{render(tx.strip())}</span></p>')
        else: parts.append(f'<p class="b">{render(ln.strip())}</p>')
        i+=1
    parts.append("</section>"); return ch,heads,"\n".join(parts)
src=ORIG.read_text(encoding="utf-8")
a=src.index('<section class="sheet chapter"><h2 class="chtitle" id="ch1"'); e=src.index('<section class="sheet " id="biblio"')
shells=re.findall(r'<h2 class="chtitle" id="(ch\d)"><span class="chno">([^<]+)</span><span class="chname">([^<]+)</span></h2>',src[a:e])
PH='<p class="b">[รอเขียนใหม่]</p>'
chapters=[]  # (id,no,name,heads,body,written)
for cid,no,nm in shells:
    f=NEW/f"{cid.replace('ch','ch')}.txt"
    if f.exists():
        ch,heads,body=parse(f); chapters.append((cid,no,nm,heads,body,True))
    else:
        chapters.append((cid,no,nm,[],f'<section class="sheet chapter"><h2 class="chtitle" id="{cid}"><span class="chno">{no}</span><span class="chname">{nm}</span></h2>\n{PH}\n</section>',False))
sub=lambda s: re.sub(r"\{\{(\w+)\}\}",lambda m:str(keys[m.group(1)]),s)
chapters=[(c,n,m,h,sub(b),w) for c,n,m,h,b,w in chapters]
for f in footnotes: f["text"]=sub(f["text"])
notes='<section class="sheet notes" id="notes"><p class="secheadctr">เชิงอรรถ</p><ol class="fnlist">'+"".join(f'<li id="fn-{f["n"]}"><a class="back" href="#fnref-{f["n"]}">↑</a> {inline(f["text"])}</li>' for f in footnotes)+"</ol></section>"
plain=lambda t:re.sub(r"<[^>]+>","",t); CPP=1500; pos=0; pages={}
for cid,no,nm,heads,body,w in chapters:
    if not w: continue
    pages[cid]=1+int(pos/CPP)
    for p in re.split(r'(?=<h[34] class="h[AB]")',body):
        m=re.match(r'<h[34] class="h[AB]" id="([^"]+)"',p)
        if m: pages[m.group(1)]=1+int(pos/CPP)
        t=plain(p)
        for n in re.findall(r'id="fnref-(\d+)"',p): t+=plain(footnotes[int(n)-1]["text"])
        pos+=len(t)+700*p.count("<table>")+25*p.count("<tr>")
    pos=(int(pos/CPP)+1)*CPP
toc=['<section class="sheet " id="toc"><div class="folio">IV</div><p class="secheadctr">สารบัญ</p>']
for h,t,pg in [("abs-th","บทคัดย่อภาษาไทย","I"),("abs-en","บทคัดย่อภาษาอังกฤษ","II"),("ack","กิตติกรรมประกาศ","III"),("toc","สารบัญ","IV")]:
    toc.append(f'<p class="toc t0"><span class="tl"><a href="#{h}">{t}</a></span><span class="tp">{pg}</span></p>')
toc.append('<p class="secheadl">บทที่</p>')
nav=['<nav><ul><li class="sc"><a href="#abs-th">บทคัดย่อ</a></li>']
for cid,no,nm,heads,body,w in chapters:
    toc.append(f'<p class="toc t1"><span class="tl"><a href="#{cid}">{no[-1]}&nbsp;&nbsp;{nm}</a></span><span class="tp">{pages.get(cid,"-")}</span></p>')
    nav.append(f'<li class="sc"><a href="#{cid}"><span class="cn">{no}</span> {nm}</a>')
    if heads:
        nav.append("<ul>")
        for lvl,t,sid in heads:
            if lvl==1: toc.append(f'<p class="toc t2"><span class="tl"><a href="#{sid}">{t}</a></span><span class="tp">{pages[sid]}</span></p>')
            nav.append(f'<li class="s{"A" if lvl==1 else "B"}"><a href="#{sid}">{t}</a></li>')
        nav.append("</ul>")
    nav.append("</li>")
toc+=['<p class="toc t0"><span class="tl"><a href="#biblio">บรรณานุกรม</a></span><span class="tp">-</span></p>','<p class="toc t0"><span class="tl"><a href="#vita">ประวัติผู้เขียน</a></span><span class="tp">-</span></p>','</section>']
nav.append('<li class="sc"><a href="#biblio">บรรณานุกรม</a></li><li class="sc"><a href="#notes">เชิงอรรถ</a></li></ul>')
t0=src.index('<section class="sheet " id="toc">'); t1=src.index("</section>",t0)+len("</section>"); src=src[:t0]+"\n".join(toc)+src[t1:]
n0=src.index("<nav><ul>"); n1=src.index("</nav>",n0); src=src[:n0]+"".join(nav)+src[n1:]
a=src.index('<section class="sheet chapter"><h2 class="chtitle" id="ch1"'); e=src.index('<section class="sheet " id="biblio"')
src=src[:a]+"\n".join(b for *_,b,_w in chapters)+"\n"+src[e:]
n0=src.index('<section class="sheet notes" id="notes">'); n1=src.index("</section>",n0)+len("</section>"); src=src[:n0]+notes+src[n1:]
ORIG.write_text(src,encoding="utf-8")
pj=REPO/"tools/pending.json"; txt=pj.read_text(encoding="utf-8")
ent={str(f["n"]):f["reason"] for f in footnotes if f["reason"]}
blk='"footnotes": {\n'+",\n".join(f'  {json.dumps(k)}: {json.dumps(v,ensure_ascii=False)}' for k,v in sorted(ent.items(),key=lambda kv:int(kv[0])))+"\n },"
txt2=re.sub(r'"footnotes": (\{\},|\{.*?\n \},)',lambda m:blk,txt,count=1,flags=re.S)
pj.write_text(txt2,encoding="utf-8"); json.loads(txt2)
print("footnotes",len(footnotes),"explicit pending",len(ent),"keys",keys,"pages",pages)
