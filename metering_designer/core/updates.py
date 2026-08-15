"""
Automatic update check for the meter metering-station-designer app.

On startup the UI queries the GitHub releases API (via certifi when available)
and reports whether a newer version exists. All network failures degrade to a
no-update / offline result so the desktop app never blocks on the check.
"""

import threading
import time

# GitHub repository that publishes the app (format: owner/name).
GITHUB_REPO = "SLedgehammer-dev12/metering-station-designer"

# Refresh the version check at most this often within one process.
CHECK_TTL_SECONDS = 6 * 3600
# How long to wait for the GitHub API before giving up (network timeout).
FETCH_TIMEOUT_SECONDS = 4.0


def get_app_version() -> str:
    """Return the installed app version from package metadata or pyproject.toml."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("metering-station-designer")
        except PackageNotFoundError:
            pass
    except Exception:
        pass

    import os
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


def fetch_latest_release_tag(repo: str = GITHUB_REPO, timeout: float = FETCH_TIMEOUT_SECONDS) -> str | None:
    """Query the GitHub latest-release endpoint and return the tag ('v1.0.0')."""
    import json
    import urllib.request

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "metering-station-designer-update-check"})
    with _requests_urlopen(req, timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return (payload.get("tag_name") or "").strip() or None


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
        # Unparseable latest tag never counts as a newer release.
        return False


_state = {
    "lock": threading.Lock(),
    "result": None,          # dict: {update_available, latest, error} or None
    "checked_at": 0.0,       # epoch seconds of the last completed check
    "in_flight": False,
}


def _run_check(repo: str) -> dict:
    try:
        latest = fetch_latest_release_tag(repo=repo)
        return {
            "update_available": bool(latest) and compare_versions(get_app_version(), latest),
            "latest": latest,
            "error": None,
        }
    except Exception as exc:  # offline, 404, TTL, SSL failure — all non-fatal
        return {"update_available": False, "latest": None, "error": str(exc)}


def check_in_background(repo: str = GITHUB_REPO) -> dict:
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
            return _state["result"] or {"update_available": False, "latest": None, "error": None}
        _state["in_flight"] = True

        def _worker():
            result = _run_check(repo)
            with _state["lock"]:
                _state["result"] = result
                _state["checked_at"] = time.time()
                _state["in_flight"] = False

        threading.Thread(target=_worker, daemon=True).start()
        return _state["result"] or {"update_available": False, "latest": None, "error": None}


def reset_check_cache() -> None:
    """Clear the cached result (used by tests to force a re-check)."""
    with _state["lock"]:
        _state["result"] = None
        _state["checked_at"] = 0.0
        _state["in_flight"] = False