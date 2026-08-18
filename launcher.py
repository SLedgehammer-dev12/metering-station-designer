"""Desktop entry point for the frozen app (and dev testing).

Streamlit apps are run with `streamlit run app.py`, which starts a server.
A PyInstaller bundle cannot use the CLI, so this launcher boots the Streamlit
server directly via `streamlit.web.bootstrap`. It resolves the app script
from `sys._MEIPASS` when frozen and from the repository root otherwise.

Environment:
    MSD_PORT  - server port (default 8501)
"""
import os
import sys

# In a frozen build the app packages (streamlit_app, metering_designer) ship
# as data under sys._MEIPASS. Put that base on sys.path before anything else
# imports them (app.py imports metering_designer at module top-level).
if getattr(sys, "frozen", False):
    _BASE = sys._MEIPASS
    if _BASE not in sys.path:
        sys.path.insert(0, _BASE)


def _streamlit_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "streamlit_app")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "streamlit_app")


def _self_test() -> None:
    """Run the main app and navigate through every page via the ScriptRunner.

    Uses Streamlit's AppTest inside the same process: app.py runs once, then
    each page key is selected and the app is re-run (mimicking real sidebar
    navigation), so every page's imports AND runtime code execute. Exits 0
    only if no page raises. Used by CI and local build verification.
    """
    import traceback
    from streamlit.testing.v1 import AppTest

    base = _streamlit_app_dir()
    app_py = os.path.join(base, "app.py")
    page_keys = ["project", "process", "requirements", "weights",
                 "results", "engineering", "report", "inspection"]
    failures: list[str] = []

    def check(at: AppTest, label: str) -> None:
        excs = list(at.exception)
        if excs:
            failures.append(f"{label}: {[e.message for e in excs]}")
            for e in excs:
                print(e.stack_trace)
        else:
            print(f"SELFTEST OK {label}")

    try:
        at = AppTest.from_file(app_py, default_timeout=60)
        at.session_state["lang"] = "tr"
        at.session_state["page"] = "project"
        at.run()
        check(at, "app.py")
        for key in page_keys:
            at.session_state["page"] = key
            at.run()
            check(at, f"page {key}")
    except Exception:
        failures.append(f"app.py:\n{traceback.format_exc()}")

    if failures:
        print("SELFTEST FAILURES")
        for f in failures:
            print(f)
        sys.exit(1)
    print("SELFTEST ALL OK")
    sys.exit(0)


def main() -> None:
    from streamlit.web import bootstrap

    if os.environ.get("MSD_SELFTEST") == "1":
        _self_test()

    main_script = os.path.join(_streamlit_app_dir(), "app.py")
    flag_options = {
        # Bundled Streamlit's config.py lives under sys._MEIPASS (not
        # site-packages), so its auto-detected default would be `True` and
        # would reject server.port; force production mode.
        "global.developmentMode": False,
        "browser.gatherUsageStats": False,
        "server.port": int(os.environ.get("MSD_PORT", "8501")),
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(main_script, is_hello=False, args=[], flag_options=flag_options)


if __name__ == "__main__":
    main()
