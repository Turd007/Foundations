import yaml, pprint
with open("claims_min.yaml", "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f)
print("top type:", type(doc))
print("content:")
pprint.pp(doc)
if not (isinstance(doc, dict) and "claims" in doc and isinstance(doc["claims"], list)):
    raise SystemExit("YAML not in expected format.")
print("OK: claims list length =", len(doc["claims"]))
