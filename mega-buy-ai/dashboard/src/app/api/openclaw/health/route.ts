import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 10000)
    const res = await fetch('http://localhost:8002/health', {
      next: { revalidate: 0 },
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) return NextResponse.json({ ok: false })
    const data = await res.json()
    return NextResponse.json({ ok: data?.status === 'ok' })
  } catch {
    return NextResponse.json({ ok: false })
  }
}
