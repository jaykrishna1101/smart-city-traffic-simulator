import os
import sys
import json
import csv
import time

# Ensure project directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import traci
from controller.config import SUMO_CONFIG_PATH, SCENARIO_NAME
from controller.traffic_state import TrafficStateAggregator
from controller.adaptive_controller import AdaptiveTrafficController
from controller.emergency import EmergencySystem

EVALUATION_DIR = os.path.join(PROJECT_DIR, "output", "evaluation")
EMERGENCY_JSON_PATH = os.path.join(EVALUATION_DIR, "emergency_comparison.json")
EMERGENCY_CSV_PATH = os.path.join(EVALUATION_DIR, "emergency_report.csv")

def get_sumo_binary() -> str:
    sumo_home = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
    sumo_bin = os.path.join(sumo_home, "bin", "sumo.exe")
    return sumo_bin if os.path.exists(sumo_bin) else "sumo"

DEMO_CONFIGS = [
    {
        "vehicle_id": "AMBULANCE_NAGPUR",
        "type": "ambulance",
        "route_id": "route_AMBULANCE_DEMO",
        "from_edge": "372646899#9",
        "to_edge": "-93620634#5",
        "depart": 50,
        "color": (255, 0, 0, 255),
        "target_tls": "cluster_2683490416_2683507646_2683507647_2684658305_#2more"
    },
    {
        "vehicle_id": "POLICE_NAGPUR",
        "type": "police",
        "route_id": "route_POLICE_DEMO",
        "from_edge": "93620634#5",
        "to_edge": "29104458#4",
        "depart": 150,
        "color": (0, 0, 255, 255),
        "target_tls": "cluster_2683490405_298938456"
    },
    {
        "vehicle_id": "FIRETRUCK_NAGPUR",
        "type": "fire_truck",
        "route_id": "route_FIRETRUCK_DEMO",
        "from_edge": "29104185#2",
        "to_edge": "29104472#1",
        "depart": 250,
        "color": (255, 77, 0, 255),
        "target_tls": "cluster_2683490405_298938456"
    }
]

