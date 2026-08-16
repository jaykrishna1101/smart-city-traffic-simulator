from controller.config import PEAK_PERIOD_BOUNDARIES

class PeakHourDetector:
    """
    Detects current logical traffic scenario period based on compressed simulation clock.
    """
    def __init__(self):
        self.boundaries = PEAK_PERIOD_BOUNDARIES

    def get_period(self, sim_time: float) -> str:
        if sim_time < self.boundaries["MORNING_PEAK"][1]:
            return "MORNING_PEAK"
        elif sim_time < self.boundaries["NORMAL"][1]:
            return "NORMAL"
        else:
            return "EVENING_PEAK"

    def get_period_info(self, sim_time: float) -> dict:
        period = self.get_period(sim_time)
        logical_time_map = {
            "MORNING_PEAK": "09:00 - 12:00",
            "NORMAL": "12:00 - 16:00",
            "EVENING_PEAK": "16:00 - 19:00"
        }
        return {
            "period": period,
            "logical_clock": logical_time_map.get(period, "N/A"),
            "sim_time": round(sim_time, 1)
        }
