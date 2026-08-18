import type {
  AdaptiveControlData,
  ConnectionStatus,
  EmergencyVehicle,
  IntersectionData,
  PerformanceComparison,
  RoadData,
  SignalData,
  SimulationSnapshot,
  SimulationState,
  SimulationStatus,
  TrafficMetrics,
  TrafficPoint,
  WebSocketEvent
} from "./types"

// Maintain rolling chart buffer and event log across updates
let trafficHistory: TrafficPoint[] = []
let eventHistory: WebSocketEvent[] = []

function formatPeriodName(rawPeriod?: string): string {
  if (!rawPeriod) return "Normal Period"
  const upper = rawPeriod.toUpperCase()
  if (upper.includes("MORNING")) return "Morning Peak"
  if (upper.includes("EVENING")) return "Evening Peak"
  if (upper.includes("NORMAL")) return "Normal Flow"
  return rawPeriod.replace(/_/g, " ")
}

function formatClockFromSeconds(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

export function resetNormalizationHistory() {
  trafficHistory = []
  eventHistory = []
}

export function normalizeSimulationData(
  raw: any,
  connectionStatus: ConnectionStatus = "connected"
): SimulationSnapshot {
  if (!raw || typeof raw !== "object") {
    return createEmptySnapshot(connectionStatus)
  }

  // 1. Simulation State
  const rawSim = raw.simulation || {}
  const simTime = Number(rawSim.time ?? raw.simulation_time ?? 0)
  const currentClock = rawSim.clock || formatClockFromSeconds(simTime)
  const currentPeriod = formatPeriodName(rawSim.period || raw.period)
  const adaptiveMode = rawSim.adaptiveMode ?? (rawSim.mode === "ADAPTIVE" || rawSim.mode === "EMERGENCY_DEMO")
  const simulationStatus: SimulationStatus = rawSim.status === "paused" ? "paused" : rawSim.status === "stopped" ? "stopped" : "running"

  const state: SimulationState = {
    simulationTime: simTime,
    currentClock,
    currentPeriod,
    adaptiveMode: Boolean(adaptiveMode),
    connectionStatus,
    simulationStatus
  }

  // 2. Metrics
  const rawMetrics = raw.traffic || raw.metrics || {}
  const metrics: TrafficMetrics = {
    activeVehicles: Number(rawMetrics.activeVehicles ?? rawMetrics.active_vehicles ?? 0),
    completedVehicles: Number(rawMetrics.completedVehicles ?? rawMetrics.completed_vehicles ?? 0),
    averageSpeed: Number(rawMetrics.averageSpeed ?? rawMetrics.average_speed_kmh ?? rawMetrics.average_speed ?? 0),
    averageWaitingTime: Number(rawMetrics.averageWaitingTime ?? rawMetrics.average_waiting_time ?? 0),
    averageQueueLength: Number(rawMetrics.averageQueueLength ?? rawMetrics.average_queue_length ?? 0),
    maximumQueueLength: Number(rawMetrics.maximumQueueLength ?? rawMetrics.max_queue ?? 0),
    trafficFlow: Number(rawMetrics.trafficFlow ?? rawMetrics.traffic_flow ?? 0),
    congestionEvents: Number(rawMetrics.congestionEvents ?? rawMetrics.congestion_events ?? 0),
    trafficEfficiency: Number(rawMetrics.trafficEfficiency ?? rawMetrics.traffic_efficiency ?? 90)
  }

  // 3. Intersections
  const rawIntersections = Array.isArray(raw.intersections)
    ? raw.intersections
    : typeof raw.intersections === "object" && raw.intersections !== null
    ? Object.values(raw.intersections)
    : []

  const intersections: IntersectionData[] = rawIntersections.map((item: any, index: number) => {
    const id = String(item.id || item.intersection_id || `INT-${index + 1}`)
    const name = item.name || id
    const approaches = Array.isArray(item.approaches)
      ? item.approaches.map((app: any) => ({
          direction: String(app.direction || app.edge_id || "Approach"),
          vehicles: Number(app.vehicles ?? 0),
          queueLength: Number(app.queueLength ?? app.queue ?? 0)
        }))
      : typeof item.approaches === "object" && item.approaches !== null
      ? Object.entries(item.approaches).map(([edgeId, app]: [string, any]) => ({
          direction: edgeId,
          vehicles: Number(app.vehicles ?? 0),
          queueLength: Number(app.queue ?? 0)
        }))
      : []

    return {
      id,
      name,
      zone: item.zone || "Nagpur Ring Road",
      latitude: Number(item.latitude ?? 21.1458),
      longitude: Number(item.longitude ?? 79.0882),
      approaches,
      averageWaitingTime: Number(item.averageWaitingTime ?? item.average_waiting_time ?? 0),
      congestionLevel: Number(item.congestionLevel ?? 0),
      status: item.status === "emergency" ? "emergency" : item.status === "congested" ? "congested" : "normal"
    }
  })

  // 4. Signals
  const rawSignals = Array.isArray(raw.signals) ? raw.signals : []
  const signals: SignalData[] = rawSignals.map((item: any) => {
    const rawState = String(item.state || "").toLowerCase()
    const state: "green" | "yellow" | "red" = rawState.includes("green") || rawState === "g"
      ? "green"
      : rawState.includes("yellow") || rawState === "y"
      ? "yellow"
      : "red"

    const controlMode: "adaptive" | "fixed" | "emergency" = item.controlMode === "emergency"
      ? "emergency"
      : item.controlMode === "fixed"
      ? "fixed"
      : "adaptive"

    return {
      intersectionId: String(item.intersectionId || item.intersection_id || ""),
      currentPhase: String(item.currentPhase || item.signal_phase || "Phase 0"),
      state,
      remainingTime: Number(item.remainingTime ?? item.phase_remaining ?? 0),
      currentGreenTime: Number(item.currentGreenTime ?? 16),
      controlMode
    }
  })

  // 5. Adaptive Control
  const rawAdaptive = Array.isArray(raw.adaptiveControl ?? raw.adaptive_control)
    ? (raw.adaptiveControl ?? raw.adaptive_control)
    : []
  const adaptiveControl: AdaptiveControlData[] = rawAdaptive.map((item: any) => ({
    intersectionId: String(item.intersectionId || item.intersection_id || ""),
    approach: String(item.approach || item.selected_movement || ""),
    vehicleCount: Number(item.vehicleCount ?? item.vehicle_count ?? 0),
    calculatedGreenTime: Number(item.calculatedGreenTime ?? item.calculated_green_time ?? 16),
    actualGreenTime: Number(item.actualGreenTime ?? item.actual_green_time ?? 16)
  }))

  // 6. Emergency Vehicles
  const rawEmergency = Array.isArray(raw.emergencyVehicles ?? raw.emergency_vehicles)
    ? (raw.emergencyVehicles ?? raw.emergency_vehicles)
    : []
  const emergencyVehicles: EmergencyVehicle[] = rawEmergency.map((item: any) => {
    const typeStr = String(item.type || "").toLowerCase()
    const type: "ambulance" | "fire" | "police" = typeStr.includes("fire")
      ? "fire"
      : typeStr.includes("police")
      ? "police"
      : "ambulance"

    return {
      id: String(item.id || item.vehicle_id || "EMERGENCY"),
      type,
      location: String(item.location || item.edge_id || "En route"),
      status: item.status === "cleared" ? "cleared" : "approaching",
      priorityStatus: item.priorityStatus === "standby" ? "standby" : "active",
      priorityIntersection: String(item.priorityIntersection || item.next_tls || "None"),
      responseTime: Number(item.responseTime ?? item.response_time ?? 0)
    }
  })

  // 7. Roads
  const rawRoads = Array.isArray(raw.roads) ? raw.roads : []
  const roads: RoadData[] = rawRoads.map((item: any) => ({
    roadName: String(item.roadName || item.road_name || "Corridor"),
    coordinates: Array.isArray(item.coordinates) ? item.coordinates : [[21.1, 79.0], [21.12, 79.08]],
    vehicleCount: Number(item.vehicleCount ?? item.vehicles ?? 0),
    queueLength: Number(item.queueLength ?? item.queue ?? 0),
    congestionLevel: Number(item.congestionLevel ?? 0)
  }))

  // 8. Performance Comparison
  const rawComp = Array.isArray(raw.performanceComparison ?? raw.performance_comparison)
    ? (raw.performanceComparison ?? raw.performance_comparison)
    : []
  const performanceComparison: PerformanceComparison[] = rawComp.map((item: any) => ({
    metric: String(item.metric || ""),
    fixed: Number(item.fixed ?? 0),
    adaptive: Number(item.adaptive ?? 0),
    improvement: Number(item.improvement ?? 0),
    unit: String(item.unit || "")
  }))

  // 9. Rolling Traffic History (for Area Chart)
  const timeLabel = currentClock.slice(3) // "MM:SS"
  const newPoint: TrafficPoint = {
    time: timeLabel,
    vehicles: metrics.activeVehicles,
    averageSpeed: metrics.averageSpeed,
    congestion: Math.max(0, 100 - metrics.trafficEfficiency)
  }

  if (trafficHistory.length === 0 || trafficHistory[trafficHistory.length - 1].time !== timeLabel) {
    trafficHistory = [...trafficHistory.slice(-14), newPoint]
  } else {
    trafficHistory[trafficHistory.length - 1] = newPoint
  }

  // 10. WebSocket Event Log
  const newEvents: WebSocketEvent[] = []
  if (emergencyVehicles.length > 0) {
    newEvents.push({
      time: currentClock,
      event: "emergency.priority",
      payload: `${emergencyVehicles[0].id} → ${emergencyVehicles[0].priorityIntersection}`
    })
  }
  if (signals.length > 0) {
    newEvents.push({
      time: currentClock,
      event: "telemetry.step",
      payload: `${metrics.activeVehicles} veh · ${metrics.averageSpeed} km/h · ${intersections.length} TLS`
    })
  }

  if (newEvents.length > 0) {
    eventHistory = [...newEvents, ...eventHistory].slice(0, 8)
  }

  return {
    state,
    metrics,
    intersections,
    signals,
    adaptiveControl,
    emergencyVehicles,
    roads,
    performanceComparison,
    traffic: [...trafficHistory],
    events: [...eventHistory]
  }
}

export function createEmptySnapshot(connectionStatus: ConnectionStatus = "disconnected"): SimulationSnapshot {
  return {
    state: {
      simulationTime: 0,
      currentClock: "00:00:00",
      currentPeriod: "Connecting...",
      adaptiveMode: true,
      connectionStatus,
      simulationStatus: "stopped"
    },
    metrics: {
      activeVehicles: 0,
      completedVehicles: 0,
      averageSpeed: 0,
      averageWaitingTime: 0,
      averageQueueLength: 0,
      maximumQueueLength: 0,
      trafficFlow: 0,
      congestionEvents: 0,
      trafficEfficiency: 100
    },
    intersections: [],
    signals: [],
    adaptiveControl: [],
    emergencyVehicles: [],
    roads: [],
    performanceComparison: [],
    traffic: trafficHistory.length > 0 ? [...trafficHistory] : [{ time: "00:00", vehicles: 0, averageSpeed: 0, congestion: 0 }],
    events: eventHistory.length > 0 ? [...eventHistory] : [{ time: "00:00:00", event: "connection.status", payload: connectionStatus }]
  }
}
