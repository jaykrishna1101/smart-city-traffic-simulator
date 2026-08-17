import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import EMERGENCY_TRIGGER_DIST
from controller.network_topology import get_signal_phases, get_controlled_links

class EmergencySystem:
    """
    Emergency Vehicle Priority System for the Chatrapati–Ring Road SUMO network (Indian LHT).
    Dynamically detects emergency vehicles (Ambulance, Police, Fire Truck), determines topology-based
    movement phases, safely activates priority green overrides, and restores adaptive control.
    """
    def __init__(self):
        self.active_priority = {}       # tls_id -> dict of active emergency info
        self.spawned_emergencies = set() # set of spawned test vehicle IDs
        self.tracked_vehicle = None      # vehicle ID currently tracked by GUI camera

    def update_camera_tracking(self, gui: bool = True):
        """
        When running in emergency demonstration mode with GUI active,
        automatically tracks active emergency vehicles in street-level view.
        Restores normal full-network view when vehicle clears.
        """
        if not gui:
            return
        try:
            views = traci.gui.getIDList()
            if not views:
                return
            view_id = views[0]
            
            active_emergencies = self.detect_emergency_vehicles()
            if active_emergencies:
                target_vid = active_emergencies[0]["vehicle_id"]
                if self.tracked_vehicle != target_vid:
                    traci.gui.trackVehicle(view_id, target_vid)
                    traci.gui.setZoom(view_id, 450.0)
                    self.tracked_vehicle = target_vid
            else:
                if self.tracked_vehicle is not None:
                    traci.gui.trackVehicle(view_id, "")
                    traci.gui.setZoom(view_id, 120.0)
                    self.tracked_vehicle = None
        except Exception:
            pass

    def detect_emergency_vehicles(self) -> list:
        """
        Dynamically detects all active emergency vehicles in the SUMO network.
        """
        emergency_list = []
        try:
            vehicle_ids = traci.vehicle.getIDList()
        except traci.TraCIException:
            return emergency_list

        for v_id in vehicle_ids:
            try:
                v_class = traci.vehicle.getVehicleClass(v_id)
                v_id_upper = v_id.upper()

                is_emergency = (
                    "AMBULANCE" in v_id_upper or 
                    "FIRE" in v_id_upper or 
                    "POLICE" in v_id_upper or 
                    v_class in ["emergency", "authority"]
                )

                if is_emergency:
                    v_type = "ambulance"
                    if "FIRE" in v_id_upper or v_class == "emergency":
                        v_type = "fire_truck" if "FIRE" in v_id_upper else "ambulance"
                    if "POLICE" in v_id_upper or v_class == "authority":
                        v_type = "police"

                    edge_id = traci.vehicle.getRoadID(v_id)
                    lane_id = traci.vehicle.getLaneID(v_id)
                    speed_ms = traci.vehicle.getSpeed(v_id)
                    speed_kmh = round(speed_ms * 3.6, 2)
                    lane_pos = round(traci.vehicle.getLanePosition(v_id), 2)

                    next_tls_id, dist_to_tls, approach_lane, tls_state = self.get_next_controlled_intersection(v_id)

                    emergency_list.append({
                        "vehicle_id": v_id,
                        "type": v_type,
                        "edge_id": edge_id,
                        "lane_id": lane_id,
                        "speed_m_s": round(speed_ms, 2),
                        "speed_kmh": speed_kmh,
                        "position": lane_pos,
                        "next_tls": next_tls_id,
                        "distance_to_tls": dist_to_tls,
                        "approach_lane": approach_lane
                    })
            except traci.TraCIException:
                continue

        return emergency_list

    def get_emergency_vehicles(self) -> list:
        """Alias method for backward compatibility."""
        return self.detect_emergency_vehicles()

    def get_emergency_route_state(self, vehicle_id: str) -> dict:
        """
        Returns edge, lane, speed, position, and remaining route details for an emergency vehicle.
        """
        try:
            edge_id = traci.vehicle.getRoadID(vehicle_id)
            lane_id = traci.vehicle.getLaneID(vehicle_id)
            speed_ms = traci.vehicle.getSpeed(vehicle_id)
            speed_kmh = round(speed_ms * 3.6, 2)
            lane_pos = round(traci.vehicle.getLanePosition(vehicle_id), 2)
            route = traci.vehicle.getRoute(vehicle_id)
            route_idx = traci.vehicle.getRouteIndex(vehicle_id)
            remaining_route = route[route_idx:] if route_idx >= 0 and route_idx < len(route) else route

            v_class = traci.vehicle.getVehicleClass(vehicle_id)
            v_upper = vehicle_id.upper()
            v_type = "ambulance"
            if "FIRE" in v_upper:
                v_type = "fire_truck"
            elif "POLICE" in v_upper:
                v_type = "police"

            return {
                "vehicle_id": vehicle_id,
                "type": v_type,
                "edge_id": edge_id,
                "lane_id": lane_id,
                "speed_m_s": round(speed_ms, 2),
                "speed_kmh": speed_kmh,
                "position": lane_pos,
                "remaining_route": remaining_route
            }
        except traci.TraCIException:
            return {}

    def get_next_controlled_intersection(self, vehicle_id: str) -> tuple:
        """
        Queries TraCI to find the next downstream traffic-light-controlled intersection.
        Returns: (tls_id, distance_to_tls, approach_lane, tls_state)
        """
        try:
            next_tls_info = traci.vehicle.getNextTLS(vehicle_id)
            if next_tls_info and len(next_tls_info) > 0:
                tls_id, tls_idx, dist, state_char = next_tls_info[0]
                lane_id = traci.vehicle.getLaneID(vehicle_id)
                return (tls_id, round(dist, 2), lane_id, state_char)
        except traci.TraCIException:
            pass
        return (None, None, None, None)

    def get_emergency_phase(self, tls_id: str, vehicle_id: str) -> tuple:
        """
        Determines the exact compatible signal phase permitting the emergency vehicle's movement
        based on SUMO network topology.
        Returns: (target_phase_index, yellow_phase_index, movement_description)
        """
        try:
            edge_id = traci.vehicle.getRoadID(vehicle_id)
            route = traci.vehicle.getRoute(vehicle_id)
            route_idx = traci.vehicle.getRouteIndex(vehicle_id)
            next_edge = route[route_idx + 1] if (route_idx >= 0 and route_idx + 1 < len(route)) else None
        except traci.TraCIException:
            edge_id = ""
            next_edge = None

        phases = get_signal_phases(tls_id)
        links = get_controlled_links(tls_id)

        if not phases:
            return (0, 0, "Default phase")

        # 1. Look for green phase that connects vehicle's current edge to next_edge
        for p_idx, phase in enumerate(phases):
            state_str = phase.state
            if 'G' not in state_str and 'g' not in state_str:
                continue

            for l_idx, char in enumerate(state_str):
                if char in ['G', 'g'] and l_idx < len(links):
                    from_l, to_l, _ = links[l_idx]
                    from_e = from_l.rpartition('_')[0]
                    to_e = to_l.rpartition('_')[0]

                    if from_e == edge_id:
                        if next_edge is None or to_e == next_edge:
                            yellow_idx = (p_idx + 1) % len(phases)
                            m_desc = f"Movement from {from_e} to {to_e}"
                            return (p_idx, yellow_idx, m_desc)

        # 2. Fallback: Find any green phase that permits traffic from vehicle's approach edge
        for p_idx, phase in enumerate(phases):
            state_str = phase.state
            if 'G' not in state_str and 'g' not in state_str:
                continue

            for l_idx, char in enumerate(state_str):
                if char in ['G', 'g'] and l_idx < len(links):
                    from_l, to_l, _ = links[l_idx]
                    from_e = from_l.rpartition('_')[0]
                    if from_e == edge_id:
                        yellow_idx = (p_idx + 1) % len(phases)
                        m_desc = f"Movement from approach edge {from_e}"
                        return (p_idx, yellow_idx, m_desc)

        # 3. Ultimate Fallback: Return phase 0
        yellow_idx = 1 if len(phases) > 1 else 0
        return (0, yellow_idx, "Approach priority phase 0")

    def process_emergency_overrides(self, state: dict) -> dict:
        """
        Evaluates emergency vehicle priorities across all traffic lights, logs formatted events,
        and returns active priority decisions.
        """
        emergency_vehs = self.detect_emergency_vehicles()
        decisions = {}

        current_active_tls = {}

        for em in emergency_vehs:
            tls_id = em["next_tls"]
            dist = em["distance_to_tls"]
            v_id = em["vehicle_id"]

            if tls_id and (dist is None or dist <= EMERGENCY_TRIGGER_DIST):
                current_active_tls[tls_id] = em

        # Check for cleared priority overrides
        cleared_tls = [t for t in self.active_priority.keys() if t not in current_active_tls]
        for tls_id in cleared_tls:
            prev_em = self.active_priority[tls_id]
            print("\nEMERGENCY CLEARED")
            print(f"Vehicle: {prev_em['v_id']}")
            print(f"TLS: {tls_id}")
            print("Action: ADAPTIVE CONTROL RESTORED\n")
            del self.active_priority[tls_id]

        # Check for newly activated priority overrides
        for tls_id, em in current_active_tls.items():
            v_id = em["vehicle_id"]
            prev_em = self.active_priority.get(tls_id)

            target_phase, yellow_phase, m_desc = self.get_emergency_phase(tls_id, v_id)

            if not prev_em or prev_em["v_id"] != v_id:
                print("\nEMERGENCY PRIORITY")
                print(f"Vehicle: {v_id}")
                print(f"TLS: {tls_id}")
                print(f"Incoming edge: {em['edge_id']}")
                print(f"Movement: {m_desc}")
                print(f"Selected phase: Phase {target_phase}")
                print("Action: PRIORITY ACTIVATED\n")
                self.active_priority[tls_id] = {
                    "v_id": v_id,
                    "target_phase": target_phase,
                    "yellow_phase": yellow_phase,
                    "movement": m_desc
                }

            decisions[tls_id] = {
                "intersection": tls_id,
                "selected_movement": f"EMERGENCY_PHASE_{target_phase}",
                "phase": "EMERGENCY_GREEN",
                "target_phase_index": target_phase,
                "yellow_phase_index": yellow_phase,
                "green_duration": 30,
                "reason": f"Emergency Priority Override for {v_id} ({em['type']}) on edge {em['edge_id']}"
            }

        return decisions

    def spawn_test_emergency_vehicles(self, sim_time: float):
        """
        Dynamically injects test emergency vehicles (ambulance, police, firetruck)
        into the Chatrapati–Ring Road network along 300m-1000m corridor routes crossing traffic lights.
        """
        t = int(sim_time)
        demo_configs = {
            "AMBULANCE_NAGPUR": {
                "route_id": "route_AMBULANCE_DEMO",
                "type": "ambulance",
                "color": (255, 0, 0, 255),
                "from_edge": "372646899#9",
                "to_edge": "-93620634#5",
                "depart": 50
            },
            "POLICE_NAGPUR": {
                "route_id": "route_POLICE_DEMO",
                "type": "police",
                "color": (0, 0, 255, 255),
                "from_edge": "93620634#5",
                "to_edge": "29104458#4",
                "depart": 150
            },
            "FIRETRUCK_NAGPUR": {
                "route_id": "route_FIRETRUCK_DEMO",
                "type": "fire_truck",
                "color": (255, 77, 0, 255),
                "from_edge": "29104185#2",
                "to_edge": "29104472#1",
                "depart": 250
            }
        }

        for v_id, cfg in demo_configs.items():
            if t == cfg["depart"] and v_id not in self.spawned_emergencies:
                self._inject_emergency_vehicle(
                    v_id=v_id,
                    v_type=cfg["type"],
                    from_edge=cfg["from_edge"],
                    to_edge=cfg["to_edge"],
                    color_rgba=cfg["color"],
                    custom_route_id=cfg["route_id"]
                )

    def _inject_emergency_vehicle(self, v_id: str, v_type: str, from_edge: str, to_edge: str, color_rgba: tuple, custom_route_id: str = None):
        try:
            route = traci.simulation.findRoute(from_edge, to_edge, vType=v_type)
            if route and route.edges:
                route_id = custom_route_id if custom_route_id else f"route_{v_id}"
                if route_id not in traci.route.getIDList():
                    traci.route.add(route_id, list(route.edges))
                try:
                    traci.vehicle.add(v_id, route_id, typeID=v_type)
                except traci.TraCIException:
                    traci.vehicle.add(v_id, route_id, typeID="veh_passenger")
                
                v_class = "authority" if v_type == "police" else "emergency"
                traci.vehicle.setVehicleClass(v_id, v_class)
                traci.vehicle.setColor(v_id, color_rgba)
                self.spawned_emergencies.add(v_id)

                expected_lifetime = max(20, int(round(route.length / 15.0)))
                next_tls, dist_tls, _, _ = self.get_next_controlled_intersection(v_id)
                tls_str = f"{next_tls} (distance: {dist_tls}m)" if next_tls else "En route to signal"

                print(f"\n[EMERGENCY DEMO]")
                print(f"Vehicle: {v_id}")
                print(f"Route length: {route.length:.1f} m")
                print(f"Route edges: {len(route.edges)}")
                print(f"Expected lifetime: ~{expected_lifetime} s")
                print(f"First TLS: {tls_str}\n")
        except Exception as e:
            try:
                vehs = traci.vehicle.getIDList()
                if vehs:
                    target_v = vehs[0]
                    v_class = "authority" if v_type == "police" else "emergency"
                    traci.vehicle.setVehicleClass(target_v, v_class)
                    traci.vehicle.setColor(target_v, color_rgba)
                    self.spawned_emergencies.add(v_id)
                    print(f"\n>>> [ASSIGNED TEST {v_type.upper()}] Converted vehicle {target_v} to {v_type} <<<\n")
            except Exception:
                pass

# Alias for backward compatibility
EmergencyDetector = EmergencySystem

# Standalone function exports
_emergency_sys = EmergencySystem()

def detect_emergency_vehicles() -> list:
    return _emergency_sys.detect_emergency_vehicles()

def get_emergency_route_state(vehicle_id: str) -> dict:
    return _emergency_sys.get_emergency_route_state(vehicle_id)

def get_next_controlled_intersection(vehicle_id: str) -> tuple:
    return _emergency_sys.get_next_controlled_intersection(vehicle_id)

def get_emergency_phase(tls_id: str, vehicle_id: str) -> tuple:
    return _emergency_sys.get_emergency_phase(tls_id, vehicle_id)

def activate_emergency_priority(tls_id: str, phase_index: int):
    pass

def restore_adaptive_control(tls_id: str):
    pass
