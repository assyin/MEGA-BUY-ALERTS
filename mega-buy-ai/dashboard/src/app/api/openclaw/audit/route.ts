import { NextRequest, NextResponse } from 'next/server'

const OPENCLAW_URL = 'http://localhost:8002'

export async function GET(request: NextRequest) {
  const auditId = request.nextUrl.searchParams.get('id')

  try {
    let url: string
    if (auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}`
    } else {
      url = `${OPENCLAW_URL}/audit/list`
    }

    const res = await fetch(url, { next: { revalidate: 0 } })
    if (!res.ok) return NextResponse.json({ error: 'Failed' }, { status: res.status })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}))
  const action = body?.action
  const auditId = body?.audit_id

  try {
    let url: string
    let method = 'POST'
    if (action === 'start') {
      url = `${OPENCLAW_URL}/audit/start`
    } else if (action === 'confirm' && auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}/confirm`
    } else if (action === 'apply' && auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}/apply`
    } else if (action === 'delete' && auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}`
      method = 'DELETE'
    } else if (action === 'rename' && auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}`
      method = 'PATCH'
    } else if (action === 'rollback' && auditId) {
      url = `${OPENCLAW_URL}/audit/${auditId}/rollback`
    } else {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
    }

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: method !== 'DELETE' ? JSON.stringify(body) : undefined,
    })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'OpenClaw unreachable' }, { status: 502 })
  }
}
