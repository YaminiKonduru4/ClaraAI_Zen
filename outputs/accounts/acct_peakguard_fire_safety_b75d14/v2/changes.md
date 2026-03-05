# Changelog: acct_peakguard_fire_safety_b75d14

**From:** v1  →  **To:** v2
**Generated at:** 2026-03-04T11:27:42.932142Z
**Total changes:** 11

---

## Changes
- 🔄 **MODIFIED** `after_hours_flow_summary`: `Greet caller; identify if emergency. Emergencies (We've had technicians dispatched on nuisance calls, missed a real leak once...): collect name, number, address → transfer to on-call technician; if transfer fails after 60s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.` → `Greet caller; identify if emergency. Emergencies (types — active sprinkler discharge, fire suppression trigger...): collect name, number, address → transfer to 720-555-0148; if transfer fails after 40s, assure callback within 10 min. Non-emergencies: collect name, number, issue → confirm next-business-day callback.`
- 🔄 **MODIFIED** `call_transfer_rules.timeout_seconds`: `None` → `40`
- 🔄 **MODIFIED** `call_transfer_rules.transfer_fail_message`: `None` → `We've paged our emergency dispatch team and someone will contact you within 15 minutes. If there is immediate danger to life or property, please call 911.`
- 🔄 **MODIFIED** `emergency_definition`: `["We've had technicians dispatched on nuisance calls", 'missed a real leak once']` → `['types — active sprinkler discharge', 'fire suppression trigger', 'confirmed fire alarm at monitored site', 'kitchen hood suppression activation?']`
- 🔄 **MODIFIED** `emergency_routing_rules.fallback`: `None` → `We've paged our emergency dispatch team and someone will contact you within 15 minutes. If there is immediate danger to life or property, please call 911.`
- 🔄 **MODIFIED** `emergency_routing_rules.order`: `[]` → `['720-555-0148', '720-555-0263', '720-555-0391']`
- 🔄 **MODIFIED** `emergency_routing_rules.primary_contact`: `None` → `720-555-0148`
- 🔄 **MODIFIED** `non_emergency_routing_rules.primary_contact`: `None` → `720-555-0391`
- 🔄 **MODIFIED** `office_hours_flow_summary`: `Office open Monday - Friday 7:30 AM–5 PM Mountain. Greet caller, identify purpose, collect name & number. Emergencies → transfer to on-call technician. Non-emergencies → route to main office line. Wrap-up confirm next steps.` → `Office open Monday - Friday 7:30 AM–5 PM Mountain. Greet caller, identify purpose, collect name & number. Emergencies → transfer to 720-555-0148. Non-emergencies → route to main office line. Wrap-up confirm next steps.`
- 🔄 **MODIFIED** `services_supported`: `['fire suppression', 'inspection']` → `['fire suppression']`
- 🔄 **MODIFIED** `transcript_source`: `peakguard_fire_demo.txt` → `peakguard_fire_onboarding.txt`