#!/usr/bin/env python3
"""วิเคราะห์สเตรทเมนต์ธนาคาร (CSV / XLSX / PDF ที่มีตาราง) -> รายงาน Excel

ใช้:  python3 analyze.py statement.csv -o report.xlsx [--threshold 50000]
ผลเป็นสัญญาณให้ตรวจต่อ ไม่ใช่ข้อสรุปว่ากระทำผิด
"""
import argparse, re, sys
from pathlib import Path
import pandas as pd

ALIASES = {
    "date": ["date", "วันที่", "วันที่ทำรายการ", "transaction date", "txn date", "posting date"],
    "time": ["time", "เวลา"],
    "desc": ["description", "details", "รายการ", "รายละเอียด", "หมายเหตุ", "คำอธิบาย", "particulars", "narrative"],
    "debit": ["debit", "withdrawal", "withdraw", "ถอน", "ถอนเงิน", "เงินออก", "จ่าย", "ฝากถอน(ถอน)"],
    "credit": ["credit", "deposit", "ฝาก", "ฝากเงิน", "เงินเข้า", "รับ"],
    "amount": ["amount", "จำนวนเงิน", "ยอดเงิน", "จำนวน"],
    "balance": ["balance", "ยอดคงเหลือ", "คงเหลือ", "ยอดเงินคงเหลือ", "running balance"],
    "channel": ["channel", "ช่องทาง", "สาขา", "branch"],
}
CASH_KW = ["cash", "เงินสด", "atm", "cdm", "ฝากเงินสด", "ถอนเงินสด"]


