import re
import threading
import time

import requests

RUSTDESK_RELEASES_URL = "https://api.github.com/repos/rustdesk/rustdesk/releases"
CACHE_TTL_SECONDS = 3600
REQUEST_TIMEOUT_SECONDS = 10
MAX_RELEASES = 30
VERSION_TAG_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")

FALLBACK_VERSIONS = [
    "1.5.0",
    "1.4.9",
    "1.4.8",
    "1.4.7",
    "1.4.6",
    "1.4.5",
    "1.4.4",
    "1.4.3",
    "1.4.2",
    "1.4.1",
    "1.4.0",
]

_cache_lock = threading.Lock()
_cached_choices = None
_cached_default = None
_cached_at = 0


def _fallback_choices():
    return [("master", "nightly")] + [(version, version) for version in FALLBACK_VERSIONS]


def _is_release_tag(tag_name, prerelease, draft):
    if draft or prerelease:
        return False
    if not tag_name or tag_name.lower() == "nightly":
        return False
    return bool(VERSION_TAG_RE.match(tag_name))


def _build_choices(versions):
    choices = [("master", "nightly")]
    seen = {"master"}
    for version in versions:
        if version in seen:
            continue
        seen.add(version)
        choices.append((version, version))
    return choices


def _auth_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "rdgen-version-fetcher",
    }
    try:
        from django.conf import settings
        token = getattr(settings, "GHBEARER", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass
    return headers


def fetch_official_versions():
    response = requests.get(
        RUSTDESK_RELEASES_URL,
        headers=_auth_headers(),
        params={"per_page": 100},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    releases = response.json()
    if not isinstance(releases, list):
        raise ValueError("Unexpected GitHub releases payload")

    versions = []
    for release in releases:
        tag_name = str(release.get("tag_name") or "").lstrip("v")
        if _is_release_tag(tag_name, release.get("prerelease"), release.get("draft")):
            versions.append(tag_name)
        if len(versions) >= MAX_RELEASES:
            break
    return versions


def get_version_choices(force_refresh=False):
    global _cached_choices, _cached_default, _cached_at

    now = time.time()
    with _cache_lock:
        cache_valid = (
            _cached_choices
            and not force_refresh
            and now - _cached_at < CACHE_TTL_SECONDS
        )
        if cache_valid:
            return list(_cached_choices), _cached_default

    versions = []
    try:
        versions = fetch_official_versions()
    except Exception:
        versions = []

    with _cache_lock:
        if versions:
            choices = _build_choices(versions)
            default = versions[0]
            _cached_choices = choices
            _cached_default = default
            _cached_at = time.time()
            return list(choices), default
        if _cached_choices:
            return list(_cached_choices), _cached_default
        fallback = _fallback_choices()
        return list(fallback), FALLBACK_VERSIONS[0]


def get_default_version():
    _, default = get_version_choices()
    return default
