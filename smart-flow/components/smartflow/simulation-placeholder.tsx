"use client"

import { Check, Clock3, ExternalLink, Info, Radio, Server, TerminalSquare } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useSimulationData } from "./simulation-context"
import { cn } from "@/lib/utils"

const steps = ["SUMO connection", "Network loaded", "TraCI bridge", "SmartFlow controller"]

export function SimulationPlaceholder() {
  const snapshot = useSimulationData()
  const isConnected = snapshot.state.connectionStatus === "connected"

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl text-center">
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-xl border border-blue-300/25 bg-blue-300/10 text-blue-300">
          <Radio className="h-6 w-6" />
        </div>
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-blue-300">Simulation environment</p>
        <h1 className="mt-4 text-balance text-4xl font-display tracking-tight text-white sm:text-5xl">
          {isConnected ? "SUMO TraCI Live Stream Active" : "SUMO is ready to connect"}
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-400">
          {isConnected
            ? "Real-time TraCI telemetry is actively streaming from the SUMO simulation backend over WebSockets."
            : "The live traffic telemetry stream will sync here once the SUMO / TraCI bridge is connected. This screen preserves the connection boundary — no fake vehicle rendering."}
        </p>
      </div>

      <div className="mx-auto mt-10 max-w-4xl border border-white/15 bg-white/[0.03] p-5 shadow-2xl shadow-black/20 sm:p-8">
        <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs text-slate-500">Simulation clock</p>
            <p className="mt-1 flex items-center gap-2 font-mono text-sm text-white">
              <Clock3 className="h-4 w-4 text-blue-300" />
              {snapshot.state.currentClock} · {snapshot.state.currentPeriod}
            </p>
          </div>
          <Badge
            variant="outline"
            className={cn(
              "capitalize",
              isConnected
                ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
                : "border-amber-400/25 bg-amber-400/10 text-amber-200"
            )}
          >
            <span
              className={cn(
                "mr-2 h-1.5 w-1.5 rounded-full",
                isConnected ? "bg-emerald-400" : "bg-amber-300"
              )}
            />
            {isConnected ? "Bridge Active (Connected)" : "Awaiting bridge"}
          </Badge>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step} className="relative">
              <div className="flex items-center gap-3">
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border font-mono text-xs",
                    isConnected
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                      : "border-white/10 bg-white/[0.04] text-slate-400"
                  )}
                >
                  {isConnected ? <Check className="h-3.5 w-3.5" /> : index + 1}
                </span>
                <span className="text-xs text-slate-400">{step}</span>
              </div>
              {index < steps.length - 1 && (
                <div className="ml-4 mt-2 hidden h-6 border-l border-dashed border-white/15 sm:block" />
              )}
            </div>
          ))}
        </div>

        <div className="mt-8 border border-blue-300/15 bg-blue-300/[0.04] p-5">
          <div className="flex gap-3">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-300" />
            <div>
              <p className="text-sm font-medium text-white">Connection boundary preserved</p>
              <p className="mt-1 text-sm leading-6 text-slate-400">
                WebSocket provider endpoint: <code className="font-mono text-blue-200">ws://localhost:8765/ws</code>. The frontend UI communicates strictly over the established provider contract.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="border border-white/10 bg-black/20 p-4">
            <Server className="h-4 w-4 text-slate-400" />
            <p className="mt-3 text-xs text-slate-500">Transport</p>
            <p className="mt-1 font-mono text-sm text-white">WebSocket / TraCI</p>
          </div>
          <div className="border border-white/10 bg-black/20 p-4">
            <TerminalSquare className="h-4 w-4 text-slate-400" />
            <p className="mt-3 text-xs text-slate-500">Provider state</p>
            <p className={cn("mt-1 font-mono text-sm", isConnected ? "text-emerald-300" : "text-amber-300")}>
              {snapshot.state.connectionStatus}
            </p>
          </div>
          <div className="border border-white/10 bg-black/20 p-4">
            <Check className="h-4 w-4 text-slate-400" />
            <p className="mt-3 text-xs text-slate-500">Simulation status</p>
            <p className="mt-1 font-mono text-sm text-white">{snapshot.state.simulationStatus}</p>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Button className="bg-white text-black hover:bg-blue-100">
            <ExternalLink className="mr-2 h-4 w-4" />View integration guide
          </Button>
          <Button variant="outline" className="border-white/15 bg-transparent text-slate-300 hover:bg-white/10 hover:text-white">
            Open connection settings
          </Button>
        </div>
      </div>
    </div>
  )
}
