"use client"

import { useMemo, useState } from "react"
import { Activity, AlertTriangle, ArrowDownRight, CarFront, Clock3, Gauge, MapPin, Pause, Play, Radio, Siren, TrendingUp } from "lucide-react"
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useSimulationControls, useSimulationData } from "./simulation-context"
import type { IntersectionData, SignalState } from "@/lib/simulation/types"

const signalColor: Record<SignalState, string> = { green: "bg-emerald-400", yellow: "bg-amber-300", red: "bg-red-400" }

function Metric({ label, value, unit, icon: Icon, tone = "blue" }: { label: string; value: string | number; unit: string; icon: typeof Activity; tone?: string }) {
  return (
    <div className="border border-white/15 bg-white/[0.03] p-4 transition-colors hover:border-white/25">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-display text-white">{value}<span className="ml-1 text-sm font-sans text-slate-500">{unit}</span></p>
        </div>
        <span className={cn("flex h-8 w-8 items-center justify-center rounded-md", tone === "amber" ? "bg-amber-400/10 text-amber-300" : tone === "green" ? "bg-emerald-400/10 text-emerald-300" : "bg-blue-400/10 text-blue-300")}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 flex items-center gap-1 text-xs text-emerald-300"><ArrowDownRight className="h-3 w-3" />live from provider</p>
    </div>
  )
}

function NetworkMap({ intersections, selected, onSelect }: { intersections: IntersectionData[]; selected: string; onSelect: (id: string) => void }) {
  const positions = [[24, 64], [63, 72], [32, 30], [72, 24], [53, 47], [82, 58]]

  return (
    <div className="relative min-h-[420px] overflow-hidden border border-white/15 bg-[#08151f] bg-[linear-gradient(rgba(96,165,250,.045)_1px,transparent_1px),linear-gradient(90deg,rgba(96,165,250,.045)_1px,transparent_1px)] bg-[size:38px_38px]">
      <div className="absolute left-5 top-5 z-10 flex items-center gap-2 border border-white/15 bg-black/70 px-3 py-2 text-xs text-slate-400">
        <MapPin className="h-3.5 w-3.5 text-blue-300" />Nagpur urban network <span className="text-slate-600">·</span> live state
      </div>
      {intersections.map((item, index) => {
        const pos = positions[index % positions.length]
        return (
          <button key={item.id} onClick={() => onSelect(item.id)} className="group absolute -translate-x-1/2 -translate-y-1/2 text-left" style={{ left: `${pos[0]}%`, top: `${pos[1]}%` }}>
            <span className={cn("relative flex h-5 w-5 items-center justify-center rounded-full border-2 border-[#08151f] shadow-lg transition-transform group-hover:scale-125", item.status === "emergency" ? "bg-red-400" : item.status === "congested" ? "bg-amber-300" : "bg-emerald-400", selected === item.id && "ring-2 ring-white ring-offset-2 ring-offset-[#08151f]")} />
            <span className="absolute left-7 top-0 whitespace-nowrap text-[11px] text-slate-400">{item.name.split(" ").slice(0, 3).join(" ")}</span>
          </button>
        )
      })}
    </div>
  )
}

