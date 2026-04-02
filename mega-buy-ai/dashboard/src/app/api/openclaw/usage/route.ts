import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const res = await fetch('http://localhost:8002/usage', { next: { revalidate: 0 } })
    if (!res.ok) return NextResponse.json(null)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json(null)
  }
}
