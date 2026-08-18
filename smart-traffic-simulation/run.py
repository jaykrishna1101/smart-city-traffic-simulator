import os
import sys
import argparse

# Ensure smart-traffic-simulation root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.main import run_simulation_session
from scripts.run_comparison import run_fixed_vs_adaptive_benchmark

def main():
    parser = argparse.ArgumentParser(description="Smart City Adaptive Traffic Management System (Indian Left-Hand Traffic)")
    parser.add_argument("--mode", type=str, choices=["fixed", "adaptive", "compare", "emergency-demo", "emergency_demo"], default="adaptive", help="Signal control strategy ('fixed', 'adaptive', 'compare', or 'emergency-demo')")
    parser.add_argument("--scenario", type=str, choices=["all", "morning", "normal", "evening"], default="all", help="Traffic period scenario filter ('all', 'morning', 'normal', 'evening')")
    parser.add_argument("--gui", action="store_true", help="Launch SUMO in GUI mode (sumo-gui)")
    parser.add_argument("--3d", "--osg", action="store_true", dest="use_3d", help="Launch SUMO-GUI with OpenSceneGraph (OSG) 3D Viewport enabled")
    parser.add_argument("--nogui", action="store_true", help="Launch SUMO in headless mode (sumo)")
    parser.add_argument("--compare", action="store_true", help="Execute Fixed vs Adaptive benchmark comparison")
    parser.add_argument("--max-steps", type=int, default=480, help="Maximum simulation steps")
    parser.add_argument("--ws-port", type=int, default=None, help="WebSocket broadcaster port (default: 8765)")
    parser.add_argument("--no-ws", action="store_true", help="Disable WebSocket broadcaster")

    args = parser.parse_args()

    use_gui = True if (args.gui or args.use_3d) else False
    if args.nogui:
        use_gui = False

    if args.compare or args.mode.lower() == "compare":
        run_fixed_vs_adaptive_benchmark(gui=use_gui, max_steps=args.max_steps)
    else:
        mode_upper = args.mode.upper()
        run_simulation_session(
            mode=mode_upper,
            gui=use_gui,
            use_3d=args.use_3d,
            max_steps=args.max_steps,
            scenario=args.scenario,
            ws_enabled=not args.no_ws,
            ws_port=args.ws_port
        )

if __name__ == "__main__":
    main()

