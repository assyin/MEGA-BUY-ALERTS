'use client'

import { useState, useEffect } from 'react'
import { X, CheckCircle, XCircle, Loader2, TrendingUp, Activity, Shield, BarChart3, Zap, Copy, Check, Code } from 'lucide-react'
import type { Alert, Decision } from '@/types/database'

interface AlertWithDecision extends Alert {
  decisions?: Decision[]
}

interface AnalysisData {
  pair: string
  timing: { total_seconds: number }
  entry_conditions: Record<string, any>
  prerequisites: Record<string, any>
  bonus_filters: Record<string, any>
  indicators: Record<string, Record<string, number | null>>
  volume_profile: Record<string, any>
}

interface Props {
  alert: AlertWithDecision
  onClose: () => void
}

function ConditionBadge({ valid, label, value }: { valid: boolean; label: string; value?: string | number | null }) {
  return (
    <div className={`flex items-center justify-between p-2 rounded-lg ${
      valid ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'
    }`}>
      <div className="flex items-center gap-2">
        {valid ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
        <span className={`text-sm font-medium ${valid ? 'text-green-400' : 'text-red-400'}`}>{label}</span>
      </div>
      {value !== undefined && value !== null && (
        <span className="text-xs text-gray-400 font-mono">
          {typeof value === 'number' ? (value < 1 ? value.toFixed(6) : value.toFixed(4)) : value}
        </span>
      )}
    </div>
  )
}

function BonusBadge({ bonus, label, detail }: { bonus: boolean; label: string; detail?: string }) {
  return (
    <div className={`px-2 py-1.5 rounded text-xs font-medium text-center ${
      bonus ? 'bg-green-500/15 text-green-400 border border-green-500/20' : 'bg-gray-700/50 text-gray-500 border border-gray-700'
    }`}>
      <div>{label}</div>
      {detail && <div className="text-[10px] opacity-70 mt-0.5">{detail}</div>}
    </div>
  )
}

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50">
      <div className="px-4 py-2.5 border-b border-gray-700/50 flex items-center gap-2">
        <Icon className="w-4 h-4 text-blue-400" />
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function formatPrice(p: number | null | undefined) {
  if (p == null) return '-'
  if (p >= 100) return p.toFixed(2)
  if (p >= 1) return p.toFixed(4)
  return p.toFixed(6)
}

function generateAlertPineScript(pair: string, alertTs: string, analysis: AnalysisData | null): string {
  const lines = [
    '//@version=5',
    `indicator("MEGA BUY Alert Analysis - ${pair}", overlay=true)`,
    '',
    '// ══════════════════════════════════════════════════════════════════════════════',
    `// MEGA BUY AI - Alert Analysis`,
    `// Symbol: ${pair}`,
    `// Alert: ${alertTs ? new Date(alertTs).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'} UTC`,
    `// Mode: ${analysis?.mode || 'N/A'}`,
    '// ══════════════════════════════════════════════════════════════════════════════',
    '',
  ]

  if (!analysis) return lines.join('\n')

  const bf = analysis.bonus_filters || {}
  const vp = analysis.volume_profile || {}
  const ec = analysis.entry_conditions || {}
  const ind = analysis.indicators || {}
  const price1h = ind['1h']?.price || 0

  const prereqs = analysis.prerequisites || {}

  // ==================== TRENDLINE ====================
  const tl = prereqs.trendline
  if (tl?.valid && tl.p1_time && tl.p2_time) {
    lines.push('// ═══════════════════ TRENDLINE (4H) ═══════════════════')
    lines.push(`// P1: ${tl.p1_date || 'N/A'} @ ${tl.p1_price}`)
    lines.push(`// P2: ${tl.p2_date || 'N/A'} @ ${tl.p2_price}`)
    lines.push(`tl_p1_time = ${tl.p1_time}`)
    lines.push(`tl_p1_price = ${tl.p1_price}`)
    lines.push(`tl_p2_time = ${tl.p2_time}`)
    lines.push(`tl_p2_price = ${tl.p2_price}`)
    lines.push('')
  }

  // ==================== ENTRY CONDITIONS LEVELS ====================
  lines.push('// ═══════════════════ ENTRY CONDITIONS LEVELS ═══════════════════')
  if (ec.ema100_1h?.value) lines.push(`ema100_1h = ${ec.ema100_1h.value}`)
  if (ec.ema20_4h?.value) lines.push(`ema20_4h = ${ec.ema20_4h.value}`)
  if (ec.cloud_1h?.value) lines.push(`cloud_1h = ${ec.cloud_1h.value}`)
  if (ec.cloud_30m?.value) lines.push(`cloud_30m = ${ec.cloud_30m.value}`)
  lines.push('')

  // ==================== ORDER BLOCKS ====================
  for (const tf of ['1h', '4h']) {
    const ob = bf[`ob_${tf}`]
    if (ob?.blocks?.length > 0) {
      lines.push(`// ═══════════════════ ${tf.toUpperCase()} ORDER BLOCKS ═══════════════════`)
      ob.blocks.forEach((b: any, i: number) => {
        lines.push(`// OB${i+1}: ${b.type} | Str: ${b.strength} | ${b.position} (${b.distance_pct?.toFixed(1)}%)`)
        lines.push(`ob_${tf}_${i}_high = ${b.zone_high}`)
        lines.push(`ob_${tf}_${i}_low = ${b.zone_low}`)
      })
      lines.push('')
    }
  }

  // ==================== VOLUME PROFILE ====================
  for (const tf of ['1h', '4h']) {
    const v = vp[tf]
    if (v && !v.error && v.poc) {
      lines.push(`// ═══════════════════ ${tf.toUpperCase()} VOLUME PROFILE ═══════════════════`)
      lines.push(`// Position: ${v.position} | POC Distance: ${v.poc_distance_pct?.toFixed(1)}%`)
      lines.push(`vp_poc_${tf} = ${v.poc}`)
      lines.push(`vp_vah_${tf} = ${v.vah}`)
      lines.push(`vp_val_${tf} = ${v.val}`)
      lines.push('')
    }
  }

  // ==================== FIBONACCI ====================
  if (bf.fib_4h?.levels) {
    lines.push('// ═══════════════════ FIBONACCI 4H ═══════════════════')
    for (const [lvl, price] of Object.entries(bf.fib_4h.levels)) {
      lines.push(`fib_${(parseFloat(lvl) * 1000).toFixed(0)} = ${price}`)
    }
    lines.push('')
  }

  // ==================== DRAWING CODE ====================
  lines.push('// ═══════════════════ DRAWING ═══════════════════')
  lines.push('if barstate.islast')

  // Trendline
  if (tl?.valid && tl.p1_time && tl.p2_time) {
    lines.push('    // Trendline (4H swing highs)')
    lines.push('    line.new(tl_p1_time, tl_p1_price, tl_p2_time, tl_p2_price, xloc.bar_time, extend.right, color.orange, line.style_solid, 2)')
    lines.push('    label.new(tl_p1_time, tl_p1_price, "P1", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)')
    lines.push('    label.new(tl_p2_time, tl_p2_price, "P2", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)')
    lines.push('')
  }

  // Alert marker
  const alertTime = alertTs ? new Date(alertTs).getTime() : 0
  if (alertTime > 0) {
    lines.push(`    // Alert marker`)
    lines.push(`    label.new(${alertTime}, ${price1h}, "MEGA BUY\\n${pair}\\n${new Date(alertTs).toISOString().slice(5, 16).replace('T', ' ')}", xloc.bar_time, yloc.price, color.yellow, label.style_label_up, color.white, size.large)`)
    lines.push('')
  }

  // Entry conditions levels
  if (ec.ema100_1h?.value) {
    const clr = ec.ema100_1h.valid ? 'color.green' : 'color.red'
    lines.push(`    line.new(bar_index - 100, ema100_1h, bar_index + 20, ema100_1h, color=${clr}, style=line.style_dashed, width=1)`)
    lines.push(`    label.new(bar_index + 20, ema100_1h, "EMA100 1H ${ec.ema100_1h.valid ? '✓' : '✗'}", xloc.bar_index, yloc.price, ${clr}, label.style_label_left, color.white, size.tiny)`)
  }
  if (ec.cloud_1h?.value) {
    const clr = ec.cloud_1h.valid ? 'color.green' : 'color.red'
    lines.push(`    line.new(bar_index - 100, cloud_1h, bar_index + 20, cloud_1h, color=${clr}, style=line.style_dotted, width=1)`)
    lines.push(`    label.new(bar_index + 20, cloud_1h, "Cloud 1H ${ec.cloud_1h.valid ? '✓' : '✗'}", xloc.bar_index, yloc.price, ${clr}, label.style_label_left, color.white, size.tiny)`)
  }
  lines.push('')

  // Order Block boxes
  for (const tf of ['1h', '4h']) {
    const ob = bf[`ob_${tf}`]
    if (ob?.blocks?.length > 0) {
      const borderColor = tf === '1h' ? 'color.teal' : 'color.purple'
      const bgColor = tf === '1h' ? 'color.new(color.teal, 80)' : 'color.new(color.purple, 80)'
      ob.blocks.forEach((b: any, i: number) => {
        if (i >= 3) return // max 3 OB per TF
        lines.push(`    // ${tf.toUpperCase()} OB #${i+1} (${b.type}, Str: ${b.strength})`)
        lines.push(`    box.new(bar_index - 80, ob_${tf}_${i}_high, bar_index + 30, ob_${tf}_${i}_low, border_color=${borderColor}, border_width=2, bgcolor=${bgColor}, extend=extend.right)`)
        lines.push(`    label.new(bar_index - 80, (ob_${tf}_${i}_high + ob_${tf}_${i}_low) / 2, "OB ${tf.toUpperCase()} #${i+1}\\n${b.type}\\nStr:${b.strength}", xloc.bar_index, yloc.price, ${borderColor}, label.style_label_right, color.white, size.small)`)
      })
      lines.push('')
    }
  }

  // Volume Profile zones
  for (const tf of ['1h', '4h']) {
    const v = vp[tf]
    if (v && !v.error && v.poc) {
      lines.push(`    // ${tf.toUpperCase()} Volume Profile`)
      lines.push(`    box.new(bar_index - 150, vp_vah_${tf}, bar_index + 50, vp_val_${tf}, border_color=color.new(color.fuchsia, 30), border_width=2, bgcolor=color.new(color.fuchsia, 85), extend=extend.right)`)
      lines.push(`    line.new(bar_index - 200, vp_poc_${tf}, bar_index + 100, vp_poc_${tf}, color=color.fuchsia, style=line.style_solid, width=3, extend=extend.right)`)
      lines.push(`    label.new(bar_index - 200, vp_poc_${tf}, "POC ${tf.toUpperCase()}", xloc.bar_index, yloc.price, color.fuchsia, label.style_label_right, color.white, size.small)`)
      lines.push(`    label.new(bar_index + 50, vp_vah_${tf}, "VAH ${tf.toUpperCase()}", xloc.bar_index, yloc.price, color.new(color.red, 30), label.style_label_left, color.white, size.tiny)`)
      lines.push(`    label.new(bar_index + 50, vp_val_${tf}, "VAL ${tf.toUpperCase()}", xloc.bar_index, yloc.price, color.new(color.green, 30), label.style_label_left, color.white, size.tiny)`)
      lines.push('')
    }
  }

  // Fibonacci lines
  if (bf.fib_4h?.levels) {
    lines.push('    // Fibonacci 4H Levels')
    const fibColors: Record<string, string> = { '0.236': 'color.gray', '0.382': 'color.orange', '0.5': 'color.yellow', '0.618': 'color.green', '0.786': 'color.blue' }
    for (const [lvl, price] of Object.entries(bf.fib_4h.levels)) {
      const pct = parseFloat(lvl)
      if (pct > 0 && pct < 1) {
        const clr = fibColors[lvl] || 'color.gray'
        const varName = `fib_${(pct * 1000).toFixed(0)}`
        lines.push(`    line.new(bar_index - 100, ${varName}, bar_index + 50, ${varName}, color=${clr}, style=line.style_dotted, width=1)`)
        lines.push(`    label.new(bar_index + 50, ${varName}, "${(pct * 100).toFixed(1)}%", xloc.bar_index, yloc.price, ${clr}, label.style_label_left, color.white, size.tiny)`)
      }
    }
  }

  return lines.join('\n')
}

const MEGA_BUY_CONDITIONS = [
  { key: 'rsi_check', label: 'RSI Surge (>=12)', mandatory: true },
  { key: 'dmi_check', label: 'DMI+ Surge (>=10)', mandatory: true },
  { key: 'ast_check', label: 'SuperTrend Flip', mandatory: true },
  { key: 'choch', label: 'CHoCH/BOS' },
  { key: 'zone', label: 'Green Zone' },
  { key: 'lazy', label: 'LazyBar' },
  { key: 'vol', label: 'Volume' },
  { key: 'st', label: 'SuperTrend' },
  { key: 'pp', label: 'PP SuperTrend Buy' },
  { key: 'ec', label: 'Entry Confirmation' },
]

export function AlertAnalysisModal({ alert, onClose }: Props) {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showPineScript, setShowPineScript] = useState(false)
  const [psCopied, setPsCopied] = useState(false)

  const decision = alert.decisions?.[0]
  const pSuccess = decision?.p_success

  // Fetch Tier 2 analysis on mount
  useEffect(() => {
    const fetchAnalysis = async () => {
      const url = `/api/alerts/analyze?pair=${encodeURIComponent(alert.pair)}&timestamp=${encodeURIComponent(alert.alert_timestamp)}&price=${alert.price}`
      console.log('[AlertAnalysis] Fetching:', url)
      try {
        const res = await fetch(url)
        console.log('[AlertAnalysis] Response status:', res.status)
        if (res.ok) {
          const data = await res.json()
          console.log('[AlertAnalysis] Data received, mode:', data.mode, 'timing:', data.timing?.total_seconds)
          if (data.error) {
            setError(data.error)
          } else {
            setAnalysis(data)
          }
        } else {
          const text = await res.text()
          console.error('[AlertAnalysis] Error response:', text.substring(0, 200))
          setError(`HTTP ${res.status}`)
        }
      } catch (e: any) {
        console.error('[AlertAnalysis] Fetch error:', e?.message || e)
        setError(`Failed to fetch analysis: ${e?.message || 'Unknown error'}`)
      } finally {
        setLoading(false)
      }
    }
    fetchAnalysis()
  }, [alert.pair, alert.alert_timestamp])

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const ec = analysis?.entry_conditions || {}
  const prereqs = analysis?.prerequisites || {}
  const bf = analysis?.bonus_filters || {}
  const indicators = analysis?.indicators || {}

  return (
    <div className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-5xl my-8 overflow-hidden" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{alert.pair}</h2>
              <p className="text-xs text-gray-400">
                {new Date(alert.alert_timestamp).toLocaleString('fr-FR', { timeZone: 'Europe/Paris' })} | Score: {alert.scanner_score}/10
                {alert.timeframes?.map(tf => ` | ${tf}`)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {pSuccess != null && (
              <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
                pSuccess >= 0.5 ? 'bg-green-500/20 text-green-400' : pSuccess >= 0.3 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
              }`}>
                P(success) {(pSuccess * 100).toFixed(0)}%
              </span>
            )}
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">

          {/* Basic Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800/50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500">Prix</div>
              <div className="text-lg font-bold text-white font-mono">{formatPrice(alert.price)}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500">Score</div>
              <div className={`text-lg font-bold ${alert.scanner_score >= 8 ? 'text-green-400' : alert.scanner_score >= 6 ? 'text-yellow-400' : 'text-red-400'}`}>
                {alert.scanner_score}/10
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500">DI+ / DI- / ADX</div>
              <div className="text-sm font-mono text-white">
                {alert.di_plus_4h?.toFixed(1) ?? '-'} / {alert.di_minus_4h?.toFixed(1) ?? '-'} / {alert.adx_4h?.toFixed(1) ?? '-'}
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500">Vol Max</div>
              <div className="text-lg font-bold text-white">
                {alert.vol_pct ? Math.max(...Object.values(alert.vol_pct)).toFixed(0) + '%' : '-'}
              </div>
            </div>
          </div>

          {/* MEGA BUY Conditions */}
          <Section title="MEGA BUY Conditions (10)" icon={Zap}>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {MEGA_BUY_CONDITIONS.map(c => (
                <ConditionBadge
                  key={c.key}
                  valid={!!(alert as any)[c.key]}
                  label={`${c.mandatory ? '* ' : ''}${c.label}`}
                />
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">* = condition mandatoire</p>
          </Section>

          {/* Tier 2: Loading or Results */}
          {loading ? (
            <div className="flex items-center justify-center py-12 gap-3 text-gray-400">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>Analyse en temps reel en cours (~10s)...</span>
            </div>
          ) : error ? (
            <div className="bg-red-900/30 border border-red-500/30 rounded-lg p-4 text-red-300 text-sm">
              Erreur d'analyse: {error}
            </div>
          ) : analysis ? (
            <>
              {/* Prerequisites */}
              <Section title="Prerequisites V5" icon={Shield}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <ConditionBadge
                    valid={prereqs.stc_oversold?.valid}
                    label="STC Oversold (<0.2)"
                    value={prereqs.stc_oversold?.valid_tfs?.length > 0
                      ? `Valid: ${prereqs.stc_oversold.valid_tfs.join(', ')}`
                      : `Valeurs: ${Object.entries(prereqs.stc_oversold?.values || {}).map(([k, v]) => `${k}=${typeof v === 'number' ? v.toFixed(2) : v}`).join(' ')}`
                    }
                  />
                  <ConditionBadge valid={prereqs.trendline?.valid} label="Trendline Exists" value={prereqs.trendline?.price ? `@ ${formatPrice(prereqs.trendline.price)}` : undefined} />
                </div>
              </Section>

              {/* Progressive Conditions */}
              <Section title={`Conditions Progressives (${ec.count || 0}/${ec.total || 5})`} icon={Activity}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {ec.ema100_1h && (
                    <ConditionBadge valid={ec.ema100_1h.valid} label="Price > EMA100 1H" value={`${formatPrice(ec.ema100_1h.price)} > ${formatPrice(ec.ema100_1h.value)} (${ec.ema100_1h.distance_pct?.toFixed(1)}%)`} />
                  )}
                  {ec.ema20_4h && (
                    <ConditionBadge valid={ec.ema20_4h.valid} label="Price > EMA20 4H" value={`${formatPrice(ec.ema20_4h.price)} > ${formatPrice(ec.ema20_4h.value)} (${ec.ema20_4h.distance_pct?.toFixed(1)}%)`} />
                  )}
                  {ec.cloud_1h && (
                    <ConditionBadge valid={ec.cloud_1h.valid} label="Price > Cloud 1H" value={`${formatPrice(ec.cloud_1h.price)} > ${formatPrice(ec.cloud_1h.value)} (${ec.cloud_1h.distance_pct?.toFixed(1)}%)`} />
                  )}
                  {ec.cloud_30m && (
                    <ConditionBadge valid={ec.cloud_30m.valid} label="Price > Cloud 30M" value={`${formatPrice(ec.cloud_30m.price)} > ${formatPrice(ec.cloud_30m.value)} (${ec.cloud_30m.distance_pct?.toFixed(1)}%)`} />
                  )}
                  {ec.choch_bos && (
                    <ConditionBadge valid={ec.choch_bos.valid} label="CHoCH/BOS Confirmed" value={ec.choch_bos.swing_high_price ? `SH @ ${formatPrice(ec.choch_bos.swing_high_price)}` : undefined} />
                  )}
                </div>
              </Section>

              {/* 22 Bonus Filters */}
              <Section title={`Bonus Filters (${bf.count || 0}/${bf.total || 0})`} icon={TrendingUp}>
                <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                  <BonusBadge bonus={bf.fib_4h?.bonus} label="Fib 4H" detail={bf.fib_4h?.bonus ? '>38.2%' : undefined} />
                  <BonusBadge bonus={bf.fib_1h?.bonus} label="Fib 1H" />
                  <BonusBadge bonus={bf.ob_1h?.bonus} label="OB 1H" detail={bf.ob_1h?.count ? `${bf.ob_1h.count} found` : undefined} />
                  <BonusBadge bonus={bf.ob_4h?.bonus} label="OB 4H" detail={bf.ob_4h?.count ? `${bf.ob_4h.count} found` : undefined} />
                  <BonusBadge bonus={bf.fvg_1h?.bonus} label="FVG 1H" detail={bf.fvg_1h?.position} />
                  <BonusBadge bonus={bf.fvg_4h?.bonus} label="FVG 4H" detail={bf.fvg_4h?.position} />
                  <BonusBadge bonus={bf.btc_corr_1h?.bonus} label="BTC 1H" detail={bf.btc_corr_1h?.trend} />
                  <BonusBadge bonus={bf.btc_corr_4h?.bonus} label="BTC 4H" detail={bf.btc_corr_4h?.trend} />
                  <BonusBadge bonus={bf.eth_corr_1h?.bonus} label="ETH 1H" detail={bf.eth_corr_1h?.trend} />
                  <BonusBadge bonus={bf.eth_corr_4h?.bonus} label="ETH 4H" detail={bf.eth_corr_4h?.trend} />
                  <BonusBadge bonus={bf.vol_spike_1h?.bonus} label="Vol 1H" detail={bf.vol_spike_1h?.ratio ? `${bf.vol_spike_1h.ratio.toFixed(1)}x` : undefined} />
                  <BonusBadge bonus={bf.vol_spike_4h?.bonus} label="Vol 4H" detail={bf.vol_spike_4h?.ratio ? `${bf.vol_spike_4h.ratio.toFixed(1)}x` : undefined} />
                  <BonusBadge bonus={bf.rsi_mtf?.bonus} label="RSI MTF" detail={bf.rsi_mtf?.aligned_count != null ? `${bf.rsi_mtf.aligned_count}/3` : undefined} />
                  <BonusBadge bonus={bf.adx_1h?.bonus} label="ADX 1H" detail={bf.adx_1h?.strength} />
                  <BonusBadge bonus={bf.adx_4h?.bonus} label="ADX 4H" detail={bf.adx_4h?.strength} />
                  <BonusBadge bonus={bf.macd_1h?.bonus} label="MACD 1H" detail={bf.macd_1h?.trend} />
                  <BonusBadge bonus={bf.macd_4h?.bonus} label="MACD 4H" detail={bf.macd_4h?.trend} />
                  <BonusBadge bonus={bf.bb_1h?.bonus} label="BB 1H" detail={bf.bb_1h?.squeeze ? 'SQZ' : undefined} />
                  <BonusBadge bonus={bf.bb_4h?.bonus} label="BB 4H" detail={bf.bb_4h?.squeeze ? 'SQZ' : undefined} />
                  <BonusBadge bonus={bf.stochrsi_1h?.bonus} label="StochRSI 1H" detail={bf.stochrsi_1h?.zone} />
                  <BonusBadge bonus={bf.stochrsi_4h?.bonus} label="StochRSI 4H" detail={bf.stochrsi_4h?.zone} />
                  <BonusBadge bonus={bf.ema_stack_1h?.bonus} label="EMA 1H" detail={bf.ema_stack_1h?.trend} />
                  <BonusBadge bonus={bf.ema_stack_4h?.bonus} label="EMA 4H" detail={bf.ema_stack_4h?.trend} />
                </div>
              </Section>

              {/* Detailed Indicators */}
              <Section title="Indicateurs Detailles" icon={BarChart3}>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500">
                        <th className="text-left py-1 pr-3">Indicateur</th>
                        {['15m', '30m', '1h', '4h', '1d'].map(tf => (
                          <th key={tf} className="text-right py-1 px-2">{tf}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="text-gray-300">
                      {['price', 'rsi', 'adx', 'di_plus', 'di_minus', 'ema20', 'ema50', 'ema100', 'cloud_top', 'stc'].map(key => (
                        <tr key={key} className="border-t border-gray-800/50">
                          <td className="py-1.5 pr-3 font-medium text-gray-400">{key.toUpperCase()}</td>
                          {['15m', '30m', '1h', '4h', '1d'].map(tf => {
                            const v = indicators[tf]?.[key]
                            return (
                              <td key={tf} className="text-right py-1.5 px-2 font-mono">
                                {v != null ? (key === 'price' ? formatPrice(v) : typeof v === 'number' ? v.toFixed(2) : '-') : <span className="text-gray-600">-</span>}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>

              {/* ADX Detail */}
              {(bf.adx_1h || bf.adx_4h) && (
                <Section title="ADX/DI Detail" icon={Activity}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['1h', '4h'].map(tf => {
                      const d = bf[`adx_${tf}`]
                      if (!d) return null
                      return (
                        <div key={tf} className="bg-gray-800/30 rounded-lg p-3">
                          <h4 className="text-sm font-semibold text-white mb-2">{tf.toUpperCase()}</h4>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>ADX: <span className={`font-bold ${d.adx > 25 ? 'text-green-400' : 'text-gray-400'}`}>{d.adx?.toFixed(1)}</span></div>
                            <div>DI Spread: <span className={`font-bold ${d.di_spread > 0 ? 'text-green-400' : 'text-red-400'}`}>{d.di_spread?.toFixed(1)}</span></div>
                            <div>DI+: <span className="text-blue-400">{d.di_plus?.toFixed(1)}</span></div>
                            <div>DI-: <span className="text-orange-400">{d.di_minus?.toFixed(1)}</span></div>
                            <div>Strength: <span className={`font-bold ${d.strength === 'STRONG' ? 'text-green-400' : d.strength === 'MODERATE' ? 'text-yellow-400' : 'text-red-400'}`}>{d.strength}</span></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* MACD Detail */}
              {(bf.macd_1h || bf.macd_4h) && (
                <Section title="MACD Detail" icon={TrendingUp}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['1h', '4h'].map(tf => {
                      const d = bf[`macd_${tf}`]
                      if (!d) return null
                      return (
                        <div key={tf} className="bg-gray-800/30 rounded-lg p-3">
                          <h4 className="text-sm font-semibold text-white mb-2">{tf.toUpperCase()} - <span className={d.trend === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>{d.trend}</span></h4>
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div>Line: <span className="font-mono">{d.line?.toFixed(6)}</span></div>
                            <div>Signal: <span className="font-mono">{d.signal?.toFixed(6)}</span></div>
                            <div>Hist: <span className={`font-mono font-bold ${d.histogram > 0 ? 'text-green-400' : 'text-red-400'}`}>{d.histogram?.toFixed(6)}</span> {d.growing ? '↑' : '↓'}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* BTC/ETH Correlation */}
              <Section title="Correlation BTC/ETH" icon={TrendingUp}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {['btc_corr_1h', 'btc_corr_4h', 'eth_corr_1h', 'eth_corr_4h'].map(key => {
                    const d = bf[key]
                    if (!d) return null
                    const label = key.replace('_corr_', ' ').toUpperCase()
                    return (
                      <div key={key} className="bg-gray-800/30 rounded-lg p-3 text-center">
                        <div className="text-xs text-gray-500">{label}</div>
                        <div className={`text-sm font-bold ${d.trend === 'BULLISH' ? 'text-green-400' : d.trend === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}`}>
                          {d.trend}
                        </div>
                        {d.rsi != null && <div className="text-xs text-gray-400 mt-1">RSI: {d.rsi.toFixed(1)} | {formatPrice(d.price)}</div>}
                      </div>
                    )
                  })}
                </div>
              </Section>

              {/* Fibonacci Levels */}
              {bf.fib_4h?.levels && (
                <Section title="Fibonacci Levels (4H)" icon={BarChart3}>
                  <div className="grid grid-cols-3 md:grid-cols-7 gap-2">
                    {Object.entries(bf.fib_4h.levels).map(([level, price]) => {
                      const currentPrice = analysis.indicators?.['4h']?.price
                      const above = currentPrice != null && typeof price === 'number' && currentPrice > price
                      return (
                        <div key={level} className={`text-center p-2 rounded ${above ? 'bg-green-500/10 border border-green-500/20' : 'bg-gray-800/50 border border-gray-700/50'}`}>
                          <div className="text-xs text-gray-500">{(parseFloat(level) * 100).toFixed(1)}%</div>
                          <div className={`text-xs font-mono ${above ? 'text-green-400' : 'text-gray-400'}`}>
                            {formatPrice(price as number)}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* Volume Profile */}
              {analysis.volume_profile && (Object.values(analysis.volume_profile).some(v => v && !v.error)) && (
                <Section title="Volume Profile" icon={BarChart3}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['1h', '4h'].map(tf => {
                      const vp = analysis.volume_profile?.[tf]
                      if (!vp || vp.error) return null
                      const posColor = vp.position === 'IN_VA' ? 'text-green-400' : vp.position === 'ABOVE_VAH' ? 'text-blue-400' : 'text-red-400'
                      return (
                        <div key={tf} className="bg-gray-800/30 rounded-lg p-3">
                          <h4 className="text-sm font-semibold text-white mb-3">{tf.toUpperCase()} Volume Profile</h4>
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-500">VAH (Value Area High)</span>
                              <span className="font-mono text-gray-300">{formatPrice(vp.vah)}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-yellow-500 font-medium">POC (Point of Control)</span>
                              <span className="font-mono text-yellow-400 font-bold">{formatPrice(vp.poc)}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-500">VAL (Value Area Low)</span>
                              <span className="font-mono text-gray-300">{formatPrice(vp.val)}</span>
                            </div>
                            <div className="border-t border-gray-700 pt-2 mt-2">
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-500">Entry Price</span>
                                <span className="font-mono text-white">{formatPrice(vp.entry_price)}</span>
                              </div>
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-500">Position</span>
                                <span className={`font-bold ${posColor}`}>{vp.position}</span>
                              </div>
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-500">Distance to POC</span>
                                <span className={`font-mono ${vp.poc_distance_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {vp.poc_distance_pct > 0 ? '+' : ''}{vp.poc_distance_pct?.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            {vp.hvn_levels?.length > 0 && (
                              <div className="border-t border-gray-700 pt-2 mt-2">
                                <div className="text-xs text-gray-500 mb-1">HVN (Support/Resistance)</div>
                                <div className="flex flex-wrap gap-1">
                                  {vp.hvn_levels.map((lvl: number, i: number) => (
                                    <span key={i} className="px-1.5 py-0.5 bg-yellow-500/10 text-yellow-400 text-[10px] rounded font-mono">
                                      {formatPrice(lvl)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {vp.lvn_levels?.length > 0 && (
                              <div className="mt-1">
                                <div className="text-xs text-gray-500 mb-1">LVN (Breakout Zones)</div>
                                <div className="flex flex-wrap gap-1">
                                  {vp.lvn_levels.map((lvl: number, i: number) => (
                                    <span key={i} className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 text-[10px] rounded font-mono">
                                      {formatPrice(lvl)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* Order Blocks Detail */}
              {(bf.ob_1h?.blocks?.length > 0 || bf.ob_4h?.blocks?.length > 0) && (
                <Section title="Order Blocks (SMC)" icon={Shield}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['1h', '4h'].map(tf => {
                      const ob = bf[`ob_${tf}`]
                      if (!ob?.blocks?.length) return null
                      return (
                        <div key={tf} className="bg-gray-800/30 rounded-lg p-3">
                          <h4 className="text-sm font-semibold text-white mb-2">
                            {tf.toUpperCase()} - {ob.count} OB detected
                            {ob.bonus && <span className="ml-2 text-green-400 text-xs">(NEAR ENTRY)</span>}
                          </h4>
                          <div className="space-y-2">
                            {ob.blocks.map((block: any, i: number) => (
                              <div key={i} className={`flex items-center justify-between p-2 rounded text-xs ${
                                block.position === 'INSIDE' ? 'bg-green-500/10 border border-green-500/20' :
                                block.mitigated ? 'bg-gray-700/30 border border-gray-700' :
                                'bg-blue-500/5 border border-blue-500/10'
                              }`}>
                                <div>
                                  <span className={`font-bold ${block.type === 'BULLISH' ? 'text-green-400' : 'text-red-400'}`}>
                                    {block.type}
                                  </span>
                                  <span className="text-gray-500 ml-2">Str: {block.strength}</span>
                                  {block.mitigated && <span className="text-gray-600 ml-2">(mitigated)</span>}
                                </div>
                                <div className="text-right">
                                  <div className="font-mono text-gray-300">
                                    {formatPrice(block.zone_low)} - {formatPrice(block.zone_high)}
                                  </div>
                                  <div className={`text-[10px] ${
                                    block.position === 'INSIDE' ? 'text-green-400' :
                                    block.position === 'ABOVE' ? 'text-blue-400' : 'text-red-400'
                                  }`}>
                                    {block.position} ({block.distance_pct > 0 ? '+' : ''}{block.distance_pct?.toFixed(1)}%)
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* PineScript for TradingView */}
              <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden">
                <button
                  onClick={() => setShowPineScript(!showPineScript)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Code className="w-4 h-4 text-orange-400" />
                    <span className="text-sm font-medium text-orange-400">TradingView PineScript Code</span>
                    <span className="text-xs text-gray-500">(OB + VP + Fib + Conditions)</span>
                  </div>
                  <span className="text-xs text-gray-500">{showPineScript ? 'Masquer' : 'Afficher'}</span>
                </button>
                {showPineScript && (
                  <div className="border-t border-gray-700">
                    <div className="flex items-center justify-between px-4 py-2 bg-gray-900/50">
                      <span className="text-xs text-gray-500">Copiez ce code dans TradingView &gt; Pine Editor &gt; Add to chart</span>
                      <button
                        onClick={() => {
                          const code = generateAlertPineScript(alert.pair, alert.alert_timestamp, analysis)
                          navigator.clipboard.writeText(code)
                          setPsCopied(true)
                          setTimeout(() => setPsCopied(false), 2000)
                        }}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                          psCopied ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30'
                        }`}
                      >
                        {psCopied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        {psCopied ? 'Copied!' : 'Copy Code'}
                      </button>
                    </div>
                    <pre className="p-4 text-[11px] leading-relaxed font-mono text-gray-300 overflow-x-auto max-h-96 overflow-y-auto bg-gray-950">
                      {generateAlertPineScript(alert.pair, alert.alert_timestamp, analysis)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Timing footer */}
              <div className="text-xs text-gray-600 text-right">
                Analyse en {analysis.timing.total_seconds}s | {new Date(analysis.computed_at).toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris' })} | Mode: {analysis.mode}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
