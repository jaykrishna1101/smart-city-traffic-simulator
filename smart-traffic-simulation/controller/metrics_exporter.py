import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import COMPARISON_JSON_PATH, SCENARIO_NAME
import json
import csv

class BenchmarkTracker:
    """
    Tracks and aggregates empirical simulation metrics for Fixed vs Adaptive performance comparison.

    FIX (Bug 1): Waiting time is now tracked per-vehicle using traci.vehicle.getWaitingTime(),
    averaged over unique vehicles — not over (edge, timestep) samples.
    FIX (Bug 5): Speed is measured on controlled approach edges only, not all network vehicles.
    """
    def __init__(self):
        self.max_queue = 0
        self.total_queue_samples = []
        self.congestion_events = 0
        self.emergency_depart_times = {}
        self.emergency_durations = {}
        self.departed_ids_set = set()
        self.arrived_ids_set = set()

        # Per-vehicle waiting time accumulator (more realistic)
        # last_vehicle_wait: snapshot of accumulated wait from the PREVIOUS step
        # (needed to capture wait for vehicles that just departed and are no longer queryable)
        self._last_vehicle_wait = {}    # v_id -> last accumulated wait (float)
        self._completed_vehicle_waits = []  # final accumulated wait for each completed vehicle
        self.approach_speed_samples = []    # speed samples from controlled edges only

        # Track per-edge congestion state to count transitions, not per-step counts
        self._edge_was_congested = {}  # edge_id -> bool

    def update(self, sim_time: float, state: dict):
        """
        Updates step-level metric aggregations.
        Measures waiting time per vehicle directly from TraCI, not per edge/step.
        """
        # Track loaded/departed vehicles
        try:
            dep_ids = traci.simulation.getDepartedIDList()
            for d in dep_ids:
                self.departed_ids_set.add(d)
        except traci.TraCIException:
            pass

        # Track active vehicle current accumulated waiting times
        try:
            active_ids = traci.vehicle.getIDList()
        except traci.TraCIException:
            active_ids = []

        for v_id in active_ids:
            v_id_upper = v_id.upper()
            if "AMBULANCE" in v_id_upper or "FIRE" in v_id_upper or "POLICE" in v_id_upper:
                if v_id not in self.emergency_depart_times:
                    self.emergency_depart_times[v_id] = sim_time

            try:
                # Track last-known accumulated wait for each active vehicle
                v_wait = traci.vehicle.getAccumulatedWaitingTime(v_id)
                self._last_vehicle_wait[v_id] = v_wait
            except traci.TraCIException:
                pass

        # Capture waiting times of vehicles that just completed their trip
        # (they've departed, so we use their last-known accumulated wait)
        try:
            arrived_ids = traci.simulation.getArrivedIDList()
        except traci.TraCIException:
            arrived_ids = []

        for arr_id in arrived_ids:
            self.arrived_ids_set.add(arr_id)
            # Use last-known accumulated wait for this vehicle (captured before it left)
            if arr_id in self._last_vehicle_wait:
                self._completed_vehicle_waits.append(self._last_vehicle_wait[arr_id])

            arr_upper = arr_id.upper()
            if "AMBULANCE" in arr_upper or "FIRE" in arr_upper or "POLICE" in arr_upper:
                if arr_id in self.emergency_depart_times:
                    duration = sim_time - self.emergency_depart_times[arr_id]
                    self.emergency_durations[arr_id] = duration

        # Track queue, congestion events, and speed from controlled approach edges
        for tls_id, tls_data in state.get("intersections", {}).items():
            approaches = tls_data.get("approaches", {})
            for edge_id, app in approaches.items():
                q = app["queue"]
                cong = app["congestion"]
                spd = app.get("speed", 0.0)

                if q > self.max_queue:
                    self.max_queue = q

                self.total_queue_samples.append(q)

                # Count only NEW congestion events (transition from non-congested to congested)
                is_congested_now = cong in ["HIGH", "SEVERE"]
                was_congested = self._edge_was_congested.get(edge_id, False)
                if is_congested_now and not was_congested:
                    self.congestion_events += 1
                self._edge_was_congested[edge_id] = is_congested_now

                # FIX: Only collect speed from approach edges (controlled area)
                if spd > 0.0:
                    self.approach_speed_samples.append(spd)

    def generate_benchmark_summary(self, mode: str) -> dict:
        inserted = len(self.departed_ids_set)

        try:
            arrived_count = len(self.arrived_ids_set)
        except Exception:
            arrived_count = 0

        # Average waiting time: only over COMPLETED vehicles (matches SUMO's own stats method)
        if self._completed_vehicle_waits:
            avg_waiting = round(sum(self._completed_vehicle_waits) / len(self._completed_vehicle_waits), 2)
        else:
            avg_waiting = 0.0

        # FIX (Bug 5): Speed only from controlled approach edges
        avg_speed_ms = (sum(self.approach_speed_samples) / max(len(self.approach_speed_samples), 1)) if self.approach_speed_samples else 0.0
        avg_speed_kmh = round(avg_speed_ms * 3.6, 2)

        avg_queue = round(sum(self.total_queue_samples) / max(len(self.total_queue_samples), 1), 2) if self.total_queue_samples else 0.0

        if self.emergency_durations:
            avg_emergency_response = round(sum(self.emergency_durations.values()) / len(self.emergency_durations), 1)
        else:
            avg_emergency_response = 0.0

        return {
            "scenario": SCENARIO_NAME,
            "mode": mode,
            "total_vehicles_inserted": inserted,
            "completed_vehicles": arrived_count,
            "throughput": arrived_count,
            "average_waiting_time": avg_waiting,
            "average_queue_length": avg_queue,
            "max_queue": self.max_queue,
            "average_speed": round(avg_speed_ms, 2),
            "average_speed_kmh": avg_speed_kmh,
            "congestion_events": self.congestion_events,
            "emergency_response_time": avg_emergency_response
        }

    @staticmethod
    def export_comparison_json(fixed_res: dict, adaptive_res: dict, json_path: str = COMPARISON_JSON_PATH):
        """
        Generates structured comparison.json with measured values and percentage improvements.
        """
        def calc_pct(fixed_val, adapt_val, lower_is_better=True):
            if fixed_val == 0:
                return "N/A"
            diff = fixed_val - adapt_val if lower_is_better else adapt_val - fixed_val
            pct = (diff / fixed_val) * 100.0
            direction_str = "reduction" if lower_is_better else "increase"
            return f"{pct:.1f}% {direction_str}"

        comparison_data = {
            "scenario": SCENARIO_NAME,
            "fixed": {
                "total_vehicles_inserted": fixed_res["total_vehicles_inserted"],
                "completed_vehicles": fixed_res["completed_vehicles"],
                "throughput": fixed_res["throughput"],
                "average_waiting_time": fixed_res["average_waiting_time"],
                "average_queue_length": fixed_res["average_queue_length"],
                "max_queue": fixed_res["max_queue"],
                "average_speed_kmh": fixed_res["average_speed_kmh"],
                "congestion_events": fixed_res["congestion_events"],
                "emergency_response_time": fixed_res["emergency_response_time"]
            },
            "adaptive": {
                "total_vehicles_inserted": adaptive_res["total_vehicles_inserted"],
                "completed_vehicles": adaptive_res["completed_vehicles"],
                "throughput": adaptive_res["throughput"],
                "average_waiting_time": adaptive_res["average_waiting_time"],
                "average_queue_length": adaptive_res["average_queue_length"],
                "max_queue": adaptive_res["max_queue"],
                "average_speed_kmh": adaptive_res["average_speed_kmh"],
                "congestion_events": adaptive_res["congestion_events"],
                "emergency_response_time": adaptive_res["emergency_response_time"]
            },
            "improvement_percentage": {
                "average_waiting_time": calc_pct(fixed_res["average_waiting_time"], adaptive_res["average_waiting_time"], True),
                "average_queue_length": calc_pct(fixed_res["average_queue_length"], adaptive_res["average_queue_length"], True),
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
