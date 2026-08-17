from controller.config import VEHICLE_WEIGHT, QUEUE_WEIGHT, WAITING_WEIGHT
from controller.network_topology import get_signal_phases, get_controlled_links

class TrafficPressureCalculator:
    """
    Calculates traffic pressure scores for individual approaches, incoming edges,
    and dynamic signal phases based on network topology.
    """
    def __init__(self, veh_w=VEHICLE_WEIGHT, queue_w=QUEUE_WEIGHT, wait_w=WAITING_WEIGHT):
        self.veh_w = veh_w
        self.queue_w = queue_w
        self.wait_w = wait_w

    def calculate_approach_pressure(self, approach_data: dict) -> float:
        """
        Formula:
        pressure = (vehicle_weight * vehicles) + (queue_weight * queue) + (waiting_weight * waiting_time)
        """
        if not approach_data:
            return 0.0

        vehs = approach_data.get("vehicles", 0)
        queue = approach_data.get("queue", 0)
        waiting_time = approach_data.get("waiting_time", 0.0)

        pressure = (self.veh_w * vehs) + (self.queue_w * queue) + (self.wait_w * waiting_time)
        return round(pressure, 2)

    def calculate_intersection_pressures(self, intersection_data: dict) -> dict:
        """
        Computes pressure scores across all incoming approach edges for an intersection.
        """
        approaches = intersection_data.get("approaches", {})
        edge_pressures = {}
        total_pressure = 0.0

        for edge_id, app_data in approaches.items():
            press = self.calculate_approach_pressure(app_data)
            edge_pressures[edge_id] = press
            total_pressure += press

        edge_pressures["total_pressure"] = round(total_pressure, 2)
        return edge_pressures

    def calculate_phase_pressures(self, tls_id: str, intersection_data: dict) -> dict:
        """
        Dynamically computes phase-level pressure scores by mapping green links in each phase
        to their incoming approach edges via network_topology.
        """
        phase_pressures = {}
        phases = get_signal_phases(tls_id)
        links = get_controlled_links(tls_id)

        if not phases:
            return {0: 0.0}

        approaches = intersection_data.get("approaches", {})

        for p_idx, phase in enumerate(phases):
            state_str = phase.state
            # Check if this is a green phase (contains 'G' or 'g')
            if 'G' not in state_str and 'g' not in state_str:
                continue  # Skip yellow or red-only phases

            green_edges = set()
            for l_idx, char in enumerate(state_str):
                if char in ['G', 'g'] and l_idx < len(links):
                    link_info = links[l_idx]
                    if link_info:
                        from_lane = link_info[0]
                        from_edge = from_lane.rpartition('_')[0]
                        if from_edge:
                            green_edges.add(from_edge)

            phase_press = 0.0
            for edge_id in green_edges:
                app_data = approaches.get(edge_id, {})
                phase_press += self.calculate_approach_pressure(app_data)

            phase_pressures[p_idx] = round(phase_press, 2)

        if not phase_pressures:
            phase_pressures[0] = 0.0

        return phase_pressures
