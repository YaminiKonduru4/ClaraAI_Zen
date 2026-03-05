
import os
import json
import time
import argparse
import traceback
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    get_logger, write_json, get_version_dir,
    OUTPUTS_DIR, DATA_DIR, timestamp,
)
from extract_memo import extract_memo
from generate_agent_spec import generate_from_memo
from patch_memo import patch_memo

logger = get_logger("batch_run")



# File discovery

def discover_files(base_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return (demo_files, onboarding_files) sorted lists."""
    demo_files = sorted(
        [f for f in base_dir.rglob("*.txt") if "demo" in f.name.lower()]
        + [f for f in base_dir.rglob("*.md") if "demo" in f.name.lower()]
    )
    onboarding_files = sorted(
        [f for f in base_dir.rglob("*.txt") if "onboarding" in f.name.lower()]
        + [f for f in base_dir.rglob("*.md") if "onboarding" in f.name.lower()]
    )
    return demo_files, onboarding_files


def match_pairs(demo_files: list[Path], onboarding_files: list[Path]) -> list[tuple]:
   
    pairs = []
    used_onboarding = set()

    for df in demo_files:
        demo_stem = df.stem.lower().replace("_demo", "").replace("demo_", "").replace("demo", "")
        best_match = None
        for of in onboarding_files:
            if id(of) in used_onboarding:
                continue
            ob_stem = of.stem.lower().replace("_onboarding", "").replace("onboarding_", "").replace("onboarding", "")
            if demo_stem and ob_stem and (demo_stem in ob_stem or ob_stem in demo_stem):
                best_match = of
                break
        pairs.append((df, best_match))
        if best_match:
            used_onboarding.add(id(best_match))

    unmatched_ob = [of for of in onboarding_files if id(of) not in used_onboarding]
    for i, (df, ob) in enumerate(pairs):
        if ob is None and unmatched_ob:
            pairs[i] = (df, unmatched_ob.pop(0))

    return pairs



# Per-account pipeline

def run_account(demo_file: Path | None, onboarding_file: Path | None,
                account_id: str | None = None) -> dict:
    result = {
        "account_id": account_id,
        "demo_file": str(demo_file) if demo_file else None,
        "onboarding_file": str(onboarding_file) if onboarding_file else None,
        "pipeline_a_status": "skipped",
        "pipeline_b_status": "skipped",
        "error": None,
    }

    try:
        # ── Pipeline A: Demo → v1 memo + v1 agent spec ──────────────────────
        if demo_file:
            logger.info(f"[Pipeline A] {demo_file.name}")
            v1_memo = extract_memo(str(demo_file), call_type="demo",
                                   account_id=account_id)
            account_id = v1_memo["account_id"]
            result["account_id"] = account_id

            v1_dir = get_version_dir(account_id, "v1")
            v1_memo_path = v1_dir / "account_memo.json"
            generate_from_memo(str(v1_memo_path), version="v1")
            result["pipeline_a_status"] = "success"
        else:
            logger.warning("No demo file – skipping Pipeline A.")

        # ── Pipeline B: Onboarding → v2 memo + v2 agent spec ────────────────
        if onboarding_file and account_id:
            logger.info(f"[Pipeline B] {onboarding_file.name}")
            ob_memo = extract_memo(str(onboarding_file), call_type="onboarding",
                                   account_id=account_id)

            v1_memo_path = get_version_dir(account_id, "v1") / "account_memo.json"
            ob_memo_path = get_version_dir(account_id, "v1_onboarding_raw") / "account_memo.json"

            if not v1_memo_path.exists():
                raise FileNotFoundError(f"v1 memo not found: {v1_memo_path}")

            v2_memo, _ = patch_memo(str(v1_memo_path), str(ob_memo_path))
            v2_dir = get_version_dir(account_id, "v2")
            generate_from_memo(str(v2_dir / "account_memo.json"), version="v2")
            result["pipeline_b_status"] = "success"
        elif onboarding_file:
            logger.warning(f"No account_id yet – cannot run Pipeline B.")

    except Exception as e:
        logger.error(f"Error processing account: {e}")
        result["error"] = traceback.format_exc()

    
    if account_id:
        _write_task_item(account_id, result)

    return result



# Task tracker

def _write_task_item(account_id: str, result: dict) -> None:
    
    a_ok = result["pipeline_a_status"] == "success"
    b_ok = result["pipeline_b_status"] == "success"

    if b_ok:
        status = "Onboarding Processed"
        version = "v2"
        next_step = "Review v2 agent spec and schedule Retell import"
    elif a_ok:
        status = "Demo Processed"
        version = "v1"
        next_step = "Await onboarding call transcript"
    else:
        status = "Processing Failed"
        version = "unknown"
        next_step = "Check error log and re-run pipeline"

    memo_path = get_version_dir(account_id, "v1") / "account_memo.json"
    company_name = account_id  
    try:
        import json as _json
        memo_data = _json.loads(memo_path.read_text(encoding="utf-8"))
        company_name = memo_data.get("company_name") or account_id
    except Exception:
        pass

    task_item = {
        "account": company_name,
        "account_id": account_id,
        "status": status,
        "agent_version": version,
        "pipeline_a_status": result["pipeline_a_status"],
        "pipeline_b_status": result["pipeline_b_status"],
        "next_step": next_step,
        "created_at": timestamp(),
    }

    task_path = OUTPUTS_DIR / account_id / "task_item.json"
    write_json(task_item, task_path)
    logger.info(f"Task item written → {task_path}")



# Batch summary
def write_batch_summary(results: list[dict]) -> None:
    summary = {
        "run_at": timestamp(),
        "total_accounts": len(results),
        "pipeline_a": {
            "success": sum(1 for r in results if r["pipeline_a_status"] == "success"),
            "failed": sum(1 for r in results if r["pipeline_a_status"] == "failed"),
            "skipped": sum(1 for r in results if r["pipeline_a_status"] == "skipped"),
        },
        "pipeline_b": {
            "success": sum(1 for r in results if r["pipeline_b_status"] == "success"),
            "failed": sum(1 for r in results if r["pipeline_b_status"] == "failed"),
            "skipped": sum(1 for r in results if r["pipeline_b_status"] == "skipped"),
        },
        "accounts": results,
    }
    out_path = OUTPUTS_DIR.parent / "batch_summary.json"
    write_json(summary, out_path)
    logger.info(f"Batch summary → {out_path}")

    # Print table
    print("\n" + "=" * 60)
    print(f"  BATCH RUN SUMMARY  |  {summary['run_at']}")
    print("=" * 60)
    print(f"  Total accounts : {summary['total_accounts']}")
    print(f"  Pipeline A     : ✅ {summary['pipeline_a']['success']}  ❌ {summary['pipeline_a']['failed']}  ⏭ {summary['pipeline_a']['skipped']}")
    print(f"  Pipeline B     : ✅ {summary['pipeline_b']['success']}  ❌ {summary['pipeline_b']['failed']}  ⏭ {summary['pipeline_b']['skipped']}")
    print("=" * 60)
    for r in results:
        a_icon = "✅" if r["pipeline_a_status"] == "success" else ("❌" if r["pipeline_a_status"] == "failed" else "⏭")
        b_icon = "✅" if r["pipeline_b_status"] == "success" else ("❌" if r["pipeline_b_status"] == "failed" else "⏭")
        print(f"  {r['account_id'] or 'unknown':40s}  A:{a_icon}  B:{b_icon}")
    print("=" * 60 + "\n")



# CLI
def main() -> None:
    parser = argparse.ArgumentParser(description="Batch run Clara AI pipeline on all transcripts")
    parser.add_argument("--base-dir", default=str(DATA_DIR),
                        help="Base directory containing transcript files")
    parser.add_argument("--demo-dir", default=None, help="Override demo transcripts directory")
    parser.add_argument("--onboarding-dir", default=None, help="Override onboarding transcripts directory")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds to wait between accounts (avoids rate limits)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)

    if args.demo_dir or args.onboarding_dir:
        demo_dir = Path(args.demo_dir) if args.demo_dir else base_dir
        ob_dir = Path(args.onboarding_dir) if args.onboarding_dir else base_dir
        demo_files, _ = discover_files(demo_dir)
        _, onboarding_files = discover_files(ob_dir)
    else:
        demo_files, onboarding_files = discover_files(base_dir)

    if not demo_files and not onboarding_files:
        logger.error(f"No transcript files found in: {base_dir}")
        logger.info("Place .txt files named *_demo.txt and *_onboarding.txt in data/transcripts/")
        return

    pairs = match_pairs(demo_files, onboarding_files)
    logger.info(f"Found {len(demo_files)} demo + {len(onboarding_files)} onboarding files → {len(pairs)} pairs")

    results = []
    for i, (demo_file, ob_file) in enumerate(pairs, 1):
        logger.info(f"\n{'─'*50}\n[{i}/{len(pairs)}] Processing pair: {getattr(demo_file, 'name', 'N/A')} + {getattr(ob_file, 'name', 'N/A')}\n{'─'*50}")
        result = run_account(demo_file, ob_file)
        results.append(result)
        if i < len(pairs):
            time.sleep(args.delay)  

    write_batch_summary(results)


if __name__ == "__main__":
    main()
