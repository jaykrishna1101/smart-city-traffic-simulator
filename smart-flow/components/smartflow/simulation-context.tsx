"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { simulationProvider } from "@/lib/simulation/provider"
import type { SimulationControls, SimulationSnapshot } from "@/lib/simulation/types"

interface SimulationContextValue {
  snapshot: SimulationSnapshot
  controls: SimulationControls
  pause: () => void
  resume: () => void
  step: () => void
}

const SimulationContext = createContext<SimulationContextValue | null>(null)

export function SimulationProvider({ children }: { children: React.ReactNode }) {
  const [snapshot, setSnapshot] = useState<SimulationSnapshot | null>(null)

  useEffect(() => simulationProvider.subscribe(setSnapshot), [])

  const controls = useMemo<SimulationControls>(
    () => ({
      pause: () => simulationProvider.pause(),
      resume: () => simulationProvider.resume(),
      step: () => simulationProvider.step(),
      setSpeed: (speed: number) => simulationProvider.setSpeed(speed),
      setDelay: (delaySec: number) => simulationProvider.setDelay(delaySec),
      trackVehicle: (vehicleId: string) => simulationProvider.trackVehicle(vehicleId),
      setZoom: (zoomLevel: number) => simulationProvider.setZoom(zoomLevel),
      centerIntersection: (intersectionId: string) => simulationProvider.centerIntersection(intersectionId),
      sendCommand: (command: string, params?: Record<string, any>) => simulationProvider.sendCommand(command, params)
    }),
    []
  )

  if (!snapshot) {
    return (
      <div className="min-h-screen bg-black px-6 py-24">
        <div className="mx-auto max-w-5xl space-y-4">
          <div className="h-3 w-28 animate-pulse bg-white/10" />
          <div className="h-12 w-2/3 animate-pulse bg-white/10" />
          <div className="h-32 animate-pulse border border-white/10 bg-white/[0.03]" />
        </div>
      </div>
    )
  }

  return (
    <SimulationContext.Provider
      value={{
        snapshot,
        controls,
        pause: controls.pause,
        resume: controls.resume,
        step: controls.step
      }}
    >
      {children}
    </SimulationContext.Provider>
  )
}

export function useSimulationData() {
  const context = useContext(SimulationContext)
  if (!context) throw new Error("useSimulationData must be used inside SimulationProvider")
  return useMemo(() => context.snapshot, [context.snapshot])
}

export function useSimulationControls(): SimulationControls {
  const context = useContext(SimulationContext)
  if (!context) throw new Error("useSimulationControls must be used inside SimulationProvider")
  return context.controls
}
