import argparse, csv, json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="JSON results from run_proofs.py")
    ap.add_argument("--map",     required=True, help="JSON claim_id -> source doc path")
    ap.add_argument("--csv",     required=True, help="CSV to write")
    args = ap.parse_args()

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    claim_to_doc = json.loads(Path(args.map).read_text(encoding="utf-8"))

    # results is a list of objects with keys: id, type, status, details
    rows = []
    for r in results:
        cid = r.get("id")
        rows.append({
            "claim_id": cid,
            "type": r.get("type"),
            "status": r.get("status"),
            "source_doc": claim_to_doc.get(cid, ""),
        })

    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["claim_id","type","status","source_doc"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {args.csv} with {len(rows)} rows")

if __name__ == "__main__":
    main()
