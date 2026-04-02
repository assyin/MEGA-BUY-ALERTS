import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const body = await request.json()
  const memoryId = body?.memory_id
  if (!memoryId) {
    return NextResponse.json({ error: 'Missing memory_id' }, { status: 400 })
  }

  try {
    const res = await fetch(`http://localhost:8002/reanalyze/${memoryId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}
