# Changelog: acct_statewide_sprinkler_co_a95758

**From:** v1  →  **To:** v2
**Generated at:** 2026-03-04T10:47:22.655856Z
**Total changes:** 12

---

## Changes
- 🔄 **MODIFIED** `after_hours_flow_summary`: `Greet caller; identify if emergency. Emergencies (just... waits...): collect name, number, address → transfer to on-call technician; if transfer fails after 60s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.` → `Greet caller; identify if emergency. Emergencies (types — sprinkler head discharge, fire alarm connected to suppression...): collect name, number, address → transfer to 480-555-0144; if transfer fails after 45s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.`
- 🔄 **MODIFIED** `business_hours.end`: `None` → `3:30 PM`
- 🔄 **MODIFIED** `business_hours.start`: `None` → `7 AM`
- 🔄 **MODIFIED** `call_transfer_rules.timeout_seconds`: `None` → `45`
- 🔄 **MODIFIED** `emergency_definition`: `['just... waits']` → `['types — sprinkler head discharge', 'fire alarm connected to suppression', "audible water flow where it shouldn't be?"]`
- 🔄 **MODIFIED** `emergency_routing_rules.order`: `[]` → `['480-555-0144', '480-555-0376', '480-555-0100']`
- 🔄 **MODIFIED** `emergency_routing_rules.primary_contact`: `None` → `480-555-0144`
- 🔄 **MODIFIED** `integration_constraints`: `['ServiceTrade integration required — do not create or modify records']` → `['Do not create or modify records in ServiceTrade']`
- 🔄 **MODIFIED** `non_emergency_routing_rules.primary_contact`: `None` → `480-555-0100`
- 🔄 **MODIFIED** `office_hours_flow_summary`: `Office open Monday - Friday business hours start–business hours end Mst. Greet caller, identify purpose, collect name & number. Emergencies → transfer to on-call technician. Non-emergencies → route to main office line. Wrap-up confirm next steps.` → `Office open Monday - Friday 7 AM–3:30 PM Mst. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 480-555-0144. Non-emergencies → route to main office line. Wrap-up confirm next steps.`
- 🔄 **MODIFIED** `services_supported`: `['sprinkler installation', 'fire suppression', 'inspection']` → `['fire suppression', 'inspection']`
- 🔄 **MODIFIED** `transcript_source`: `statewide_sprinkler_demo.txt` → `statewide_sprinkler_onboarding.txt`