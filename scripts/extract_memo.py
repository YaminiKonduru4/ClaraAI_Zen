
import os
import json
import re
import argparse
from pathlib import Path

from utils import (
    get_logger, read_text, write_json, generate_account_id,
    ensure_version_dir, timestamp, clean_company_name,
)

logger = get_logger("extract_memo")


# Prompt templates

EXTRACTION_PROMPT = """
You are a precise data extraction assistant for Clara Answers, an AI voice agent platform.

You will be given a call transcript (demo or onboarding). Your job is to extract a structured
Account Memo JSON. Be extremely accurate and conservative:

RULES:
- Only extract what is EXPLICITLY stated in the transcript.
- Do NOT invent, assume, or infer any configuration detail that is not clearly mentioned.
- If a field is not mentioned, set it to null.
- If something is ambiguous or unclear, add it to "questions_or_unknowns".
- Do NOT hallucinate phone numbers, names, hours, or routing logic.
- For lists, use empty list [] if nothing is mentioned.

TRANSCRIPT TYPE: {call_type} (demo = preliminary / onboarding = confirmed config)

TRANSCRIPT:
---
{transcript}
---

Return ONLY valid JSON with exactly these fields (no extra text, no markdown fences):
{{
  "account_id": null,
  "company_name": "<legal business name only — e.g. 'Apex Fire Protection LLC' — NOT a full sentence or description>",
  "call_type": "{call_type}",
  "transcript_source": "{source_file}",
  "extracted_at": "{timestamp}",
  "business_hours": {{
    "days": null,
    "start": null,
    "end": null,
    "timezone": null
  }},
  "office_address": null,
  "services_supported": [],
  "emergency_definition": [],
  "emergency_routing_rules": {{
    "primary_contact": null,
    "order": [],
    "fallback": null
  }},
  "non_emergency_routing_rules": {{
    "primary_contact": null,
    "fallback": null
  }},
  "call_transfer_rules": {{
    "timeout_seconds": null,
    "retries": null,
    "transfer_fail_message": null
  }},
  "integration_constraints": [],
  "after_hours_flow_summary": null,
  "office_hours_flow_summary": null,
  "questions_or_unknowns": [],
  "notes": null
}}
"""


# Gemini API extraction

def extract_with_gemini(transcript: str, call_type: str, source_file: str) -> dict:
    try:
        from google import genai
        from google.genai import types # type: ignore
    except ImportError:
        raise ImportError(
            "google-genai not installed. Run: pip install google-genai"
        )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)

    prompt = EXTRACTION_PROMPT.format(
        call_type=call_type,
        transcript=transcript,
        source_file=source_file,
        timestamp=timestamp(),
    )

    logger.info(f"Calling Gemini API for: {source_file}")

    import time as _time
    for attempt in range(4):   # up to 4 attempts
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=4096,
                ),
            )
            break  # success
        except Exception as api_err:
            err_str = str(api_err)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 15 * (attempt + 1)   # 15s, 30s, 45s
                logger.warning(f"Rate limited (429). Waiting {wait}s before retry {attempt+1}/3…")
                _time.sleep(wait)
                if attempt == 3:
                    raise  # give up after 4 attempts
            else:
                raise  # non-rate-limit error — propagate immediately

    raw = response.text.strip()
    # Strip markdown fences if model adds them
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    return json.loads(raw)




# Fallback rule-based extraction  (comprehensive — parses transcript headers + dialogue)

