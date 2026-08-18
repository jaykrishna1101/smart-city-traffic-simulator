import asyncio
import threading
import json
import queue
import logging
from typing import Set, Optional, List, Dict, Any

import websockets

logger = logging.getLogger("smartflow.realtime")

class RealtimeServer:
    """
    Lightweight, non-blocking WebSocket server running on a dedicated background thread.
    Broadcasts simulation telemetry to connected SmartFlow browser clients and receives commands.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.ServerConnection] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.server = None
        self.latest_payload_json: Optional[str] = None
        self.command_queue: queue.Queue = queue.Queue()
        self._running = False
        self._ready_event = threading.Event()
        self._stop_event: Optional[asyncio.Event] = None

    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Retrieves and clears all pending commands received from WebSocket clients."""
        commands = []
        while not self.command_queue.empty():
            try:
                commands.append(self.command_queue.get_nowait())
            except queue.Empty:
                break
        return commands

    def start(self):
        """Starts the WebSocket server in a background daemon thread."""
        if self._running:
            return

        self._running = True
        self._ready_event.clear()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True, name="SmartFlow-WebSocket-Server")
        self.thread.start()

        # Wait up to 3 seconds for server to bind
        self._ready_event.wait(timeout=3.0)
        print(f"[SmartFlow WebSocket] Server running at ws://{self.host}:{self.port}/ws")

    def _run_event_loop(self):
        """Event loop target for background thread."""
        import sys
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def main():
            try:
                self._stop_event = asyncio.Event()
                # websockets.serve works as an async context manager
                async with websockets.serve(self._handle_client, self.host, self.port) as server:
                    self.server = server
                    self._ready_event.set()
                    await self._stop_event.wait()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[SmartFlow WebSocket] Server error: {e}")
            finally:
                self._ready_event.set()

        try:
            self.loop.run_until_complete(main())
        except Exception as e:
            logger.debug(f"Event loop terminated: {e}")
        finally:
            try:
                # Cancel any remaining pending tasks
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self.loop.close()

    async def _handle_client(self, websocket):
        """Manages individual client connection lifecycle."""
        client_addr = getattr(websocket, "remote_address", "unknown")
        self.clients.add(websocket)
        logger.info(f"[SmartFlow WebSocket] Client connected: {client_addr} (total: {len(self.clients)})")

        # Immediately send the latest available state snapshot upon connection
        if self.latest_payload_json:
            try:
                await websocket.send(self.latest_payload_json)
            except Exception:
                pass

        try:
            async for raw_msg in websocket:
                try:
                    msg = json.loads(raw_msg)
                    msg_type = msg.get("type")
                    if msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif msg_type == "command" or "command" in msg:
                        logger.info(f"[SmartFlow WebSocket] Command received: {msg}")
                        self.command_queue.put(msg)
                except Exception as parse_err:
                    logger.debug(f"[SmartFlow WebSocket] Parse error for message from {client_addr}: {parse_err}")
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.debug(f"[SmartFlow WebSocket] Client error ({client_addr}): {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"[SmartFlow WebSocket] Client disconnected: {client_addr} (remaining: {len(self.clients)})")


    def broadcast(self, payload_dict: dict):
        """
        Thread-safe method to schedule broadcasting of a simulation payload to all connected clients.
        Will NOT block the calling SUMO simulation thread.
        """
        if not self._running or self.loop is None or not self.loop.is_running():
            return

        try:
            payload_json = json.dumps(payload_dict)
            self.latest_payload_json = payload_json
        except Exception as e:
            logger.error(f"[SmartFlow WebSocket] Serialization error in broadcast: {e}")
            return

        if not self.clients:
            return

        asyncio.run_coroutine_threadsafe(self._async_broadcast(payload_json), self.loop)

    async def _async_broadcast(self, payload_json: str):
        """Asynchronously dispatches the JSON payload to all connected WebSocket clients."""
        if not self.clients:
            return

        # Snapshot current clients to avoid concurrent modification issues
        active_clients = list(self.clients)
        if not active_clients:
            return

        # Send to all clients concurrently, catching disconnect exceptions
        results = await asyncio.gather(
            *[client.send(payload_json) for client in active_clients],
            return_exceptions=True
        )

        for client, result in zip(active_clients, results):
            if isinstance(result, Exception):
                self.clients.discard(client)

    def stop(self):
        """Gracefully terminates the WebSocket server and background thread."""
        if not self._running:
            return

        self._running = False
        if self.loop and self.loop.is_running() and self._stop_event is not None:
            self.loop.call_soon_threadsafe(self._stop_event.set)

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

        print("[SmartFlow WebSocket] Server stopped.")

