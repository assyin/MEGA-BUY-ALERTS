"use client"

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
  PlayCircle
} from "lucide-react"
import { cn } from "@/lib/utils"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Alerts", href: "/alerts", icon: Bell },
  { name: "Decisions", href: "/decisions", icon: Brain },
  { name: "Strategies", href: "/strategies", icon: Target },
  { name: "Backtest", href: "/backtest", icon: FlaskConical },
  { name: "Simulation", href: "/simulation", icon: PlayCircle },
  { name: "Performance", href: "/performance", icon: TrendingUp },
  { name: "Live", href: "/live", icon: Activity },
  { name: "Settings", href: "/settings", icon: Settings },
]

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

      {/* Status */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-gray-400">System Online</span>
        </div>
        <p className="text-xs text-gray-600 mt-1">Model v2.0.0</p>
      </div>
    </div>
  )
}
