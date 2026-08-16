import os
import sys
import argparse
import time

# Ensure project directory is in sys.path
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CONTROLLER_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.config import FIXED_RESULTS_CSV, ADAPTIVE_RESULTS_CSV
from controller.simulation_manager import SimulationManager
from controller.adaptive_controller import AdaptiveTrafficController
from controller.metrics_exporter import BenchmarkTracker

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

def run_simulation_session(mode: str = "ADAPTIVE", gui: bool = False, use_3d: bool = False, max_steps: int = 480, scenario: str = "all") -> dict:
    """
    Executes a simulation session under specified CONTROL_MODE ("FIXED" or "ADAPTIVE") and scenario filter.
    Returns aggregated empirical benchmark metrics.
    """
    manager = SimulationManager(gui=gui, use_3d=use_3d)
    controller = AdaptiveTrafficController() if mode == "ADAPTIVE" else None
    tracker = BenchmarkTracker()
    current_period = None

    csv_output_path = ADAPTIVE_RESULTS_CSV if mode == "ADAPTIVE" else FIXED_RESULTS_CSV
    start_step, end_step = get_scenario_bounds(scenario, max_steps)

    try:
        manager.start()
        print(f"\n=========================================================================")
        print(f"  RUNNING CONTROL MODE: {mode:<10} | SCENARIO: {scenario.upper():<8} | INDIAN LHT   ")
        print(f"=========================================================================\n")

        step_count = 0

        # Fast forward if starting scenario at t > 0
        while manager.is_active():
            sim_time = manager.step()
            
            if sim_time < start_step:
                continue

            state = manager.get_traffic_state()

            # Execute Adaptive Controller decisions if in ADAPTIVE mode
            decisions = {}
            if mode == "ADAPTIVE" and controller:
                for tls_id in ["INT_NW", "INT_NE", "INT_SW", "INT_SE"]:
                    decision = controller.get_signal_decision(tls_id)
                    controller.apply_signal_decision(decision)
                    decisions[tls_id] = decision

            # Track benchmark metrics & export CSV/JSON
            tracker.update(sim_time, state)
            manager.aggregator.export_csv(state, csv_path=csv_output_path)
            manager.aggregator.export_json(state)

            # Track Period Transition
            period = state["period"]
            if period != current_period:
                current_period = period
                print(f"\n>>> [SIMULATION TIME: {sim_time:5.1f}s] LOGICAL SCENARIO SWITCHED TO: {current_period} <<<")

            # Periodic Console Reporting (Every 30 steps)
            if step_count % 30 == 0:
                print(f"Step {int(sim_time):3d}s | Mode: {mode:<8} | Period: {period:<13}")
                if mode == "ADAPTIVE":
                    for tls_id, decision in decisions.items():
                        print(f"   [{tls_id}] Decision: {decision['phase']:<20} ({decision['green_duration']}s) | Reason: {decision['reason']}")

            step_count += 1
            if sim_time >= end_step:
                print(f"\nReached target scenario boundary of {end_step}s for scenario '{scenario}'.")
                break

            if gui:
                time.sleep(0.02)

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
        manager.close()
        print(f"Simulation session for mode '{mode}' finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart City Traffic Control System")
    parser.add_argument("--mode", type=str, choices=["FIXED", "ADAPTIVE"], default="ADAPTIVE", help="Traffic signal control mode")
    parser.add_argument("--scenario", type=str, choices=["all", "morning", "normal", "evening"], default="all", help="Traffic period scenario filter")
    parser.add_argument("--gui", action="store_true", help="Launch SUMO in GUI mode")
    parser.add_argument("--3d", action="store_true", dest="use_3d", help="Enable OpenSceneGraph (OSG) 3D Viewport in sumo-gui")
    parser.add_argument("--nogui", action="store_true", help="Launch SUMO in headless mode")
    parser.add_argument("--max-steps", type=int, default=480, help="Maximum simulation steps")
    args = parser.parse_args()

    use_gui = True if (args.gui or args.use_3d) else False
    if args.nogui:
        use_gui = False

    metrics = run_simulation_session(mode=args.mode, gui=use_gui, use_3d=args.use_3d, max_steps=args.max_steps, scenario=args.scenario)
    print(f"\n--- SESSION METRICS SUMMARY ({args.mode} | {args.scenario.upper()}) ---")
    for k, v in metrics.items():
        print(f"  {k:<26}: {v}")
