import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A"
  return `${(value * 100).toFixed(1)}%`
}

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A"
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  })
}

export function getDecisionColor(decision: string): string {
  switch (decision) {
    case "TRADE":
      return "text-green-500"
    case "WATCH":
      return "text-yellow-500"
    case "SKIP":
      return "text-red-500"
    default:
      return "text-gray-500"
  }
}

export function getDecisionBgColor(decision: string): string {
  switch (decision) {
    case "TRADE":
      return "bg-green-500/10 border-green-500/20"
    case "WATCH":
      return "bg-yellow-500/10 border-yellow-500/20"
    case "SKIP":
      return "bg-red-500/10 border-red-500/20"
    default:
      return "bg-gray-500/10 border-gray-500/20"
  }
}

export function getScoreColor(score: number): string {
  if (score >= 8) return "text-green-500"
  if (score >= 6) return "text-yellow-500"
  return "text-red-500"
}
