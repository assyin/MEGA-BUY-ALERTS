import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const path = request.nextUrl.searchParams.get('path') || ''
  try {
    const url = path ? `http://localhost:8002/portfolio/${path}` : 'http://localhost:8002/portfolio'
    const res = await fetch(url, { next: { revalidate: 0 } })
    if (!res.ok) return NextResponse.json({ error: 'Failed' }, { status: res.status })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}))
  const positionId = body?.position_id
  const action = body?.action

  if (action === 'close' && positionId) {
    try {
      const res = await fetch(`http://localhost:8002/portfolio/close/${positionId}`, { method: 'POST' })
      return NextResponse.json(await res.json())
    } catch {
      return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
    }
  }
  if (action === 'check') {
    try {
      const res = await fetch('http://localhost:8002/portfolio/check', { method: 'POST' })
      return NextResponse.json(await res.json())
    } catch {
      return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
    }
  }
  return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
}
