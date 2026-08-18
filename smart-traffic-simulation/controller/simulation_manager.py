import os
import sys
import time

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.config import SUMO_CONFIG_PATH
from controller.traffic_state import TrafficStateAggregator

class SimulationManager:
    """
    Manages TraCI connection lifecycle, step execution, and graceful termination.
    Supports regular 2D view and OpenSceneGraph (OSG) 3D view in sumo-gui.
    """
    def __init__(self, config_path: str = SUMO_CONFIG_PATH, gui: bool = False, use_3d: bool = False):
        self.config_path = config_path
        self.gui = gui
        self.use_3d = use_3d
        self.is_running = False
        self.aggregator = TrafficStateAggregator()

    def start(self, retries: int = 3):
        """
        Starts the SUMO process and connects via TraCI with retry handling.
        """
        sumo_home = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
        binary_name = "sumo-gui.exe" if self.gui else "sumo.exe"
        sumo_binary = os.path.join(sumo_home, "bin", binary_name)

        if not os.path.exists(sumo_binary):
            sumo_binary = "sumo-gui" if self.gui else "sumo"

        cmd = [sumo_binary, "-c", self.config_path, "--no-warnings", "true"]
        if self.gui:
            # Fix window position and size so sumo_window_vnc.py can reliably locate the HWND.
            # Place at top-left (0,0) with a consistent resolution. User can move it later;
            # the VNC server tracks position changes dynamically via GetWindowRect.
            cmd += ["--window-pos", "0,0", "--window-size", "1280,720"]
        if self.gui and self.use_3d:
            cmd.append("--osg-view")

        print(f"Connecting TraCI to SUMO binary: {sumo_binary}")
        print(f"Loading config: {self.config_path}")
        if self.gui and self.use_3d:
            print("Enabling 3D OpenSceneGraph (OSG) Viewport")

        attempt = 0
        while attempt < retries:
            try:
                traci.start(cmd)
                self.is_running = True
                print("TraCI successfully connected to SUMO process.")
                return True
            except Exception as e:
                attempt += 1
                print(f"TraCI connection attempt {attempt}/{retries} failed: {e}")
                time.sleep(1.0)

        raise RuntimeError("Failed to establish TraCI connection after multiple attempts.")

    def step(self) -> float:
        """
        Advances the simulation by one step and returns current simulation time.
        """
        if not self.is_running:
            raise RuntimeError("Simulation is not running. Call start() first.")
        
        traci.simulationStep()
        return traci.simulation.getTime()

    def get_traffic_state(self) -> dict:
        """
        Helper method to retrieve structured traffic state snapshot.
        """
        return self.aggregator.get_traffic_state()

    def export_telemetry(self, state: dict):
        """
        Exports state snapshot to CSV and JSON.
        """
        self.aggregator.export_csv(state)
        self.aggregator.export_json(state)

    def is_active(self) -> bool:
        """
        Checks if vehicles remain expected in simulation.
        """
        if not self.is_running:
            return False
        try:
            return traci.simulation.getMinExpectedNumber() > 0
        except traci.TraCIException:
            return False

    def close(self):
        """
        Gracefully terminates the TraCI connection and shuts down SUMO.
        """
        if self.is_running:
            try:
                traci.close()
                print("TraCI connection gracefully closed.")
            except Exception as e:
                print(f"Warning during TraCI shutdown: {e}")
            finally:
                self.is_running = False
