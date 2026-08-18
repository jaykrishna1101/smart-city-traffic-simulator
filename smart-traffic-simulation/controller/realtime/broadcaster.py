import os
from typing import Optional

from controller.realtime.server import RealtimeServer
from controller.realtime.serializer import serialize_simulation_state

class RealtimeBroadcaster:
    """
    High-level facade connecting the SUMO simulation cycle with the WebSocket server.
    """
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, enabled: bool = True):
        self.enabled = enabled
        self.host = host or os.environ.get("SMARTFLOW_WS_HOST", os.environ.get("WS_HOST", "0.0.0.0"))
        default_port = int(os.environ.get("SMARTFLOW_WS_PORT", os.environ.get("WS_PORT", "8765")))
        self.port = port if port is not None else default_port
        self.server = RealtimeServer(host=self.host, port=self.port) if self.enabled else None

    def start(self):
        """Starts the WebSocket broadcaster."""
        if self.enabled and self.server:
            self.server.start()

    def get_pending_commands(self) -> list:
        """Retrieves any pending commands received from WebSocket clients."""
        if self.enabled and self.server:
            return self.server.get_pending_commands()
        return []


    def broadcast_state(
        self,
        sim_time: float,
        state: dict,
        decisions: dict = None,
        tracker = None,
        mode: str = "ADAPTIVE",
        status: str = "running"
    ):
        """Serializes and broadcasts the current simulation step state."""
        if not self.enabled or not self.server:
            return

        try:
            payload = serialize_simulation_state(
                sim_time=sim_time,
                state=state,
                decisions=decisions,
                tracker=tracker,
                mode=mode,
                status=status
            )
            self.server.broadcast(payload)
        except Exception as e:
            # Never crash the SUMO simulation loop due to broadcasting errors
            print(f"[SmartFlow WebSocket] Error in broadcast_state: {e}")

    def stop(self):
        """Stops the WebSocket broadcaster and closes connections."""
        if self.enabled and self.server:
            self.server.stop()
