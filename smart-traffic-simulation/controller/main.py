import os
import sys
import argparse
import time

# Ensure project directory is in sys.path
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CONTROLLER_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.config import FIXED_RESULTS_CSV, ADAPTIVE_RESULTS_CSV, SCENARIO_NAME
from controller.simulation_manager import SimulationManager
from controller.adaptive_controller import AdaptiveTrafficController
from controller.metrics_exporter import BenchmarkTracker
from controller.realtime import RealtimeBroadcaster

def get_scenario_bounds(scenario: str, default_max: int = 480) -> tuple:
    """
    Returns (start_time, end_time) bounds for scenario filtering.
    """
    scenario = scenario.lower()
    if scenario == "morning":
        return (0.0, 180.0)
    elif scenario == "normal":
        return (180.0, 240.0)
    elif scenario == "evening":
        return (240.0, 480.0)
    else:
        return (0.0, float(default_max))

# Intersection coordinate lookup for camera centering in SUMO-GUI
INTERSECTION_GUI_OFFSETS = {
    "cluster_2683490405_298938456": (1780.0, 1420.0),
    "joinedS_2705384848_3138462214": (2620.0, 1680.0),
    "cluster_2683490416_2683507646_2683507647_2684658305_#2more": (980.0, 920.0)
}

def process_traci_gui_command(cmd: dict, gui: bool = False):
    """Executes safe TraCI GUI commands (camera tracking, zoom, center view)."""
    if not gui:
        return
    try:
        import traci
        views = traci.gui.getIDList()
        if not views:
            return
        view_id = views[0]

        action = cmd.get("command") or cmd.get("action")
        params = cmd.get("params") or {}

        if action == "set_zoom":
            zoom = float(params.get("zoom", 300))
            traci.gui.setZoom(view_id, zoom)
        elif action == "track_vehicle":
            vid = str(params.get("vehicle_id", ""))
            traci.gui.trackVehicle(view_id, vid)
        elif action == "center_intersection":
            tls_id = str(params.get("intersection_id", ""))
            if tls_id in INTERSECTION_GUI_OFFSETS:
                x, y = INTERSECTION_GUI_OFFSETS[tls_id]
                traci.gui.setOffset(view_id, x, y)
                traci.gui.trackVehicle(view_id, "")
        elif action == "set_schema":
            schema_name = str(params.get("schema", "real world"))
            traci.gui.setSchema(view_id, schema_name)
    except Exception as e:
        print(f"[TraCI GUI Command] Error applying {cmd}: {e}")

