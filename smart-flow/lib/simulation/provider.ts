import type {
  AdaptiveControlData,
  ConnectionStatus,
  IntersectionData,
  SimulationProvider,
  SimulationSnapshot,
  TrafficPoint
} from "./types"
import { normalizeSimulationData } from "./normalize"
import { WebSocketSimulationProvider } from "./websocket-provider"

export type { SimulationProvider }
export { WebSocketSimulationProvider, normalizeSimulationData }

const intersectionSeed: IntersectionData[] = [
  {
    id: "cluster_2683490405_298938456",
    name: "Chatrapati Main Square",
    zone: "Central Ring Road",
    latitude: 21.1095,
    longitude: 79.0722,
    approaches: [
      { direction: "1212699691#3", vehicles: 42, queueLength: 18 },
      { direction: "372646899#19", vehicles: 31, queueLength: 13 },
      { direction: "304646594#1", vehicles: 18, queueLength: 8 }
    ],
    averageWaitingTime: 18,
    congestionLevel: 23,
    status: "normal"
  },
  {
    id: "joinedS_2705384848_3138462214",
    name: "Ring Road Junction",
    zone: "Southwest Corridor",
    latitude: 21.1120,
    longitude: 79.0810,
    approaches: [
      { direction: "304334916#4", vehicles: 52, queueLength: 27 },
      { direction: "262683844#4", vehicles: 43, queueLength: 22 },
      { direction: "27116790#3", vehicles: 28, queueLength: 14 }
    ],
    averageWaitingTime: 31,
    congestionLevel: 61,
    status: "congested"
  },
  {
    id: "cluster_2683490416_2683507646_2683507647_2684658305_#2more",
    name: "Wardha Road Interchange",
    zone: "South Nagpur",
    latitude: 21.0965,
    longitude: 79.0634,
    approaches: [
      { direction: "372646899#12", vehicles: 48, queueLength: 21 },
      { direction: "27117517#9", vehicles: 36, queueLength: 16 }
    ],
    averageWaitingTime: 26,
    congestionLevel: 48,
    status: "emergency"
  }
]

const traffic: TrafficPoint[] = [
  "12:00", "12:15", "12:30", "12:45", "13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30"
].map((time, index) => ({
  time,
  vehicles: 812 + index * 44 + (index > 6 ? 40 : 0),
  averageSpeed: 42 - index * 0.7,
  congestion: 17 + index * 2.2
}))

const phaseById: Record<string, { state: "green" | "yellow" | "red"; phase: string; seconds: number }> = {
  "cluster_2683490405_298938456": { state: "green", phase: "PHASE 0 (GREEN)", seconds: 18 },
  "joinedS_2705384848_3138462214": { state: "red", phase: "PHASE 1 (RED)", seconds: 32 },
  "cluster_2683490416_2683507646_2683507647_2684658305_#2more": { state: "green", phase: "EMERGENCY_GREEN", seconds: 26 }
}

function adaptiveControl(intersections: IntersectionData[]): AdaptiveControlData[] {
  return intersections.flatMap((intersection) =>
    intersection.approaches.map((approach) => ({
      intersectionId: intersection.id,
      approach: approach.direction,
      vehicleCount: approach.vehicles,
      calculatedGreenTime: Math.min(60, Math.max(10, Math.round(approach.vehicles * 0.9))),
      actualGreenTime: Math.min(60, Math.max(10, Math.round(approach.vehicles * 0.9)))
    }))
  )
}