def extract_rule_based(transcript: str, call_type: str, source_file: str) -> dict:
    """
    Comprehensive rule-based extraction that parses transcript structured headers
    and dialogue patterns. Designed to cover ~95% of fields without an LLM.
    """
    logger.info("Using rule-based extraction (enhanced parser).")

    memo = {
        "account_id": None,
        "company_name": None,
        "call_type": call_type,
        "transcript_source": source_file,
        "extracted_at": timestamp(),
        "business_hours": {"days": None, "start": None, "end": None, "timezone": None},
        "office_address": None,
        "services_supported": [],
        "emergency_definition": [],
        "emergency_routing_rules": {"primary_contact": None, "order": [], "fallback": None},
        "non_emergency_routing_rules": {"primary_contact": None, "fallback": "Collect name, number, and issue for next business day callback"},
        "call_transfer_rules": {"timeout_seconds": None, "retries": None, "transfer_fail_message": None},
        "integration_constraints": [],
        "after_hours_flow_summary": None,
        "office_hours_flow_summary": None,
        "questions_or_unknowns": [],
        "notes": "Extracted via enhanced rule-based parser.",
    }

    # ── 1. Company name from header ─────────────────────────────────────────
    company_m = re.search(r"^Company:\s*(.+)$", transcript, re.MULTILINE)
    if company_m:
        memo["company_name"] = company_m.group(1).strip()

    # Fallback: first capitalised entity with LLC/Inc/Corp/Co
    if not memo["company_name"]:
        for pat in [
            r"(?:company(?:\s+name)?(?:\s+is)?|we(?:'re| are)|this is)\s+([A-Z][A-Za-z &'.]+(?:LLC|Inc|Corp|Co\.?))",
            r"\bfor\s+([A-Z][A-Za-z &'.]+(?:LLC|Inc|Corp|Co\.?))",
            r"([A-Z][A-Za-z &'.]+(?:LLC|Inc|Corp|Co\.?))",
        ]:
            m = re.search(pat, transcript)
            if m:
                memo["company_name"] = m.group(1).strip()
                break

    # ── 2. Office address ───────────────────────────────────────────────────
    addr_m = re.search(
        r"\b(\d{3,5}\s+[A-Z][A-Za-z0-9\s,\.]+(?:Blvd|Ave|St|Dr|Rd|Way|Ln|Court|Lane|Road|Boulevard|Street|Drive|Place|Circle)[,\s]+[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})",
        transcript,
    )
    if addr_m:
        memo["office_address"] = addr_m.group(1).strip()

    # ── 3. Business hours ───────────────────────────────────────────────────
    days_m = re.search(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*(?:through|to|–|-)\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
        transcript, re.IGNORECASE,
    )
    if days_m:
        memo["business_hours"]["days"] = f"{days_m.group(1).title()} - {days_m.group(2).title()}"

    time_m = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM))\s*(?:to|–|-)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM))",
        transcript, re.IGNORECASE,
    )
    if time_m:
        memo["business_hours"]["start"] = time_m.group(1).strip()
        memo["business_hours"]["end"] = time_m.group(2).strip()

    tz_m = re.search(
        r"\b(Eastern|Central|Mountain|Pacific|EST|CST|MST|PST|EDT|CDT|MDT|PDT)\b",
        transcript, re.IGNORECASE,
    )
    if tz_m:
        memo["business_hours"]["timezone"] = tz_m.group(1).title()

    # ── 4. Services ─────────────────────────────────────────────────────────
    service_map = {
        "fire protection": ["fire protection", "fire protect"],
        "sprinkler installation": ["sprinkler install"],
        "sprinkler inspection": ["sprinkler inspect"],
        "fire alarm monitoring": ["fire alarm monitor", "alarm monitor"],
        "fire suppression": ["suppression"],
        "inspection": ["inspection"],
        "backflow testing": ["backflow"],
        "extinguisher services": ["extinguisher"],
        "HVAC": ["hvac"],
        "electrical": ["electrical"],
        "security systems": ["security system"],
        "alarm systems": ["alarm system"],
    }
    found_services = []
    tl = transcript.lower()
    for svc, kws in service_map.items():
        if any(kw in tl for kw in kws):
            found_services.append(svc)
    memo["services_supported"] = found_services

    # ── 5. Emergency definitions ────────────────────────────────────────────
    # Extract from explicit list-style dialogue
    emerg_defs = []

    # Pattern: "Active sprinkler leak, fire alarm activation, any smoke detection alert, and CO alarms"
    emerg_section = re.search(
        r"(?:emergency|emergencies)\s*[:\—\-–]?\s*(.{10,400}?)(?:\n\n|\.\s+[A-Z]|$)",
        transcript, re.IGNORECASE | re.DOTALL,
    )
    if emerg_section:
        raw = emerg_section.group(1)
        # Split on commas/and/semicolons
        parts = re.split(r",\s*(?:and\s+)?|;\s*|\band\b", raw)
        for part in parts:
            part = part.strip().strip(".").strip()
            if 5 < len(part) < 120 and part[0].isupper() or part[0].islower():
                emerg_defs.append(part)

    # Keyword-based fallback
    if not emerg_defs:
        kw_map = [
            ("active sprinkler leak", "active sprinkler leak"),
            ("sprinkler leak", "sprinkler leak"),
            ("fire alarm activation", "fire alarm activation"),
            ("fire alarm", "fire alarm"),
            ("smoke detection", "smoke detection alert"),
            ("CO alarm", "CO alarm"),
            ("carbon monoxide", "carbon monoxide"),
            ("fire suppression", "fire suppression trigger"),
            ("sprinkler discharge", "active sprinkler discharge"),
            ("kitchen hood", "kitchen hood suppression"),
        ]
        for needle, label in kw_map:
            if needle.lower() in tl:
                emerg_defs.append(label)

    memo["emergency_definition"] = emerg_defs if emerg_defs else ["fire alarm activation", "active sprinkler leak", "emergency"]

    # ── 6. Phone numbers + named contacts ──────────────────────────────────
    # Find "Name, [role], NNN-NNN-NNNN" or "Name at NNN-NNN-NNNN"
    phone_pattern = r"\b(\d{3}[-.\s]\d{3}[-.\s]\d{4})\b"
    phones = re.findall(phone_pattern, transcript)
    phones = [p.replace(" ", "-").replace(".", "-") for p in phones]

    # Named contact patterns covering transcript styles:
    # "Dave Kowalski. His direct cell is 614-555-0182"
    # "Tom Reyes, at 614-555-0291" | "Carlos Mendez, 217-555-0177"
    # "Primary: Rachel Fong (me), 720-555-0148"
    named_contacts = []
    PHONE = r"(\d{3}[-.]\d{3}[-.]\d{4})"
    name_phone_patterns = [
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)[\s.][^.]{0,60}?(?:cell|number|line|direct)[^.]{0,40}?" + PHONE,
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?:\([^)]*\))?,\s*(?:at\s+)?" + PHONE,
        r"(?:try|backup|contact|call|reach)\s+(?:our\s+)?(?:\w+\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)[^.]{0,40}?" + PHONE,
        r"(?:primary|backup|tertiary|secondary)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)[^.]{0,40}?" + PHONE,
    ]
    for pat in name_phone_patterns:
        for m in re.finditer(pat, transcript):
            named_contacts.append({"name": m.group(1).strip(), "number": m.group(2).strip().replace(" ", "-").replace(".", "-")})

    if named_contacts:
        memo["emergency_routing_rules"]["primary_contact"] = named_contacts[0]["number"]
        memo["emergency_routing_rules"]["order"] = [c["number"] for c in named_contacts]
    elif phones:
        memo["emergency_routing_rules"]["primary_contact"] = phones[0]
        memo["emergency_routing_rules"]["order"] = phones

    # Non-emergency main office line
    ne_m = re.search(
        r"(?:main office|office line|non.emergency)[^.]*?(\d{3}[-.\s]\d{3}[-.\s]\d{4})",
        transcript, re.IGNORECASE,
    )
    if ne_m:
        memo["non_emergency_routing_rules"]["primary_contact"] = ne_m.group(1).replace(" ", "-").replace(".", "-")
    elif len(phones) > len(named_contacts):
        # last phone is often office line
        memo["non_emergency_routing_rules"]["primary_contact"] = phones[-1]

    # ── 7. Transfer timeout & retries ──────────────────────────────────────
    timeout_m = re.search(r"(\d+)[- ]second(?:s)?\s*timeout", transcript, re.IGNORECASE)
    if not timeout_m:
        timeout_m = re.search(r"timeout[^.]*?(\d+)\s*second", transcript, re.IGNORECASE)
    if timeout_m:
        memo["call_transfer_rules"]["timeout_seconds"] = int(timeout_m.group(1))

    retry_m = re.search(r"(\d+)\s*(?:retries|retry|attempts|tries|cycles)", transcript, re.IGNORECASE)
    if retry_m:
        memo["call_transfer_rules"]["retries"] = int(retry_m.group(1))

    # Fallback message for transfer fail
    fail_m = re.search(
        r'"([^"]{20,200}(?:dispatch|call back|follow.?up|minutes|paged)[^"]{0,100})"',
        transcript, re.IGNORECASE,
    )
    if fail_m:
        memo["call_transfer_rules"]["transfer_fail_message"] = fail_m.group(1).strip()

    # Fallback routing message
    fallback_m = re.search(
        r'(?:fallback|fail(?:ure)?|if(?:.*?)(?:fails|no answer))[^.]*?\"([^\"]{10,200})\"',
        transcript, re.IGNORECASE,
    )
    if fallback_m:
        memo["emergency_routing_rules"]["fallback"] = fallback_m.group(1)
    elif memo["call_transfer_rules"].get("transfer_fail_message"):
        memo["emergency_routing_rules"]["fallback"] = memo["call_transfer_rules"]["transfer_fail_message"]

    # ── 8. Integration constraints ──────────────────────────────────────────
    constraints = []
    integration_patterns = [
        (r"never\s+create\s+(?:a\s+)?(?:sprinkler\s+)?(?:jobs?|orders?|profiles?|work orders?)\s+in\s+(Service\w+)", "Never create jobs in {}"),
        (r"(Service\w+)[^.]*?(?:never|not|don.t|should not)[^.]*?(?:create|access|update|touch)", "Do not create or modify records in {}"),
        (r"only\s+(?:our\s+)?(?:office|staff)\s+(?:team\s+)?(?:can\s+)?(?:create|handle)\s+(?:jobs?|orders?)\s+in\s+(Service\w+)", "Only office staff can create jobs in {}"),
    ]
    for pat, label in integration_patterns:
        for m in re.finditer(pat, transcript, re.IGNORECASE):
            constraints.append(label.format(m.group(1)))
    # Generic ServiceTrade/ServiceTitan mentions
    for svc in ["ServiceTrade", "ServiceTitan", "Salesforce", "HubSpot"]:
        if svc.lower() in tl and not any(svc in c for c in constraints):
            constraints.append(f"{svc} integration required — do not create or modify records")
    memo["integration_constraints"] = list(dict.fromkeys(constraints))  # dedupe

    # ── 9. Flow summaries ────────────────────────────────────────────────────
    bh = memo["business_hours"]
    days_str = bh.get("days") or "Monday-Friday"
    start_str = bh.get("start") or "business hours start"
    end_str = bh.get("end") or "business hours end"
    tz_str = bh.get("timezone") or "local time"
    primary = memo["emergency_routing_rules"].get("primary_contact") or "on-call technician"

    memo["after_hours_flow_summary"] = (
        f"Greet caller; identify if emergency. "
        f"Emergencies ({', '.join(memo['emergency_definition'][:2])}...): "
        f"collect name, number, address → transfer to {primary}; "
        f"if transfer fails after {memo['call_transfer_rules'].get('timeout_seconds') or 60}s, "
        f"assure callback within 10 min. "
        f"Non-emergencies: collect name, number, issue → confirm next-business-day callback."
    )
    memo["office_hours_flow_summary"] = (
        f"Office open {days_str} {start_str}–{end_str} {tz_str}. "
        f"Greet caller, identify purpose, collect name & number. "
        f"Emergencies → transfer to {primary}. "
        f"Non-emergencies → route to main office line. "
        f"Wrap-up confirm next steps."
    )

    # ── 10. Open questions ──────────────────────────────────────────────────
    if not memo["business_hours"].get("days"):
        memo["questions_or_unknowns"].append("Business days not confirmed")
    if not memo["business_hours"].get("start"):
        memo["questions_or_unknowns"].append("Business hours start time not confirmed")
    if not memo["emergency_routing_rules"].get("primary_contact"):
        memo["questions_or_unknowns"].append("Emergency contact number not found")
    if not memo["call_transfer_rules"].get("timeout_seconds"):
        memo["questions_or_unknowns"].append("Call transfer timeout not specified — defaulting to 60s")

    return memo



