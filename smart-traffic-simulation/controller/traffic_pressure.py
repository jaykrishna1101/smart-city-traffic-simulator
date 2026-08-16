from controller.config import VEHICLE_WEIGHT, QUEUE_WEIGHT, WAITING_WEIGHT

class TrafficPressureCalculator:
    """
    Calculates traffic pressure scores for individual approaches and orthogonal movement groups (NS vs EW).
    """
    def __init__(self, veh_w=VEHICLE_WEIGHT, queue_w=QUEUE_WEIGHT, wait_w=WAITING_WEIGHT):
        self.veh_w = veh_w
        self.queue_w = queue_w
        self.wait_w = wait_w

    def calculate_approach_pressure(self, approach_data: dict) -> float:
        """
        Conceptual Formula:
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
        Computes pressures for all 4 cardinal directions and aggregates into NS vs EW movement group scores.
        """
        pressures = {}
        for direction in ["north", "south", "east", "west"]:
            app_data = intersection_data.get(direction, {})
            pressures[direction] = self.calculate_approach_pressure(app_data)

        ns_pressure = round(pressures["north"] + pressures["south"], 2)
        ew_pressure = round(pressures["east"] + pressures["west"], 2)

        pressures["NS_pressure"] = ns_pressure
        pressures["EW_pressure"] = ew_pressure

        return pressures
