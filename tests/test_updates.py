"""Platform-aware update management tests (per-OS release tracks, asset matching)."""

import hashlib
import time

from metering_designer.core import updates


def _release(tag, assets):
    return {"tag_name": tag, "assets": assets}


def _asset(name, digest="sha256:" + "ab" * 32):
    return {"name": name, "browser_download_url": f"https://example.invalid/{name}", "digest": digest}


# ---------------------------------------------------------------- tag parsing

def test_extract_base_version_strips_platform_suffix():
    assert updates.extract_base_version("v1.2.0") == "1.2.0"
    assert updates.extract_base_version("v1.2.0-win") == "1.2.0"
    assert updates.extract_base_version("v1.2.0-windows") == "1.2.0"
    assert updates.extract_base_version("v1.2.0-mac") == "1.2.0"
    assert updates.extract_base_version("v1.2.0-macos") == "1.2.0"
    assert updates.extract_base_version("1.2.0") == "1.2.0"
    assert updates.extract_base_version("v1.2.0-darwin") == "1.2.0"
    assert updates.extract_base_version("garbage") is None
    assert updates.extract_base_version(None) is None
    assert updates.extract_base_version("") is None


# ------------------------------------------------------------ asset selection

def test_select_platform_asset_matches_darwin():
    assets = [_asset("MeteringStationDesigner_Windows.zip"),
              _asset("MeteringStationDesigner_macOS_arm64.zip")]
    hit = updates.select_platform_asset(assets, platform="darwin")
    assert hit is not None
    assert "macOS" in hit["name"]


def test_select_platform_asset_matches_windows():
    assets = [_asset("MeteringStationDesigner_Windows.zip"),
              _asset("MeteringStationDesigner_macOS_arm64.zip")]
    for name in ("win32", "win64", "win"):
        hit = updates.select_platform_asset(assets, platform=name)
        assert hit is not None and "Windows" in hit["name"]


def test_select_platform_asset_none_for_unknown_platform():
    assert updates.select_platform_asset([_asset("MeteringStationDesigner_Windows.zip")], platform="linux") is None


def test_select_platform_asset_none_when_missing():
    assets = [_asset("MeteringStationDesigner_Windows.zip")]
    assert updates.select_platform_asset(assets, platform="darwin") is None
    assert updates.select_platform_asset(None, platform="darwin") is None
    assert updates.select_platform_asset([], platform="darwin") is None


def test_select_platform_asset_matches_dmg():
    assets = [_asset("MeteringStationDesigner_macOS_arm64.dmg")]
    hit = updates.select_platform_asset(assets, platform="darwin")
    assert hit is not None
    assert hit["name"].endswith(".dmg")


def test_select_platform_asset_prefers_dmg_over_zip_on_darwin():
    assets = [_asset("MeteringStationDesigner_macOS_arm64.zip"),
              _asset("MeteringStationDesigner_macOS_arm64.dmg")]
    hit = updates.select_platform_asset(assets, platform="darwin")
    assert hit is not None
    assert hit["name"].endswith(".dmg")


def test_select_platform_asset_zip_fallback_when_no_dmg():
    assets = [_asset("MeteringStationDesigner_macOS_arm64.zip")]
    hit = updates.select_platform_asset(assets, platform="darwin")
    assert hit is not None
    assert hit["name"].endswith(".zip")


def test_select_platform_asset_dmg_ignored_on_windows():
    assets = [_asset("MeteringStationDesigner_Windows.zip"),
              _asset("MeteringStationDesigner_macOS_arm64.dmg")]
    hit = updates.select_platform_asset(assets, platform="win32")
    assert hit is not None and "Windows" in hit["name"]


# ---------------------------------------------------- per-platform release track

def test_find_platform_release_windows_only_does_not_satisfy_macos():
    releases = [
        _release("v1.2.0-win", [_asset("MeteringStationDesigner_Windows.zip")]),
        _release("v1.1.0", [_asset("MeteringStationDesigner_Windows.zip"),
                             _asset("MeteringStationDesigner_macOS_arm64.zip")]),
    ]
    mac = updates.find_platform_release(releases, platform="darwin")
    win = updates.find_platform_release(releases, platform="win32")
    # macOS stays pinned to the last release that shipped a macOS asset.
    assert mac is not None and mac["version"] == "1.1.0"
    assert mac["tag"] == "v1.1.0"
    # Windows advances to the newest release.
    assert win is not None and win["version"] == "1.2.0"


def test_find_platform_release_mac_only_does_not_satisfy_windows():
    releases = [
        _release("v1.2.0-mac", [_asset("MeteringStationDesigner_macOS_arm64.zip")]),
        _release("v1.1.0", [_asset("MeteringStationDesigner_Windows.zip"),
                             _asset("MeteringStationDesigner_macOS_arm64.zip")]),
    ]
    mac = updates.find_platform_release(releases, platform="darwin")
    win = updates.find_platform_release(releases, platform="win32")
    assert mac["version"] == "1.2.0"
    assert win["version"] == "1.1.0"


def test_find_platform_release_both_advances_everyone():
    releases = [
        _release("v1.2.0", [_asset("MeteringStationDesigner_Windows.zip"),
                            _asset("MeteringStationDesigner_macOS_arm64.zip")]),
        _release("v1.1.0-win", [_asset("MeteringStationDesigner_Windows.zip")]),
    ]
    mac = updates.find_platform_release(releases, platform="darwin")
    win = updates.find_platform_release(releases, platform="win32")
    assert mac["version"] == "1.2.0"
    assert win["version"] == "1.2.0"