def num(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace(",", "").replace("฿", "")
    if not s or s in "-–":
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -abs(v) if neg else v


def parse_date(x):
    if isinstance(x, (pd.Timestamp,)) or hasattr(x, "year") and not isinstance(x, str):
        d = pd.Timestamp(x)
    else:
        s = str(x).strip()
        m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
        if m:
            dd, mm, yy = map(int, m.groups())
            if yy < 100:
                yy += 2500 if yy > 50 else 2000
            if yy > 2400:
                yy -= 543
            try:
                return pd.Timestamp(yy, mm, dd)
            except ValueError:
                return pd.NaT
        d = pd.to_datetime(s, errors="coerce")
    if pd.notna(d) and d.year > 2400:
        d = d.replace(year=d.year - 543)
    return d


def load(path):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".csv":
        for enc in ("utf-8-sig", "cp874", "utf-8"):
            try:
                return pd.read_csv(p, dtype=str, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise SystemExit("อ่านไฟล์ CSV ไม่ได้ (encoding)")
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype=str)
    if ext == ".pdf":
        import pdfplumber
        rows, header = [], None
        with pdfplumber.open(p) as pdf:
            for pg in pdf.pages:
                for t in pg.extract_tables():
                    for r in t:
                        r = [(c or "").replace("\n", " ").strip() for c in r]
                        if header is None and detect_cols(r):
                            header = r
                        elif header and len(r) == len(header):
                            rows.append(r)
        if not header:
            raise SystemExit("PDF นี้ไม่พบตารางที่มีหัวคอลัมน์ (อาจเป็นภาพสแกน ต้อง OCR ก่อน)")
        return pd.DataFrame(rows, columns=header)
    raise SystemExit(f"ไม่รองรับไฟล์ {ext}")


def detect_cols(names):
    m = {}
    for i, n in enumerate(names):
        k = str(n).strip().lower()
        for key, al in ALIASES.items():
            if key not in m and any(k == a.lower() for a in al):
                m[key] = i
    for i, n in enumerate(names):  # รอบสอง: ตรงบางส่วน
        k = str(n).strip().lower()
        for key, al in ALIASES.items():
            if key not in m and any(a.lower() in k for a in al) and i not in m.values():
                m[key] = i
    ok = "date" in m and ("amount" in m or "debit" in m or "credit" in m)
    return m if ok else None


def normalize(raw):
    m = detect_cols(list(raw.columns))
    if not m:
        raise SystemExit(f"ไม่พบคอลัมน์วันที่/จำนวนเงิน พบหัวคอลัมน์: {list(raw.columns)}")
    cols = raw.columns
    g = lambda k: raw[cols[m[k]]] if k in m else pd.Series([""] * len(raw))
    df = pd.DataFrame({"date": g("date").map(parse_date), "desc": g("desc").fillna("").astype(str)})
    if "debit" in m or "credit" in m:
        df["debit"] = g("debit").map(num).abs()
        df["credit"] = g("credit").map(num).abs()
    else:  # คอลัมน์เดียว ลบ=ออก
        a = g("amount").map(num)
        df["debit"] = (-a).clip(lower=0)
        df["credit"] = a.clip(lower=0)
    df["balance"] = g("balance").map(num) if "balance" in m else float("nan")
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    df = df[(df.debit > 0) | (df.credit > 0)].reset_index(drop=True)
    df["amount"] = df.credit - df.debit
    df["month"] = df.date.dt.to_period("M").astype(str)
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def analyze(df, thr, passdays, bandpct):
    out = {}
    tot_in, tot_out = df.credit.sum(), df.debit.sum()
    out["สรุป"] = pd.DataFrame({"รายการ": [
        "ช่วงวันที่", "จำนวนรายการ", "เงินเข้ารวม", "เงินออกรวม", "สุทธิ",
        "เงินเข้าสูงสุด/รายการ", "เงินออกสูงสุด/รายการ"],
        "ค่า": [f"{df.date.min().date()} ถึง {df.date.max().date()}", len(df), tot_in, tot_out,
                tot_in - tot_out, df.credit.max(), df.debit.max()]})
    out["รายเดือน"] = df.groupby("month").agg(
        รายการ=("amount", "size"), เงินเข้า=("credit", "sum"), เงินออก=("debit", "sum"),
        สุทธิ=("amount", "sum")).reset_index()

    d = df.copy()
    d["key"] = d.desc.str.lower().str.replace(r"\d+", "#", regex=True).str.strip()
    out["คู่รายการ_ตามคำอธิบาย"] = d.groupby("key").agg(
        ครั้ง=("amount", "size"), เงินเข้า=("credit", "sum"), เงินออก=("debit", "sum")
    ).sort_values(["เงินเข้า", "เงินออก"], ascending=False).head(30).reset_index()

    flags = []
    def add(idx, why):
        for i in idx:
            flags.append((i, why))

    big = df.amount.abs()
    lim = thr
    add(df.index[big >= lim], f"ยอดสูง (≥ {lim:,.0f})")
    mag = df[["credit", "debit"]].max(axis=1)
    add(df.index[(mag >= thr) & (mag % 1000 == 0)], "ยอดกลมพัน")
    cash = d.desc.str.lower().apply(lambda s: any(k in s for k in CASH_KW))
    add(df.index[cash & (mag >= thr)], "เงินสดยอดสูง")

    # แตกยอดเลี่ยงเกณฑ์: หลายรายการ 90–99.99% ของ thr ภายใน 7 วัน
    near = df[(mag >= thr * bandpct) & (mag < thr)]
    for i, r in near.iterrows():
        w = near[(near.date >= r.date - pd.Timedelta(days=3)) & (near.date <= r.date + pd.Timedelta(days=3))]
        if len(w) >= 2:
            add([i], f"ใกล้เกณฑ์ {thr:,.0f} หลายครั้งใน 7 วัน")

    # เงินพักผ่าน: เข้าแล้วออก ≥80% ภายใน passdays วัน
    for i, r in df[df.credit > 0].iterrows():
        w = df[(df.index > i) & (df.debit > 0) & (df.date <= r.date + pd.Timedelta(days=passdays))]
        if r.credit >= thr / 5 and w.debit.sum() >= 0.8 * r.credit:
            add([i], f"เงินเข้าแล้วออก ≥80% ภายใน {passdays} วัน")

    dup = df.duplicated(["date", "credit", "debit", "desc"], keep=False)
    add(df.index[dup], "รายการซ้ำ (วัน/ยอด/คำอธิบายเหมือนกัน)")

    # ความต่อเนื่องของยอดคงเหลือ
    if df.balance.notna().any() and (df.balance != 0).any():
        exp = df.balance.shift(1) + df.amount
        bad = (exp - df.balance).abs() > 0.01
        bad.iloc[0] = False
        add(df.index[bad], "ยอดคงเหลือไม่ต่อเนื่อง (อาจขาดรายการ/ลำดับผิด)")

    if flags:
        f = pd.DataFrame(flags, columns=["i", "เหตุ"]).groupby("i")["เหตุ"].apply(lambda s: "; ".join(sorted(set(s))))
        fl = df.loc[f.index, ["date", "desc", "debit", "credit", "balance"]].copy()
        fl["สัญญาณ"] = f
        fl["date"] = fl.date.dt.date
        out["รายการที่ควรตรวจ"] = fl.reset_index(drop=True)
    else:
        out["รายการที่ควรตรวจ"] = pd.DataFrame(columns=["date", "desc", "debit", "credit", "balance", "สัญญาณ"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="report.xlsx")
    ap.add_argument("--threshold", type=float, default=50000, help="เกณฑ์ยอดสูง/เกณฑ์แตกยอด (บาท)")
    ap.add_argument("--passdays", type=int, default=2, help="กรอบวันสำหรับเงินพักผ่าน")
    ap.add_argument("--band", type=float, default=0.9, help="สัดส่วนต่ำสุดที่ถือว่าใกล้เกณฑ์")
    a = ap.parse_args()
    df = normalize(load(a.input))
    res = analyze(df, a.threshold, a.passdays, a.band)
    with pd.ExcelWriter(a.output, engine="openpyxl") as w:
        df.drop(columns=["month"]).assign(date=df.date.dt.date).to_excel(w, sheet_name="รายการทั้งหมด", index=False)
        for k, v in res.items():
            v.to_excel(w, sheet_name=k[:31], index=False)
        for ws in w.book.worksheets:
            for c in ws.columns:
                ws.column_dimensions[c[0].column_letter].width = min(60, max(10, max(len(str(x.value or "")) for x in c) + 2))
    print(res["สรุป"].to_string(index=False))
    print(f"\nรายการที่ควรตรวจ: {len(res['รายการที่ควรตรวจ'])} รายการ -> {a.output}")


if __name__ == "__main__":
    main()
