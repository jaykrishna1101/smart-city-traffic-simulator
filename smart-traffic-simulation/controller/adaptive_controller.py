import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import (
    INTERSECTION_MAP, PHASE_MAP, MIN_GREEN_TIME, YELLOW_TIME,
    EMERGENCY_TRIGGER_DIST
)
from controller.traffic_state import TrafficStateAggregator
from controller.signal_optimizer import SignalOptimizer

class AdaptiveTrafficController:
    """
    Real-time Traffic-Pressure-Based Adaptive Signal Controller with Emergency Priority Overrides for LHT networks.
    """
    def __init__(self):
        self.aggregator = TrafficStateAggregator()
        self.optimizer = SignalOptimizer()

        # Controller state tracking per intersection
        self.tls_states = {}
        # Active emergency priority tracking per intersection
        self.active_emergency = {}

        for tls_id in INTERSECTION_MAP.keys():
            self.tls_states[tls_id] = {
                "current_phase": 0,
                "phase_start_time": 0.0,
                "in_yellow": False,
                "yellow_target_phase": 0,
                "last_green": {
                    "NORTH_SOUTH": 0.0,
                    "EAST_WEST": 0.0
                }
            }
            self.active_emergency[tls_id] = None

    def check_emergency_override(self, tls_id: str, state: dict) -> dict:
        """
        Detects emergency vehicles on incoming approach edges, triggers priority activation,
        and logs EMERGENCY DETECTED and EMERGENCY CLEARED events.
        """
        em_vehs = state.get("emergency_vehicles", [])
        incoming_edges = INTERSECTION_MAP.get(tls_id, {})
        
        current_em_at_tls = None

        for em in em_vehs:
            edge = em.get("edge_id")
            dist = em.get("distance_to_tls")
            v_id = em.get("vehicle_id")
            v_type = em.get("type", "emergency")
            
            for direction, mapped_edge in incoming_edges.items():
                if edge == mapped_edge and (dist is None or dist <= EMERGENCY_TRIGGER_DIST):
                    movement = "NORTH_SOUTH" if direction in ["north", "south"] else "EAST_WEST"
                    current_em_at_tls = {
                        "v_id": v_id,
                        "v_type": v_type,
                        "edge": edge,
                        "direction": direction,
                        "movement": movement
                    }
                    break
            if current_em_at_tls:
                break

        prev_em = self.active_emergency[tls_id]

        # Log EMERGENCY CLEARED if vehicle left the intersection approach
        if prev_em and (not current_em_at_tls or current_em_at_tls["v_id"] != prev_em["v_id"]):
            print(f"\n[EMERGENCY CLEARED]")
            print(f"   Vehicle: {prev_em['v_id']}")
            print(f"   Intersection: {tls_id}")
            print(f"   ACTION: Adaptive control resumed\n")
            self.active_emergency[tls_id] = None

        # Log EMERGENCY DETECTED if new emergency priority activated
        if current_em_at_tls and (not prev_em or prev_em["v_id"] != current_em_at_tls["v_id"]):
            print(f"\n[EMERGENCY DETECTED]")
            print(f"   Vehicle: {current_em_at_tls['v_id']} ({current_em_at_tls['v_type']})")
            print(f"   Intersection: {tls_id}")
            print(f"   Incoming edge: {current_em_at_tls['edge']} ({current_em_at_tls['direction']})")
            print(f"   Movement: {current_em_at_tls['movement']}")
            print(f"   ACTION: Emergency priority activated\n")
            self.active_emergency[tls_id] = current_em_at_tls

        if current_em_at_tls:
            movement = current_em_at_tls["movement"]
            target_phase = PHASE_MAP[tls_id][movement]
            yellow_phase = PHASE_MAP[tls_id][f"YELLOW_{'EW' if movement == 'EAST_WEST' else 'NS'}"]
            
            return {
                "intersection": tls_id,
                "selected_movement": movement,
                "phase": f"EMERGENCY_{movement}_GREEN",
                "target_phase_index": target_phase,
                "yellow_phase_index": yellow_phase,
                "green_duration": 30,
                "ns_pressure": 0.0,
                "ew_pressure": 0.0,
                "reason": f"Emergency Priority Override for {current_em_at_tls['v_id']} on {current_em_at_tls['direction']} approach ({current_em_at_tls['edge']})"
            }

        return None

    def get_signal_decision(self, intersection_id: str) -> dict:
        sim_time = traci.simulation.getTime()
        state = self.aggregator.get_traffic_state()
        intersection_data = state["intersections"].get(intersection_id, {})

        # Check Emergency Priority Override
        emergency_decision = self.check_emergency_override(intersection_id, state)
        if emergency_decision:
            return emergency_decision

        tls_state = self.tls_states[intersection_id]
        last_green = tls_state["last_green"]

        decision = self.optimizer.optimize_signal(intersection_id, intersection_data, last_green, sim_time)
        return decision

    def apply_signal_decision(self, decision: dict):
        tls_id = decision["intersection"]
        target_phase = decision["target_phase_index"]
        yellow_phase = decision["yellow_phase_index"]
        green_duration = decision["green_duration"]
        movement = decision["selected_movement"]

        sim_time = traci.simulation.getTime()
        tls_state = self.tls_states[tls_id]

        current_phase = tls_state["current_phase"]
        phase_start = tls_state["phase_start_time"]
        in_yellow = tls_state["in_yellow"]
        elapsed = sim_time - phase_start

        if in_yellow:
            if elapsed >= YELLOW_TIME:
                traci.trafficlight.setPhase(tls_id, target_phase)
                traci.trafficlight.setPhaseDuration(tls_id, green_duration)
                
                tls_state["current_phase"] = target_phase
                tls_state["phase_start_time"] = sim_time
                tls_state["in_yellow"] = False
                tls_state["last_green"][movement] = sim_time
            return

        if current_phase == target_phase:
            traci.trafficlight.setPhaseDuration(tls_id, max(1.0, green_duration - elapsed))
            tls_state["last_green"][movement] = sim_time
            return

        if elapsed >= MIN_GREEN_TIME:
            traci.trafficlight.setPhase(tls_id, yellow_phase)
            traci.trafficlight.setPhaseDuration(tls_id, YELLOW_TIME)

            tls_state["current_phase"] = yellow_phase
            tls_state["phase_start_time"] = sim_time
            tls_state["in_yellow"] = True
            tls_state["yellow_target_phase"] = target_phase
        else:
            traci.trafficlight.setPhaseDuration(tls_id, max(1.0, MIN_GREEN_TIME - elapsed))
