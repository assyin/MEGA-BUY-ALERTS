import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
)

// Stratégies disponibles
const STRATEGIES = {
  aggressive: {
    id: 'aggressive',
    name: 'Aggressive',
    description: 'Prend plus de trades, accepte plus de risque',
    thresholds: { trade: 0.30, watch: 0.15 },
    expected_precision: '~30%',
    expected_trades: '~90% des alertes',
    color: 'red'
  },
  balanced: {
    id: 'balanced',
    name: 'Balanced',
    description: 'Équilibre entre opportunités et précision (défaut)',
    thresholds: { trade: 0.50, watch: 0.35 },
    expected_precision: '~50%',
    expected_trades: '~55% des alertes',
    color: 'blue'
  },
  selective: {
    id: 'selective',
    name: 'Selective',
    description: 'Très sélectif, haute précision, moins de trades',
    thresholds: { trade: 0.60, watch: 0.45 },
    expected_precision: '~65%',
    expected_trades: '~25% des alertes',
    color: 'green'
  },
  conservative: {
    id: 'conservative',
    name: 'Conservative',
    description: 'Ultra sélectif, seulement les meilleures opportunités',
    thresholds: { trade: 0.70, watch: 0.55 },
    expected_precision: '~75%',
    expected_trades: '~10% des alertes',
    color: 'purple'
  }
}

type StrategyKey = keyof typeof STRATEGIES

