import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const type = request.nextUrl.searchParams.get('type') || ''
  const limit = request.nextUrl.searchParams.get('limit') || '50'
  try {
    const url = `http://localhost:8002/reports?type=${type}&limit=${limit}`
    const res = await fetch(url, { next: { revalidate: 0 } })
    if (!res.ok) return NextResponse.json({ reports: [], total: 0 })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ reports: [], total: 0 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8002/reports/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}
