import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 15000)
    const res = await fetch('http://localhost:8002/watchdog', {
      next: { revalidate: 0 },
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) return NextResponse.json(null)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json(null)
  }
}
