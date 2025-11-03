from __future__ import annotations
import os
import json
from datetime import date, timedelta
from typing import List, Dict
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.llm_client import LLMClient
from app.services.rag_engine import clean_legal_response

NYAY_DIR = os.path.join(".data", "nyayshala")
os.makedirs(NYAY_DIR, exist_ok=True)

FIELDS = ["contract", "criminal", "family", "ip", "tax", "property"]

# Curated topic hints per field to encourage variety
FIELD_TOPICS: Dict[str, List[str]] = {
    "contract": [
        "consideration need not be adequate",
        "free consent and coercion",
        "undue influence and unconscionable bargains",
        "minor's agreement and void ab initio",
        "contingent contracts basics",
        "void agreements vs voidable contracts",
        "specific performance overview",
        "liquidated damages vs penalty",
        "frustration of contract (Section 56)",
        "privity of contract and exceptions",
    ],
    "criminal": [
        "FIR essentials (Section 154 CrPC)",
        "bail: anticipatory vs regular",
        "cognizable vs non-cognizable offences",
        "arrest without warrant: safeguards",
        "confession and Section 164 CrPC",
        "charge framing basics",
        "compoundable vs non-compoundable",
        "limitations for taking cognizance",
    ],
    "family": [
        "divorce by mutual consent",
        "maintenance under Section 125 CrPC",
        "guardianship best interests principle",
        "domestic violence: protection orders",
        "adoption under HAMA",
        "Hindu Succession Act daughters' rights",
    ],
    "ip": [
        "well-known trademarks: criteria",
        "copyright fair dealing in India",
        "patent novelty and inventive step",
        "design registration basics",
        "passing off vs infringement",
        "GI tags overview",
    ],
    "tax": [
        "GST e-invoicing threshold",
        "input tax credit basics",
        "GST composition scheme",
        "TDS vs TCS overview",
        "appeal timelines under GST",
    ],
    "property": [
        "benami transactions prohibition",
        "mutation not proof of title",
        "adverse possession basics",
        "easements: right of way",
        "registration vs notarization",
    ],
}

PROMPT = (
    "You are NyaySaathi. Generate a concise 'law nugget' for the FIELD domain in India. "
    "Return 1-2 paragraphs (<= 120 words) with a short title and a couple of references to public sources (names/URLs). "
    "Keep it educational, not legal advice."
)


def _pick_topic(field: str, randomize: bool) -> str | None:
    topics = FIELD_TOPICS.get(field) or []
    if not topics:
        return None
    if randomize:
        return random.choice(topics)
    # Deterministic choice per day/field when not random: rotate based on day-of-year
    try:
        idx = (date.today().toordinal() + hash(field)) % len(topics)
        return topics[idx]
    except Exception:
        return topics[0]


def _path_for(d: date) -> str:
    return os.path.join(NYAY_DIR, f"{d.isoformat()}.json")


def generate_for_day(d: date, persist: bool = True, randomize: bool = False) -> List[Dict]:
    def build_item(field: str) -> Dict:
        topic_hint = _pick_topic(field, randomize=randomize)
        msgs = [
            {"role": "system", "content": "You write concise legal learning snippets."},
            {"role": "user", "content": (
                PROMPT.replace("FIELD", field)
                + (f"\n\nTopic Hint: {topic_hint}." if topic_hint else "")
                + (" Focus on a different subtopic on each request; do not repeat previous examples if possible." if randomize else "")
            )},
        ]
        # Create a client per task to avoid thread-safety issues
        attempts = 3 if randomize else 2
        last_err: Exception | None = None
        for i in range(attempts):
            try:
                client = LLMClient()
                raw = client.generate(
                    msgs,
                    temperature=(0.8 if randomize else 0.4),
                    top_p=0.9 if randomize else None,
                    max_tokens=240,
                )
                text = clean_legal_response(raw)
                break
            except Exception as e:
                last_err = e
                # Backoff on transient errors (rate limits/network)
                time.sleep(0.25 * (2 ** i))
                text = None
        if not text:
            # Fallback: try today's cached daily for this field (if exists), else yesterday's
            try:
                for day in [d, d - timedelta(days=1)]:
                    cached = read_for_day(day)
                    if cached and cached.get("items"):
                        for it in cached["items"]:
                            if it.get("field") == field and it.get("content"):
                                text = clean_legal_response(it.get("content"))
                                raise StopIteration  # break out of nested loops
            except StopIteration:
                pass
            except Exception:
                pass
        if not text:
            # Final fallback placeholder (kept short)
            text = "(Temporarily unable to load this item. Please refresh.)"
        first_line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
        base_title = first_line.rstrip(":")
        if base_title.lower().startswith("title: "):
            base_title = base_title[7:].strip()
        title = base_title[:80]
        return {"field": field, "title": title, "content": text}

    items: List[Dict] = []
    if randomize:
        # Parallelize random generation for lower latency
        with ThreadPoolExecutor(max_workers=min(3, len(FIELDS))) as ex:
            futures = {ex.submit(build_item, f): f for f in FIELDS}
            for fut in as_completed(futures):
                try:
                    items.append(fut.result())
                except Exception:
                    # On failure, fallback to a minimal placeholder
                    failed_field = futures[fut]
                    items.append({
                        "field": failed_field,
                        "title": "NyayShala",
                        "content": "(Temporarily unable to load this item. Please refresh.)",
                    })
        # Preserve original order of fields
        items.sort(key=lambda x: FIELDS.index(x["field"]))
    else:
        # Sequential for persisted daily (runs at most once per day)
        for field in FIELDS:
            items.append(build_item(field))
    # persist if requested
    if persist:
        with open(_path_for(d), "w", encoding="utf-8") as f:
            json.dump({"date": d.isoformat(), "items": items}, f, ensure_ascii=False, indent=2)
    return items


def generate_random_for_day(d: date) -> List[Dict]:
    """Generate a non-persistent fresh set for the given date (used for random refresh)."""
    return generate_for_day(d, persist=False, randomize=True)


def read_for_day(d: date) -> Dict | None:
    p = _path_for(d)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
