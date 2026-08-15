"""
Automatic update check for the meter metering-station-designer app.

On startup the UI queries the GitHub releases API (via certifi when available)
and reports whether a newer version exists for the *current platform*. Release
tags may target only one platform (``v1.2.0`` = both, ``v1.2.0-win`` = Windows
only, ``v1.2.0-mac`` = macOS only), so the check is asset-aware: it looks for
the newest release whose downloadable assets contain an artifact for the running
platform instead of trusting the global ``releases/latest`` tag. All network
failures degrade to a no-update / offline result so the desktop app never blocks
on the check.
"""

import hashlib
import os
import re
import sys
import threading
import time

# GitHub repository that publishes the app (format: owner/name).
GITHUB_REPO = "SLedgehammer-dev12/metering-station-designer"

# Refresh the version check at most this often within one process.
CHECK_TTL_SECONDS = 6 * 3600
# How long to wait for the GitHub API before giving up (network timeout).
FETCH_TIMEOUT_SECONDS = 4.0
# How many recent releases to scan when resolving the per-platform latest tag.
RELEASES_TO_SCAN = 10

# Asset names produced by .github/workflows/build.yml.
_WINDOWS_ASSET_RE = re.compile(r"Windows.*\.zip$", re.IGNORECASE)
_MACOS_ASSET_RE = re.compile(r"macOS.*\.zip$", re.IGNORECASE)
# Release tags: optional 'v', numeric version, optional platform suffix.
_TAG_RE = re.compile(
    r"^[vV]?(\d+(?:\.\d+){1,3})(?:[-_.]?(win|windows|mac|macos|darwin))?$",
    re.IGNORECASE,
)

# Per-process download state (status machine for the semi-automatic updater).
_download_state = {
    "lock": threading.Lock(),
    "status": "idle",          # idle | running | done | failed | no_asset
    "progress": 0.0,           # 0..1 while running
    "dest": None,
    "sha_ok": None,
    "digest": None,
    "url": None,
    "error": None,
}


