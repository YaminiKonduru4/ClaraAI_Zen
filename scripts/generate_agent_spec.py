"""
generate_agent_spec.py – Generate Retell Agent Draft Spec from an Account Memo.

Output: JSON + YAML that matches how a Retell agent would be configured.
"""
import os
import json
import argparse
from pathlib import Path

import yaml  # pip install pyyaml

from utils import (
    get_logger, read_json, write_json, write_text,
    ensure_version_dir, timestamp,
)

logger = get_logger("generate_agent_spec")



# Prompt builder – creates the system prompt for the Retell agent

def build_system_prompt(memo: dict) -> str:
    company = memo.get("company_name") or "the company"
    bh = memo.get("business_hours") or {}
    days = bh.get("days") or "Monday through Friday"
    start = bh.get("start") or "8:00 AM"
    end = bh.get("end") or "5:00 PM"
    tz = bh.get("timezone") or "your local time"

    services = memo.get("services_supported") or []
    services_str = ", ".join(services) if services else "fire protection and related services"

    emergency_defs = memo.get("emergency_definition") or []
    emergency_str = "; ".join(emergency_defs) if emergency_defs else "active sprinkler leak, fire alarm activation, imminent fire hazard"

    err = memo.get("emergency_routing_rules") or {}
    transfer_primary = err.get("primary_contact") or "{{emergency_contact_number}}"
    transfer_order = err.get("order") or [transfer_primary]
    transfer_fallback = err.get("fallback") or "Apologize and assure the caller that the on-call dispatcher will follow up within 10 minutes."

    ctr = memo.get("call_transfer_rules") or {}
    timeout = ctr.get("timeout_seconds") or 60
    fail_msg = ctr.get("transfer_fail_message") or "I apologize, I wasn't able to reach the on-call technician right now."

    nerr = memo.get("non_emergency_routing_rules") or {}
    ne_primary = nerr.get("primary_contact") or "{{main_office_number}}"

    integration_constraints = memo.get("integration_constraints") or []
    constraints_section = ""
    if integration_constraints:
        constraints_section = (
            "\n\nINTEGRATION CONSTRAINTS (INTERNAL - do not mention to caller):\n"
            + "\n".join(f"- {c}" for c in integration_constraints)
        )

    office_address = memo.get("office_address") or "{{office_address}}"
    notes = memo.get("notes") or ""
    questions = memo.get("questions_or_unknowns") or []

    prompt = f"""# Clara AI Voice Agent – {company}

## Identity
You are Clara, the AI-powered receptionist for {company}. You handle inbound calls professionally and efficiently. You provide a warm, concise, and helpful experience. You never mention that you are an AI unless directly asked.

## Services
{company} provides: {services_str}.

## Office Information
- Address: {office_address}
- Business Hours: {days}, {start} to {end} ({tz})

## IMPORTANT BEHAVIORAL RULES
- NEVER mention "function calls", "system calls", "tools", or any internal technical operations to the caller.
- Do NOT ask multiple questions in one turn. Ask one question at a time.
- Collect only what is needed for routing and dispatch. Do not probe for unnecessary details.
- Keep responses concise. No lengthy explanations.
- Always be empathetic during emergencies.

---

## BUSINESS HOURS CALL FLOW

**Step 1 – Greeting**
"Thank you for calling {company}, this is Clara. How can I help you today?"

**Step 2 – Understand Purpose**
Listen to the caller's need. Determine if it is an emergency or non-emergency.

**Step 3 – Collect Name and Callback Number**
"Can I get your name and the best number to reach you?"

**Step 4 – Route / Transfer**
- For emergencies: Transfer to on-call immediately.
  - Transfer order: {', '.join(str(x) for x in transfer_order)}
  - Timeout: {timeout} seconds before trying next.
- For non-emergency: Route to office.
  - Transfer to: {ne_primary}

**Step 5 – Fallback if Transfer Fails**
If transfer is unsuccessful after all attempts:
"{fail_msg}. I've recorded your name and callback number and someone will follow up with you shortly."
Then log the interaction.

**Step 6 – Wrap-Up**
"Is there anything else I can help you with today?"
If no: "Thank you for calling {company}. Have a great day!"

---

## AFTER-HOURS CALL FLOW

**Step 1 – Greeting**
"Thank you for calling {company}. Our office is currently closed. We are open {days}, from {start} to {end} {tz}. This is Clara, the AI assistant. How can I help you?"

**Step 2 – Understand Purpose**
Listen carefully. Determine if this is an emergency.

**Step 3 – Emergency Check**
If the caller indicates an emergency (e.g., {emergency_str}):
→ Confirm: "I understand. Is this an active emergency such as a sprinkler leak or fire alarm?"

**Step 4A – IF EMERGENCY:**
"I'm going to connect you with our on-call technician right away."
- Collect (in order, quickly):
  1. Full name
  2. Callback number
  3. Address or location of the issue
- Immediately initiate transfer to on-call: {', '.join(str(x) for x in transfer_order)}
- Timeout: {timeout} seconds.
- **If transfer fails:**
  "{fail_msg} I have your information and our on-call team will call you back as quickly as possible. Please stay safe."

**Step 4B – IF NON-EMERGENCY:**
"I understand. Since our office is currently closed, let me collect your information and we'll follow up during business hours."
- Collect: Name, callback number, brief description of the issue.
- Confirm: "We will reach out to you during our next business day. Is there anything else I can help you with?"

**Step 5 – Close**
"Thank you for calling {company}. Stay safe and we'll be in touch soon."

---{constraints_section}

## EMERGENCY DEFINITIONS
The following are considered emergencies and must be escalated immediately:
{emergency_str}

## NOTES
{notes if notes else "None."}
"""
    if questions:
        prompt += f"\n## OPEN QUESTIONS (config team to resolve before go-live)\n"
        for q in questions:
            prompt += f"- {q}\n"

    return prompt.strip()



