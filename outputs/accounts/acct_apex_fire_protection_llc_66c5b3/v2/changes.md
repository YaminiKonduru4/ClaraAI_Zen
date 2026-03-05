# Changelog: acct_apex_fire_protection_llc_66c5b3

**From:** v1  →  **To:** v2
**Generated at:** 2026-03-04T11:34:16.925082Z
**Total changes:** 11

---

## Changes
- 🔄 **MODIFIED** `after_hours_flow_summary`: `Greet caller; identify if emergency. Emergencies (calls. We have a dedicated on-call guy, but callers don't always get straight through...): collect name, number, address → transfer to on-call technician; if transfer fails after 60s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.` → `Greet caller; identify if emergency. Emergencies (what exactly should Clara treat as a confirmed emergency?...): collect name, number, address → transfer to 614-555-0182; if transfer fails after 45s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.`
- 🔄 **MODIFIED** `call_transfer_rules.retries`: `None` → `2`
- 🔄 **MODIFIED** `call_transfer_rules.timeout_seconds`: `None` → `45`
- 🔄 **MODIFIED** `emergency_definition`: `['calls. We have a dedicated on-call guy', "but callers don't always get straight through"]` → `['what exactly should Clara treat as a confirmed emergency?']`
- 🔄 **MODIFIED** `emergency_routing_rules.order`: `[]` → `['614-555-0182', '614-555-0291']`
- 🔄 **MODIFIED** `emergency_routing_rules.primary_contact`: `None` → `614-555-0182`
- 🔄 **MODIFIED** `integration_constraints`: `['ServiceTrade integration required — do not create or modify records']` → `['Do not create or modify records in ServiceTrade']`
- 🔄 **MODIFIED** `non_emergency_routing_rules.primary_contact`: `None` → `614-555-0100`
- 🔄 **MODIFIED** `office_hours_flow_summary`: `Office open Monday - Friday 7 AM–5 PM Eastern. Greet caller, identify purpose, collect name & number. Emergencies → transfer to on-call technician. Non-emergencies → route to main office line. Wrap-up confirm next steps.` → `Office open Monday - Friday 7 AM–5 PM Eastern. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 614-555-0182. Non-emergencies → route to main office line. Wrap-up confirm next steps.`
- 🔄 **MODIFIED** `services_supported`: `['fire protection', 'sprinkler installation', 'fire alarm monitoring', 'fire suppression', 'inspection']` → `['fire protection', 'fire alarm monitoring', 'inspection']`
- 🔄 **MODIFIED** `transcript_source`: `apex_fire_demo.txt` → `apex_fire_onboarding.txt`