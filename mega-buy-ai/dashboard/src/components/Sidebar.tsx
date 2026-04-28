"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Bell,
  Brain,
  TrendingUp,
  Settings,
  Activity,
  Target,
  FlaskConical,
  PlayCircle,
  MessageSquare,
  Wallet,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Alerts", href: "/alerts", icon: Bell },
  { name: "OpenClaw", href: "/openclaw", icon: Brain },
  { name: "Portfolio", href: "/portfolio", icon: Wallet },
  { name: "Decisions", href: "/decisions", icon: Brain },
  { name: "Strategies", href: "/strategies", icon: Target },
  { name: "Backtest", href: "/backtest", icon: FlaskConical },
  { name: "Simulation", href: "/simulation", icon: PlayCircle },
  { name: "Chat AI", href: "/chat", icon: MessageSquare },
  { name: "Performance", href: "/performance", icon: TrendingUp },
  { name: "Live", href: "/live", icon: Activity },
  { name: "Settings", href: "/settings", icon: Settings },
]

function WatchdogWidget({ collapsed }: { collapsed: boolean }) {
  const [services, setServices] = useState<Record<string, any>>({})
  const [connected, setConnected] = useState(false)
  const failCountRef = useState({ current: 0 })[0]

  useEffect(() => {
    const safeFetchJson = async (url: string, timeoutMs: number): Promise<any> => {
      return new Promise(resolve => {
        let done = false
        const finish = (v: any) => { if (!done) { done = true; resolve(v) } }
        const timer = setTimeout(() => finish(null), timeoutMs)
        try {
          fetch(url)
            .then(r => r.ok ? r.json() : null)
            .then(v => { clearTimeout(timer); finish(v) })
            .catch(() => { clearTimeout(timer); finish(null) })
        } catch {
          clearTimeout(timer); finish(null)
        }
      })
    }

    const load = async () => {
      // Go through Next.js API proxy to avoid browser-level CORS/network errors.
      // Very tolerant: health proxy has its own 4s timeout, we give 12s here for event-loop hiccups.
      const health = await safeFetchJson('/api/openclaw/health', 12000)
      if (health && health.ok) {
        setConnected(true)
        failCountRef.current = 0
        const wd = await safeFetchJson('/api/openclaw/watchdog', 16000)
        if (wd && wd.services) setServices(wd.services)
      } else {
        failCountRef.current += 1
        if (failCountRef.current >= 3) setConnected(false)
      }
    }

    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [])

  const allAlive = Object.values(services).every((s: any) => s.alive)
  const downCount = Object.values(services).filter((s: any) => !s.alive).length

  if (collapsed) {
    return (
      <div className="p-2 border-t border-gray-800 flex justify-center">
        <div className={`w-2.5 h-2.5 rounded-full ${!connected ? 'bg-red-500' : allAlive ? 'bg-green-500 animate-pulse' : 'bg-red-500 animate-pulse'}`}
          title={!connected ? 'OpenClaw Offline' : allAlive ? 'All Online' : `${downCount} down`} />
      </div>
    )
  }

  return (
    <div className="p-3 border-t border-gray-800">
      {!connected ? (
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-red-400">OpenClaw Offline</span>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${allAlive ? 'bg-green-500 animate-pulse' : 'bg-red-500 animate-pulse'}`} />
              <span className={`text-xs font-medium ${allAlive ? 'text-green-400' : 'text-red-400'}`}>
                {allAlive ? 'All Systems Online' : `${downCount} service${downCount > 1 ? 's' : ''} down`}
              </span>
            </div>
            <span className="text-[10px] text-gray-600">🐕 Watchdog</span>
          </div>
          <div className="space-y-0.5">
            {Object.entries(services).map(([id, svc]: [string, any]) => (
              <div key={id} className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${svc.alive ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className={`text-[11px] ${svc.alive ? 'text-gray-500' : 'text-red-400 font-medium'}`}>
                    {svc.name}
                  </span>
                </div>
                {svc.port && (
                  <span className="text-[10px] text-gray-700">:{svc.port}</span>
                )}
                {svc.restarts > 0 && (
                  <span className="text-[10px] text-yellow-500">{svc.restarts}x</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  // Persist state
  useEffect(() => {
    const saved = localStorage.getItem('sidebar_collapsed')
    if (saved === 'true') setCollapsed(true)
  }, [])

  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem('sidebar_collapsed', String(next))
  }

  return (
    <div className={cn(
      "flex h-full flex-col bg-gray-900 border-r border-gray-800 transition-all duration-200",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* Logo + Toggle */}
      <div className="flex h-16 items-center justify-between px-3 border-b border-gray-800">
        {!collapsed ? (
          <div className="flex items-center gap-2 px-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">M</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">MEGA BUY</h1>
              <p className="text-xs text-gray-500">AI Trading</p>
            </div>
          </div>
        ) : (
          <div className="w-10 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center mx-auto">
            <span className="text-white font-bold text-sm">M</span>
          </div>
        )}
        <button onClick={toggle} className="p-1.5 rounded-lg text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          title={collapsed ? "Ouvrir le menu" : "Fermer le menu"}>
          {collapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              title={collapsed ? item.name : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg text-sm font-medium transition-colors",
                collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2",
                isActive
                  ? "bg-green-500/10 text-green-500"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && item.name}
            </Link>
          )
        })}
      </nav>

      {/* Watchdog Status */}
      <WatchdogWidget collapsed={collapsed} />
    </div>
  )
}
