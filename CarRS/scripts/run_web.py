"""Launch CarRS local web UI (LAN-reachable)."""

from __future__ import annotations

import argparse
import os
import socket
import sys


def _lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)

    parser = argparse.ArgumentParser(description="CarRS local web server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    print("CarRS Web")
    print(f"  This PC:  http://127.0.0.1:{args.port}")
    for ip in _lan_ips():
        print(f"  Phone/LAN: http://{ip}:{args.port}")
    print("  Same Wi-Fi required. Ctrl+C to stop.")
    print()

    import uvicorn

    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
