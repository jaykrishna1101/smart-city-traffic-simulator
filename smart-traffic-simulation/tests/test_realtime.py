import os
import sys
import unittest
import json

# Ensure project root is in sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.realtime.serializer import serialize_simulation_state, format_clock, derive_signal_color
from controller.realtime.broadcaster import RealtimeBroadcaster

class TestRealtimeWebSocket(unittest.TestCase):
    """
    Unit tests for Realtime WebSocket serializer, payload contract, and broadcaster.
    """

    def test_format_clock(self):
        self.assertEqual(format_clock(0), "00:00:00")
        self.assertEqual(format_clock(125), "00:02:05")
        self.assertEqual(format_clock(3661), "01:01:01")

    def test_derive_signal_color(self):
        self.assertEqual(derive_signal_color("GGggGGGrrr"), "green")
        self.assertEqual(derive_signal_color("yyyy"), "yellow")
        self.assertEqual(derive_signal_color("rrrr"), "red")
        self.assertEqual(derive_signal_color(""), "green")

    def test_serialize_simulation_state_envelope(self):
        mock_state = {
            "scenario": "CHATRAPATI_RING_ROAD",
            "simulation_time": 75.0,
            "period": "MORNING_PEAK",
            "intersections": {
                "cluster_2683490405_298938456": {
                    "intersection_id": "cluster_2683490405_298938456",
                    "signal_phase": 0,
                    "phase_state": "GGggGGGrrr",
                    "phase_remaining": 16.0,
                    "controlled_lanes": ["lane_1", "lane_2"],
                    "controlled_edges": ["edge_1"],
                    "outgoing_edges": ["edge_out"],
                    "approaches": {
                        "edge_1": {
                            "vehicles": 12,
                            "queue": 4,
                            "waiting_time": 15.0,
                            "speed": 8.5,
                            "speed_kmh": 30.6,
                            "traffic_flow": 2,
                            "congestion": "MEDIUM"
                        }
                    },
                    "total_vehicles": 12,
                    "total_queue": 4,
                    "average_waiting_time": 15.0,
                    "average_speed": 8.5,
                    "average_speed_kmh": 30.6
                }
            },
            "emergency_vehicles": [
                {
                    "vehicle_id": "AMBULANCE_NAGPUR",
                    "type": "ambulance",
                    "edge_id": "edge_1",
                    "lane_id": "lane_1",
                    "speed_kmh": 45.0,
                    "next_tls": "cluster_2683490405_298938456",
                    "distance_to_tls": 120.0
                }
            ]
        }

        mock_decisions = {
            "cluster_2683490405_298938456": {
                "intersection": "cluster_2683490405_298938456",
                "selected_movement": "PHASE_0_GREEN",
                "phase": "PHASE_0_GREEN",
                "target_phase_index": 0,
                "yellow_phase_index": 1,
                "green_duration": 30,
                "reason": "Emergency Priority Override for AMBULANCE_NAGPUR"
            }
        }

        payload = serialize_simulation_state(
            sim_time=75.0,
            state=mock_state,
            decisions=mock_decisions,
            mode="ADAPTIVE",
            status="running"
        )

        # Validate envelope
        self.assertEqual(payload["type"], "simulation_update")
        self.assertEqual(payload["simulation"]["time"], 75.0)
        self.assertEqual(payload["simulation"]["clock"], "00:01:15")
        self.assertEqual(payload["simulation"]["period"], "MORNING_PEAK")
        self.assertEqual(payload["simulation"]["mode"], "ADAPTIVE")
        self.assertEqual(payload["simulation"]["status"], "running")

        # Validate intersection normalization
        self.assertEqual(len(payload["intersections"]), 1)
        tls = payload["intersections"][0]
        self.assertEqual(tls["id"], "cluster_2683490405_298938456")
        self.assertEqual(tls["status"], "emergency")
        self.assertEqual(len(tls["approaches"]), 1)

        # Validate emergency vehicles
        self.assertEqual(len(payload["emergencyVehicles"]), 1)
        em = payload["emergencyVehicles"][0]
        self.assertEqual(em["id"], "AMBULANCE_NAGPUR")
        self.assertEqual(em["type"], "ambulance")
        self.assertEqual(em["priorityStatus"], "active")

        # Ensure JSON serializable
        json_str = json.dumps(payload)
        self.assertTrue(len(json_str) > 100)

    def test_broadcaster_lifecycle(self):
        broadcaster = RealtimeBroadcaster(port=8775, enabled=True)
        broadcaster.start()
        self.assertTrue(broadcaster.server._running)
        broadcaster.stop()
        self.assertFalse(broadcaster.server._running)

if __name__ == "__main__":
    unittest.main()