# Agent spec builder

def generate_agent_spec(memo: dict, version: str = "v1") -> dict:
    system_prompt = build_system_prompt(memo)
    bh = memo.get("business_hours") or {}
    err = memo.get("emergency_routing_rules") or {}
    ctr = memo.get("call_transfer_rules") or {}

    spec = {
        "agent_name": f"{memo.get('company_name', 'Unknown')} – Clara Agent",
        "version": version,
        "generated_at": timestamp(),
        "account_id": memo.get("account_id"),
        "voice_style": {
            "model": "eleven_turbo_v2_5",
            "voice": "rachel",  # warm, professional female voice
            "speed": 1.0,
            "language": "en-US",
        },
        "system_prompt": system_prompt,
        "key_variables": {
            "company_name": memo.get("company_name"),
            "timezone": bh.get("timezone"),
            "business_hours_days": bh.get("days"),
            "business_hours_start": bh.get("start"),
            "business_hours_end": bh.get("end"),
            "office_address": memo.get("office_address"),
            "emergency_contact_number": err.get("primary_contact"),
            "emergency_transfer_order": err.get("order", []),
            "transfer_timeout_seconds": ctr.get("timeout_seconds", 60),
        },
        "tool_invocation_placeholders": [
            {
                "name": "transfer_call",
                "description": "Transfer the call to a live operator or on-call technician. Never mention this to the caller.",
                "parameters": {
                    "target_number": "string",
                    "timeout_seconds": "integer",
                },
            },
            {
                "name": "log_call",
                "description": "Log call details (name, number, issue) to the backend. Never mention this to the caller.",
                "parameters": {
                    "caller_name": "string",
                    "callback_number": "string",
                    "issue_description": "string",
                    "call_type": "string",   # emergency | non_emergency
                    "timestamp": "string",
                },
            },
        ],
        "call_transfer_protocol": {
            "primary_number": err.get("primary_contact"),
            "fallback_numbers": err.get("order", []),
            "timeout_seconds": ctr.get("timeout_seconds", 60),
            "retries": ctr.get("retries", 1),
            "message_on_transfer": "Please hold while I connect you with our on-call technician.",
            "message_on_transfer_fail": ctr.get("transfer_fail_message",
                "I'm sorry, I wasn't able to connect you right now. Your information has been recorded."),
        },
        "fallback_protocol": {
            "trigger": "transfer_fail_after_all_retries",
            "actions": [
                "Acknowledge caller with empathy",
                "Confirm name and callback number were captured",
                "Assure follow-up within 10 minutes for emergencies",
                "Assure follow-up during business hours for non-emergencies",
                "End call gracefully",
            ],
        },
        "questions_or_unknowns": memo.get("questions_or_unknowns", []),
    }
    return spec



# Main entry point

def generate_from_memo(memo_path: str, version: str = "v1") -> dict:
    memo = read_json(memo_path)
    account_id = memo["account_id"]

    spec = generate_agent_spec(memo, version)
    out_dir = ensure_version_dir(account_id, version)

    # Save as JSON
    write_json(spec, out_dir / "agent_spec.json")

    # Save as YAML (more readable)
    yaml_path = out_dir / "agent_spec.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info(f"Agent spec saved (JSON + YAML) for account: {account_id} @ {version}")

    # Save raw system prompt separately for easy reading
    write_text(spec["system_prompt"], out_dir / "system_prompt.txt")

    return spec



# CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Retell Agent Spec from memo")
    parser.add_argument("memo", help="Path to account_memo.json")
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    result = generate_from_memo(args.memo, args.version)
    print(json.dumps(result, indent=2, default=str))
