"""
utils.py – Shared utilities for the Clara AI Pipeline
"""
import os
import json
import re
import hashlib
import logging
import datetime
from pathlib import Path

# Load .env from project root so GEMINI_API_KEY is always available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on env being pre-set


# Paths

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs" / "accounts"
CHANGELOG_DIR = ROOT_DIR / "changelog"
DATA_DIR = ROOT_DIR / "data" / "transcripts"



# Logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s – %(message)s",
                                datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger("utils")



# Account ID helpers

def slugify(text: str) -> str:
    """Turn a company name into a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


def clean_company_name(name: str) -> str:
    """
    Strip boilerplate suffixes that Gemini may append to company names.
    E.g. 'Apex Fire Protection LLC, based out of Columbus...' → 'Apex Fire Protection LLC'
    """
    import re as _re
    # Cut at common stop phrases (case-insensitive)
    stop_phrases = [
        r",?\s+based (out )?in\b",
        r",?\s+based (out )?of\b",
        r",?\s+located in\b",
        r",?\s+we (are|do|provide|offer|specialize)\b",
        r",?\s+a\s+(fire|electrical|hvac|mechanical|plumbing|security)\b",
        r"\.\s+We\b",
    ]
    for pat in stop_phrases:
        name = _re.split(pat, name, maxsplit=1, flags=_re.IGNORECASE)[0]
    # Also hard-cap at 60 chars to avoid filesystem issues
    name = name.strip().strip(",").strip()
    if len(name) > 60:
        # Try to cut at last word boundary within 60 chars
        name = name[:60].rsplit(" ", 1)[0].strip()
    return name


def generate_account_id(company_name: str, call_type: str = "demo") -> str:
    """
    Deterministic account ID based on company name so the same company
    always maps to the same ID (idempotent).
    """
    clean = clean_company_name(company_name)
    slug = slugify(clean)
    digest = hashlib.md5(slug.encode()).hexdigest()[:6]
    return f"acct_{slug}_{digest}"



# File I/O

def read_text(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def write_json(obj: dict, path: str | Path, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=indent, default=str), encoding="utf-8")
    logger.info(f"Written → {path}")


def read_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(content: str, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info(f"Written → {path}")



# Version helpers

def get_version_dir(account_id: str, version: str = "v1") -> Path:
    return OUTPUTS_DIR / account_id / version


def ensure_version_dir(account_id: str, version: str = "v1") -> Path:
    d = get_version_dir(account_id, version)
    d.mkdir(parents=True, exist_ok=True)
    return d


def timestamp() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"



# Diff helpers

def dict_diff(old: dict, new: dict, path: str = "") -> list[dict]:
    """
    Return a list of change records: {path, action, old, new}
    Recursively walks nested dicts/lists.
    """
    changes = []
    all_keys = set(list(old.keys()) + list(new.keys()))
    for key in sorted(all_keys):
        full_path = f"{path}.{key}" if path else key
        if key not in old:
            changes.append({"path": full_path, "action": "added",
                             "old": None, "new": new[key]})
        elif key not in new:
            changes.append({"path": full_path, "action": "removed",
                             "old": old[key], "new": None})
        elif isinstance(old[key], dict) and isinstance(new[key], dict):
            changes.extend(dict_diff(old[key], new[key], full_path))
        elif old[key] != new[key]:
            changes.append({"path": full_path, "action": "modified",
                             "old": old[key], "new": new[key]})
    return changes


def build_changelog(account_id: str, changes: list[dict],
                    from_version: str = "v1", to_version: str = "v2") -> dict:
    return {
        "account_id": account_id,
        "from_version": from_version,
        "to_version": to_version,
        "generated_at": timestamp(),
        "total_changes": len(changes),
        "changes": changes,
    }
