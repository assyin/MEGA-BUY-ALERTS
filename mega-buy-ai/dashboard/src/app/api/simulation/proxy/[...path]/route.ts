import { NextRequest, NextResponse } from 'next/server'

const SIMULATION_API = process.env.SIMULATION_API_URL || 'http://localhost:8001'

/**
 * Proxy all requests to the simulation API server.
 * This avoids CORS issues when the dashboard is accessed from a remote machine.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const search = request.nextUrl.search
  const url = `${SIMULATION_API}/${path}${search}`

  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Simulation API unreachable', url },
      { status: 502 }
    )
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${SIMULATION_API}/${path}`

  try {
    const body = await request.text()
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body || undefined,
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Simulation API unreachable', url },
      { status: 502 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${SIMULATION_API}/${path}`

  try {
    const body = await request.text()
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body || undefined,
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Simulation API unreachable', url },
      { status: 502 }
    )
  }
}
