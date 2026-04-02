import { NextRequest, NextResponse } from 'next/server'

const OPENCLAW_URL = 'http://localhost:8002'

export async function GET(request: NextRequest) {
  const pending = request.nextUrl.searchParams.get('pending')

  try {
    const url = pending === 'true'
      ? `${OPENCLAW_URL}/engagements/pending`
      : `${OPENCLAW_URL}/engagements`

    const res = await fetch(url, { next: { revalidate: 0 } })
    if (!res.ok) return NextResponse.json({ error: 'Failed' }, { status: res.status })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}

export async function POST() {
  try {
    const res = await fetch(`${OPENCLAW_URL}/engagements/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}
