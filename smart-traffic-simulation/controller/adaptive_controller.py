import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import MIN_GREEN_TIME, YELLOW_TIME
from controller.network_topology import get_signal_phases
from controller.traffic_state import TrafficStateAggregator
from controller.signal_optimizer import SignalOptimizer
from controller.emergency import EmergencySystem

class AdaptiveTrafficController:
    """
    Real-time Traffic-Pressure-Based Adaptive Signal Controller with Emergency Priority Overrides
    for arbitrary OpenStreetMap SUMO networks (Left-Hand Traffic).

    Performance fix: state is fetched ONCE per control cycle externally and passed in.
    Yellow phase mapping is now topology-aware (via SignalOptimizer fix).
    """
    def __init__(self, enable_emergency: bool = True):
        self.aggregator = TrafficStateAggregator()
        self.optimizer = SignalOptimizer()
        self.emergency_sys = EmergencySystem() if enable_emergency else None

        # Controller state tracking per traffic light ID
        self.tls_states = {}

    def ensure_tls_initialized(self, tls_id: str, sim_time: float = 0.0):
        if tls_id not in self.tls_states:
            self.tls_states[tls_id] = {
                "current_phase": 0,
                "phase_start_time": sim_time,
                "in_yellow": False,
                "yellow_target_phase": 0,
                "last_green": {}
            }

    def get_signal_decision(self, intersection_id: str, state: dict = None) -> dict:
        """
        Returns a signal decision for intersection_id.
        Accepts pre-fetched state to avoid redundant TraCI calls per TLS per step.
        """
        sim_time = traci.simulation.getTime()
        self.ensure_tls_initialized(intersection_id, sim_time)

        # If state not passed in, fetch it (but caller should batch-fetch for efficiency)
        if state is None:
            state = self.aggregator.get_traffic_state()
        
        intersection_data = state["intersections"].get(intersection_id, {})

        # Check Emergency Priority Overrides via EmergencySystem
        if self.emergency_sys is not None:
            emergency_decisions = self.emergency_sys.process_emergency_overrides(state)
            if intersection_id in emergency_decisions:
                return emergency_decisions[intersection_id]

        tls_state = self.tls_states[intersection_id]
        last_green = tls_state["last_green"]

        decision = self.optimizer.optimize_signal(intersection_id, intersection_data, last_green, sim_time)
        return decision

    def apply_signal_decision(self, decision: dict):
        tls_id = decision["intersection"]
        sim_time = traci.simulation.getTime()
        self.ensure_tls_initialized(tls_id, sim_time)

        target_phase = decision["target_phase_index"]
        yellow_phase = decision["yellow_phase_index"]
        green_duration = decision["green_duration"]

        tls_state = self.tls_states[tls_id]
        current_phase = tls_state["current_phase"]
        phase_start = tls_state["phase_start_time"]
        in_yellow = tls_state["in_yellow"]
        elapsed = sim_time - phase_start

        if in_yellow:
            if elapsed >= YELLOW_TIME:
                try:
                    traci.trafficlight.setPhase(tls_id, target_phase)
                    traci.trafficlight.setPhaseDuration(tls_id, green_duration)
                except traci.TraCIException:
                    pass
                tls_state["current_phase"] = target_phase
                tls_state["phase_start_time"] = sim_time
                tls_state["in_yellow"] = False
                tls_state["last_green"][target_phase] = sim_time
            return

        if current_phase == target_phase:
            remaining = max(1.0, green_duration - elapsed)
            try:
                traci.trafficlight.setPhaseDuration(tls_id, remaining)
            except traci.TraCIException:
                pass
            tls_state["last_green"][target_phase] = sim_time
            return

        if elapsed >= MIN_GREEN_TIME:
            try:
                traci.trafficlight.setPhase(tls_id, yellow_phase)
                traci.trafficlight.setPhaseDuration(tls_id, YELLOW_TIME)
            except traci.TraCIException:
                pass
            tls_state["current_phase"] = yellow_phase
            tls_state["phase_start_time"] = sim_time
            tls_state["in_yellow"] = True
            tls_state["yellow_target_phase"] = target_phase
        else:
            remaining = max(1.0, MIN_GREEN_TIME - elapsed)
            try:
                traci.trafficlight.setPhaseDuration(tls_id, remaining)
            except traci.TraCIException:
                pass
