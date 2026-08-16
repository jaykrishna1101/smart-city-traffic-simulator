import os
import sys
import json
import csv

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import INTERSECTION_MAP, OUTPUT_CSV_PATH, OUTPUT_JSON_PATH
from controller.peak_hour import PeakHourDetector
from controller.emergency import EmergencyDetector
from controller.traffic_metrics import TrafficMetricsCollector

class TrafficStateAggregator:
    """
    Aggregates full traffic simulation state and manages CSV/JSON telemetry export.
    """
    def __init__(self):
        self.peak_detector = PeakHourDetector()
        self.emergency_detector = EmergencyDetector()
        self.metrics_collector = TrafficMetricsCollector()
        self.csv_initialized = False

    def get_tls_state(self, tls_id: str, sim_time: float) -> dict:
        """
        Retrieves current signal phase index, phase state string, and remaining phase duration.
        """
        try:
            current_phase = traci.trafficlight.getPhase(tls_id)
            phase_state = traci.trafficlight.getRedYellowGreenState(tls_id)
            next_switch = traci.trafficlight.getNextSwitch(tls_id)
            remaining_duration = max(0.0, round(next_switch - sim_time, 1))
        except traci.TraCIException:
            current_phase = -1
            phase_state = "UNKNOWN"
            remaining_duration = 0.0

        return {
            "signal_phase": current_phase,
            "phase_state": phase_state,
            "phase_remaining": remaining_duration
        }

    def get_traffic_state(self) -> dict:
        """
        Builds and returns the comprehensive structured simulation state dictionary.
        """
        sim_time = traci.simulation.getTime()
        period = self.peak_detector.get_period(sim_time)
        emergency_vehs = self.emergency_detector.get_emergency_vehicles()

        intersections_data = {}

        for tls_id, directions in INTERSECTION_MAP.items():
            tls_info = self.get_tls_state(tls_id, sim_time)
            
            intersection_entry = {
                "signal_phase": tls_info["signal_phase"],
                "phase_state": tls_info["phase_state"],
                "phase_remaining": tls_info["phase_remaining"]
            }

            for direction, edge_id in directions.items():
                edge_metrics = self.metrics_collector.get_edge_metrics(edge_id)
                edge_metrics["edge_id"] = edge_id
                intersection_entry[direction] = edge_metrics

            intersections_data[tls_id] = intersection_entry

        state = {
            "simulation_time": round(sim_time, 1),
            "period": period,
            "intersections": intersections_data,
            "emergency_vehicles": emergency_vehs
        }

        return state

    def export_csv(self, state: dict, csv_path: str = OUTPUT_CSV_PATH):
        """
        Exports simulation state snapshot to CSV.
        """
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        file_exists = os.path.exists(csv_path)

        fieldnames = [
            "simulation_time", "period", "intersection_id", "direction", "edge_id",
            "vehicles", "queue", "waiting_time", "speed", "speed_kmh", "traffic_flow",
            "congestion", "signal_phase", "phase_state", "phase_remaining", "emergency_vehicle_count"
        ]

        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            sim_time = state["simulation_time"]
            period = state["period"]
            em_count = len(state.get("emergency_vehicles", []))

            for tls_id, tls_data in state["intersections"].items():
                sig_phase = tls_data["signal_phase"]
                phase_state = tls_data["phase_state"]
                phase_rem = tls_data["phase_remaining"]

                for direction in ["north", "south", "east", "west"]:
                    if direction in tls_data:
                        approach = tls_data[direction]
                        writer.writerow({
                            "simulation_time": sim_time,
                            "period": period,
                            "intersection_id": tls_id,
                            "direction": direction,
                            "edge_id": approach["edge_id"],
                            "vehicles": approach["vehicles"],
                            "queue": approach["queue"],
                            "waiting_time": approach["waiting_time"],
                            "speed": approach["speed"],
                            "speed_kmh": approach["speed_kmh"],
                            "traffic_flow": approach["traffic_flow"],
                            "congestion": approach["congestion"],
                            "signal_phase": sig_phase,
                            "phase_state": phase_state,
                            "phase_remaining": phase_rem,
                            "emergency_vehicle_count": em_count
                        })

    def export_json(self, state: dict, json_path: str = OUTPUT_JSON_PATH):
        """
        Exports latest simulation state snapshot to JSON file for adaptive controllers.
        """
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