function baseSnapshot(): SimulationSnapshot {
  return {
    state: {
      simulationTime: 2538,
      currentClock: "00:42:18",
      currentPeriod: "Afternoon peak",
      adaptiveMode: true,
      connectionStatus: "connected",
      simulationStatus: "running"
    },
    metrics: {
      activeVehicles: 1247,
      completedVehicles: 8342,
      averageSpeed: 34,
      averageWaitingTime: 18,
      averageQueueLength: 21,
      maximumQueueLength: 67,
      trafficFlow: 1310,
      congestionEvents: 12,
      trafficEfficiency: 91
    },
    intersections: intersectionSeed,
    signals: intersectionSeed.map((i) => ({
      intersectionId: i.id,
      currentPhase: phaseById[i.id]?.phase || "PHASE 0",
      state: phaseById[i.id]?.state || "green",
      remainingTime: phaseById[i.id]?.seconds || 20,
      currentGreenTime: 28,
      controlMode: i.status === "emergency" ? "emergency" : "adaptive"
    })),
    adaptiveControl: adaptiveControl(intersectionSeed),
    emergencyVehicles: [
      {
        id: "AMBULANCE_NAGPUR",
        type: "ambulance",
        location: "372646899#9 → -93620634#5",
        status: "approaching",
        priorityStatus: "active",
        priorityIntersection: "cluster_2683490416_2683507646_2683507647_2684658305_#2more",
        responseTime: 8
      }
    ],
    roads: [
      {
        roadName: "Wardha Road",
        coordinates: [[21.09, 79.06], [21.12, 79.075]],
        vehicleCount: 241,
        queueLength: 38,
        congestionLevel: 61
      },
      {
        roadName: "Ring Road Corridor",
        coordinates: [[21.10, 79.07], [21.11, 79.08]],
        vehicleCount: 118,
        queueLength: 12,
        congestionLevel: 22
      }
    ],
    performanceComparison: [
      { metric: "Average waiting time", fixed: 52, adaptive: 18, improvement: -65, unit: "sec" },
      { metric: "Average queue length", fixed: 38, adaptive: 21, improvement: -45, unit: "veh" },
      { metric: "Average speed", fixed: 19, adaptive: 34, improvement: 79, unit: "km/h" },
      { metric: "Throughput", fixed: 820, adaptive: 1310, improvement: 60, unit: "veh/hr" }
    ],
    traffic,
    events: [
      { time: "00:42:18", event: "signal.phase.changed", payload: "Chatrapati GREEN" },
      { time: "00:42:16", event: "controller.reallocated", payload: "Ring Road +14s" },
      { time: "00:42:12", event: "emergency.priority", payload: "AMBULANCE_NAGPUR PRIORITY_ACTIVE" }
    ]
  }
}

export class MockSimulationProvider implements SimulationProvider {
  private snapshot = baseSnapshot()
  private listeners = new Set<(snapshot: SimulationSnapshot) => void>()
  private timer?: ReturnType<typeof setInterval>

  constructor() {
    this.timer = setInterval(() => this.tick(), 1000)
  }

  async getSnapshot() {
    return this.snapshot
  }

  subscribe(listener: (snapshot: SimulationSnapshot) => void) {
    this.listeners.add(listener)
    listener(this.snapshot)
    return () => this.listeners.delete(listener)
  }

  pause() {
    this.snapshot = {
      ...this.snapshot,
      state: { ...this.snapshot.state, simulationStatus: "paused" }
    }
    this.emit()
  }

  resume() {
    this.snapshot = {
      ...this.snapshot,
      state: { ...this.snapshot.state, simulationStatus: "running" }
    }
    this.emit()
  }

  step() {
    this.tick()
  }

  setSpeed(_speed: number) {}

  setDelay(_delaySec: number) {}

  trackVehicle(vehicleId: string) {
    this.snapshot = {
      ...this.snapshot,
      events: [
        {
          time: this.snapshot.state.currentClock,
          event: "gui.trackVehicle",
          payload: vehicleId || "Free camera view"
        },
        ...this.snapshot.events
      ].slice(0, 6)
    }
    this.emit()
  }

  setZoom(_zoom: number) {}

  centerIntersection(intersectionId: string) {
    this.snapshot = {
      ...this.snapshot,
      events: [
        {
          time: this.snapshot.state.currentClock,
          event: "gui.centerIntersection",
          payload: intersectionId
        },
        ...this.snapshot.events
      ].slice(0, 6)
    }
    this.emit()
  }

  sendCommand(_command: string, _params?: Record<string, any>) {}

