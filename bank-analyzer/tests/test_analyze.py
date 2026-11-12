import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze as a

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "sample_statement.csv"

def run():
    df = a.normalize(a.load(SAMPLE))
    return df, a.analyze(df, 50000, 2, 0.9)

def test_thai_year_and_totals():
    df, _ = run()
    assert df.date.min().year == 2025
    assert df.credit.sum() == 677000

def test_flags():
    _, res = run()
    why = " ".join(res["รายการที่ควรตรวจ"]["สัญญาณ"])
    for k in ["ใกล้เกณฑ์", "เงินเข้าแล้วออก", "รายการซ้ำ"]:
        assert k in why

def test_num():
    assert a.num("(1,234.50)") == -1234.5
