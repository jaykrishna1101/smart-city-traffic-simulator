"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Activity,
  Code2,
  LayoutDashboard,
  Map,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  Settings2,
  X,
  Zap
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { SimulationProvider, useSimulationData } from "./simulation-context"
import { getConnectionLabel } from "@/lib/simulation/provider"

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Live Simulation", href: "/simulation", icon: Map },
  { label: "Developer Console", href: "/developer", icon: Code2 }
]

function ShellFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [isDark, setIsDark] = useState(true)
  const snapshot = useSimulationData()

  const isConnected = snapshot.state.connectionStatus === "connected"
  const isReconnecting = snapshot.state.connectionStatus === "reconnecting"
  const statusLabel = getConnectionLabel(snapshot.state.connectionStatus)

  return (
    <div
      data-theme={isDark ? "dark" : "light"}
      className="min-h-screen bg-[var(--shell-bg)] text-[var(--shell-fg)] selection:bg-blue-300/30"
      aria-label="SmartFlow operations workspace"
    >
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/10 bg-black transition-all duration-300 lg:translate-x-0",
          collapsed ? "lg:w-[72px]" : "lg:w-[260px]",
          "w-[260px]",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Sidebar Header */}
        <div className={cn("flex h-16 items-center border-b border-white/10 px-4", collapsed ? "lg:justify-center" : "justify-between")}>
          <Link href="/" className="flex items-center gap-3" onClick={() => setMobileOpen(false)}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/10 text-white">
              <Activity className="h-4 w-4 text-blue-300" />
            </span>
            {!collapsed && (
              <span className="font-mono text-sm font-semibold tracking-[0.18em] text-white">
                SMARTFLOW
              </span>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="hidden text-slate-400 hover:bg-white/5 hover:text-white lg:flex"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </Button>

          {/* Mobile Close Button */}
          <Button
            variant="ghost"
            size="icon"
            className="text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto px-3 py-5">
          {!collapsed && (
            <p className="px-3 pb-2 text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">
              Command center
            </p>
          )}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  title={collapsed ? item.label : undefined}
                  className={cn(
                    "flex items-center rounded-md text-sm transition-colors",
                    collapsed ? "justify-center p-2.5" : "gap-3 px-3 py-2.5",
                    active
                      ? "bg-white/10 text-white"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                  {!collapsed && active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-300" />}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Sidebar Footer: System Status */}
        <div className="border-t border-white/10 p-3">
          {collapsed ? (
            <div
              className="flex justify-center py-2"
              title={`Status: ${statusLabel} (${snapshot.state.currentClock})`}
            >
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full",
                  isConnected
                    ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"
                    : isReconnecting
                    ? "bg-amber-300 animate-pulse"
                    : "bg-red-400"
                )}
              />
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2 w-2 rounded-full",
                      isConnected
                        ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]"
                        : isReconnecting
                        ? "bg-amber-300 animate-pulse"
                        : "bg-red-400"
                    )}
                  />
                  <span className="font-mono text-[11px] text-slate-300">{statusLabel}</span>
                </div>
                <span className="font-mono text-[10px] text-slate-500">{snapshot.state.currentClock}</span>
              </div>

              <div className="rounded-md border border-white/10 bg-white/[0.02] p-2.5 text-[11px]">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5 font-medium text-slate-300">
                    <Zap className="h-3 w-3 text-blue-300" />
                    SUMO / TraCI Bridge
                  </span>
                  <span className="font-mono text-[10px] text-emerald-400">v1.27</span>
                </div>
                <p className="mt-1 truncate text-[10px] text-slate-500 font-mono">
                  {snapshot.state.currentPeriod} · LHT Network
                </p>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <div className={cn("transition-all duration-300", collapsed ? "lg:pl-[72px]" : "lg:pl-[260px]")}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-black/90 px-4 backdrop-blur-xl sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="hidden text-slate-400 hover:bg-white/5 hover:text-white lg:flex"
              onClick={() => setCollapsed(!collapsed)}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </Button>
            <div>
              <p className="text-xs text-slate-500">Workspace / SmartFlow</p>
              <p className="text-sm font-medium text-white">
                {pathname === "/dashboard"
                  ? "Live Traffic Command Center"
                  : pathname === "/simulation"
                  ? "SUMO Simulation"
                  : "Developer Console"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 text-xs text-slate-400 sm:flex">
              <Radio
                className={cn(
                  "h-3.5 w-3.5",
                  isConnected ? "text-emerald-400" : isReconnecting ? "text-amber-300" : "text-slate-500"
                )}
              />
              <span className="font-mono">{statusLabel}</span>
              <span className="text-slate-600">·</span>
              <span className="font-mono text-white">{snapshot.state.currentClock}</span>
            </span>
            {/* Light / Dark mode toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsDark(!isDark)}
              className="text-slate-400 hover:bg-white/5 hover:text-white"
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-slate-400 hover:bg-white/5 hover:text-white"
              aria-label="Settings"
            >
              <Settings2 className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <main>{children}</main>
      </div>
    </div>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SimulationProvider>
      <ShellFrame>{children}</ShellFrame>
    </SimulationProvider>
  )
}
