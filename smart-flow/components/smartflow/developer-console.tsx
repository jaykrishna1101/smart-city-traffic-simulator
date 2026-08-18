"use client"

import { useState } from "react"
import { Activity, Braces, Code2, Database, RefreshCw, Server, Wifi } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useSimulationData } from "./simulation-context"

const tabs = ["Overview", "Intersections", "Signals", "Emergency", "Road data", "WebSocket"]
const code = `// SmartFlow Live TraCI WebSocket Contract
const socket = new WebSocket("ws://localhost:8765/ws")
socket.onmessage = (event) => {
  const telemetry = JSON.parse(event.data)
  console.log("SUMO Telemetry Step:", telemetry.simulation.time, telemetry.traffic)
}`

export function DeveloperConsole() {
  const snapshot = useSimulationData()
  const [activeTab, setActiveTab] = useState("Overview")

  const visible =
    activeTab === "Intersections"
      ? snapshot.intersections
      : activeTab === "Signals"
      ? snapshot.signals
      : activeTab === "Emergency"
      ? snapshot.emergencyVehicles
      : activeTab === "Road data"
      ? snapshot.roads
      : snapshot.events

  const providerName =
    typeof process !== "undefined" && process.env.NEXT_PUBLIC_SIMULATION_MODE?.toLowerCase() === "websocket"
      ? "WebSocketSimulationProvider"
      : "MockSimulationProvider"

  const wsEndpoint =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) || "ws://localhost:8765/ws"

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-mono uppercase tracking-[0.16em] text-blue-300">
            <Code2 className="h-3.5 w-3.5" />Engineering surface · {snapshot.state.currentClock}
          </div>
          <h1 className="text-balance text-3xl font-display tracking-tight text-white">Developer Console</h1>
          <p className="mt-1 text-sm text-slate-500">Inspect the live simulation contract powering every SmartFlow view.</p>
        </div>
        <Badge variant="outline" className="w-fit border-emerald-400/30 bg-emerald-400/10 text-emerald-300">
          <Wifi className="mr-1.5 h-3 w-3" />{snapshot.state.connectionStatus} · {snapshot.metrics.activeVehicles} vehicles
        </Badge>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_1.9fr]">
        <section className="space-y-4">
          <div className="border border-white/15 bg-white/[0.03] p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-mono text-blue-300">SIMULATION PROVIDER</p>
                <h2 className="mt-2 text-lg font-medium text-white">{providerName}</h2>
                <p className="mt-1 text-xs text-slate-500">Live transport layer for SUMO / TraCI</p>
              </div>
              <Server className="h-5 w-5 text-slate-500" />
            </div>
            <div className="mt-5 space-y-2 text-xs">
              {[
                ["status", snapshot.state.connectionStatus],
                ["endpoint", wsEndpoint],
                ["clock", snapshot.state.currentClock],
                ["mode", snapshot.state.adaptiveMode ? "adaptive" : "fixed"]
              ].map(([key, value]) => (
                <div key={key} className="flex justify-between border-b border-white/5 py-2">
                  <span className="text-slate-500">{key}</span>
                  <span className="font-mono text-slate-300">{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-white/15 bg-white/[0.03] p-5">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-300" />
              <h2 className="text-sm font-medium text-white">Normalized collections</h2>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-400">
              {[
                ["intersections", snapshot.intersections.length],
                ["signals", snapshot.signals.length],
                ["emergency", snapshot.emergencyVehicles.length],
                ["roads", snapshot.roads.length]
              ].map(([label, value]) => (
                <div key={label} className="border border-white/10 bg-black/20 p-3">
                  <span className="font-mono text-blue-200">{value}</span>
                  <p className="mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border border-white/15 bg-white/[0.03] p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono text-blue-300">LIVE INSPECTOR</p>
              <h2 className="mt-2 text-lg font-medium text-white">Simulation data surface</h2>
            </div>
            <Button variant="outline" size="sm" className="border-white/15 bg-transparent text-slate-300">
              <RefreshCw className="mr-2 h-3.5 w-3.5" />Live
            </Button>
          </div>

          <div className="flex gap-1 overflow-x-auto border-b border-white/10 pb-2">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`whitespace-nowrap px-3 py-2 text-xs transition-colors ${
                  activeTab === tab ? "border-b border-blue-300 text-white" : "text-slate-500 hover:text-white"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="mt-5 max-h-[330px] overflow-auto space-y-2">
            {activeTab === "Overview" ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ["activeVehicles", snapshot.metrics.activeVehicles],
                    ["averageSpeed", `${snapshot.metrics.averageSpeed} km/h`],
                    ["waitingTime", `${snapshot.metrics.averageWaitingTime} sec`],
                    ["trafficFlow", `${snapshot.metrics.trafficFlow} /hr`]
                  ].map(([label, value]) => (
                    <div key={label} className="border border-white/10 bg-black/20 p-3">
                      <p className="font-mono text-[11px] text-slate-500">{label}</p>
                      <p className="mt-2 text-lg text-white">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 border border-blue-300/15 bg-blue-300/[0.04] p-4">
                  <div className="flex items-center gap-2">
                    <Braces className="h-4 w-4 text-blue-300" />
                    <p className="text-xs text-slate-400">WebSocket Integration Contract</p>
                  </div>
                  <pre className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-blue-100">{code}</pre>
                </div>
              </>
            ) : visible.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No {activeTab.toLowerCase()} entries in current state</div>
            ) : (
              visible.map((item: any, index: number) => (
                <div key={index} className="flex items-center justify-between border-b border-white/5 py-3 text-xs">
                  <span className="font-mono text-slate-300">
                    {"id" in item ? item.id : "event" in item ? item.event : "roadName" in item ? item.roadName : item.intersectionId}
                  </span>
                  <span className="text-slate-500 max-w-[300px] truncate">
                    {"event" in item ? item.payload : JSON.stringify(item)}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="mt-4 border border-white/15 bg-white/[0.03] p-5">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-300" />
          <h2 className="text-sm font-medium text-white">WebSocket event log</h2>
        </div>
        <div className="space-y-2">
          {snapshot.events.map((event, idx) => (
            <div key={`${event.time}-${idx}`} className="flex flex-wrap gap-x-4 gap-y-1 border-b border-white/5 py-2 font-mono text-xs">
              <span className="text-slate-600">{event.time}</span>
              <span className="text-blue-200">{event.event}</span>
              <span className="text-slate-500">{event.payload}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
