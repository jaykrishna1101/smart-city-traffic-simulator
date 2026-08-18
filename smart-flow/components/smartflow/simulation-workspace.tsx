"use client"

import { useState } from "react"
import {
  Activity,
  AlertCircle,
  Camera,
  CheckCircle2,
  ChevronRight,
  Crosshair,
  FastForward,
  Gauge,
  Layers,
  MapPin,
  Pause,
  Play,
  Radio,
  RotateCw,
  Search,
  ShieldAlert,
  Siren,
  SkipForward,
  Sliders,
  Sparkles,
  TrafficCone,
  Zap
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useSimulationControls, useSimulationData } from "./simulation-context"
import { getConnectionLabel } from "@/lib/simulation/provider"
import { VncViewport } from "./vnc-viewport"

export function SimulationWorkspace() {
  const snapshot = useSimulationData()
  const controls = useSimulationControls()

  const [selectedSpeed, setSelectedSpeed] = useState<number>(1.0)
  const [selectedZoom, setSelectedZoom] = useState<number>(300)
  const [selectedIntersectionId, setSelectedIntersectionId] = useState<string>(
    snapshot.intersections[0]?.id || ""
  )
  const [trackedVehicleId, setTrackedVehicleId] = useState<string>("")

  const isConnected = snapshot.state.connectionStatus === "connected"
  const isRunning = snapshot.state.simulationStatus === "running"
  const activeEmergency = snapshot.emergencyVehicles.find((v) => v.priorityStatus === "active") || snapshot.emergencyVehicles[0]

  const selectedIntersection =
    snapshot.intersections.find((i) => i.id === selectedIntersectionId) ||
    snapshot.intersections[0]

  const selectedSignal = snapshot.signals.find(
    (s) => s.intersectionId === selectedIntersection?.id
  )

  const handleTogglePlay = () => {
    if (isRunning) {
      controls.pause()
    } else {
      controls.resume()
    }
  }

  const handleSpeedChange = (speed: number) => {
    setSelectedSpeed(speed)
    controls.setSpeed(speed)
  }

  const handleZoomChange = (zoom: number) => {
    setSelectedZoom(zoom)
    controls.setZoom(zoom)
  }

  const handleTrackVehicle = (vehicleId: string) => {
    setTrackedVehicleId(vehicleId)
    controls.trackVehicle(vehicleId)
  }

  const handleCenterIntersection = (intersectionId: string) => {
    setSelectedIntersectionId(intersectionId)
    controls.centerIntersection(intersectionId)
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      {/* Top Status & Mode Strip */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          {/* SUMO Process Badge */}
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isConnected ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" : "bg-red-400"
              )}
            />
            <span className="text-slate-300">SUMO-GUI:</span>
            <span className="font-semibold text-white">
              {isConnected ? "CONNECTED" : "OFFLINE"}
            </span>
          </div>

          {/* TraCI Status */}
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-blue-300" />
            <span className="text-slate-300">TraCI:</span>
            <span className="font-semibold text-white">
              {isConnected ? "SYNCHRONIZED" : "STANDBY"}
            </span>
          </div>

          {/* WebSocket Status */}
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs">
            <Radio className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-slate-300">WebSocket:</span>
            <span className="font-semibold text-emerald-300">
              {getConnectionLabel(snapshot.state.connectionStatus).toUpperCase()}
            </span>
          </div>

          {/* Adaptive Mode Status */}
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs">
            <Sparkles className="h-3.5 w-3.5 text-amber-300" />
            <span className="text-slate-300">Control:</span>
            <span className="font-semibold text-amber-300">ADAPTIVE LHT</span>
          </div>

          {/* Emergency System */}
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs">
            <Siren className="h-3.5 w-3.5 text-rose-400" />
            <span className="text-slate-300">Emergency Priority:</span>
            <span className={cn("font-semibold", activeEmergency ? "text-rose-400" : "text-slate-400")}>
              {activeEmergency ? "ACTIVE OVERRIDE" : "STANDBY READY"}
            </span>
          </div>
        </div>

        {/* Clock & Scenario Period */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">
              Simulation Clock
            </p>
            <p className="font-mono text-base font-bold text-white">
              {snapshot.state.currentClock}
              <span className="ml-2 text-xs font-normal text-slate-400">
                ({snapshot.state.simulationTime.toFixed(0)}s)
              </span>
            </p>
          </div>
          <div className="rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-right">
            <p className="text-[9px] font-mono uppercase text-slate-400">Period</p>
            <p className="font-mono text-xs font-semibold text-blue-300">
              {snapshot.state.currentPeriod}
            </p>
          </div>
        </div>
      </div>

      {/* Main 3-Column Command Workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: TraCI Controls (3 Cols) */}
        <div className="space-y-6 lg:col-span-3">
          {/* Primary Controls Card */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
                <Sliders className="h-4 w-4 text-blue-300" />
                TraCI Controls
              </h2>
              <span className="rounded bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] text-blue-300">
                Authoritative
              </span>
            </div>

            {/* Play / Pause & Step Buttons */}
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={isRunning ? "outline" : "default"}
                  onClick={handleTogglePlay}
                  className={cn(
                    "w-full gap-2 font-mono text-xs",
                    isRunning
                      ? "border-amber-400/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                      : "bg-emerald-600 text-white hover:bg-emerald-500"
                  )}
                >
                  {isRunning ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {isRunning ? "Pause" : "Play"}
                </Button>

                <Button
                  variant="outline"
                  onClick={() => controls.step()}
                  disabled={isRunning}
                  className="w-full gap-2 border-white/10 bg-white/5 font-mono text-xs text-slate-200 hover:bg-white/10 disabled:opacity-40"
                  title="Advance 1 step while paused"
                >
                  <SkipForward className="h-4 w-4" />
                  Single Step
                </Button>
              </div>

              {/* Speed Multiplier Presets */}
              <div className="pt-2">
                <p className="text-[11px] font-medium text-slate-400 mb-2">
                  Simulation Speed:
                </p>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { label: "0.5x", value: 0.5 },
                    { label: "1.0x", value: 1.0 },
                    { label: "2.0x", value: 2.0 },
                    { label: "Max", value: 4.0 }
                  ].map((speed) => (
                    <button
                      key={speed.label}
                      onClick={() => handleSpeedChange(speed.value)}
                      className={cn(
                        "rounded-md py-1.5 font-mono text-xs transition-colors",
                        selectedSpeed === speed.value
                          ? "bg-blue-600 text-white font-semibold shadow-sm"
                          : "border border-white/10 bg-white/[0.03] text-slate-400 hover:bg-white/10 hover:text-white"
                      )}
                    >
                      {speed.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* SUMO-GUI Camera & Viewport Controls */}
            <div className="mt-6 pt-5 border-t border-white/10 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                  <Camera className="h-3.5 w-3.5 text-slate-400" />
                  SUMO-GUI Viewport
                </h3>
                <span className="font-mono text-[10px] text-slate-500">
                  traci.gui
                </span>
              </div>

              {/* Zoom Level */}
              <div>
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
                  <span>Zoom Level</span>
                  <span className="font-mono text-blue-300">{selectedZoom}%</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="800"
                  step="50"
                  value={selectedZoom}
                  onChange={(e) => handleZoomChange(Number(e.target.value))}
                  className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-400"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
                  <span>100% (City)</span>
                  <span>400% (Junction)</span>
                  <span>800% (Lane)</span>
                </div>
              </div>

              {/* Vehicle Tracking Target */}
              <div>
                <p className="text-xs text-slate-400 mb-1.5">Camera Vehicle Lock:</p>
                <select
                  value={trackedVehicleId}
                  onChange={(e) => handleTrackVehicle(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-slate-900 px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                >
                  <option value="">Free Camera (No lock)</option>
                  <option value="AMBULANCE_NAGPUR">🚑 AMBULANCE_NAGPUR</option>
                  <option value="POLICE_NAGPUR">🚓 POLICE_NAGPUR</option>
                  <option value="FIRETRUCK_NAGPUR">🚒 FIRETRUCK_NAGPUR</option>
                </select>
              </div>

              {/* Jump to Intersection */}
              <div>
                <p className="text-xs text-slate-400 mb-1.5">Center on Junction:</p>
                <div className="space-y-1.5">
                  {snapshot.intersections.map((inter) => (
                    <button
                      key={inter.id}
                      onClick={() => handleCenterIntersection(inter.id)}
                      className={cn(
                        "w-full flex items-center justify-between rounded-md px-3 py-2 text-left text-xs transition-colors",
                        selectedIntersectionId === inter.id
                          ? "border border-blue-500/40 bg-blue-500/10 text-white font-medium"
                          : "border border-white/5 bg-white/[0.02] text-slate-400 hover:bg-white/5 hover:text-white"
                      )}
                    >
                      <span className="truncate">{inter.name}</span>
                      <MapPin className="h-3 w-3 shrink-0 text-slate-500" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column: Actual SUMO-GUI Viewport (6 Cols) */}
        <div className="lg:col-span-6 flex flex-col">
          <VncViewport className="flex-1" />
        </div>

        {/* Right Column: Object & Signal Inspector (3 Cols) */}
        <div className="space-y-6 lg:col-span-3">
          {/* Selected Intersection Card */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
                <TrafficCone className="h-4 w-4 text-emerald-400" />
                Signal Inspector
              </h2>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-300">
                Live State
              </span>
            </div>

            {selectedIntersection ? (
              <div className="mt-4 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {selectedIntersection.name}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono truncate">
                    ID: {selectedIntersection.id}
                  </p>
                </div>

                {/* Live Phase Badge */}
                {selectedSignal && (
                  <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Current Phase:</span>
                      <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-white">
                        <span
                          className={cn(
                            "h-2.5 w-2.5 rounded-full",
                            selectedSignal.state === "green"
                              ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                              : selectedSignal.state === "yellow"
                              ? "bg-amber-300"
                              : "bg-red-400"
                          )}
                        />
                        {selectedSignal.currentPhase}
                      </div>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Phase Duration:</span>
                      <span className="font-mono text-white">
                        {selectedSignal.remainingTime.toFixed(0)}s remaining
                      </span>
                    </div>
                  </div>
                )}

                {/* Approaches Breakdown */}
                <div>
                  <p className="text-xs font-medium text-slate-300 mb-2">
                    Approach Queues ({selectedIntersection.approaches.length} Approaches):
                  </p>
                  <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                    {selectedIntersection.approaches.map((app, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-2.5 py-1.5 text-xs font-mono"
                      >
                        <span className="truncate text-slate-400 text-[11px]">
                          {app.direction}
                        </span>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-slate-300">{app.vehicles} veh</span>
                          <span className="rounded bg-white/10 px-1.5 py-0.2 text-[10px] text-amber-300">
                            Q: {app.queueLength}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-xs text-slate-500">No intersection selected</p>
            )}
          </div>

          {/* Active Emergency Vehicle Card */}
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/[0.03] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-3 border-b border-rose-500/20">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-rose-300">
                <ShieldAlert className="h-4 w-4 text-rose-400" />
                Emergency Priority
              </h2>
              <span className="rounded bg-rose-500/20 px-2 py-0.5 font-mono text-[10px] text-rose-300 animate-pulse">
                {activeEmergency ? "ACTIVE" : "STANDBY"}
              </span>
            </div>

            {activeEmergency ? (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-white">
                    {activeEmergency.id}
                  </span>
                  <span className="rounded bg-rose-500/20 px-2 py-0.5 text-[10px] font-mono uppercase text-rose-200">
                    {activeEmergency.type}
                  </span>
                </div>

                <div className="text-xs space-y-1.5 text-slate-300 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Target TLS:</span>
                    <span className="truncate max-w-[140px] text-white">
                      {activeEmergency.priorityIntersection || "Approaching"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Response Time:</span>
                    <span className="text-emerald-300">
                      {activeEmergency.responseTime.toFixed(1)}s
                    </span>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleTrackVehicle(activeEmergency.id)}
                  className="w-full mt-2 gap-1.5 border-rose-500/30 bg-rose-500/10 font-mono text-xs text-rose-200 hover:bg-rose-500/20"
                >
                  <Crosshair className="h-3.5 w-3.5" />
                  Lock Camera on Emergency Unit
                </Button>
              </div>
            ) : (
              <div className="mt-4 text-center py-4">
                <p className="text-xs text-slate-400 font-mono">
                  No active emergency override currently dispatched.
                </p>
                <p className="text-[10px] text-slate-500 mt-1">
                  Ambulance auto-spawns at 50s, Police at 150s, Firetruck at 250s.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row: Live Telemetry Strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl">
          <p className="text-[11px] font-medium text-slate-400">Active Vehicles</p>
          <p className="mt-1 font-mono text-2xl font-bold text-white">
            {snapshot.metrics.activeVehicles}
            <span className="ml-1.5 text-xs font-normal text-slate-400">veh</span>
          </p>
          <p className="mt-1 text-[10px] text-emerald-400 font-mono">SUMO Real-time</p>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl">
          <p className="text-[11px] font-medium text-slate-400">Average Speed</p>
          <p className="mt-1 font-mono text-2xl font-bold text-white">
            {snapshot.metrics.averageSpeed.toFixed(1)}
            <span className="ml-1.5 text-xs font-normal text-slate-400">km/h</span>
          </p>
          <p className="mt-1 text-[10px] text-blue-400 font-mono">LHT Network Average</p>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl">
          <p className="text-[11px] font-medium text-slate-400">Avg Waiting Time</p>
          <p className="mt-1 font-mono text-2xl font-bold text-white">
            {snapshot.metrics.averageWaitingTime.toFixed(1)}
            <span className="ml-1.5 text-xs font-normal text-slate-400">s</span>
          </p>
          <p className="mt-1 text-[10px] text-amber-400 font-mono">-42% vs Fixed Time</p>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl">
          <p className="text-[11px] font-medium text-slate-400">Max Queue Length</p>
          <p className="mt-1 font-mono text-2xl font-bold text-white">
            {snapshot.metrics.maximumQueueLength}
            <span className="ml-1.5 text-xs font-normal text-slate-400">veh</span>
          </p>
          <p className="mt-1 text-[10px] text-slate-400 font-mono">Across All Approaches</p>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl col-span-2 sm:col-span-1">
          <p className="text-[11px] font-medium text-slate-400">Traffic Efficiency</p>
          <p className="mt-1 font-mono text-2xl font-bold text-emerald-400">
            {snapshot.metrics.trafficEfficiency.toFixed(0)}%
          </p>
          <p className="mt-1 text-[10px] text-emerald-300 font-mono">Adaptive Optimization</p>
        </div>
      </div>
    </div>
  )
}
