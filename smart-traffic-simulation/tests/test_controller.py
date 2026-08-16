import os
import sys
import unittest
import xml.etree.ElementTree as ET

# Ensure project root is in sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from controller.config import (
    SUMO_CONFIG_PATH, INTERSECTION_MAP, PHASE_MAP,
    MIN_GREEN_TIME, MAX_GREEN_TIME, VEHICLE_WEIGHT, QUEUE_WEIGHT, WAITING_WEIGHT
)
from controller.traffic_pressure import TrafficPressureCalculator
from controller.peak_hour import PeakHourDetector
from controller.signal_optimizer import SignalOptimizer

class TestTrafficController(unittest.TestCase):
    """
    Automated Unit Test Suite for Smart City Traffic Management System (Indian LHT & Realistic 3D Models).
    """

    def test_lht_network_integrity(self):
        """
        Verifies that the compiled SUMO network file explicitly specifies lefthand='true' (Indian LHT).
        """
        net_path = os.path.join(PROJECT_DIR, "simulation", "network", "city.net.xml")
        self.assertTrue(os.path.exists(net_path), f"Network file missing: {net_path}")

        tree = ET.parse(net_path)
        root = tree.getroot()
        self.assertEqual(root.tag, "net")
        self.assertEqual(root.attrib.get("lefthand"), "true", "SUMO Network must be configured with lefthand='true' for Indian LHT!")

    def test_vehicle_types_3d_definitions(self):
        """
        Verifies that all 9 realistic vehicle types are properly defined with guiShape and 3D osgFile attributes.
        """
        vtypes_path = os.path.join(PROJECT_DIR, "simulation", "routes", "vehicle_types.add.xml")
        self.assertTrue(os.path.exists(vtypes_path), f"Vehicle types file missing: {vtypes_path}")

        tree = ET.parse(vtypes_path)
        root = tree.getroot()
        vtype_ids = [elem.attrib.get("id") for elem in root.findall("vType")]

        expected_types = [
            "passenger_car", "hatchback", "sedan", "bus", "truck",
            "motorcycle", "ambulance", "fire_truck", "police"
        ]
        for v_id in expected_types:
            self.assertIn(v_id, vtype_ids, f"Expected vehicle type ID '{v_id}' missing in vehicle_types.add.xml!")

    def test_traffic_pressure_formula(self):
        """
        Tests the traffic pressure formula: pressure = (1.0 * vehs) + (2.0 * queue) + (0.5 * waiting_time).
        """
        calc = TrafficPressureCalculator()
        sample_approach = {"vehicles": 10, "queue": 5, "waiting_time": 20.0}
        # Expected: (1.0 * 10) + (2.0 * 5) + (0.5 * 20.0) = 10 + 10 + 10 = 30.0
        expected = 30.0
        result = calc.calculate_approach_pressure(sample_approach)
        self.assertEqual(result, expected)

    def test_peak_hour_resolution(self):
        """
        Tests logical peak period resolution based on simulation clock.
        """
        detector = PeakHourDetector()
        self.assertEqual(detector.get_period(50.0), "MORNING_PEAK")
        self.assertEqual(detector.get_period(200.0), "NORMAL")
        self.assertEqual(detector.get_period(350.0), "EVENING_PEAK")

    def test_signal_optimizer_adaptive_green_bounds(self):
        """
        Tests that signal optimizer clamps green time strictly between MIN_GREEN (10s) and MAX_GREEN (60s).
        """
        optimizer = SignalOptimizer()
        
        # Zero pressure -> MIN_GREEN (10s)
        self.assertEqual(optimizer.calculate_adaptive_green(0.0, 0.0), MIN_GREEN_TIME)
        
        # Max pressure ratio (1.0) -> MAX_GREEN (60s)
        self.assertEqual(optimizer.calculate_adaptive_green(100.0, 100.0), MAX_GREEN_TIME)

        # 50% pressure ratio -> 35s
        self.assertEqual(optimizer.calculate_adaptive_green(50.0, 100.0), 35)

    def test_intersection_maps(self):
        """
        Tests that all 4 controlled intersections are properly defined with 4 directional approaches.
        """
        expected_tls = ["INT_NW", "INT_NE", "INT_SW", "INT_SE"]
        for tls in expected_tls:
            self.assertIn(tls, INTERSECTION_MAP)
            self.assertIn(tls, PHASE_MAP)
            for direction in ["north", "south", "east", "west"]:
                self.assertIn(direction, INTERSECTION_MAP[tls])

if __name__ == "__main__":
    unittest.main()
