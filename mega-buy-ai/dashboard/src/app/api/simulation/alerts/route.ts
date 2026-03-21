import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
)

/**
 * GET /api/simulation/alerts
 *
 * Returns alerts for the Live Simulation system.
 *
 * Query params:
 * - limit: number of alerts to return (default 100)
 * - since: ISO timestamp to get alerts after (optional)
 * - last_id: get alerts after this ID (for polling)
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') || '100')
  const since = searchParams.get('since')
  const lastId = searchParams.get('last_id')

  try {
    // Build query
    let query = supabase
      .from('alerts')
      .select(`
        id,
        pair,
        price,
        alert_timestamp,
        timeframes,
        scanner_score,
        bougie_4h,
        rsi,
        di_plus_4h,
        di_minus_4h,
        adx_4h,
        vol_pct,
        rsi_check,
        dmi_check,
        ast_check,
        choch,
        zone,
        lazy,
        vol,
        st,
        pp,
        ec,
        emotion,
        puissance,
        created_at,
        decisions (
          p_success,
          confidence
        )
      `)
      .order('alert_timestamp', { ascending: false })
      .limit(limit)

    // Filter by timestamp if provided
    if (since) {
      query = query.gt('alert_timestamp', since)
    }

    // Filter by last_id for incremental polling
    if (lastId) {
      query = query.gt('id', lastId)
    }

    const { data: alerts, error } = await query

    if (error) {
      console.error('Error fetching alerts:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    // Transform for simulation consumption
    const transformedAlerts = (alerts || []).map(alert => {
      // Get decision data
      const decision = Array.isArray(alert.decisions)
        ? alert.decisions[0]
        : alert.decisions

      // Get vol_pct from first timeframe
      const volPctMax = alert.vol_pct
        ? Math.max(...Object.values(alert.vol_pct as Record<string, number>))
        : null

      return {
        id: alert.id,
        pair: alert.pair,
        price: alert.price,
        alert_timestamp: alert.alert_timestamp,
        timeframes: alert.timeframes,
        scanner_score: alert.scanner_score,
        bougie_4h: alert.bougie_4h,
        // Indicators for filters
        di_plus_4h: alert.di_plus_4h,
        di_minus_4h: alert.di_minus_4h,
        adx_4h: alert.adx_4h,
        vol_pct_max: volPctMax,
        // Conditions for empirical filters
        pp: alert.pp,
        ec: alert.ec,
        // ML prediction
        p_success: decision?.p_success || null,
        confidence: decision?.confidence || null,
        // Metadata
        created_at: alert.created_at,
      }
    })

    return NextResponse.json({
      success: true,
      count: transformedAlerts.length,
      alerts: transformedAlerts,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('Simulation alerts API error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch alerts' },
      { status: 500 }
    )
  }
}
