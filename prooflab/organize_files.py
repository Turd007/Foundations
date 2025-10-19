import argparse, re, shutil, csv, json, sys
from pathlib import Path
from datetime import datetime

try:
    import yaml
except Exception:
    print("[ERROR] PyYAML required. Run: pip install pyyaml", file=sys.stderr); raise
try:
    from docx import Document
except Exception:
    print("[ERROR] python-docx required. Run: pip install python-docx", file=sys.stderr); raise

def ensure_defaults(r):
    r = r or {}
    r.setdefault("naming", {})
    r.setdefault("routing", {})
    r.setdefault("subjects", [])
    n = r["naming"];  t = r["routing"]
    n.setdefault("replace_spaces_with","_")
    n.setdefault("strip_chars", ["[","]","(",")","{","}",",",";"])
    n.setdefault("collapse_underscores", True)
    n.setdefault("max_len", 120)
    # 3 buckets
    t.setdefault("confirmed_dir",   "Research_CONFIRMED")
    t.setdefault("needs_work_dir",  "Research_NEEDS_WORK")
    t.setdefault("speculative_dir", "Speculation_REJECTED")
    return r

def safe_ascii(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")

def normalize_name(name, rules):
    base, ext = Path(name).stem, Path(name).suffix.lower()
    rep = rules["naming"]["replace_spaces_with"]
    base = base.replace(" ", rep).replace("-", rep)
    for ch in rules["naming"]["strip_chars"]:
        base = base.replace(ch, "")
    if rules["naming"]["collapse_underscores"]:
        import re as _re
        base = _re.sub(r"_+", "_", base).strip("_")
    base = safe_ascii(base)[: int(rules["naming"]["max_len"])]
    return f"{base}{ext}"

def detect_subjects(text, rules):
    t = (text or "").lower()
    labs = set()
    for rule in rules.get("subjects", []):
        toks = rule.get("match", [])
        if any((tok or "").lower() in t for tok in toks):
            labs.add(rule.get("label","misc"))
    return ";".join(sorted(labs)) if labs else ""

def read_doc_subject(path: Path) -> str:
    try:
        d = Document(str(path))
        subj = (getattr(d.core_properties, "subject", "") or "").strip()
        if subj: return subj
        # fallback: first few paras
        return " | ".join(p.text for p in d.paragraphs[:5])
    except Exception:
        return ""

def file_dt_str(p: Path):
    try:
        stat = p.stat()
        c = datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds")
        m = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        return c, m
    except Exception:
        return "", ""

STATUS_MAP = {
    "proved":       ("Confirmed",   "confirmed_dir"),
    "rejected":     ("Speculative", "speculative_dir"),
    "inconclusive": ("Needs work",  "needs_work_dir"),
    "":             ("Needs work",  "needs_work_dir"),
    None:           ("Needs work",  "needs_work_dir"),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Folder of .docx (scanned recursively)")
    ap.add_argument("--rules", default="organize_rules.yaml")
    ap.add_argument("--out_manifest", default="reports/organize_manifest.csv")
    ap.add_argument("--move", action="store_true", help="Move instead of copy")
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()

    root = Path(args.src)
    if not root.exists():
        print(f"[ERROR] Source not found: {root}", file=sys.stderr); sys.exit(1)

    # load rules
    rp = Path(args.rules)
    rules = ensure_defaults(yaml.safe_load(rp.read_text(encoding="utf-8")) if rp.exists() else {})

    # outputs
    out_dirs = {
        "confirmed_dir":   Path(rules["routing"]["confirmed_dir"]),
        "needs_work_dir":  Path(rules["routing"]["needs_work_dir"]),
        "speculative_dir": Path(rules["routing"]["speculative_dir"]),
    }
    for d in out_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # optional proof artifacts
    results_json = Path("reports/proof_from_docs.json")
    claims_map   = Path("reports/claims_doc_map.json")
    id_to_status = {}
    doc_best = {}

    def rank(s):  # Confirmed > Needs work > Speculative
        order = {"proved":2, "inconclusive":1, "rejected":0}
        return order.get((s or "").lower(), -1)

    if results_json.exists():
        try:
            results = json.loads(results_json.read_text(encoding="utf-8"))
            for r in results:
                cid = r.get("id"); st = r.get("status","inconclusive")
                if cid: id_to_status[cid] = st
        except Exception as e:
            print(f"[WARN] Results JSON unreadable: {e}")

    if claims_map.exists():
        try:
            cmap = json.loads(claims_map.read_text(encoding="utf-8"))
            for cid, doc_path in cmap.items():
                st = id_to_status.get(cid, "inconclusive")
                cur = doc_best.get(doc_path)
                if (cur is None) or (rank(st) > rank(cur)):
                    doc_best[doc_path] = st
        except Exception as e:
            print(f"[WARN] Claims map unreadable: {e}")

    files = list(root.rglob("*.docx"))
    print(f"[INFO] Found {len(files)} .docx under {root}")

    rows = []
    for doc in files:
        ctime, mtime = file_dt_str(doc)
        subject_blob = (doc.stem + " " + read_doc_subject(doc))
        labels = detect_subjects(subject_blob, rules)
        new_name = normalize_name(doc.name, rules)

        proof_status = (doc_best.get(str(doc)) or "").lower()
        status_label, bucket_key = STATUS_MAP.get(proof_status, ("Needs work", "needs_work_dir"))
        dest_dir = out_dirs[bucket_key]
        dest = dest_dir / new_name

        if not args.dry_run:
            try:
                if args.move:
                    shutil.move(str(doc), str(dest))
                else:
                    if dest.exists():
                        stem, ext = dest.stem, dest.suffix; k=1
                        alt = dest_dir / f"{stem}_{k}{ext}"
                        while alt.exists(): k+=1; alt = dest_dir / f"{stem}_{k}{ext}"
                        dest = alt
                    shutil.copy2(str(doc), str(dest))
            except Exception as e:
                print(f"[copy/move-fail] {doc} -> {dest} :: {e}")

        rows.append({
            "original_path": str(doc),
            "normalized_name": dest.name,
            "created_time": ctime,
            "modified_time": mtime,
            "subjects": labels,
            "proof_status_raw": proof_status or "unknown",
            "status_bucket": status_label,
            "routed_to": str(dest)
        })

    Path(args.out_manifest).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "original_path","normalized_name","created_time","modified_time",
            "subjects","proof_status_raw","status_bucket","routed_to"])
        w.writeheader()
        w.writerows(rows)

    print(f"[ok] Manifest: {args.out_manifest}")
    print(f"[ok] Routed {len(rows)} files → {out_dirs['confirmed_dir']}, {out_dirs['needs_work_dir']}, {out_dirs['speculative_dir']}")
