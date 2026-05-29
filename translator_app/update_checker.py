from __future__ import annotations

import json
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


RELEASES_API_URL = "https://api.github.com/repos/0sterman/AI-LinguaFlow/releases/latest"
DOWNLOAD_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    release_url: str
    installer_url: str
    installer_name: str


def fetch_required_update(current_version: str, timeout_seconds: int = 5) -> UpdateInfo | None:
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LinguaFlowAI-UpdateChecker",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None

    tag_name = str(payload.get("tag_name") or "").strip()
    latest_version = normalize_version(tag_name)
    if not latest_version or compare_versions(latest_version, current_version) <= 0:
        return None

    installer = _find_installer_asset(payload)
    if installer is None:
        return None
    return UpdateInfo(
        version=latest_version,
        release_url=str(payload.get("html_url") or ""),
        installer_url=str(installer.get("browser_download_url") or ""),
        installer_name=str(installer.get("name") or f"LinguaFlow.AI.Setup.v{latest_version}.exe"),
    )


def download_installer(update: UpdateInfo, timeout_seconds: int = DOWNLOAD_TIMEOUT_SECONDS) -> Path:
    target = Path(tempfile.gettempdir()) / safe_filename(update.installer_name)
    request = urllib.request.Request(update.installer_url, headers={"User-Agent": "LinguaFlowAI-UpdateDownloader"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        target.write_bytes(response.read())
    return target


def normalize_version(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    match = re.match(r"^(\d+(?:\.\d+){0,3})", cleaned)
    return match.group(1) if match else ""


def compare_versions(left: str, right: str) -> int:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    max_length = max(len(left_parts), len(right_parts), 1)
    left_parts.extend([0] * (max_length - len(left_parts)))
    right_parts.extend([0] * (max_length - len(right_parts)))
    if left_parts > right_parts:
        return 1
    if left_parts < right_parts:
        return -1
    return 0


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", ".", value).strip(" .")
    return cleaned or "LinguaFlow.AI.Setup.exe"


def _version_parts(value: str) -> list[int]:
    normalized = normalize_version(value)
    if not normalized:
        return [0]
    return [int(part) for part in normalized.split(".")]


def _find_installer_asset(payload: dict) -> dict | None:
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return None
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        url = str(asset.get("browser_download_url") or "")
        if name.endswith(".exe") and "setup" in name and url:
            return asset
    return None
