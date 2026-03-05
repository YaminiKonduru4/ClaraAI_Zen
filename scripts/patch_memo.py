
import json
import argparse
from pathlib import Path

from utils import (
    get_logger, read_json, write_json, write_text,
    ensure_version_dir, dict_diff, build_changelog,
    get_version_dir, timestamp, CHANGELOG_DIR,
)

logger = get_logger("patch_memo")



# Deep merge logic

def deep_merge(base: dict, updates: dict) -> dict:
    
    result = dict(base)
    for key, new_val in updates.items():
        if key == "questions_or_unknowns":
            # Merge and deduplicate questions
            existing = result.get(key) or []
            incoming = new_val or []
            result[key] = list(dict.fromkeys(existing + incoming))
            continue
        if new_val is None:
            # Don't overwrite existing value with null
            continue
        existing_val = result.get(key)
        if isinstance(new_val, dict) and isinstance(existing_val, dict):
            result[key] = deep_merge(existing_val, new_val)
        else:
            result[key] = new_val
    return result



# Main patch flow

def patch_memo(v1_memo_path: str, onboarding_memo_path: str) -> tuple[dict, dict]:
    
    v1 = read_json(v1_memo_path)
    onboarding = read_json(onboarding_memo_path)
    account_id = v1["account_id"]

    logger.info(f"Patching account: {account_id} → v2")

    # Merge onboarding data into v1
    v2 = deep_merge(v1, onboarding)

    # Update metadata
    v2["account_id"] = account_id
    v2["call_type"] = "onboarding_confirmed"
    v2["version"] = "v2"
    v2["patched_at"] = timestamp()
    v2["patched_from"] = {
        "v1_source": str(v1_memo_path),
        "onboarding_source": str(onboarding_memo_path),
    }

    # Compute diff / changelog
    changes = dict_diff(v1, v2)
    # Filter out metadata-only changes to keep changelog meaningful
    meta_keys = {"patched_at", "version", "call_type", "patched_from", "extracted_at"}
    meaningful_changes = [c for c in changes if c["path"].split(".")[0] not in meta_keys]

    changelog = build_changelog(account_id, meaningful_changes, "v1", "v2")

    # Write outputs
    v2_dir = ensure_version_dir(account_id, "v2")
    write_json(v2, v2_dir / "account_memo.json")
    write_json(changelog, v2_dir / "changes.json")

    # Human-readable changelog
    md_lines = [
        f"# Changelog: {account_id}",
        f"",
        f"**From:** v1  →  **To:** v2",
        f"**Generated at:** {changelog['generated_at']}",
        f"**Total changes:** {changelog['total_changes']}",
        f"",
        f"---",
        f"",
        f"## Changes",
    ]
    for ch in meaningful_changes:
        action = ch["action"].upper()
        path = ch["path"]
        old = ch["old"]
        new = ch["new"]
        if action == "ADDED":
            md_lines.append(f"- ✅ **ADDED** `{path}`: `{new}`")
        elif action == "REMOVED":
            md_lines.append(f"- 🗑️ **REMOVED** `{path}`: was `{old}`")
        else:
            md_lines.append(f"- 🔄 **MODIFIED** `{path}`: `{old}` → `{new}`")

    if not meaningful_changes:
        md_lines.append("_No meaningful changes detected between v1 and v2._")

    write_text("\n".join(md_lines), v2_dir / "changes.md")

    # Also write to top-level changelog dir
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    write_text("\n".join(md_lines), CHANGELOG_DIR / f"{account_id}_v1_to_v2.md")
    write_json(changelog, CHANGELOG_DIR / f"{account_id}_v1_to_v2.json")

    logger.info(f"v2 memo + changelog saved for: {account_id}")
    return v2, changelog



# CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Patch a v1 Account Memo with onboarding data → v2"
    )
    parser.add_argument("v1_memo", help="Path to v1/account_memo.json")
    parser.add_argument("onboarding_memo", help="Path to v1_onboarding_raw/account_memo.json")
    args = parser.parse_args()

    v2_memo, changelog = patch_memo(args.v1_memo, args.onboarding_memo)
    print("=== v2 Memo ===")
    print(json.dumps(v2_memo, indent=2, default=str))
    print("\n=== Changelog ===")
    print(json.dumps(changelog, indent=2, default=str))
