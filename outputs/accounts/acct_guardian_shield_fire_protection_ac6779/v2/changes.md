# Changelog: acct_guardian_shield_fire_protection_ac6779

**From:** v1  →  **To:** v2
**Generated at:** 2026-03-04T11:39:40.791258Z
**Total changes:** 9

---

## Changes
- 🔄 **MODIFIED** `after_hours_flow_summary`: `Greet caller; identify if emergency. Emergencies (service. About 50 employees, mostly field technicians...): collect name, number, address → transfer to 404-555-0155; if transfer fails after 60s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.` → `Greet caller; identify if emergency. Emergencies (types — active sprinkler flow, fire/suppression alarm activation...): collect name, number, address → transfer to 404-555-0198; if transfer fails after 45s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.`
- 🔄 **MODIFIED** `call_transfer_rules.timeout_seconds`: `None` → `45`
- 🔄 **MODIFIED** `emergency_definition`: `['service. About 50 employees', 'mostly field technicians']` → `['types — active sprinkler flow', 'fire/suppression alarm activation', 'kitchen suppression trigger', 'active fire event at a monitored property?']`
- 🔄 **MODIFIED** `emergency_routing_rules.order`: `['404-555-0155']` → `['404-555-0198', '404-555-0247']`
- 🔄 **MODIFIED** `emergency_routing_rules.primary_contact`: `404-555-0155` → `404-555-0198`
- 🔄 **MODIFIED** `integration_constraints`: `['ServiceTrade integration required — do not create or modify records']` → `['Do not create or modify records in ServiceTrade']`
- 🔄 **MODIFIED** `office_hours_flow_summary`: `Office open Monday - Friday 8 AM–5 PM Eastern. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 404-555-0155. Non-emergencies → route to main office line. Wrap-up confirm next steps.` → `Office open Monday - Friday 8 AM–5 PM Eastern. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 404-555-0198. Non-emergencies → route to main office line. Wrap-up confirm next steps.`
- 🔄 **MODIFIED** `services_supported`: `['fire protection', 'fire suppression', 'inspection']` → `['fire protection', 'fire suppression']`
- 🔄 **MODIFIED** `transcript_source`: `guardian_shield_demo.txt` → `guardian_shield_onboarding.txt`