def get_app_version() -> str:
    """Return the installed app version from the bundle, metadata, or pyproject.toml.

    Frozen (PyInstaller) builds ship a ``VERSION`` file next to the app; it is
    read first so packaged releases report the exact version they were built from.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = os.path.join(meipass, "VERSION")
        try:
            with open(candidate, encoding="utf-8") as fh:
                value = fh.read().strip()
            if value:
                return value
        except OSError:
            pass

    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("metering-station-designer")
        except PackageNotFoundError:
            pass
    except Exception:
        pass

    from pathlib import Path

    for candidate in (
        Path(__file__).resolve().parents[2] / "pyproject.toml",
        Path.cwd() / "pyproject.toml",
    ):
        if candidate.exists():
            try:
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("version ="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    return "1.0.0"


def extract_base_version(tag: str) -> str | None:
    """Strip the platform suffix from a release tag ('v1.2.0-win' -> '1.2.0')."""
    if not tag or not isinstance(tag, str):
        return None
    match = _TAG_RE.match(tag.strip())
    if not match:
        return None
    return match.group(1)


def _requests_urlopen(req, timeout):
    """Fetch a URL, preferring a certifi CA bundle for the SSL context."""
    import ssl
    import urllib.request

    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except Exception:
        return urllib.request.urlopen(req, timeout=timeout)


def fetch_releases(repo: str = GITHUB_REPO, per_page: int = RELEASES_TO_SCAN,
                   timeout: float = FETCH_TIMEOUT_SECONDS) -> list[dict]:
    """Return the most recent release objects (newest first).

    Each entry keeps only the fields we use:
      {'tag_name': 'v1.2.0-win', 'assets': [{'name', 'browser_download_url', 'digest'}]}
    """
    import json
    import urllib.request

    url = f"https://api.github.com/repos/{repo}/releases?per_page={int(per_page)}"
    req = urllib.request.Request(url, headers={"User-Agent": "metering-station-designer-update-check"})
    with _requests_urlopen(req, timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    releases = []
    for entry in payload or []:
        assets = [
            {
                "name": asset.get("name", ""),
                "browser_download_url": asset.get("browser_download_url", ""),
                "digest": asset.get("digest", ""),
            }
            for asset in (entry.get("assets") or [])
        ]
        releases.append({"tag_name": entry.get("tag_name", ""), "assets": assets})
    return releases


def select_platform_asset(assets: list[dict] | None, platform: str | None = None) -> dict | None:
    """Pick the downloadable asset that matches the running platform.

    Returns {'name', 'browser_download_url', 'digest'} or None when there is no
    suitable artifact (other OS or a release that simply has no assets).
    """
    platform = platform or sys.platform
    pattern = None
    if platform == "darwin":
        pattern = _MACOS_ASSET_RE
    elif platform.startswith("win"):
        pattern = _WINDOWS_ASSET_RE
    if pattern is None:
        return None
    for asset in assets or []:
        if pattern.search(asset.get("name", "")):
            return {
                "name": asset["name"],
                "browser_download_url": asset.get("browser_download_url", ""),
                "digest": asset.get("digest", ""),
            }
    return None


def find_platform_release(releases: list[dict] | None,
                          platform: str | None = None) -> dict | None:
    """Return the newest release that ships an asset for the given platform.

    Result: {'tag': 'v1.2.0', 'version': '1.2.0', 'asset': {...}} or None.
    Because releases are newest-first, a ``-win`` only release does not satisfy a
    macOS client — its latest *applicable* version stays whatever earlier release
    still shipped a macOS asset (per-platform update tracks).
    """
    platform = platform or sys.platform
    for release in releases or []:
        tag = (release.get("tag_name") or "").strip()
        asset = select_platform_asset(release.get("assets"), platform)
        if asset is None:
            continue
        version = extract_base_version(tag)
        if not version:
            continue
        asset["version"] = version
        return {"tag": tag, "version": version, "asset": asset}
    return None


def fetch_latest_release_tag(repo: str = GITHUB_REPO, timeout: float = FETCH_TIMEOUT_SECONDS) -> str | None:
    """Return the newest *global* release tag. Kept for backward compatibility.

    NOTE: update checks use :func:`find_platform_release` because the globally
    newest tag may not be applicable to the running platform.
    """
    releases = fetch_releases(repo=repo, per_page=1, timeout=timeout)
    if releases:
        return (releases[0].get("tag_name") or "").strip() or None
    return None


def compare_versions(current: str, latest: str) -> bool:
    """Return True when ``latest`` is a newer release than ``current``."""
    if not latest or not current:
        return False
    try:
        from packaging.version import InvalidVersion, Version

        cur = Version(str(current).lstrip("vV"))
        new = Version(str(latest).lstrip("vV"))
        return new > cur
    except (InvalidVersion, ValueError, TypeError):
        # Unparseable latest version never counts as a newer release.
        return False


_state = {
    "lock": threading.Lock(),
    "result": None,          # dict: {update_available, latest, platform_asset, error} or None
    "checked_at": 0.0,       # epoch seconds of the last completed check
    "in_flight": False,
}


def _run_check(repo: str, platform: str | None) -> dict:
    try:
        releases = fetch_releases(repo=repo)
        found = find_platform_release(releases, platform)
        if found is None:
            return {"update_available": False, "latest": None, "platform_asset": None, "error": None}
        latest = found["version"]
        return {
            "update_available": compare_versions(get_app_version(), latest),
            "latest": latest,
            "platform_asset": found["asset"],
            "error": None,
        }
    except Exception as exc:  # offline, 404, TTL, SSL failure — all non-fatal
        return {"update_available": False, "latest": None, "platform_asset": None, "error": str(exc)}


def check_in_background(repo: str = GITHUB_REPO, platform: str | None = None) -> dict:
    """Trigger an update check in a background thread; returns last cached result.

    The first call spawns a daemon thread that contacts GitHub once and stores
    the outcome. Subsequent calls return the cached outcome (or a none-y result
    while a check is still in flight) so Streamlit reruns never re-hit the API.
    """
    now = time.time()
    with _state["lock"]:
        if _state["result"] is not None and (now - _state["checked_at"]) < CHECK_TTL_SECONDS:
            return _state["result"]
        if _state["in_flight"]:
            return _state["result"] or {"update_available": False, "latest": None, "platform_asset": None, "error": None}
        _state["in_flight"] = True

        def _worker():
            result = _run_check(repo, platform)
            with _state["lock"]:
                _state["result"] = result
                _state["checked_at"] = time.time()
                _state["in_flight"] = False

        threading.Thread(target=_worker, daemon=True).start()
        return _state["result"] or {"update_available": False, "latest": None, "platform_asset": None, "error": None}


def reset_check_cache() -> None:
    """Clear the cached result (used by tests to force a re-check)."""
    with _state["lock"]:
        _state["result"] = None
        _state["checked_at"] = 0.0
        _state["in_flight"] = False


def download_asset(url: str, dest: str, expected_sha256: str | None = None,
                   timeout: float = 120.0, progress=None) -> tuple[bool, str]:
    """Download ``url`` to ``dest`` verifying a sha256 digest when provided.

    ``expected_sha256`` accepts either raw hex or GitHub's ``sha256:<hex>`` form.
    ``progress`` is an optional callback ``(fraction_done: float)``.
    Returns ``(verified, hexdigest)`` — ``verified`` is True when the digest
    matched (or when no digest was requested).
    """
    import urllib.request

    expected = None
    if expected_sha256:
        expected = str(expected_sha256).strip()
        if expected.lower().startswith("sha256:"):
            expected = expected[len("sha256:"):]
        expected = expected.lower()

    hasher = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "metering-station-designer-update-check"})
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with _requests_urlopen(req, timeout) as resp, open(dest, "wb") as out:
        info = resp.headers.get("Content-Length")
        total = float(info) if info else None
        read = 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            hasher.update(chunk)
            read += len(chunk)
            if progress is not None and total:
                try:
                    progress(min(1.0, read / total))
                except Exception:
                    pass

    digest = hasher.hexdigest()
    if expected is None:
        return True, digest
    return expected == digest, digest


def get_download_state() -> dict:
    """Return a snapshot of the ongoing/previous semi-automatic download."""
    with _download_state["lock"]:
        return dict(_download_state)


def _set_download(**kwargs) -> None:
    with _download_state["lock"]:
        _download_state.update(kwargs)


def _default_download_dir() -> str:
    home = os.path.expanduser("~")
    for sub in ("Downloads", "downloads"):
        candidate = os.path.join(home, sub)
        if os.path.isdir(candidate):
            return candidate
    return home


def start_download(repo: str = GITHUB_REPO, platform: str | None = None,
                   dest_dir: str | None = None) -> dict:
    """Kick off a background download of the newest applicable release asset.

    Reuses the cached check result if fresh; otherwise performs a quick check in
    the worker thread. Never blocks. See :func:`get_download_state` for progress.
    """
    platform = platform or sys.platform
    with _download_state["lock"]:
        if _download_state["status"] == "running":
            return dict(_download_state)
        _download_state.update({
            "status": "running",
            "progress": 0.0,
            "dest": None,
            "sha_ok": None,
            "digest": None,
            "url": None,
            "error": None,
        })
        snapshot = dict(_download_state)

    def _worker():
        try:
            result = check_in_background(repo=repo, platform=platform)
            if not result.get("update_available"):
                _set_download(status="no_asset")
                return
            asset = result.get("platform_asset") or {}
            url = asset.get("browser_download_url") or asset.get("url")
            if not url:
                _set_download(status="no_asset")
                return
            dest = os.path.join(dest_dir or _default_download_dir(), asset.get("name") or "MeteringStationDesigner.zip")
            _set_download(url=url, dest=dest, status="running", progress=0.0)
            verified, digest = download_asset(url, dest, expected_sha256=asset.get("digest"),
                                              progress=lambda frac: _set_download(progress=frac))
            _set_download(status="done", progress=1.0, sha_ok=verified, digest=digest)
        except Exception as exc:
            _set_download(status="failed", error=str(exc))

    threading.Thread(target=_worker, daemon=True).start()
    return snapshot