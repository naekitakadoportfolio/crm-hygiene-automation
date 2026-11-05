import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from hygiene import run, normalize
DATA = pathlib.Path(__file__).parent.parent / "data/contacts.csv"

def test_normalizes_email_and_phone():
    r = normalize({"id":"1","first_name":"maria","last_name":"chen","email":" A@B.COM ","company":"X Inc","phone":"(415) 555-0101","lifecycle_stage":"lead","owner":""})
    assert r["email"] == "a@b.com" and r["phone"] == "+14155550101" and r["company_key"] == "x"

def test_detects_both_duplicate_pairs():
    ids = [sorted(p["ids"]) for p in run(DATA)["merge_review_queue"]]
    assert ["1", "2"] in ids and ["5", "6"] in ids

def test_flags_invalid_email():
    assert "invalid_email" in run(DATA)["issues"]["4"]
