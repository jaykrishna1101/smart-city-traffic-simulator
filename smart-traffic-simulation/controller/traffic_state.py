import os
import sys
import json
import csv

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import SCENARIO_NAME, OUTPUT_CSV_PATH, OUTPUT_JSON_PATH
from controller.network_topology import get_traffic_lights, get_intersection_topology
from controller.peak_hour import PeakHourDetector
from controller.emergency import EmergencyDetector
from controller.traffic_metrics import TrafficMetricsCollector

class TrafficStateAggregator:
    """
    Aggregates full traffic simulation state dynamically using network_topology discovery
    and manages CSV/JSON telemetry export for any OpenStreetMap SUMO network.
    """
    def __init__(self):
        self.peak_detector = PeakHourDetector()
        self.emergency_detector = EmergencyDetector()
        self.metrics_collector = TrafficMetricsCollector()

    def get_traffic_state(self) -> dict:
        """
        Builds and returns the comprehensive structured simulation state dictionary,
        dynamically discovering all traffic light IDs and topology via network_topology module.
        """
        sim_time = traci.simulation.getTime()
        period = self.peak_detector.get_period(sim_time)
        emergency_vehs = self.emergency_detector.get_emergency_vehicles()

        tls_ids = get_traffic_lights()
        intersections_data = {}

        for tls_id in tls_ids:
            topo = get_intersection_topology(tls_id)
            
            approaches_data = {}
            tot_vehs = 0
            tot_queue = 0
            tot_wait = 0.0
            speeds = []

            for edge_id in topo["incoming_edges"]:
                edge_metrics = self.metrics_collector.get_edge_metrics(edge_id)
                edge_metrics["edge_id"] = edge_id
                approaches_data[edge_id] = edge_metrics

                tot_vehs += edge_metrics["vehicles"]
                tot_queue += edge_metrics["queue"]
                tot_wait += edge_metrics["waiting_time"]
                speeds.append(edge_metrics["speed"])

            avg_spd = round(sum(speeds) / max(len(speeds), 1), 2)
            avg_spd_kmh = round(avg_spd * 3.6, 2)
            avg_wait = round(tot_wait / max(len(topo["incoming_edges"]), 1), 2)

            intersection_entry = {
                "intersection_id": tls_id,
                "signal_phase": topo["current_phase"],
                "phase_state": topo["phase_state"],
                "phase_remaining": topo["phase_duration"],
                "controlled_lanes": topo["incoming_lanes"],
                "controlled_edges": topo["incoming_edges"],
                "outgoing_edges": topo["outgoing_edges"],
                "controlled_links_count": len(topo["controlled_links"]),
                "approaches": approaches_data,
                "total_vehicles": tot_vehs,
                "total_queue": tot_queue,
                "average_waiting_time": avg_wait,
                "average_speed": avg_spd,
                "average_speed_kmh": avg_spd_kmh
            }

            intersections_data[tls_id] = intersection_entry

        state = {
            "scenario": SCENARIO_NAME,
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
            "scenario", "simulation_time", "period", "intersection_id", "edge_id",
            "vehicles", "queue", "waiting_time", "speed", "speed_kmh", "traffic_flow",
            "congestion", "signal_phase", "phase_state", "phase_remaining", "emergency_vehicle_count"
        ]

        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            scenario = state.get("scenario", SCENARIO_NAME)
            sim_time = state["simulation_time"]
            period = state["period"]
            em_count = len(state.get("emergency_vehicles", []))

            for tls_id, tls_data in state["intersections"].items():
                sig_phase = tls_data["signal_phase"]
                phase_state = tls_data["phase_state"]
                phase_rem = tls_data["phase_remaining"]

                for edge_id, approach in tls_data.get("approaches", {}).items():
                    writer.writerow({
                        "scenario": scenario,
                        "simulation_time": sim_time,
                        "period": period,
                        "intersection_id": tls_id,
                        "edge_id": edge_id,
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
        Exports latest simulation state snapshot to JSON file.
        """
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