function applyStrategy(pSuccess: number, strategyId: StrategyKey): string {
  const strategy = STRATEGIES[strategyId]
  if (pSuccess >= strategy.thresholds.trade) return 'TRADE'
  if (pSuccess >= strategy.thresholds.watch) return 'WATCH'
  return 'SKIP'
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const strategyId = (searchParams.get('strategy') || 'balanced') as StrategyKey
  const page = parseInt(searchParams.get('page') || '1')
  const limit = parseInt(searchParams.get('limit') || '50')
  const statsOnly = searchParams.get('statsOnly') === 'true'

  try {
    // Get total count first
    const { count: totalCount } = await supabase
      .from('decisions')
      .select('*', { count: 'exact', head: true })

    // For stats calculation, fetch minimal data (just p_success and outcomes)
    const statsQuery = `
        p_success,
        alerts (
          outcomes (max_profit_pct)
        )
      `

    // Fetch stats data in batches (lighter query)
    const statsDecisions: any[] = []
    let statsOffset = 0
    const batchSize = 1000
    let hasMore = true

    while (hasMore) {
      const { data: batch, error } = await supabase
        .from('decisions')
        .select(statsQuery)
        .range(statsOffset, statsOffset + batchSize - 1)

      if (error) throw error

      if (batch && batch.length > 0) {
        statsDecisions.push(...batch)
        statsOffset += batchSize
        hasMore = batch.length === batchSize
      } else {
        hasMore = false
      }
    }

    // Full query for paginated alerts
    const selectQuery = `
        p_success,
        confidence,
        alerts (
          id,
          pair,
          timeframes,
          scanner_score,
          price,
          alert_timestamp,
          bougie_4h,
          rsi,
          di_plus_4h,
          di_minus_4h,
          adx_4h,
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
          vol_pct,
          rsi_moves,
          emotion,
          puissance,
          dmi_cross_4h,
          range_4h,
          body_4h,
          lazy_4h,
          lazy_values,
          lazy_moves,
          nb_timeframes,
          ec_moves,
          outcomes (max_profit_pct, max_drawdown_pct)
        )
      `

    // Fetch only current page of full data
    const offset = (page - 1) * limit
    const { data: pageDecisions, error: pageError } = await supabase
      .from('decisions')
      .select(selectQuery)
      .range(offset, offset + limit - 1)

    if (pageError) throw pageError

    const decisions = pageDecisions || []

    // Type helper to handle Supabase nested relations
    const getMaxProfit = (d: any): number => {
      const alerts = d.alerts
      if (!alerts) return 0
      // Handle both array and object cases
      const alert = Array.isArray(alerts) ? alerts[0] : alerts
      if (!alert) return 0
      const outcomes = alert.outcomes
      if (!outcomes) return 0
      const outcome = Array.isArray(outcomes) ? outcomes[0] : outcomes
      return outcome?.max_profit_pct || 0
    }

    const getAlert = (d: any): any => {
      const alerts = d.alerts
      if (!alerts) return null
      return Array.isArray(alerts) ? alerts[0] : alerts
    }

    // Calculate stats for each strategy using lightweight stats data
    const strategyStats: Record<string, { trade: number; watch: number; skip: number; tradeSuccess: number; precision: number }> = {}

    for (const [key, strategy] of Object.entries(STRATEGIES)) {
      const stats = { trade: 0, watch: 0, skip: 0, tradeSuccess: 0, precision: 0 }

      for (const d of statsDecisions || []) {
        const pSuccess = (d as any).p_success || 0
        const decision = applyStrategy(pSuccess, key as StrategyKey)
        const maxProfit = getMaxProfit(d)
        const isSuccess = maxProfit >= 5

        if (decision === 'TRADE') {
          stats.trade++
          if (isSuccess) stats.tradeSuccess++
        } else if (decision === 'WATCH') {
          stats.watch++
        } else {
          stats.skip++
        }
      }

      stats.precision = stats.trade > 0 ? (stats.tradeSuccess / stats.trade) * 100 : 0
      strategyStats[key] = stats
    }

    // If statsOnly, return early without full alerts
    if (statsOnly) {
      return NextResponse.json({
        strategies: Object.values(STRATEGIES),
        current_strategy: strategyId,
        stats: strategyStats,
        alerts: [],
        pagination: {
          page,
          limit,
          total: totalCount || 0,
          totalPages: Math.ceil((totalCount || 0) / limit)
        }
      })
    }

    // Helper to get max drawdown
    const getMaxDrawdown = (d: any): number => {
      const alert = getAlert(d)
      if (!alert) return 0
      const outcomes = alert.outcomes
      if (!outcomes) return 0
      const outcome = Array.isArray(outcomes) ? outcomes[0] : outcomes
      return outcome?.max_drawdown_pct || 0
    }

    // Get alerts recalculated with selected strategy
    const alertsWithStrategy = (decisions || []).map(d => {
      const pSuccess = (d as any).p_success || 0
      const confidence = (d as any).confidence || 0
      const decision = applyStrategy(pSuccess, strategyId)
      const alert = getAlert(d)
      const maxProfit = getMaxProfit(d)
      const maxDrawdown = getMaxDrawdown(d)

      // Get vol_pct from first timeframe
      const volPct = alert?.vol_pct ? Object.values(alert.vol_pct)[0] : null
      const rsiMove = alert?.rsi_moves ? Object.values(alert.rsi_moves)[0] : null

      return {
        id: alert?.id,
        pair: alert?.pair,
        timeframes: alert?.timeframes,
        alert_timestamp: alert?.alert_timestamp,
        bougie_4h: alert?.bougie_4h,
        score: alert?.scanner_score,
        price: alert?.price,
        // Indicators
        rsi: alert?.rsi,
        di_plus_4h: alert?.di_plus_4h,
        di_minus_4h: alert?.di_minus_4h,
        adx_4h: alert?.adx_4h,
        vol_pct: volPct,
        rsi_move: rsiMove,
        // Checks (score components)
        rsi_check: alert?.rsi_check,
        dmi_check: alert?.dmi_check,
        ast_check: alert?.ast_check,
        choch: alert?.choch,
        zone: alert?.zone,
        lazy: alert?.lazy,
        vol: alert?.vol,
        st: alert?.st,
        pp: alert?.pp,
        ec: alert?.ec,
        // New metrics
        emotion: alert?.emotion,
        puissance: alert?.puissance,
        dmi_cross_4h: alert?.dmi_cross_4h,
        range_4h: alert?.range_4h,
        body_4h: alert?.body_4h,
        lazy_4h: alert?.lazy_4h,
        lazy_values: alert?.lazy_values,
        lazy_moves: alert?.lazy_moves,
        nb_timeframes: alert?.nb_timeframes,
        ec_moves: alert?.ec_moves,
        // ML Decision
        p_success: pSuccess,
        confidence: confidence,
        decision,
        // Outcomes
        max_profit_pct: maxProfit,
        max_drawdown_pct: maxDrawdown,
        is_success: maxProfit >= 5
      }
    })

    return NextResponse.json({
      strategies: Object.values(STRATEGIES),
      current_strategy: strategyId,
      stats: strategyStats,
      alerts: alertsWithStrategy,
      pagination: {
        page,
        limit,
        total: totalCount || 0,
        totalPages: Math.ceil((totalCount || 0) / limit)
      }
    })

  } catch (error) {
    console.error('Strategy API error:', error)
    return NextResponse.json({ error: 'Failed to load strategies' }, { status: 500 })
  }
}
