import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const alertId = request.nextUrl.searchParams.get('alert_id')
  const pair = request.nextUrl.searchParams.get('pair')

  let url = ''
  if (alertId) {
    url = `http://localhost:8002/chart/${alertId}`
  } else if (pair) {
    url = `http://localhost:8002/charts/${pair.toUpperCase()}`
  } else {
    return NextResponse.json({ error: 'Missing alert_id or pair' }, { status: 400 })
  }

  try {
    const res = await fetch(url, { next: { revalidate: 0 } })
    if (!res.ok) {
      return NextResponse.json({ error: 'Chart not found' }, { status: 404 })
    }

    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('image')) {
      const buffer = await res.arrayBuffer()
      return new NextResponse(buffer, {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    return NextResponse.json({ error: 'Chart not found' }, { status: 404 })
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}
