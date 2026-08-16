import os
import sys
import json
import csv

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import COMPARISON_JSON_PATH

class BenchmarkTracker:
    """
    Tracks and aggregates empirical simulation metrics for Fixed vs Adaptive performance comparison.
    """
    def __init__(self):
        self.max_queue = 0
        self.total_waiting_time = 0.0
        self.total_vehicle_samples = 0
        self.speed_samples = []
        self.congestion_events = 0
        self.emergency_depart_times = {}
        self.emergency_durations = {}
        self.departed_ids_set = set()

    def update(self, sim_time: float, state: dict):
        """
        Updates step-level metric aggregations.
        """
        try:
            dep_ids = traci.simulation.getLoadedIDList()
            for d in dep_ids:
                self.departed_ids_set.add(d)
        except traci.TraCIException:
            pass
        # Track active vehicles & speeds
        try:
            active_ids = traci.vehicle.getIDList()
        except traci.TraCIException:
            active_ids = []

        for v_id in active_ids:
            # Track emergency vehicle response time
            v_id_upper = v_id.upper()
            if "AMBULANCE" in v_id_upper or "FIRE" in v_id_upper or "POLICE" in v_id_upper:
                if v_id not in self.emergency_depart_times:
                    self.emergency_depart_times[v_id] = sim_time
            
            try:
                spd = traci.vehicle.getSpeed(v_id)
                self.speed_samples.append(spd)
            except traci.TraCIException:
                pass

        # Track arrival of emergency vehicles
        try:
            arrived_ids = traci.simulation.getArrivedIDList()
        except traci.TraCIException:
            arrived_ids = []

        for arr_id in arrived_ids:
            arr_upper = arr_id.upper()
            if "AMBULANCE" in arr_upper or "FIRE" in arr_upper or "POLICE" in arr_upper:
                if arr_id in self.emergency_depart_times:
                    duration = sim_time - self.emergency_depart_times[arr_id]
                    self.emergency_durations[arr_id] = duration

        # Track queue, waiting time, and congestion events per intersection
        for tls_id, tls_data in state["intersections"].items():
            for direction in ["north", "south", "east", "west"]:
                if direction in tls_data:
                    app = tls_data[direction]
                    q = app["queue"]
                    w = app["waiting_time"]
                    cong = app["congestion"]

                    if q > self.max_queue:
                        self.max_queue = q

                    if cong in ["HIGH", "SEVERE"]:
                        self.congestion_events += 1

                    self.total_waiting_time += w
                    self.total_vehicle_samples += 1

    def generate_benchmark_summary(self, mode: str) -> dict:
        # Track cumulative departed vehicles across step execution
        if hasattr(self, 'departed_ids_set'):
            inserted = len(self.departed_ids_set)
        else:
            inserted = 0

        try:
            arrived = traci.simulation.getArrivedNumber()
        except traci.TraCIException:
            arrived = 0

        avg_speed_ms = (sum(self.speed_samples) / max(len(self.speed_samples), 1)) if self.speed_samples else 0.0
        avg_speed_kmh = round(avg_speed_ms * 3.6, 2)

        avg_waiting = round(self.total_waiting_time / max(self.total_vehicle_samples, 1), 2)

        if self.emergency_durations:
            avg_emergency_response = round(sum(self.emergency_durations.values()) / len(self.emergency_durations), 1)
        else:
            avg_emergency_response = 0.0

        return {
            "mode": mode,
            "total_vehicles_inserted": inserted,
            "throughput": arrived,
            "average_waiting_time": avg_waiting,
            "max_queue": self.max_queue,
            "average_speed": round(avg_speed_ms, 2),
            "average_speed_kmh": avg_speed_kmh,
            "congestion_events": self.congestion_events,
            "emergency_response_time": avg_emergency_response
        }

    @staticmethod
    def export_comparison_json(fixed_res: dict, adaptive_res: dict, json_path: str = COMPARISON_JSON_PATH):
        """
        Generates structured output/comparison.json with measured values and percentage improvements.
        """
        def calc_pct(fixed_val, adapt_val, lower_is_better=True):
            if fixed_val == 0:
                return "0.0%"
            diff = fixed_val - adapt_val if lower_is_better else adapt_val - fixed_val
            pct = (diff / fixed_val) * 100.0
            direction_str = "reduction" if lower_is_better else "increase"
            return f"{pct:.1f}% {direction_str}"

        comparison_data = {
            "fixed": {
                "total_vehicles_inserted": fixed_res["total_vehicles_inserted"],
                "throughput": fixed_res["throughput"],
                "average_waiting_time": fixed_res["average_waiting_time"],
                "max_queue": fixed_res["max_queue"],
                "average_speed_kmh": fixed_res["average_speed_kmh"],
                "congestion_events": fixed_res["congestion_events"],
                "emergency_response_time": fixed_res["emergency_response_time"]
            },
            "adaptive": {
                "total_vehicles_inserted": adaptive_res["total_vehicles_inserted"],
                "throughput": adaptive_res["throughput"],
                "average_waiting_time": adaptive_res["average_waiting_time"],
                "max_queue": adaptive_res["max_queue"],
                "average_speed_kmh": adaptive_res["average_speed_kmh"],
                "congestion_events": adaptive_res["congestion_events"],
                "emergency_response_time": adaptive_res["emergency_response_time"]
            },
            "improvement_percentage": {
                "average_waiting_time": calc_pct(fixed_res["average_waiting_time"], adaptive_res["average_waiting_time"], True),
                "max_queue": calc_pct(fixed_res["max_queue"], adaptive_res["max_queue"], True),
                "throughput": calc_pct(fixed_res["throughput"], adaptive_res["throughput"], False),
                "average_speed": calc_pct(fixed_res["average_speed_kmh"], adaptive_res["average_speed_kmh"], False),
                "congestion_events": calc_pct(fixed_res["congestion_events"], adaptive_res["congestion_events"], True),
                "emergency_response_time": calc_pct(fixed_res["emergency_response_time"], adaptive_res["emergency_response_time"], True)
            }
        }

        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=4)
        print(f"\nGenerated benchmark comparison JSON: {json_path}")
        return comparison_data