  private tick() {

    if (this.snapshot.state.simulationStatus !== "running") return
    const nextTime = this.snapshot.state.simulationTime + 1
    const wave = Math.sin(nextTime / 9)

    const intersections = this.snapshot.intersections.map((intersection, index) => {
      const vehicleDelta = Math.round(wave * 2 + Math.sin(nextTime / 13 + index) * 1.5)
      const approaches = intersection.approaches.map((approach, approachIndex) => {
        const vehicles = Math.max(4, approach.vehicles + Math.round(vehicleDelta + Math.sin(nextTime / 7 + approachIndex) * 1.2))
        return {
          ...approach,
          vehicles,
          queueLength: Math.max(2, Math.round(vehicles * (0.35 + intersection.congestionLevel / 220)))
        }
      })
      const total = approaches.reduce((sum, approach) => sum + approach.vehicles, 0)
      const congestionLevel = Math.max(5, Math.min(85, Math.round(total / 2.2)))
      return {
        ...intersection,
        approaches,
        congestionLevel,
        averageWaitingTime: Math.max(5, Math.round(congestionLevel * 0.58)),
        status: (index === 2 ? "emergency" : congestionLevel > 50 ? "congested" : "normal") as "normal" | "congested" | "emergency"
      }
    })

    const signals = this.snapshot.signals.map((signal, index) => {
      const remainingTime = signal.remainingTime - 1
      if (remainingTime > 0) return { ...signal, remainingTime }
      const cycle = (nextTime + index * 11) % 60
      const state = cycle < 42 ? "green" : cycle < 46 ? "yellow" : "red" as const
      return {
        ...signal,
        state,
        currentPhase: state === "green" ? "PHASE 0 (GREEN)" : state === "yellow" ? "PHASE 1 (YELLOW)" : "PHASE 2 (RED)",
        remainingTime: state === "green" ? 24 : state === "yellow" ? 4 : 18
      }
    })

    const metrics = {
      ...this.snapshot.metrics,
      activeVehicles: Math.round(1247 + wave * 9),
      averageSpeed: Number((34 + wave * 1.2).toFixed(1)),
      averageWaitingTime: Number((18 - wave * 1.4).toFixed(1)),
      averageQueueLength: Math.round(21 + wave * 2),
      trafficEfficiency: Math.round(91 + wave * 2),
      trafficFlow: Math.round(1310 + wave * 18)
    }

    this.snapshot = {
      ...this.snapshot,
      state: {
        ...this.snapshot.state,
        simulationTime: nextTime,
        currentClock: new Date(nextTime * 1000).toISOString().slice(11, 19)
      },
      metrics,
      intersections,
      signals,
      adaptiveControl: adaptiveControl(intersections),
      traffic: [
        ...this.snapshot.traffic.slice(-10),
        {
          time: this.snapshot.state.currentClock.slice(3),
          vehicles: metrics.activeVehicles,
          averageSpeed: metrics.averageSpeed,
          congestion: Math.round(100 - metrics.trafficEfficiency)
        }
      ],
      events: [
        {
          time: this.snapshot.state.currentClock,
          event: "telemetry.snapshot",
          payload: `${metrics.activeVehicles} vehicles · ${metrics.averageSpeed} km/h`
        },
        ...this.snapshot.events
      ].slice(0, 5)
    }
    this.emit()
  }

  private emit() {
    this.listeners.forEach((listener) => listener(this.snapshot))
  }
}

// Mode Selection: Controlled via environment variable NEXT_PUBLIC_SIMULATION_MODE (defaults to websocket)
const simMode =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_SIMULATION_MODE?.toLowerCase()) ||
  "websocket"

export const simulationProvider: SimulationProvider =
  simMode === "mock"
    ? new MockSimulationProvider()
    : new WebSocketSimulationProvider()

export const getConnectionLabel = (status: ConnectionStatus) =>
  status === "connected"
    ? "WebSocket Connected"
    : status === "connecting"
    ? "Connecting"
    : status === "reconnecting"
    ? "Reconnecting"
    : "Offline"
