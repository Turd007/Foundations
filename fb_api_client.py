# fb_api_client.py
from __future__ import annotations
import os, json, time, pathlib
from datetime import datetime
from openai import OpenAI

# --- Configurable defaults ---
DEFAULT_MODEL = os.getenv("FB_OPENAI_MODEL", "gpt-4o-mini")
MAX_RETRIES = int(os.getenv("FB_API_MAX_RETRIES", "3"))
RETRY_BASE_SLEEP = float(os.getenv("FB_API_RETRY_BASE", "0.8"))  # seconds

# Where we store reliability logs (auto-created)
REPORTS_DIR = pathlib.Path(os.getenv("FB_REPORTS_DIR", "./Reports")).resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Singleton client ---
_client: OpenAI | None = None

def _client_singleton() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()  # Picks up OPENAI_API_KEY from environment
    return _client

# --- Logging ---
def _log_event(event: dict) -> None:
    """Append a JSON line to daily log for reliability tracking."""
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = REPORTS_DIR / f"openai_calls_{stamp}.jsonl"
    event["ts_utc"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

# --- Text call ---
def ask(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    extra_messages: list[dict] | None = None,
) -> str:
    """
    Basic text call. Returns assistant's response string.
    """
    cli = _client_singleton()
    use_model = model or DEFAULT_MODEL

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    if extra_messages:
        messages.extend(extra_messages)

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            r = cli.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = r.choices[0].message.content or ""
            _log_event({
                "ok": True,
                "fn": "ask",
                "model": use_model,
                "temperature": temperature,
                "latency_s": round(time.perf_counter() - t0, 3),
                "prompt_chars": sum(len(m.get("content","")) for m in messages),
                "response_chars": len(content),
            })
            return content
        except Exception as e:
            last_exc = e
            time.sleep(RETRY_BASE_SLEEP * (2 ** (attempt - 1)))

    _log_event({
        "ok": False,
        "fn": "ask",
        "model": use_model,
        "error": repr(last_exc),
    })
    raise last_exc if last_exc else RuntimeError("Unknown error in ask()")

# --- JSON call ---
def ask_json(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    schema_hint: str | None = None,
    max_tokens: int | None = None,
) -> dict:
    """
    Requests structured JSON from the model and parses it.
    Light auto-repair if the model adds any extra text.
    """
    schema_note = f"\n\nSchema hint:\n{schema_hint}" if schema_hint else ""

    json_prompt = (
        "Respond ONLY with compact JSON (no backticks, no text before/after). "
        "If a field is unknown, use null. "
        "Do not include comments."
        + schema_note
        + "\n\nUser request:\n"
        + prompt
    )

    raw = ask(
        json_prompt,
        system=system or "You are a precise JSON generator.",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    ).strip()

    # Attempt a direct parse
    try:
        return json.loads(raw)
    except Exception:
        # Attempt minimal repair: find first { ... } block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except Exception:
                pass

        # If still not valid, log the failure and raise
        _log_event({
            "ok": False,
            "fn": "ask_json",
            "model": model or DEFAULT_MODEL,
            "error": "JSON parse failed",
            "raw_head": raw[:200],
        })
        raise
