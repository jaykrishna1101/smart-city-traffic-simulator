#!/usr/bin/env python3
"""
SmartFlow noVNC WebSocket-to-VNC Bridge Launcher
Bridges SmartFlow browser noVNC client on port 6080 to the SUMO-GUI window VNC server on port 5901.

NOTE: This now targets sumo_window_vnc.py (port 5901) by default, which streams ONLY the
sumo-gui.exe window — NOT the entire Windows desktop. TightVNC on port 5900 is no longer
in the SmartFlow streaming path.

Startup sequence:
  1. python run.py --gui                           # Start SUMO with GUI
  2. python scripts/sumo_window_vnc.py --port 5901 # Start SUMO window VNC server
  3. python scripts/start_vnc_bridge.py             # Start websockify bridge (this script)
  4. npm run dev (in smart-flow/)                  # Start SmartFlow frontend
"""

import sys
import os
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="SmartFlow noVNC / websockify Bridge Launcher")
    parser.add_argument("--port", type=int, default=6080, help="WebSocket port for browser noVNC clients (default: 6080)")
    parser.add_argument("--vnc-host", type=str, default="127.0.0.1", help="Target VNC server host (default: 127.0.0.1)")
    parser.add_argument("--vnc-port", type=int, default=5901, help="Target VNC server port (default: 5901 = sumo_window_vnc.py; use 5900 for TightVNC)")
    args = parser.parse_args()

    target = f"{args.vnc_host}:{args.vnc_port}"

    print("=========================================================================")
    print("  SMARTFLOW noVNC / WEBSOCKIFY RFB BRIDGE")
    print(f"  WebSocket Endpoint : ws://localhost:{args.port}")
    print(f"  Target VNC Server  : {target}")
    print(f"  Stream Mode        : SUMO-GUI window only (sumo_window_vnc.py)")
    print("=========================================================================\n")

    try:
        import websockify
        print(f"Starting websockify RFB bridge on port {args.port} -> {target}...")
        cmd = [
            sys.executable,
            "-m",
            "websockify",
            str(args.port),
            target
        ]
        subprocess.run(cmd)
    except ModuleNotFoundError:
        print("\n[!] 'websockify' is not installed in your Python environment.")
        print("To install websockify, run:")
        print("    pip install websockify\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[SmartFlow Bridge] Stopped.")

if __name__ == "__main__":
    main()
