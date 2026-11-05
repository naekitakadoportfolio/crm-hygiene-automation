"""CRM hygiene pipeline: normalize -> validate -> detect duplicates -> propose merges -> report.
Writes a review queue instead of auto-merging, so a human approves anything destructive."""
import csv, json, re, sys
from pathlib import Path
from difflib import SequenceMatcher

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
STAGES = {"subscriber", "lead", "mql", "sql", "prospect", "customer"}
SUFFIXES = re.compile(r"\b(inc|corp|corporation|llc|ltd|co)\.?$", re.I)

def normalize(r):
    r = {k: (v or "").strip() for k, v in r.items()}
    r["email"] = r["email"].lower()
    r["first_name"], r["last_name"] = r["first_name"].title(), r["last_name"].title()
    r["company_key"] = SUFFIXES.sub("", r["company"].lower()).strip()
    digits = re.sub(r"\D", "", r["phone"])
    r["phone"] = f"+1{digits[-10:]}" if len(digits) >= 10 else ""
    return r

def validate(r):
    issues = []
    if not EMAIL_RE.match(r["email"]): issues.append("invalid_email")
    if r["lifecycle_stage"] not in STAGES: issues.append("unknown_stage")
    if not r["owner"]: issues.append("missing_owner")
    if not r["phone"]: issues.append("missing_phone")
    return issues

def similarity(a, b):
    if a["email"] and a["email"] == b["email"]: return 1.0
    name = SequenceMatcher(None, f"{a['first_name']} {a['last_name']}", f"{b['first_name']} {b['last_name']}").ratio()
    comp = 1.0 if a["company_key"] == b["company_key"] else 0.0
    return round(0.6 * name + 0.4 * comp, 2)

def find_duplicates(rows, threshold=0.85):
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            s = similarity(rows[i], rows[j])
            if s >= threshold:
                keep = max(rows[i], rows[j], key=lambda r: sum(bool(v) for v in r.values()))
                pairs.append({"ids": [rows[i]["id"], rows[j]["id"]], "score": s, "keep": keep["id"]})
    return pairs

def run(path):
    rows = [normalize(r) for r in csv.DictReader(open(path))]
    issues = {r["id"]: validate(r) for r in rows if validate(r)}
    dupes = find_duplicates(rows)
    total_fields = len(rows) * 4
    report = {"records": len(rows), "records_with_issues": len(issues),
              "data_quality_score": round(1 - sum(map(len, issues.values())) / total_fields, 2),
              "issues": issues, "merge_review_queue": dupes}
    return report

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "data/contacts.csv"
    print(json.dumps(run(p), indent=2))
