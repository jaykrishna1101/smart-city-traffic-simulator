# SmartFlow Official noVNC Client Integration Walkthrough

## Summary of Integration

The official **noVNC browser client (`@novnc/novnc` v1.7.0)** has been installed as a frontend project dependency and directly embedded inside [`components/smartflow/vnc-viewport.tsx`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-flow/components/smartflow/vnc-viewport.tsx). 

The client connects over pure WebSockets (`ws://localhost:6080` or `NEXT_PUBLIC_VNC_WS_URL`) to `websockify`, which forwards RFB packets to the local **TightVNC Server** on `127.0.0.1:5900`, rendering the live Windows desktop with the native SUMO-GUI window directly inside SmartFlow.

---

## 1. Flow Architecture

```
Browser (SmartFlow `/simulation`)
  ↓
noVNC Core RFB Engine (`@novnc/novnc`)
  ↓
WebSocket `ws://localhost:6080`
  ↓
websockify (`python -m websockify 6080 127.0.0.1:5900`)
  ↓
TightVNC Server (`127.0.0.1:5900`)
  ↓
Windows Desktop Session
  ↓
Native SUMO-GUI Process (sumo-gui.exe)
```

---

## 2. Package & Files Created / Modified

### Package Added
- **Frontend**: `@novnc/novnc@1.7.0` added to `smart-flow/package.json`.

### Files Modified / Created
- **[MODIFY]** [`smart-flow/components/smartflow/vnc-viewport.tsx`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-flow/components/smartflow/vnc-viewport.tsx):
  - Integrates `RFB` from `@novnc/novnc` with `scaleViewport = true`, `focusOnClick = true`, `qualityLevel = 8`, `compressionLevel = 2`.
  - Implements connection state lifecycle (`CONNECTING`, `CONNECTED`, `DISCONNECTED`, `RECONNECTING`).
  - Full mouse and keyboard interaction passed directly to the VNC session.
  - Dynamic fullscreen toggle, stream reconnect button, and clean listener/session teardown on unmount.
  - Polished fallback standby state with endpoint diagnostic summary if VNC is disconnected.
- **[MODIFY]** [`smart-flow/.env.local`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-flow/.env.local) & [`smart-flow/.env.local.example`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-flow/.env.local.example):
  - Added `NEXT_PUBLIC_VNC_WS_URL=ws://localhost:6080`.
- **[MODIFY]** [`smart-traffic-simulation/scripts/start_vnc_bridge.py`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-traffic-simulation/scripts/start_vnc_bridge.py):
  - Configured pure RFB WebSocket proxying (`websockify 6080 127.0.0.1:5900`).

---

## 3. Environment Variables

```ini
# Simulation Provider Mode
NEXT_PUBLIC_SIMULATION_MODE=websocket

# TraCI WebSocket Server (Telemetry & Simulation Controls)
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8765/ws

# SUMO-GUI noVNC WebSocket Bridge (Visual RFB Stream)
NEXT_PUBLIC_VNC_WS_URL=ws://localhost:6080
```

---

## 4. How to Run

1. **Verify TightVNC Server is running on port 5900**:
   - `127.0.0.1:5900`
2. **Start websockify on port 6080**:
   ```powershell
   cd c:\Users\jkkho\OneDrive\Documents\traffic_simulation\smart-traffic-simulation
   python -m websockify 6080 127.0.0.1:5900
   ```
3. **Start the SUMO Simulation**:
   ```powershell
   python run.py --gui
   ```
4. **Open SmartFlow**:
   - Open **[http://localhost:3000/simulation](http://localhost:3000/simulation)**.
   - The embedded noVNC canvas will immediately connect to `ws://localhost:6080`, display the live SUMO-GUI window, and allow full mouse/keyboard control alongside SmartFlow's TraCI controls and real-time telemetry.

---

## 5. Verification Results

- `npm run build` in `smart-flow`: Static generation compiled successfully with 0 errors.
- Dynamic client-only import of `@novnc/novnc` prevents any SSR/hydration mismatch.
- WebSocket URL configurable dynamically via `NEXT_PUBLIC_VNC_WS_URL`.