def run_emergency_experiment(mode: str, seed: int = 42, max_steps: int = 350) -> dict:
    """
    Runs an emergency experiment under FIXED (no priority) or ADAPTIVE (with priority).
    """
    os.makedirs(EVALUATION_DIR, exist_ok=True)
    is_adaptive = (mode.upper() == "ADAPTIVE")

    cmd = [
        get_sumo_binary(),
        "-c", SUMO_CONFIG_PATH,
        "--seed", str(seed),
        "--no-step-log", "true",
        "--no-warnings", "true"
    ]

    print(f"\n>>> Running Emergency Benchmark | Mode: {mode:<8} | Seed: {seed} | Duration: {max_steps}s <<<")
    traci.start(cmd)

    aggregator = TrafficStateAggregator()
    emergency_sys = EmergencySystem()
    controller = AdaptiveTrafficController(enable_emergency=True) if is_adaptive else None

    # Track metrics per emergency vehicle
    ev_metrics = {}
    for cfg in DEMO_CONFIGS:
        vid = cfg["vehicle_id"]
        ev_metrics[vid] = {
            "vehicle_id": vid,
            "type": cfg["type"],
            "route_id": cfg["route_id"],
            "target_tls": cfg["target_tls"],
            "depart_step": cfg["depart"],
            "actual_depart": None,
            "arrival_step": None,
            "travel_duration": 0.0,
            "accumulated_waiting_time": 0.0,
            "time_loss": 0.0,
            "speed_samples": [],
            "route_length": 0.0,
            "stops_count": 0,
            "priority_overrides_count": 0
        }

    # Track general network metrics
    general_speeds = []
    general_completed_waits = []
    last_general_waits = {}
    total_general_inserted = set()
    total_general_arrived = set()

    try:
        for step in range(max_steps):
            traci.simulationStep()
            sim_time = traci.simulation.getTime()
            t_int = int(sim_time)

            # Spawn emergency vehicles at specified times for both Fixed and Adaptive
            for cfg in DEMO_CONFIGS:
                vid = cfg["vehicle_id"]
                if t_int == cfg["depart"] and vid not in emergency_sys.spawned_emergencies:
                    emergency_sys._inject_emergency_vehicle(
                        v_id=vid,
                        v_type=cfg["type"],
                        from_edge=cfg["from_edge"],
                        to_edge=cfg["to_edge"],
                        color_rgba=cfg["color"],
                        custom_route_id=cfg["route_id"]
                    )
                    r = traci.simulation.findRoute(cfg["from_edge"], cfg["to_edge"], vType=cfg["type"])
                    if r:
                        ev_metrics[vid]["route_length"] = round(r.length, 1)

            # Track active vehicles
            active_ids = traci.vehicle.getIDList()
            arrived_ids = traci.simulation.getArrivedIDList()
            departed_ids = traci.simulation.getDepartedIDList()

            for d in departed_ids:
                total_general_inserted.add(d)

            # Sample metrics for active emergency vehicles
            for cfg in DEMO_CONFIGS:
                vid = cfg["vehicle_id"]
                if vid in active_ids:
                    if ev_metrics[vid]["actual_depart"] is None:
                        ev_metrics[vid]["actual_depart"] = sim_time

                    spd = traci.vehicle.getSpeed(vid)
                    ev_metrics[vid]["speed_samples"].append(spd)
                    ev_metrics[vid]["accumulated_waiting_time"] = traci.vehicle.getAccumulatedWaitingTime(vid)
                    ev_metrics[vid]["time_loss"] = traci.vehicle.getTimeLoss(vid)

                    if spd < 0.1:
                        ev_metrics[vid]["stops_count"] += 1

                if vid in arrived_ids and ev_metrics[vid]["arrival_step"] is None:
                    ev_metrics[vid]["arrival_step"] = sim_time
                    dep_t = ev_metrics[vid]["actual_depart"] if ev_metrics[vid]["actual_depart"] is not None else cfg["depart"]
                    ev_metrics[vid]["travel_duration"] = round(sim_time - dep_t, 2)

            # General traffic tracking
            for v in active_ids:
                if not ("AMBULANCE" in v or "POLICE" in v or "FIRE" in v):
                    try:
                        spd = traci.vehicle.getSpeed(v)
                        if spd > 0.0:
                            general_speeds.append(spd)
                        last_general_waits[v] = traci.vehicle.getAccumulatedWaitingTime(v)
                    except traci.TraCIException:
                        pass

            for arr in arrived_ids:
                if not ("AMBULANCE" in arr or "POLICE" in arr or "FIRE" in arr):
                    total_general_arrived.add(arr)
                    if arr in last_general_waits:
                        general_completed_waits.append(last_general_waits[arr])

            state = aggregator.get_traffic_state()

            # Apply signal control: Fixed vs Adaptive
            if is_adaptive and controller:
                for tls_id in list(state["intersections"].keys()):
                    decision = controller.get_signal_decision(tls_id, state=state)
                    controller.apply_signal_decision(decision)
                    if "Emergency Priority Override" in decision.get("reason", ""):
                        for cfg in DEMO_CONFIGS:
                            vid = cfg["vehicle_id"]
                            if vid in active_ids and cfg["target_tls"] == tls_id:
                                ev_metrics[vid]["priority_overrides_count"] += 1

    finally:
        traci.close()

    # Summarize EV metrics
    processed_evs = {}
    for vid, m in ev_metrics.items():
        avg_spd_ms = sum(m["speed_samples"]) / len(m["speed_samples"]) if m["speed_samples"] else 0.0
        processed_evs[vid] = {
            "vehicle_id": vid,
            "type": m["type"],
            "route_id": m["route_id"],
            "route_length_m": m["route_length"],
            "target_tls": m["target_tls"],
            "travel_duration_s": m["travel_duration"],
            "waiting_time_s": round(m["accumulated_waiting_time"], 2),
            "time_loss_s": round(m["time_loss"], 2),
            "average_speed_kmh": round(avg_spd_ms * 3.6, 2),
            "stops_count": m["stops_count"],
            "priority_overrides_steps": m["priority_overrides_count"]
        }

    # Compute overall EV averages
    avg_ev_travel = sum(e["travel_duration_s"] for e in processed_evs.values()) / len(processed_evs)
    avg_ev_wait = sum(e["waiting_time_s"] for e in processed_evs.values()) / len(processed_evs)
    avg_ev_loss = sum(e["time_loss_s"] for e in processed_evs.values()) / len(processed_evs)
    avg_ev_speed = sum(e["average_speed_kmh"] for e in processed_evs.values()) / len(processed_evs)

    # General traffic summary
    gen_avg_speed = (sum(general_speeds) / len(general_speeds) * 3.6) if general_speeds else 0.0
    gen_avg_wait = (sum(general_completed_waits) / len(general_completed_waits)) if general_completed_waits else 0.0

    return {
        "mode": mode,
        "seed": seed,
        "duration_steps": max_steps,
        "emergency_vehicles": processed_evs,
        "summary": {
            "avg_ev_travel_duration_s": round(avg_ev_travel, 2),
            "avg_ev_waiting_time_s": round(avg_ev_wait, 2),
            "avg_ev_time_loss_s": round(avg_ev_loss, 2),
            "avg_ev_speed_kmh": round(avg_ev_speed, 2),
            "general_traffic": {
                "total_vehicles_inserted": len(total_general_inserted),
                "completed_vehicles": len(total_general_arrived),
                "avg_speed_kmh": round(gen_avg_speed, 2),
                "avg_waiting_time_s": round(gen_avg_wait, 2)
            }
        }
    }