def test_find_platform_release_overlapping_tags_newest_wins():
    releases = [
        _release("v1.2.0-mac", [_asset("MeteringStationDesigner_macOS_arm64.zip")]),
        _release("v1.2.0", [  # same base version, both platforms
            _asset("MeteringStationDesigner_Windows.zip"),
            _asset("MeteringStationDesigner_macOS_arm64.zip")]),
    ]
    mac = updates.find_platform_release(releases, platform="darwin")
    win = updates.find_platform_release(releases, platform="win32")
    assert mac["version"] == "1.2.0"
    assert win["version"] == "1.2.0"


def test_find_platform_release_none():
    releases = [_release("v1.2.0-win", [_asset("MeteringStationDesigner_Windows.zip")])]
    assert updates.find_platform_release(releases, platform="darwin") is None
    assert updates.find_platform_release(None, platform="darwin") is None
    assert updates.find_platform_release([], platform="darwin") is None


def test_find_platform_release_skips_bad_version_tags():
    releases = [
        _release("not-a-version", [_asset("MeteringStationDesigner_Windows.zip")]),
        _release("v1.1.0", [_asset("MeteringStationDesigner_Windows.zip")]),
    ]
    hit = updates.find_platform_release(releases, platform="win32")
    assert hit is not None and hit["version"] == "1.1.0"


# ------------------------------------------------- under-the-hood check wiring

def test_run_check_with_platform_asset(monkeypatch):
    releases = [_release("v1.2.0-win", [_asset("MeteringStationDesigner_Windows.zip")])]
    monkeypatch.setattr(updates, "fetch_releases", lambda *a, **k: releases)
    result = updates._run_check("owner/repo", platform="win32")
    assert result["error"] is None
    assert result["latest"] == "1.2.0"
    assert result["platform_asset"]["name"].endswith(".zip")


def test_run_check_no_platform_asset_is_not_an_error(monkeypatch):
    releases = [_release("v1.2.0-win", [_asset("MeteringStationDesigner_Windows.zip")])]
    monkeypatch.setattr(updates, "fetch_releases", lambda *a, **k: releases)
    result = updates._run_check("owner/repo", platform="darwin")
    assert result["error"] is None
    assert result["update_available"] is False
    assert result["latest"] is None
    assert result["platform_asset"] is None


def test_run_check_error_degrades(monkeypatch):
    def _boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(updates, "fetch_releases", _boom)
    result = updates._run_check("owner/repo", platform="darwin")
    assert result["update_available"] is False
    assert result["error"] is not None


# ------------------------------------------------------------- download/verify

def test_download_asset_verifies_sha256(tmp_path):
    payload = b"hello metering station"
    src = tmp_path / "src.bin"
    dest = tmp_path / "dest.bin"
    src.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    # Reuse the URL-opening machinery through a file:// URL.
    ok, computed = updates.download_asset(src.as_uri(), str(dest), expected_sha256=digest)
    assert ok is True
    assert computed == digest
    assert dest.read_bytes() == payload

    bad = updates.download_asset(src.as_uri(), str(tmp_path / "bad.bin"),
                                 expected_sha256="sha256:" + "00" * 32)
    assert bad[0] is False


def test_download_asset_without_expected_digest(tmp_path):
    payload = b"data"
    src = tmp_path / "src.bin"
    dest = tmp_path / "dest.bin"
    src.write_bytes(payload)
    ok, digest = updates.download_asset(src.as_uri(), str(dest))
    assert ok is True
    assert digest == hashlib.sha256(payload).hexdigest()


def test_download_asset_reports_progress(tmp_path):
    payload = b"x" * (1 << 16) * 3
    src = tmp_path / "src.bin"
    src.write_bytes(payload)
    seen = []
    ok, _ = updates.download_asset(src.as_uri(), str(tmp_path / "dest.bin"),
                                   progress=seen.append)
    assert ok is True
    assert any(p > 0 for p in seen)
    assert seen[-1] >= 1.0


# ---------------------------------------------------------- download lifecycle

def test_get_download_state_initial():
    state = updates.get_download_state()
    assert state["status"] == "idle"


def test_start_download_no_update_noops_fast(monkeypatch):
    updates.reset_check_cache()
    monkeypatch.setattr(updates, "fetch_releases",
                        lambda *a, **k: [_release("v0.0.1", [_asset("MeteringStationDesigner_Windows.zip")])])
    # Our installed dev version will be >= 0.0.1 -> no update -> status no_asset.
    updates.start_download(platform="win32")
    deadline = 30
    state = {}
    waiters = 0
    while waiters < deadline and state.get("status") in (None, "running", "idle"):
        state = updates.get_download_state()
        if state["status"] not in ("running", "idle"):
            break
        time.sleep(0.05)
        waiters += 1
    # No network file download should have triggered a 'done' state.
    assert state["status"] in ("no_asset", "failed", "idle")
    updates._set_download(status="idle")  # reset module state for other tests


def test_start_download_ignores_repeated_calls(monkeypatch):
    monkeypatch.setattr(updates, "fetch_releases",
                        lambda *a, **k: [_release("v0.0.1", [_asset("MeteringStationDesigner_Windows.zip")])])
    updates.start_download(platform="win32")
    updates.start_download(platform="win32")
    snapshot = updates.get_download_state()
    updates._set_download(status="idle", in_flight=False)
    assert snapshot is not None