# Main extraction entry point

def extract_memo(transcript_path: str, call_type: str = "demo",
                 account_id: str | None = None) -> dict:
    """
    Extract an Account Memo from a transcript file.
    Returns the memo dict and writes it to the output directory.
    """
    source_file = Path(transcript_path).name
    transcript = read_text(transcript_path)

    # Try Gemini first; fall back to rule-based
    # Set env var USE_GEMINI=false (or pass --no-gemini in batch_run) to skip API
    use_gemini = os.environ.get("USE_GEMINI", "true").lower() not in ("false", "0", "no")
    try:
        if not use_gemini:
            raise ValueError("Gemini disabled via USE_GEMINI=false")
        memo = extract_with_gemini(transcript, call_type, source_file)
    except (ValueError, Exception) as e:
        logger.warning(f"Gemini extraction skipped ({type(e).__name__}). Using enhanced rule-based parser.")
        memo = extract_rule_based(transcript, call_type, source_file)

    # Assign account ID — clean company_name first to avoid garbled slugs
    raw_company = memo.get("company_name") or Path(transcript_path).stem
    clean_name = clean_company_name(raw_company)
    memo["company_name"] = clean_name  # persist the cleaned name
    if account_id:
        memo["account_id"] = account_id
    elif not memo.get("account_id"):
        memo["account_id"] = generate_account_id(clean_name, call_type)

    # Persist
    version = "v1" if call_type == "demo" else "v1_onboarding_raw"
    out_dir = ensure_version_dir(memo["account_id"], version)
    write_json(memo, out_dir / "account_memo.json")
    logger.info(f"Memo saved for account: {memo['account_id']}")
    return memo



# CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Account Memo from transcript")
    parser.add_argument("transcript", help="Path to .txt transcript file")
    parser.add_argument("--call-type", choices=["demo", "onboarding"], default="demo")
    parser.add_argument("--account-id", default=None, help="Force a specific account ID")
    args = parser.parse_args()

    result = extract_memo(args.transcript, args.call_type, args.account_id)
    print(json.dumps(result, indent=2, default=str))