def run_simulation_session(
    mode: str = "ADAPTIVE",
    gui: bool = False,
    use_3d: bool = False,
    max_steps: int = 480,
    scenario: str = "all",
    ws_enabled: bool = True,
    ws_port: int = None
) -> dict:
    """
    Executes a simulation session under specified CONTROL_MODE ("FIXED", "ADAPTIVE", or "EMERGENCY_DEMO") and scenario filter.
    Returns aggregated empirical benchmark metrics.
    """
    mode_normalized = mode.upper().replace("-", "_")
    is_adaptive_or_demo = mode_normalized in ["ADAPTIVE", "EMERGENCY_DEMO"]
    is_demo = mode_normalized == "EMERGENCY_DEMO"

    manager = SimulationManager(gui=gui, use_3d=use_3d)
    controller = AdaptiveTrafficController(enable_emergency=True) if is_adaptive_or_demo else None
    tracker = BenchmarkTracker()
    broadcaster = RealtimeBroadcaster(port=ws_port, enabled=ws_enabled)
    current_period = None

    csv_output_path = ADAPTIVE_RESULTS_CSV if is_adaptive_or_demo else FIXED_RESULTS_CSV
    start_step, end_step = get_scenario_bounds(scenario, max_steps)

    is_paused = False
    step_delay = 0.02 if gui else 0.0
    sim_time = 0.0
    state = {}
    decisions = {}

    try:
        manager.start()
        broadcaster.start()
        print(f"\n=========================================================================")
        print(f"  RUNNING CONTROL MODE: {mode:<10} | NETWORK: {SCENARIO_NAME:<22} | INDIAN LHT   ")
        print(f"=========================================================================\n")

        step_count = 0

        while manager.is_active():
            # 1. Process incoming WebSocket commands before simulation step
            pending_cmds = broadcaster.get_pending_commands()
            for cmd in pending_cmds:
                action = cmd.get("command") or cmd.get("action")
                params = cmd.get("params") or {}
                if action == "pause":
                    is_paused = True
                    print("\n>>> Simulation paused via SmartFlow control <<<")
                elif action == "resume":
                    is_paused = False
                    print("\n>>> Simulation resumed via SmartFlow control <<<")
                elif action == "set_speed" or action == "set_delay":
                    delay_val = float(params.get("delay", 0.02))
                    step_delay = max(0.0, min(1.0, delay_val))
                else:
                    process_traci_gui_command(cmd, gui=gui)

            # 2. Interactive Pause Wait Loop
            while is_paused and manager.is_active():
                if state:
                    broadcaster.broadcast_state(
                        sim_time=sim_time,
                        state=state,
                        decisions=decisions,
                        tracker=tracker,
                        mode=mode_normalized,
                        status="paused"
                    )
                time.sleep(0.05)
                pause_cmds = broadcaster.get_pending_commands()
                step_once = False
                for p_cmd in pause_cmds:
                    p_action = p_cmd.get("command") or p_cmd.get("action")
                    p_params = p_cmd.get("params") or {}
                    if p_action == "resume":
                        is_paused = False
                        print("\n>>> Simulation resumed via SmartFlow control <<<")
                        break
                    elif p_action == "step":
                        step_once = True
                        break
                    elif p_action == "set_speed" or p_action == "set_delay":
                        step_delay = max(0.0, min(1.0, float(p_params.get("delay", 0.02))))
                    else:
                        process_traci_gui_command(p_cmd, gui=gui)
                if not is_paused or step_once:
                    break

            # 3. Advance simulation step
            sim_time = manager.step()
            
            # Spawn test emergency vehicles (ambulance at 50s, police at 150s, firetruck at 250s)
            if controller and hasattr(controller, 'emergency_sys'):
                controller.emergency_sys.spawn_test_emergency_vehicles(sim_time)
            elif hasattr(manager.aggregator, 'emergency_detector'):
                pass

            if sim_time < start_step:
                continue

            state = manager.get_traffic_state()

            # Dynamically execute Adaptive / Emergency Priority decisions for all discovered traffic lights
            decisions = {}
            if is_adaptive_or_demo and controller:
                tls_ids = list(state["intersections"].keys())
                for tls_id in tls_ids:
                    decision = controller.get_signal_decision(tls_id, state=state)
                    controller.apply_signal_decision(decision)
                    decisions[tls_id] = decision

            # Update automatic camera tracking during Emergency Demo mode
            if is_demo and controller and hasattr(controller, 'emergency_sys'):
                controller.emergency_sys.update_camera_tracking(gui=gui)

            # Track benchmark metrics & export CSV/JSON
            tracker.update(sim_time, state)
            manager.aggregator.export_csv(state, csv_path=csv_output_path)
            manager.aggregator.export_json(state)

            # Real-time WebSocket state broadcast
            broadcaster.broadcast_state(
                sim_time=sim_time,
                state=state,
                decisions=decisions,
                tracker=tracker,
                mode=mode_normalized,
                status="running"
            )

            # Track Period Transition
            period = state["period"]
            if period != current_period:
                current_period = period
                print(f"\n>>> [SIMULATION TIME: {sim_time:5.1f}s] LOGICAL SCENARIO SWITCHED TO: {current_period} <<<")

            # Periodic Console Reporting (Every 30 steps)
            if step_count % 30 == 0:
                print(f"Step {int(sim_time):3d}s | Mode: {mode_normalized:<14} | Period: {period:<13}")
                if is_adaptive_or_demo:
                    for tls_id, decision in decisions.items():
                        print(f"   [{tls_id}] Decision: {decision['phase']:<20} ({decision['green_duration']}s) | Reason: {decision['reason']}")

            step_count += 1
            if sim_time >= end_step:
                print(f"\nReached target scenario boundary of {end_step}s for scenario '{scenario}'.")
                break

            if step_delay > 0:
                time.sleep(step_delay)

        summary = tracker.generate_benchmark_summary(mode)
        return summary


    except KeyboardInterrupt:
        print(f"\nKeyboardInterrupt received during '{mode}' mode. Stopping simulation...")
        return tracker.generate_benchmark_summary(mode)
    except Exception as e:
        print(f"\nError during simulation run in mode '{mode}': {e}")
        import traceback
        traceback.print_exc()
        return tracker.generate_benchmark_summary(mode)
    finally:
        broadcaster.stop()
        manager.close()
        print(f"Simulation session for mode '{mode}' finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart City Traffic Control System")
    parser.add_argument("--mode", type=str, choices=["FIXED", "ADAPTIVE", "EMERGENCY_DEMO", "EMERGENCY-DEMO", "fixed", "adaptive", "emergency-demo", "emergency_demo"], default="ADAPTIVE", help="Traffic signal control mode")
    parser.add_argument("--scenario", type=str, choices=["all", "morning", "normal", "evening"], default="all", help="Traffic period scenario filter")
    parser.add_argument("--gui", action="store_true", help="Launch SUMO in GUI mode")
    parser.add_argument("--3d", action="store_true", dest="use_3d", help="Enable OpenSceneGraph (OSG) 3D Viewport in sumo-gui")
    parser.add_argument("--nogui", action="store_true", help="Launch SUMO in headless mode")
    parser.add_argument("--max-steps", type=int, default=480, help="Maximum simulation steps")
    parser.add_argument("--ws-port", type=int, default=None, help="WebSocket broadcaster port (default: 8765)")
    parser.add_argument("--no-ws", action="store_true", help="Disable WebSocket broadcaster")
    args = parser.parse_args()

    use_gui = True if (args.gui or args.use_3d) else False
    if args.nogui:
        use_gui = False

    metrics = run_simulation_session(
        mode=args.mode,
        gui=use_gui,
        use_3d=args.use_3d,
        max_steps=args.max_steps,
        scenario=args.scenario,
        ws_enabled=not args.no_ws,
        ws_port=args.ws_port
    )
    print(f"\n--- SESSION METRICS SUMMARY ({args.mode} | {args.scenario.upper()}) ---")
    for k, v in metrics.items():
        print(f"  {k:<26}: {v}")
