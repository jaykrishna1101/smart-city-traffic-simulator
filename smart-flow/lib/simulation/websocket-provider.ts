import type { ConnectionStatus, SimulationProvider, SimulationSnapshot } from "./types"
import { createEmptySnapshot, normalizeSimulationData } from "./normalize"

export class WebSocketSimulationProvider implements SimulationProvider {
  private candidateUrls: string[] = []
  private currentUrlIndex = 0
  private socket: WebSocket | null = null
  private listeners = new Set<(snapshot: SimulationSnapshot) => void>()
  private snapshot: SimulationSnapshot
  private reconnectTimer?: ReturnType<typeof setTimeout>
  private reconnectAttempts = 0
  private maxReconnectDelay = 5000
  private baseReconnectDelay = 1000
  private isExplicitlyClosed = false

  constructor(url?: string) {
    const envUrl = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_WS_URL : undefined
    if (url) {
      this.candidateUrls = [url]
    } else if (envUrl) {
      // If localhost was specified, provide 127.0.0.1 first as it avoids Windows IPv6 localhost resolution mismatch
      const altUrl = envUrl.includes("localhost")
        ? envUrl.replace("localhost", "127.0.0.1")
        : envUrl.includes("127.0.0.1")
        ? envUrl.replace("127.0.0.1", "localhost")
        : undefined

      this.candidateUrls = altUrl ? [envUrl, altUrl] : [envUrl]
    } else {
      this.candidateUrls = ["ws://127.0.0.1:8765/ws", "ws://localhost:8765/ws"]
    }

    this.snapshot = createEmptySnapshot("connecting")
    if (typeof window !== "undefined") {
      this.connect()
    }
  }

  private get currentUrl(): string {
    return this.candidateUrls[this.currentUrlIndex % this.candidateUrls.length]
  }

  private connect() {
    if (this.isExplicitlyClosed || typeof window === "undefined") return

    if (this.socket) {
      try {
        this.socket.onopen = null
        this.socket.onmessage = null
        this.socket.onerror = null
        this.socket.onclose = null
        this.socket.close()
      } catch {
        // ignore
      }
      this.socket = null
    }

    const status: ConnectionStatus = this.reconnectAttempts > 0 ? "reconnecting" : "connecting"
    this.updateStatus(status)

    const targetUrl = this.currentUrl
    try {
      console.log(`[SmartFlow WS] Connecting to ${targetUrl}...`)
      this.socket = new WebSocket(targetUrl)

      this.socket.onopen = () => {
        console.log(`[SmartFlow WS] Successfully connected to ${targetUrl}`)
        this.reconnectAttempts = 0
        this.updateStatus("connected")
        this.send({ type: "ping" })
      }

      this.socket.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data)
          if (raw.type === "simulation_update" || raw.simulation || raw.intersections) {
            this.snapshot = normalizeSimulationData(raw, "connected")
            this.emit()
          }
        } catch (err) {
          console.warn("[SmartFlow WS] Error parsing message:", err)
        }
      }

      this.socket.onerror = () => {
        // Switch candidate on connection error
        this.currentUrlIndex++
      }

      this.socket.onclose = () => {
        if (!this.isExplicitlyClosed) {
          this.updateStatus("disconnected")
          this.scheduleReconnect()
        }
      }
    } catch (err) {
      console.warn("[SmartFlow WS] Connection error:", err)
      this.currentUrlIndex++
      this.updateStatus("disconnected")
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    const delay = Math.min(
      this.maxReconnectDelay,
      this.baseReconnectDelay * Math.pow(1.3, this.reconnectAttempts)
    )
    this.reconnectAttempts++

    this.reconnectTimer = setTimeout(() => {
      if (!this.isExplicitlyClosed) {
        this.connect()
      }
    }, delay)
  }

  private updateStatus(connectionStatus: ConnectionStatus) {
    this.snapshot = {
      ...this.snapshot,
      state: {
        ...this.snapshot.state,
        connectionStatus
      }
    }
    this.emit()
  }

  private send(msg: Record<string, any>) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(msg))
      } catch (err) {
        console.warn("[SmartFlow WS] Send error:", err)
      }
    }
  }

  async getSnapshot(): Promise<SimulationSnapshot> {
    return this.snapshot
  }

  subscribe(listener: (snapshot: SimulationSnapshot) => void): () => void {
    this.listeners.add(listener)
    listener(this.snapshot)

    if (!this.socket && typeof window !== "undefined") {
      this.connect()
    }

    return () => {
      this.listeners.delete(listener)
    }
  }

  pause() {
    this.snapshot = {
      ...this.snapshot,
      state: {
        ...this.snapshot.state,
        simulationStatus: "paused"
      }
    }
    this.send({ type: "command", command: "pause" })
    this.emit()
  }

  resume() {
    this.snapshot = {
      ...this.snapshot,
      state: {
        ...this.snapshot.state,
        simulationStatus: "running"
      }
    }
    this.send({ type: "command", command: "resume" })
    this.emit()
  }

  step() {
    this.send({ type: "command", command: "step" })
  }

  setSpeed(speedMultiplier: number) {
    // Map speed multiplier: 0.5x -> 0.08s delay, 1x -> 0.02s delay, 2x -> 0.0s delay
    const delay = speedMultiplier >= 2 ? 0.0 : speedMultiplier <= 0.5 ? 0.08 : 0.02
    this.setDelay(delay)
  }

  setDelay(delaySec: number) {
    this.send({ type: "command", command: "set_delay", params: { delay: delaySec } })
  }

  trackVehicle(vehicleId: string) {
    this.send({ type: "command", command: "track_vehicle", params: { vehicle_id: vehicleId } })
  }

  setZoom(zoomLevel: number) {
    this.send({ type: "command", command: "set_zoom", params: { zoom: zoomLevel } })
  }

  centerIntersection(intersectionId: string) {
    this.send({ type: "command", command: "center_intersection", params: { intersection_id: intersectionId } })
  }

  sendCommand(command: string, params?: Record<string, any>) {
    this.send({ type: "command", command, params: params || {} })
  }

  disconnect() {
    this.isExplicitlyClosed = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    if (this.socket) {
      try {
        this.socket.close()
      } catch {
        // ignore
      }
      this.socket = null
    }
    this.updateStatus("disconnected")
  }

  private emit() {
    this.listeners.forEach((listener) => {
      try {
        listener(this.snapshot)
      } catch (err) {
        console.error("[SmartFlow WS] Listener error:", err)
      }
    })
  }
}

