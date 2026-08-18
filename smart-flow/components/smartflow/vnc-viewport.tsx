"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import {
  ExternalLink,
  KeyRound,
  Maximize2,
  Minimize2,
  RotateCw,
  Tv,
  Terminal,
  Scaling
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type VncStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "RECONNECTING"
type ScaleMode = "fit" | "fill" | "original"

interface VncViewportProps {
  wsUrl?: string
  className?: string
}

export function VncViewport({ wsUrl, className }: VncViewportProps) {
  const rawUrl =
    wsUrl ||
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_VNC_WS_URL) ||
    "ws://127.0.0.1:6080"

  // Prefer 127.0.0.1 on Windows to prevent IPv6 localhost connection hangs
  const targetWsUrl = rawUrl.includes("localhost")
    ? rawUrl.replace("localhost", "127.0.0.1")
    : rawUrl

  const containerRef = useRef<HTMLDivElement>(null)
  const screenRef = useRef<HTMLDivElement>(null)
  const rfbRef = useRef<any>(null)

  const [status, setStatus] = useState<VncStatus>("CONNECTING")
  const [desktopName, setDesktopName] = useState<string>("")
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string>("")
  const [isPasswordRequired, setIsPasswordRequired] = useState<boolean>(false)
  const [vncPassword, setVncPassword] = useState<string>("")
  const [authError, setAuthError] = useState<string>("")
  const [scaleMode, setScaleMode] = useState<ScaleMode>("fit")

  const disconnectRfb = useCallback(() => {
    if (rfbRef.current) {
      try {
        rfbRef.current.removeEventListener("connect", onConnect)
        rfbRef.current.removeEventListener("disconnect", onDisconnect)
        rfbRef.current.removeEventListener("securityfailure", onSecurityFailure)
        rfbRef.current.removeEventListener("credentialsrequired", onCredentialsRequired)
        rfbRef.current.removeEventListener("desktopname", onDesktopName)
        if (rfbRef.current._rfbConnectionState && rfbRef.current._rfbConnectionState !== "disconnected") {
          rfbRef.current.disconnect()
        }
      } catch {
        // ignore disconnect errors
      }
      rfbRef.current = null
    }
  }, [])

  const onConnect = () => {
    setStatus("CONNECTED")
    setErrorMessage("")
    setIsPasswordRequired(false)
    setAuthError("")
  }

  const onDisconnect = (e: any) => {
    setStatus("DISCONNECTED")
    if (e?.detail?.clean) {
      setErrorMessage("VNC session closed cleanly.")
    } else {
      setErrorMessage("WebSocket bridge disconnected or unreachable.")
    }
  }

  const onSecurityFailure = (e: any) => {
    setStatus("DISCONNECTED")
    const reason = e?.detail?.reason || "Security negotiation failed."
    setErrorMessage(reason)
    if (reason.toLowerCase().includes("auth") || reason.toLowerCase().includes("password")) {
      setAuthError("Invalid password. Please re-enter your TightVNC password.")
      setIsPasswordRequired(true)
    }
  }

  const onCredentialsRequired = () => {
    setIsPasswordRequired(true)
    setAuthError("")
  }

  const onDesktopName = (e: any) => {
    if (e?.detail?.name) {
      setDesktopName(e.detail.name)
    }
  }

  const handlePasswordSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (rfbRef.current && isPasswordRequired) {
      try {
        rfbRef.current.sendCredentials({ password: vncPassword })
      } catch (err) {
        console.warn("[SmartFlow noVNC] Error sending credentials:", err)
      }
    }
  }

  const connectRfb = useCallback(async () => {
    if (typeof window === "undefined" || !screenRef.current) return

    disconnectRfb()
    setStatus("CONNECTING")
    setErrorMessage("")
    setIsPasswordRequired(false)
    setAuthError("")

    if (screenRef.current) {
      screenRef.current.innerHTML = ""
    }

    try {
      const RFBModule = await import("@novnc/novnc")
      const RFB = RFBModule.default || RFBModule

      console.log(`[SmartFlow noVNC] Connecting to ${targetWsUrl}...`)
      const rfb = new (RFB as any)(screenRef.current, targetWsUrl, {
        shared: true,
        wsProtocols: ["binary"]
      })

      rfb.scaleViewport = true
      rfb.resizeSession = false
      rfb.focusOnClick = true
      rfb.qualityLevel = 8
      rfb.compressionLevel = 2
      rfb.viewOnly = false

      rfb.addEventListener("connect", onConnect)
      rfb.addEventListener("disconnect", onDisconnect)
      rfb.addEventListener("securityfailure", onSecurityFailure)
      rfb.addEventListener("credentialsrequired", onCredentialsRequired)
      rfb.addEventListener("desktopname", onDesktopName)

      rfbRef.current = rfb
    } catch (err: any) {
      console.warn("[SmartFlow noVNC] Connection failed:", err)
      setStatus("DISCONNECTED")
      setErrorMessage(err?.message || "Failed to initialize noVNC client.")
    }
  }, [targetWsUrl, disconnectRfb])

  useEffect(() => {
    connectRfb()
    return () => {
      disconnectRfb()
    }
  }, [connectRfb, disconnectRfb])

  const handleReconnect = () => {
    setStatus("RECONNECTING")
    connectRfb()
  }

  const toggleFullscreen = () => {
    if (!containerRef.current) return

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => {
        setIsFullscreen(true)
      }).catch((err) => {
        console.warn("Fullscreen request failed:", err)
      })
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false)
      }).catch((err) => {
        console.warn("Exit fullscreen failed:", err)
      })
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener("fullscreenchange", handleFullscreenChange)
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange)
  }, [])

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative flex flex-col rounded-xl border border-white/10 bg-slate-950 overflow-hidden shadow-2xl transition-all duration-300",
        isFullscreen ? "fixed inset-0 z-50 rounded-none border-none" : "min-h-[560px] lg:min-h-[620px]",
        className
      )}
    >
      {/* Viewport Header */}
      <div className="flex h-11 items-center justify-between border-b border-white/10 bg-slate-900/90 px-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-2 w-2 rounded-full",
                status === "CONNECTED"
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse"
                  : status === "CONNECTING" || status === "RECONNECTING"
                  ? "bg-amber-300 animate-pulse"
                  : "bg-red-400"
              )}
            />
            <span className="font-mono text-xs font-medium text-slate-200">
              SUMO-GUI Viewport
            </span>
          </div>

          <span
            className={cn(
              "rounded px-2 py-0.5 font-mono text-[10px] font-semibold",
              status === "CONNECTED"
                ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                : status === "CONNECTING" || status === "RECONNECTING"
                ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                : "bg-red-500/10 text-red-300 border border-red-500/20"
            )}
          >
            {isPasswordRequired ? "PASSWORD REQUIRED" : status}
          </span>
        </div>

        {/* Viewport Toolbar (Scale, Reconnect, Fullscreen) */}
        <div className="flex items-center gap-1.5">
          {/* Scale Mode Toggle */}
          {status === "CONNECTED" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setScaleMode(scaleMode === "fit" ? "fill" : "fit")}
              className="h-7 gap-1 px-2 text-[11px] font-mono text-slate-400 hover:bg-white/10 hover:text-white"
              title={scaleMode === "fit" ? "Switch to Fill Window" : "Switch to Fit Aspect"}
            >
              <Scaling className="h-3.5 w-3.5" />
              <span className="hidden sm:inline uppercase">{scaleMode}</span>
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleReconnect}
            className="h-7 gap-1.5 px-2 text-xs text-slate-400 hover:bg-white/10 hover:text-white"
            title="Reconnect VNC stream"
          >
            <RotateCw className={cn("h-3.5 w-3.5", status === "RECONNECTING" && "animate-spin")} />
            <span className="hidden sm:inline">Reconnect</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={toggleFullscreen}
            className="h-7 gap-1.5 px-2 text-xs text-slate-400 hover:bg-white/10 hover:text-white"
            title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>

      {/* Viewport Display Area */}
      <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
        {/* Full-Box noVNC Canvas Container */}
        <div
          className={cn(
            "w-full h-full flex items-center justify-center overflow-auto focus:outline-none",
            scaleMode === "fill" ? "novnc-fill" : "novnc-fit"
          )}
        >
          <div
            ref={screenRef}
            tabIndex={0}
            className="w-full h-full flex items-center justify-center focus:outline-none [&_canvas]:w-full [&_canvas]:h-full [&_canvas]:max-w-full [&_canvas]:max-h-full [&_canvas]:object-contain [&_div]:w-full [&_div]:h-full [&_div]:flex [&_div]:items-center [&_div]:justify-center"
          />
        </div>

        {/* Password Prompt Overlay */}
        {isPasswordRequired && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/90 p-6 backdrop-blur-md">
            <div className="w-full max-w-sm rounded-xl border border-white/10 bg-slate-900/90 p-6 shadow-2xl space-y-4 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <KeyRound className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">VNC Password Required</h3>
                <p className="text-xs text-slate-400 mt-1">
                  The VNC server requires authentication. The custom sumo_window_vnc.py server uses no-auth (Security Type 1).
                </p>
              </div>

              {authError && (
                <p className="text-xs text-rose-400 font-mono bg-rose-500/10 border border-rose-500/20 rounded p-2">
                  {authError}
                </p>
              )}

              <form onSubmit={handlePasswordSubmit} className="space-y-3">
                <input
                  type="password"
                  value={vncPassword}
                  onChange={(e) => setVncPassword(e.target.value)}
                  placeholder="Enter TightVNC Password"
                  autoFocus
                  className="w-full rounded-md border border-white/10 bg-black/60 px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    className="w-full bg-blue-600 text-xs text-white hover:bg-blue-500 font-mono"
                  >
                    Authenticate
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleReconnect}
                    className="border-white/10 bg-white/5 text-xs text-slate-300 hover:bg-white/10"
                  >
                    Retry
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Fallback Screen (Shown when disconnected and password prompt is not active) */}
        {status !== "CONNECTED" && !isPasswordRequired && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/85 p-6 text-center max-w-lg mx-auto space-y-4 pointer-events-auto backdrop-blur-sm">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-500/10 text-blue-300 shadow-xl">
              <Tv className="h-8 w-8" />
            </div>

            <div>
              <h3 className="text-base font-semibold text-white">
                {status === "CONNECTING" || status === "RECONNECTING"
                  ? "Connecting to SUMO-GUI Stream..."
                  : "SUMO-GUI streaming unavailable"}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {status === "CONNECTING" || status === "RECONNECTING"
                  ? `Establishing connection to ${targetWsUrl}...`
                  : "Start the VNC server and WebSocket bridge to reconnect."}
              </p>
            </div>

            {errorMessage && (
              <div className="w-full rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 font-mono text-left space-y-1">
                <p className="font-semibold text-[11px] uppercase tracking-wider text-amber-400">
                  VNC Server Response:
                </p>
                <p className="text-slate-200">{errorMessage}</p>
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <Button
                variant="default"
                size="sm"
                onClick={handleReconnect}
                className="bg-blue-600 text-xs text-white hover:bg-blue-500 font-mono"
              >
                <RotateCw className="mr-1.5 h-3.5 w-3.5" />
                Reconnect VNC Stream
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Viewport Footer */}
      <div className="flex h-8 items-center justify-between border-t border-white/10 bg-slate-900/60 px-4 text-[11px] text-slate-400">
        <span className="font-mono">
          {status === "CONNECTED"
            ? "SUMO-GUI · Interactive window stream · Full mouse & keyboard"
            : `Endpoint: ${targetWsUrl}`}
        </span>
        <span className="hidden font-mono text-slate-500 sm:inline">
          noVNC Core v1.7.0 · Full Box Scale
        </span>
      </div>
    </div>
  )
}
