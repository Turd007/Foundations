from __future__ import annotations
import argparse, json
from pathlib import Path
from fbprooflab.registry import load_claims_from_yaml, run_claim

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", required=True)
    ap.add_argument("--out_md", default="../data/reports/proof_report.md")
    ap.add_argument("--out_json", default="../data/reports/proof_report.json")
    args = ap.parse_args()

    claims = load_claims_from_yaml(args.claims)
    results = [run_claim(c) for c in claims]

    jpath = Path(args.out_json); jpath.parent.mkdir(parents=True, exist_ok=True)
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in results], f, indent=2)

    mpath = Path(args.out_md); mpath.parent.mkdir(parents=True, exist_ok=True)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write("# Proof Report\n\n")
        for r in results:
            f.write(f"## {r.id} — {r.type} — **{r.status.upper()}**\n\n")
            for k, v in r.details.items():
                f.write(f"- **{k}**: {v}\n")
            f.write("\n---\n\n")

    print(f"Wrote {jpath} and {mpath}")

if __name__ == "__main__":
    main()