def run_emergency_evaluation():
    print("=" * 80)
    print("  FIXED vs ADAPTIVE EMERGENCY VEHICLE EVALUATION (INDIAN LHT, CHATRAPATI-RING ROAD)")
    print("=" * 80)

    fixed_results = run_emergency_experiment("FIXED", seed=42, max_steps=350)
    adaptive_results = run_emergency_experiment("ADAPTIVE", seed=42, max_steps=350)

    # Comparison calculations
    def pct_change(fixed_val, adapt_val, lower_is_better=True):
        if fixed_val == 0.0:
            return 0.0
        diff = fixed_val - adapt_val if lower_is_better else adapt_val - fixed_val
        return round((diff / fixed_val) * 100.0, 1)

    ev_comparison = {}
    for vid in fixed_results["emergency_vehicles"].keys():
        f_ev = fixed_results["emergency_vehicles"][vid]
        a_ev = adaptive_results["emergency_vehicles"][vid]

        dur_imp = pct_change(f_ev["travel_duration_s"], a_ev["travel_duration_s"], lower_is_better=True)
        wait_imp = pct_change(f_ev["waiting_time_s"], a_ev["waiting_time_s"], lower_is_better=True)
        loss_imp = pct_change(f_ev["time_loss_s"], a_ev["time_loss_s"], lower_is_better=True)
        spd_imp = pct_change(f_ev["average_speed_kmh"], a_ev["average_speed_kmh"], lower_is_better=False)

        ev_comparison[vid] = {
            "vehicle_id": vid,
            "type": f_ev["type"],
            "route_id": f_ev["route_id"],
            "route_length_m": f_ev["route_length_m"],
            "target_tls": f_ev["target_tls"],
            "fixed": f_ev,
            "adaptive": a_ev,
            "improvements": {
                "travel_duration_reduction_pct": dur_imp,
                "waiting_time_reduction_pct": wait_imp,
                "time_loss_reduction_pct": loss_imp,
                "speed_increase_pct": spd_imp
            }
        }

    overall_dur_imp = pct_change(
        fixed_results["summary"]["avg_ev_travel_duration_s"],
        adaptive_results["summary"]["avg_ev_travel_duration_s"],
        lower_is_better=True
    )
    overall_wait_imp = pct_change(
        fixed_results["summary"]["avg_ev_waiting_time_s"],
        adaptive_results["summary"]["avg_ev_waiting_time_s"],
        lower_is_better=True
    )
    overall_loss_imp = pct_change(
        fixed_results["summary"]["avg_ev_time_loss_s"],
        adaptive_results["summary"]["avg_ev_time_loss_s"],
        lower_is_better=True
    )
    overall_spd_imp = pct_change(
        fixed_results["summary"]["avg_ev_speed_kmh"],
        adaptive_results["summary"]["avg_ev_speed_kmh"],
        lower_is_better=False
    )

    final_comparison = {
        "scenario": SCENARIO_NAME,
        "seed": 42,
        "simulation_duration": 350.0,
        "vehicles": ev_comparison,
        "overall_summary": {
            "fixed": fixed_results["summary"],
            "adaptive": adaptive_results["summary"],
            "improvements": {
                "avg_response_time_reduction_pct": overall_dur_imp,
                "avg_waiting_time_reduction_pct": overall_wait_imp,
                "avg_time_loss_reduction_pct": overall_loss_imp,
                "avg_speed_increase_pct": overall_spd_imp
            }
        }
    }

    # Save JSON
    with open(EMERGENCY_JSON_PATH, "w") as f:
        json.dump(final_comparison, f, indent=2)
    print(f"\nSaved Emergency Comparison JSON: {EMERGENCY_JSON_PATH}")

    # Save CSV Report
    with open(EMERGENCY_CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Vehicle ID", "Type", "Route Length (m)", "Target TLS",
            "Fixed Travel Time (s)", "Adaptive Travel Time (s)", "Travel Time Improvement (%)",
            "Fixed Wait Time (s)", "Adaptive Wait Time (s)", "Wait Time Improvement (%)",
            "Fixed Speed (km/h)", "Adaptive Speed (km/h)", "Speed Improvement (%)"
        ])
        for vid, data in ev_comparison.items():
            f = data["fixed"]
            a = data["adaptive"]
            imp = data["improvements"]
            writer.writerow([
                vid, data["type"], data["route_length_m"], data["target_tls"],
                f["travel_duration_s"], a["travel_duration_s"], f"{imp['travel_duration_reduction_pct']}%",
                f["waiting_time_s"], a["waiting_time_s"], f"{imp['waiting_time_reduction_pct']}%",
                f["average_speed_kmh"], a["average_speed_kmh"], f"{imp['speed_increase_pct']}%"
            ])
    print(f"Saved Emergency Report CSV: {EMERGENCY_CSV_PATH}")

    # Console Report
    print("\n" + "=" * 80)
    print("              FIXED vs ADAPTIVE EMERGENCY PERFORMANCE REPORT")
    print("=" * 80)
    print(f"{'Vehicle':<18} | {'Metric':<18} | {'Fixed':<10} | {'Adaptive':<10} | {'Improvement':<12}")
    print("-" * 80)
    for vid, data in ev_comparison.items():
        f = data["fixed"]
        a = data["adaptive"]
        imp = data["improvements"]
        print(f"{vid:<18} | Travel Time (s)    | {f['travel_duration_s']:<10.1f} | {a['travel_duration_s']:<10.1f} | -{imp['travel_duration_reduction_pct']}%")
        print(f"{'':<18} | Waiting Time (s)   | {f['waiting_time_s']:<10.1f} | {a['waiting_time_s']:<10.1f} | -{imp['waiting_time_reduction_pct']}%")
        print(f"{'':<18} | Avg Speed (km/h)   | {f['average_speed_kmh']:<10.1f} | {a['average_speed_kmh']:<10.1f} | +{imp['speed_increase_pct']}%")
        print("-" * 80)

    print(f"\n{'OVERALL AVERAGE':<18} | {'Travel Time (s)':<18} | {fixed_results['summary']['avg_ev_travel_duration_s']:<10.1f} | {adaptive_results['summary']['avg_ev_travel_duration_s']:<10.1f} | -{overall_dur_imp}%")
    print(f"{'':<18} | {'Waiting Time (s)':<18} | {fixed_results['summary']['avg_ev_waiting_time_s']:<10.1f} | {adaptive_results['summary']['avg_ev_waiting_time_s']:<10.1f} | -{overall_wait_imp}%")
    print(f"{'':<18} | {'Avg Speed (km/h)':<18} | {fixed_results['summary']['avg_ev_speed_kmh']:<10.1f} | {adaptive_results['summary']['avg_ev_speed_kmh']:<10.1f} | +{overall_spd_imp}%")
    print("=" * 80)

if __name__ == "__main__":
    run_emergency_evaluation()
