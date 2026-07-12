"""DevOrbit Desktop launcher — opens a browser window and starts the server."""
import argparse
import sys
import webbrowser
import threading
import time


def main():
    parser = argparse.ArgumentParser(prog="devorbit-desktop", description="DevOrbit Desktop Application")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--mock", action="store_true", help="Run with mock client (no API key needed)")
    parser.add_argument("--workspace", default=None, help="Workspace directory")
    parser.add_argument("--headless", action="store_true", default=True, help="Headless browser (default)")
    parser.add_argument("--visible", dest="headless", action="store_false", help="Visible browser")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    from acli.desktop.server import run_desktop

    # Open browser after short delay
    if not args.no_browser:
        url = f"http://{args.host}:{args.port}"
        threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()

    run_desktop(host=args.host, port=args.port, mock=args.mock, workspace=args.workspace, headless=args.headless)


if __name__ == "__main__":
    main()
