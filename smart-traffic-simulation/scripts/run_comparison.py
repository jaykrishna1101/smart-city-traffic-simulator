import os
import sys
import json
import argparse

# Ensure project directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.main import run_simulation_session
from controller.metrics_exporter import BenchmarkTracker
from controller.config import COMPARISON_JSON_PATH

def run_fixed_vs_adaptive_benchmark(gui: bool = False, max_steps: int = 480):
    """
    Executes sequential FIXED and ADAPTIVE simulation runs under identical Indian LHT conditions.
    Exports empirical comparison metrics to output/comparison.json.
    """
    print(f"\n=========================================================================")
    print(f"  STARTING FIXED VS. ADAPTIVE SIGNAL CONTROL BENCHMARK (INDIAN LHT)     ")
    print(f"=========================================================================")

    print("\n>>> PHASE 1: Running FIXED Signal Control Mode ...")
    fixed_metrics = run_simulation_session(mode="FIXED", gui=gui, max_steps=max_steps)

    print("\n>>> PHASE 2: Running ADAPTIVE Signal Control Mode ...")
    adaptive_metrics = run_simulation_session(mode="ADAPTIVE", gui=gui, max_steps=max_steps)

    print("\n>>> PHASE 3: Generating Empirical Benchmark Comparison ...")
    comparison = BenchmarkTracker.export_comparison_json(fixed_metrics, adaptive_metrics, COMPARISON_JSON_PATH)

    print(f"\n=========================================================================")
    print(f"               EMPIRICAL BENCHMARK PERFORMANCE COMPARISON                 ")
    print(f"=========================================================================")
    print(f" Metric                          | Fixed Mode   | Adaptive Mode| Improvement  ")
    print(f"-------------------------------------------------------------------------")
    print(f" Total Vehicles Inserted        | {fixed_metrics['total_vehicles_inserted']:<12} | {adaptive_metrics['total_vehicles_inserted']:<12} | -            ")
    print(f" Throughput (Trips Completed)   | {fixed_metrics['throughput']:<12} | {adaptive_metrics['throughput']:<12} | {comparison['improvement_percentage']['throughput']} ")
    print(f" Average Waiting Time (sec)    | {fixed_metrics['average_waiting_time']:<12} | {adaptive_metrics['average_waiting_time']:<12} | {comparison['improvement_percentage']['average_waiting_time']} ")
    print(f" Maximum Halting Queue (vehs)   | {fixed_metrics['max_queue']:<12} | {adaptive_metrics['max_queue']:<12} | {comparison['improvement_percentage']['max_queue']} ")
    print(f" Average Speed (km/h)           | {fixed_metrics['average_speed_kmh']:<12} | {adaptive_metrics['average_speed_kmh']:<12} | {comparison['improvement_percentage']['average_speed']} ")
    print(f" Congestion Events (High/Severe)| {fixed_metrics['congestion_events']:<12} | {adaptive_metrics['congestion_events']:<12} | {comparison['improvement_percentage']['congestion_events']} ")
    print(f" Emergency Response Time (sec)  | {fixed_metrics['emergency_response_time']:<12} | {adaptive_metrics['emergency_response_time']:<12} | {comparison['improvement_percentage']['emergency_response_time']} ")
    print(f"=========================================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fixed vs Adaptive Traffic Simulation Benchmark")
    parser.add_argument("--gui", action="store_true", help="Launch SUMO in GUI mode")
    parser.add_argument("--nogui", action="store_true", help="Launch SUMO in headless mode")
    parser.add_argument("--max-steps", type=int, default=480, help="Maximum simulation steps")
    args = parser.parse_args()

    use_gui = True if args.gui else False
    if args.nogui:
        use_gui = False

    run_fixed_vs_adaptive_benchmark(gui=use_gui, max_steps=args.max_steps)
