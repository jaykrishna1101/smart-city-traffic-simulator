import os
import sys
import json
import csv
import time

# Ensure project directory is in sys.path
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CONTROLLER_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import traci
from controller.config import SUMO_CONFIG_PATH, SCENARIO_NAME
from controller.traffic_state import TrafficStateAggregator
from controller.adaptive_controller import AdaptiveTrafficController
from controller.metrics_exporter import BenchmarkTracker

EVALUATION_DIR = os.path.join(PROJECT_DIR, "output", "evaluation")
COMPARISON_JSON_PATH = os.path.join(EVALUATION_DIR, "comparison.json")
REPORT_CSV_PATH = os.path.join(EVALUATION_DIR, "report.csv")

# Scenario boundaries — aligned with actual simulation time
SCENARIO_BOUNDS = {
    "morning": (0.0,   600.0),
    "normal":  (0.0,   600.0),
    "evening": (0.0,   600.0),
}

def get_sumo_binary() -> str:
    sumo_home = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
    sumo_bin = os.path.join(sumo_home, "bin", "sumo.exe")
    return sumo_bin if os.path.exists(sumo_bin) else "sumo"


class ScenarioEvaluator:
    """
    Executes reproducible Fixed vs Adaptive benchmark evaluations on the Chatrapati–Ring Road
    SUMO network under identical seed, demand, and NO emergency vehicle injection.

    Bugs Fixed:
    - Bug 2: TrafficStateAggregator is instantiated ONCE per run, not every step.
    - Bug 3: Emergency vehicles are NOT injected in evaluation runs (separate standalone test).
    - Bug 1: Waiting time computed per-vehicle via traci.vehicle.getAccumulatedWaitingTime().
    - Bug 4: Yellow phase maps use actual phase sequence topology, not (phase+1)%total.
    - Bug 5: Speed averaged over controlled approach edges only.
    """
    def __init__(self, seed: int = 42, duration: float = 600.0):
        self.seed = seed
        self.duration = duration
        os.makedirs(EVALUATION_DIR, exist_ok=True)

    def run_single_experiment(self, scenario: str, mode: str) -> tuple:
        """
        Runs a single FIXED or ADAPTIVE experiment for the given scenario.
        Returns (summary_dict, step_rows).
        """
        start_step = 0.0
        target_end = self.duration

        cmd = [
            get_sumo_binary(),
            "-c", SUMO_CONFIG_PATH,
            "--seed", str(self.seed),
            "--no-step-log", "true",
            "--no-warnings", "true"
        ]

        print(f"  Running: Scenario='{scenario.upper()}' | Mode='{mode:<8}' | "
              f"Seed={self.seed} | Duration={target_end}s ({start_step}s->{target_end}s)")
        traci.start(cmd)

        # FIX Bug 2: Create ONE aggregator per run, not one per step
        aggregator = TrafficStateAggregator()

        # FIX Bug 3: No emergency vehicles in benchmark — use enable_emergency=False
        controller = AdaptiveTrafficController(enable_emergency=False) if mode == "ADAPTIVE" else None
        tracker = BenchmarkTracker()

        step_rows = []

        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                sim_time = traci.simulation.getTime()

                # FIX Bug 3: No emergency vehicle spawning during comparative benchmark runs

                if sim_time < start_step:
                    continue

                # Get traffic state from the shared aggregator (not re-created each step)
                state = aggregator.get_traffic_state()

                # Apply adaptive decisions if in adaptive mode
                if mode == "ADAPTIVE" and controller:
                    for tls_id in list(state["intersections"].keys()):
                        # Pass the pre-fetched state to avoid redundant TraCI queries per TLS
                        decision = controller.get_signal_decision(tls_id, state=state)
                        controller.apply_signal_decision(decision)

                # Update benchmark tracker with actual vehicle waiting times
                tracker.update(sim_time, state)

                # Record step telemetry rows
                for tls_id, tls_data in state.get("intersections", {}).items():
                    for edge_id, app in tls_data.get("approaches", {}).items():
                        step_rows.append({
                            "scenario": SCENARIO_NAME,
                            "period_scenario": scenario.upper(),
                            "mode": mode,
                            "simulation_time": sim_time,
                            "intersection_id": tls_id,
                            "edge_id": edge_id,
                            "vehicles": app["vehicles"],
                            "queue": app["queue"],
                            "waiting_time": app["waiting_time"],
                            "speed": app["speed"],
                            "speed_kmh": app["speed_kmh"],
                            "traffic_flow": app["traffic_flow"],
                            "congestion": app["congestion"],
                            "signal_phase": tls_data["signal_phase"],
                            "phase_state": tls_data["phase_state"],
                            "phase_remaining": tls_data["phase_remaining"]
                        })

                if sim_time >= target_end:
                    break

            summary = tracker.generate_benchmark_summary(mode)
            summary["scenario"] = SCENARIO_NAME
            summary["period_scenario"] = scenario.upper()

        finally:
            traci.close()

        return summary, step_rows

    def export_scenario_csv(self, scenario: str, mode: str, step_rows: list):
        filename = f"{scenario.lower()}_{mode.lower()}.csv"
        filepath = os.path.join(EVALUATION_DIR, filename)
        fieldnames = [
            "scenario", "period_scenario", "mode", "simulation_time", "intersection_id",
            "edge_id", "vehicles", "queue", "waiting_time", "speed", "speed_kmh",
            "traffic_flow", "congestion", "signal_phase", "phase_state", "phase_remaining"
        ]
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(step_rows)
        print(f"  Saved CSV: {filepath} ({len(step_rows)} rows)")

    def run_full_evaluation(self) -> dict:
        scenarios = ["morning", "normal", "evening"]
        modes = ["FIXED", "ADAPTIVE"]

        results = {}

        print(f"\n=========================================================================")
        print(f"  FIXED vs ADAPTIVE EVALUATION: CHATRAPATI-RING ROAD (LHT, seed={self.seed})")
        print(f"  Duration per run: {self.duration}s | No emergency vehicles in benchmark runs")
        print(f"=========================================================================\n")

        for scenario in scenarios:
            results[scenario] = {}
            for mode in modes:
                summary, step_rows = self.run_single_experiment(scenario, mode)
                results[scenario][mode] = summary
                self.export_scenario_csv(scenario, mode, step_rows)

        # Build comparison and report
        comparison = {
            "scenario": SCENARIO_NAME,
            "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seed": self.seed,
            "duration_per_run_s": self.duration,
            "note": "Emergency vehicles excluded from comparison runs for fairness.",
            "scenarios": {}
        }

        report_rows = []

        def calc_pct(fixed_val, adapt_val, lower_is_better=True):
            if fixed_val == 0 or fixed_val is None:
                return None
            diff = fixed_val - adapt_val if lower_is_better else adapt_val - fixed_val
            return round((diff / fixed_val) * 100.0, 2)

        def fmt_pct(v):
            if v is None:
                return "N/A"
            sign = "+" if v > 0 else ""
            return f"{sign}{v}%"

        for scenario in scenarios:
            f_res = results[scenario]["FIXED"]
            a_res = results[scenario]["ADAPTIVE"]

            wait_imp = calc_pct(f_res["average_waiting_time"], a_res["average_waiting_time"], True)
            queue_imp = calc_pct(f_res["average_queue_length"], a_res["average_queue_length"], True)
            max_q_imp = calc_pct(f_res["max_queue"], a_res["max_queue"], True)
            tp_imp = calc_pct(f_res["throughput"], a_res["throughput"], False)
            spd_imp = calc_pct(f_res["average_speed_kmh"], a_res["average_speed_kmh"], False)
            cong_imp = calc_pct(f_res["congestion_events"], a_res["congestion_events"], True)

            comparison["scenarios"][scenario] = {
                "fixed": f_res,
                "adaptive": a_res,
                "improvements_pct": {
                    "waiting_time_reduction_pct": wait_imp,
                    "avg_queue_reduction_pct": queue_imp,
                    "max_queue_reduction_pct": max_q_imp,
                    "throughput_improvement_pct": tp_imp,
                    "average_speed_improvement_pct": spd_imp,
                    "congestion_events_reduction_pct": cong_imp
                }
            }

            report_rows.append({
                "scenario": SCENARIO_NAME,
                "period_scenario": scenario.upper(),
                "fixed_vehicles": f_res["total_vehicles_inserted"],
                "adaptive_vehicles": a_res["total_vehicles_inserted"],
                "fixed_completed": f_res["completed_vehicles"],
                "adaptive_completed": a_res["completed_vehicles"],
                "throughput_improvement_pct": fmt_pct(tp_imp),
                "fixed_avg_waiting_s": f_res["average_waiting_time"],
                "adaptive_avg_waiting_s": a_res["average_waiting_time"],
                "waiting_time_reduction_pct": fmt_pct(wait_imp),
                "fixed_avg_queue": f_res["average_queue_length"],
                "adaptive_avg_queue": a_res["average_queue_length"],
                "queue_reduction_pct": fmt_pct(queue_imp),
                "fixed_max_queue": f_res["max_queue"],
                "adaptive_max_queue": a_res["max_queue"],
                "max_queue_reduction_pct": fmt_pct(max_q_imp),
                "fixed_avg_speed_kmh": f_res["average_speed_kmh"],
                "adaptive_avg_speed_kmh": a_res["average_speed_kmh"],
                "average_speed_improvement_pct": fmt_pct(spd_imp),
                "fixed_congestion_events": f_res["congestion_events"],
                "adaptive_congestion_events": a_res["congestion_events"],
                "congestion_events_reduction_pct": fmt_pct(cong_imp)
            })

        with open(COMPARISON_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=4)
        print(f"\n  Saved Comparison JSON: {COMPARISON_JSON_PATH}")

        with open(REPORT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"  Saved Report CSV: {REPORT_CSV_PATH}")

        return comparison, results

    def print_report(self, comparison: dict, results: dict):
        print("\n=========================================================================")
        print("           FIXED vs ADAPTIVE EVALUATION RESULTS REPORT                  ")
        print("=========================================================================")
        for scenario in ["morning", "normal", "evening"]:
            data = comparison["scenarios"][scenario]
            f = data["fixed"]
            a = data["adaptive"]
            imp = data["improvements_pct"]
            print(f"\n--- PERIOD SCENARIO: {scenario.upper()} (seed={self.seed}, {self.duration}s) ---")
            print(f"  Vehicles Inserted       : Fixed={f['total_vehicles_inserted']} | Adaptive={a['total_vehicles_inserted']}")
            print(f"  Completed Vehicles      : Fixed={f['completed_vehicles']} | Adaptive={a['completed_vehicles']} (Imp: {'+' if (imp['throughput_improvement_pct'] or 0)>0 else ''}{imp['throughput_improvement_pct']}%)")
            print(f"  Avg Waiting Time (s)    : Fixed={f['average_waiting_time']}s | Adaptive={a['average_waiting_time']}s (Change: {imp['waiting_time_reduction_pct']}%)")
            print(f"  Avg Queue Length        : Fixed={f['average_queue_length']} | Adaptive={a['average_queue_length']} (Change: {imp['avg_queue_reduction_pct']}%)")
            print(f"  Max Queue Length        : Fixed={f['max_queue']} | Adaptive={a['max_queue']} (Change: {imp['max_queue_reduction_pct']}%)")
            print(f"  Avg Speed (km/h)        : Fixed={f['average_speed_kmh']} | Adaptive={a['average_speed_kmh']} (Change: {imp['average_speed_improvement_pct']}%)")
            print(f"  Congestion Events       : Fixed={f['congestion_events']} | Adaptive={a['congestion_events']} (Change: {imp['congestion_events_reduction_pct']}%)")
        print("=========================================================================\n")


def run_evaluation():
    evaluator = ScenarioEvaluator(seed=42, duration=600.0)
    comparison, results = evaluator.run_full_evaluation()
    evaluator.print_report(comparison, results)


if __name__ == "__main__":
    run_evaluation()
