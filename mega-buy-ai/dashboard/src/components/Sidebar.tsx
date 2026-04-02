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
  Wallet
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

function WatchdogWidget() {
  const [services, setServices] = useState<Record<string, any>>({})
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('http://localhost:8002/watchdog')
        if (res.ok) {
          const data = await res.json()
          setServices(data.services || {})
          setConnected(true)
        } else {
          setConnected(false)
        }
      } catch {
        setConnected(false)
      }
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  const allAlive = Object.values(services).every((s: any) => s.alive)
  const downCount = Object.values(services).filter((s: any) => !s.alive).length

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

  return (
    <div className="flex h-full w-64 flex-col bg-gray-900 border-r border-gray-800">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 px-6 border-b border-gray-800">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
          <span className="text-white font-bold text-sm">M</span>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">MEGA BUY</h1>
          <p className="text-xs text-gray-500">AI Trading</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-green-500/10 text-green-500"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Watchdog Status */}
      <WatchdogWidget />
    </div>
  )
}
