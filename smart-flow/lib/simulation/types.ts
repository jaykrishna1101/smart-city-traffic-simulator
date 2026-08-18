export type ConnectionStatus = "connected" | "connecting" | "reconnecting" | "disconnected"
export type SimulationStatus = "running" | "paused" | "stopped"
export type SignalState = "green" | "yellow" | "red"
export type IntersectionStatus = "normal" | "congested" | "emergency"

export interface SimulationState {
  simulationTime: number
  currentClock: string
  currentPeriod: string
  adaptiveMode: boolean
  connectionStatus: ConnectionStatus
  simulationStatus: SimulationStatus
}

export interface TrafficMetrics {
  activeVehicles: number
  completedVehicles: number
  averageSpeed: number
  averageWaitingTime: number
  averageQueueLength: number
  maximumQueueLength: number
  trafficFlow: number
  congestionEvents: number
  trafficEfficiency: number
}

export interface ApproachData { direction: string; vehicles: number; queueLength: number }
export interface IntersectionData {
  id: string
  name: string
  zone: string
  latitude: number
  longitude: number
  approaches: ApproachData[]
  averageWaitingTime: number
  congestionLevel: number
  status: IntersectionStatus
}
export interface SignalData {
  intersectionId: string
  currentPhase: string
  state: SignalState
  remainingTime: number
  currentGreenTime: number
  controlMode: "adaptive" | "fixed" | "emergency"
}
export interface AdaptiveControlData {
  intersectionId: string
  approach: string
  vehicleCount: number
  calculatedGreenTime: number
  actualGreenTime: number
}
export interface EmergencyVehicle {
  id: string
  type: "ambulance" | "fire" | "police"
  location: string
  status: "approaching" | "cleared"
  priorityStatus: "active" | "standby"
  priorityIntersection: string
  responseTime: number
}
export interface RoadData { roadName: string; coordinates: [number, number][]; vehicleCount: number; queueLength: number; congestionLevel: number }
export interface PerformanceComparison { metric: string; fixed: number; adaptive: number; improvement: number; unit: string }
export interface TrafficPoint { time: string; vehicles: number; averageSpeed: number; congestion: number }
export interface WebSocketEvent { time: string; event: string; payload: string }
export interface SimulationSnapshot {
  state: SimulationState
  metrics: TrafficMetrics
  intersections: IntersectionData[]
  signals: SignalData[]
  adaptiveControl: AdaptiveControlData[]
  emergencyVehicles: EmergencyVehicle[]
  roads: RoadData[]
  performanceComparison: PerformanceComparison[]
  traffic: TrafficPoint[]
  events: WebSocketEvent[]
}

export type SimulationData = SimulationSnapshot
export type Intersection = IntersectionData
export type SignalPhase = SignalData
export type EmergencyEvent = EmergencyVehicle

export interface SimulationControls {
  pause: () => void
  resume: () => void
  step: () => void
  setSpeed: (speedMultiplier: number) => void
  setDelay: (delaySec: number) => void
  trackVehicle: (vehicleId: string) => void
  setZoom: (zoomLevel: number) => void
  centerIntersection: (intersectionId: string) => void
  sendCommand: (command: string, params?: Record<string, any>) => void
}

export interface SimulationProvider {
  getSnapshot(): Promise<SimulationSnapshot>
  subscribe(listener: (snapshot: SimulationSnapshot) => void): () => void
  pause(): void
  resume(): void
  step(): void
  setSpeed(speed: number): void
  setDelay(delaySec: number): void
  trackVehicle(vehicleId: string): void
  setZoom(zoom: number): void
  centerIntersection(intersectionId: string): void
  sendCommand(command: string, params?: Record<string, any>): void
}


