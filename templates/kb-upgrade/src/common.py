#!/usr/bin/env python3
"""Shared utilities for knowledge base modules."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


DEFAULT_PROVIDER_API_BASE_URL = "https://openrouter.ai/api/v1"


def default_kb_root() -> Path:
    """Return default KB root path."""
    return Path.cwd() / "intelligence-kb"


def ensure_kb_dirs(kb_root: Path) -> None:
    """Create all required KB directories."""
    required = [
        "entities/labs",
        "entities/models",
        "entities/people",
        "entities/companies",
        "entities/investors",
        "entities/regulators",
        "themes",
        "opportunities",
        "digests/incoming",
        "digests/processed",
        "digests/archive",
        "indexes/vector-store",
        "reports/weekly",
        "reports/snapshots",
        "config",
        "logs",
    ]
    for rel in required:
        (kb_root / rel).mkdir(parents=True, exist_ok=True)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, content
    return data, match.group(2)


def dump_frontmatter(frontmatter: Dict[str, Any], body: str) -> str:
    """Serialize YAML frontmatter and markdown body."""
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False)
    return f"---\n{fm}---\n\n{body.strip()}\n"


def slugify(value: str) -> str:
    """Slugify name to filename."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-\s]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "entity"


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today_iso() -> str:
    return datetime.utcnow().date().isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def list_entity_files(kb_root: Path) -> List[Path]:
    files: List[Path] = []
    base = kb_root / "entities"
    if base.exists():
        for p in base.rglob("*.md"):
            files.append(p)
    themes = kb_root / "themes"
    if themes.exists():
        files.extend(sorted(themes.rglob("*.md")))
    return sorted(files)


def read_config(kb_root: Path) -> Dict[str, Any]:
    config_path = kb_root / "config" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def provider_api_base_url() -> str:
    """Return the provider API base URL with a safe default."""
    base_url = os.getenv("MODEL_PROVIDER_API_BASE_URL", "").strip()
    if not base_url:
        return DEFAULT_PROVIDER_API_BASE_URL
    return base_url.rstrip("/")


def provider_api_url(path: str) -> str:
    """Build a provider API URL from the configured base."""
    return f"{provider_api_base_url()}/{path.lstrip('/')}"


def find_api_key() -> str:
    """Read embedding provider API key from env or .env."""
    key = os.getenv("EMBEDDING_PROVIDER_KEY", "").strip()
    if key:
        return key
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("EMBEDDING_PROVIDER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    parent_env = Path.cwd().parent / ".env"
    if parent_env.exists():
        for line in parent_env.read_text(encoding="utf-8").splitlines():
            if line.startswith("EMBEDDING_PROVIDER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")