export function DashboardClient() {
  const snapshot = useSimulationData()
  const { pause, resume } = useSimulationControls()

  const defaultId = snapshot.intersections[0]?.id || ""
  const [selectedId, setSelectedId] = useState(defaultId)

  const selected = useMemo(() => {
    return (
      snapshot.intersections.find((item) => item.id === selectedId) ??
      snapshot.intersections[0] ?? {
        id: "NONE",
        name: "No Active Intersections",
        zone: "Nagpur Network",
        latitude: 21.1458,
        longitude: 79.0882,
        approaches: [],
        averageWaitingTime: 0,
        congestionLevel: 0,
        status: "normal" as const
      }
    )
  }, [selectedId, snapshot.intersections])

  const activeEmergency = snapshot.emergencyVehicles[0]
  const running = snapshot.state.simulationStatus === "running"

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-mono uppercase tracking-[0.16em] text-blue-300">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-300" />Live telemetry · {snapshot.state.currentClock}
          </div>
          <h1 className="text-3xl font-display tracking-tight text-white">Live Traffic Command Center</h1>
          <p className="mt-1 text-sm text-slate-500">Nagpur, Maharashtra · {snapshot.state.currentPeriod} · adaptive mode {snapshot.state.adaptiveMode ? "enabled" : "disabled"}</p>
        </div>
        <Button variant="outline" className="border-white/15 bg-white/[0.03] text-slate-300 hover:bg-white/10 hover:text-white" onClick={() => running ? pause() : resume()}>
          {running ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
          {running ? "Pause simulation" : "Resume simulation"}
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Active vehicles" value={snapshot.metrics.activeVehicles.toLocaleString()} unit="veh" icon={CarFront} />
        <Metric label="Average speed" value={snapshot.metrics.averageSpeed} unit="km/h" icon={Gauge} tone="green" />
        <Metric label="Average waiting time" value={snapshot.metrics.averageWaitingTime} unit="sec" icon={Clock3} tone="amber" />
        <Metric label="Traffic efficiency" value={snapshot.metrics.trafficEfficiency} unit="%" icon={TrendingUp} />
        <Metric label="Max queue" value={snapshot.metrics.maximumQueueLength} unit="veh" icon={AlertTriangle} tone="amber" />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.65fr_1fr]">
        <section className="border border-white/15 bg-white/[0.03] p-4 sm:p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-medium text-white">Network traffic</h2>
              <p className="mt-1 text-xs text-slate-500">One provider state · smooth telemetry updates</p>
            </div>
            <Badge variant="outline" className="border-emerald-400/30 text-emerald-300">
              <Radio className="mr-1.5 h-3 w-3" />Live
            </Badge>
          </div>
          <div className="h-[230px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={snapshot.traffic}>
                <defs>
                  <linearGradient id="vehicles-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,.08)" vertical={false} />
                <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#050505", border: "1px solid rgba(255,255,255,.15)", color: "white" }} />
                <Area type="monotone" dataKey="vehicles" stroke="#60a5fa" fill="url(#vehicles-fill)" strokeWidth={2} />
                <Line type="monotone" dataKey="congestion" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="border border-white/15 bg-white/[0.03] p-4 sm:p-5">
          <div className="mb-4">
            <h2 className="text-sm font-medium text-white">Traffic state map</h2>
            <p className="mt-1 text-xs text-slate-500">Select an intersection to inspect live signals</p>
          </div>
          <NetworkMap intersections={snapshot.intersections} selected={selected.id} onSelect={setSelectedId} />
        </section>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_1fr_1fr]">
        <section className="border border-white/15 bg-white/[0.03] p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-mono text-blue-300">SELECTED INTERSECTION</p>
              <h2 className="mt-2 text-xl font-display text-white">{selected.name}</h2>
              <p className="mt-1 text-xs text-slate-500">{selected.zone} · {selected.congestionLevel}% congestion</p>
            </div>
            <Badge variant="outline" className="capitalize">{selected.status}</Badge>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-600">Queue</p>
              <p className="mt-1 text-xl text-white">{selected.approaches.reduce((a, b) => a + b.queueLength, 0)}<span className="ml-1 text-xs text-slate-500">veh</span></p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-600">Wait</p>
              <p className="mt-1 text-xl text-white">{selected.averageWaitingTime}<span className="ml-1 text-xs text-slate-500">sec</span></p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-600">Demand</p>
              <p className="mt-1 text-xl text-white">{selected.approaches.reduce((a, b) => a + b.vehicles, 0)}<span className="ml-1 text-xs text-slate-500">veh</span></p>
            </div>
          </div>
        </section>

        <section className="border border-white/15 bg-white/[0.03] p-5">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-300" />
            <h2 className="text-sm font-medium text-white">Adaptive control</h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">Green time follows normalized demand</p>
          <div className="mt-4 space-y-2">
            {snapshot.adaptiveControl.filter((item) => item.intersectionId === selected.id).length > 0 ? (
              snapshot.adaptiveControl
                .filter((item) => item.intersectionId === selected.id)
                .map((item) => (
                  <div key={item.approach} className="flex items-center justify-between border-b border-white/5 py-2 text-xs">
                    <span className="text-slate-400">{item.approach} · {item.vehicleCount} veh</span>
                    <span className="font-mono text-blue-300">{item.actualGreenTime}s green</span>
                  </div>
                ))
            ) : (
              <p className="py-3 text-xs text-slate-500">Dynamic cycle allocation active</p>
            )}
          </div>
        </section>

        <section className={cn("border p-5", activeEmergency ? "border-red-400/20 bg-red-400/[0.04]" : "border-white/15 bg-white/[0.03]")}>
          <div className={cn("flex items-center gap-2", activeEmergency ? "text-red-300" : "text-slate-300")}>
            <Siren className="h-4 w-4" />
            <h2 className="text-sm font-medium">Emergency priority</h2>
          </div>
          {activeEmergency ? (
            <>
              <p className="mt-1 text-xs text-slate-500">{activeEmergency.id} · {activeEmergency.location}</p>
              <div className="mt-5 flex items-end justify-between">
                <div>
                  <p className="text-2xl font-display text-white">{activeEmergency.responseTime}s</p>
                  <p className="text-xs text-slate-500">estimated time to clearance</p>
                </div>
                <Badge className="bg-red-400/15 text-red-300">Priority active</Badge>
              </div>
            </>
          ) : (
            <>
              <p className="mt-1 text-xs text-slate-500">Corridor monitoring · Indian LHT network</p>
              <div className="mt-5 flex items-end justify-between">
                <div>
                  <p className="text-2xl font-display text-slate-400">0</p>
                  <p className="text-xs text-slate-500">active emergency overrides</p>
                </div>
                <Badge variant="outline" className="border-white/15 text-slate-400">Standby</Badge>
              </div>
            </>
          )}
        </section>
      </div>

      {snapshot.performanceComparison.length > 0 && (
        <div className="mt-4 border border-white/15 bg-white/[0.03] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-medium text-white">Fixed vs adaptive</h2>
              <p className="mt-1 text-xs text-slate-500">Performance comparison from empirical simulation runs</p>
            </div>
            <AlertTriangle className="h-4 w-4 text-slate-500" />
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            {snapshot.performanceComparison.map((item) => (
              <div key={item.metric} className="border-l border-blue-300/40 pl-3">
                <p className="text-xs text-slate-500">{item.metric}</p>
                <p className="mt-2 text-lg text-white">{item.adaptive} <span className="text-xs text-slate-500">{item.unit}</span></p>
                <p className="text-xs text-emerald-300">{item.improvement > 0 ? "+" : ""}{item.improvement}% vs fixed</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
