import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import CONGESTION_LEVELS

class TrafficMetricsCollector:
    """
    Collects real-time traffic metrics for network edges and lanes, and classifies congestion.
    """
    def __init__(self):
        self.prev_edge_vehicle_counts = {}

    def classify_congestion(self, queue_len: int, avg_waiting_time: float) -> str:
        """
        Classifies congestion level (SEVERE, HIGH, MEDIUM, LOW) based on queue length and waiting time.
        """
        if queue_len >= CONGESTION_LEVELS["SEVERE"]["queue"] or avg_waiting_time >= CONGESTION_LEVELS["SEVERE"]["waiting_time"]:
            return "SEVERE"
        elif queue_len >= CONGESTION_LEVELS["HIGH"]["queue"] or avg_waiting_time >= CONGESTION_LEVELS["HIGH"]["waiting_time"]:
            return "HIGH"
        elif queue_len >= CONGESTION_LEVELS["MEDIUM"]["queue"] or avg_waiting_time >= CONGESTION_LEVELS["MEDIUM"]["waiting_time"]:
            return "MEDIUM"
        else:
            return "LOW"

    def get_edge_metrics(self, edge_id: str) -> dict:
        """
        Queries TraCI for edge-level metrics: vehicle count, queue length, average waiting time, mean speed, flow, and congestion level.
        """
        try:
            veh_count = traci.edge.getLastStepVehicleNumber(edge_id)
            queue_len = traci.edge.getLastStepHaltingNumber(edge_id)
            total_waiting_time = traci.edge.getWaitingTime(edge_id)
            avg_speed_ms = traci.edge.getLastStepMeanSpeed(edge_id)
        except traci.TraCIException:
            return {
                "vehicles": 0,
                "queue": 0,
                "waiting_time": 0.0,
                "speed": 0.0,
                "speed_kmh": 0.0,
                "traffic_flow": 0,
                "congestion": "LOW"
            }

        avg_waiting_time = round(total_waiting_time / max(veh_count, 1), 2)
        avg_speed_ms = max(0.0, round(avg_speed_ms, 2))
        avg_speed_kmh = round(avg_speed_ms * 3.6, 2)
        
        # Calculate instantaneous flow difference
        prev_count = self.prev_edge_vehicle_counts.get(edge_id, veh_count)
        traffic_flow = veh_count - prev_count
        self.prev_edge_vehicle_counts[edge_id] = veh_count

        congestion_level = self.classify_congestion(queue_len, avg_waiting_time)

        return {
            "vehicles": veh_count,
            "queue": queue_len,
            "waiting_time": avg_waiting_time,
            "speed": avg_speed_ms,
            "speed_kmh": avg_speed_kmh,
            "traffic_flow": traffic_flow,
            "congestion": congestion_level
        }

    def get_lane_metrics(self, lane_id: str) -> dict:
        """
        Queries TraCI for lane-level metrics: vehicle count, queue length, average waiting time, mean speed, and congestion level.
        """
        try:
            veh_count = traci.lane.getLastStepVehicleNumber(lane_id)
            queue_len = traci.lane.getLastStepHaltingNumber(lane_id)
            avg_speed_ms = traci.lane.getLastStepMeanSpeed(lane_id)
            # Estimate waiting time based on halting vehicles
            total_waiting_time = queue_len * 10.0
        except traci.TraCIException:
            return {
                "vehicles": 0,
                "queue": 0,
                "waiting_time": 0.0,
                "speed": 0.0,
                "speed_kmh": 0.0,
                "congestion": "LOW"
            }

        avg_waiting_time = round(total_waiting_time / max(veh_count, 1), 2)
        avg_speed_ms = max(0.0, round(avg_speed_ms, 2))
        avg_speed_kmh = round(avg_speed_ms * 3.6, 2)
        congestion_level = self.classify_congestion(queue_len, avg_waiting_time)

        return {
            "vehicles": veh_count,
            "queue": queue_len,
            "waiting_time": avg_waiting_time,
            "speed": avg_speed_ms,
            "speed_kmh": avg_speed_kmh,
            "congestion": congestion_level
        }
