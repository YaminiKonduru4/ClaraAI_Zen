# Changelog: acct_midwest_alarm_systems_inc_3e8dc8

**From:** v1  →  **To:** v2
**Generated at:** 2026-03-04T11:22:24.909893Z
**Total changes:** 11

---

## Changes
- 🔄 **MODIFIED** `after_hours_flow_summary`: `Greet caller; identify if emergency. Emergencies (Sales Rep: And how do you handle after-hours calls today?...): collect name, number, address → transfer to on-call technician; if transfer fails after 60s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.` → `Greet caller; identify if emergency. Emergencies (definition — confirmed fire alarm, CO alarm...): collect name, number, address → transfer to 217-555-0177; if transfer fails after 30s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.`
- 🔄 **MODIFIED** `call_transfer_rules.retries`: `None` → `2`
- 🔄 **MODIFIED** `call_transfer_rules.timeout_seconds`: `None` → `30`
- 🔄 **MODIFIED** `emergency_definition`: `['Sales Rep: And how do you handle after-hours calls today?']` → `['definition — confirmed fire alarm', 'CO alarm', 'actual smoke or detection?']`
- 🔄 **MODIFIED** `emergency_routing_rules.order`: `[]` → `['217-555-0177']`
- 🔄 **MODIFIED** `emergency_routing_rules.primary_contact`: `None` → `217-555-0177`
- 🔄 **MODIFIED** `integration_constraints`: `['ServiceTitan integration required — do not create or modify records']` → `['Do not create or modify records in ServiceTitan']`
- 🔄 **MODIFIED** `non_emergency_routing_rules.primary_contact`: `None` → `217-555-0100`
- 🔄 **MODIFIED** `office_hours_flow_summary`: `Office open Monday - Friday 8 AM–6 PM Central. Greet caller, identify purpose, collect name & number. Emergencies → transfer to on-call technician. Non-emergencies → route to main office line. Wrap-up confirm next steps.` → `Office open Monday - Friday 8 AM–6 PM Central. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 217-555-0177. Non-emergencies → route to main office line. Wrap-up confirm next steps.`
- 🔄 **MODIFIED** `services_supported`: `['inspection', 'alarm systems']` → `['alarm systems']`
- 🔄 **MODIFIED** `transcript_source`: `midwest_alarm_demo.txt` → `midwest_alarm_onboarding.txt`