from fb_api_client import ask, ask_json

print("Text mode:", ask("Reply with the word: ONLINE", temperature=0))

print("JSON mode:", ask_json(
    "Return tool status with fields: {'tool':'Bridge','status':'ok'}",
    schema_hint='{"tool":"string","status":"string"}',
    temperature=0
))
