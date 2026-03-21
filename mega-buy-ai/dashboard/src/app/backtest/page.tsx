"use client"

import { useState, useEffect, useMemo } from "react"
import {
  FlaskConical,
  Play,
  RefreshCw,
  Trash2,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  X,
  Copy,
  Check,
  BarChart2,
  AlertTriangle,
  Brain,
  Zap,
  Shield,
  ArrowUpCircle,
  ArrowDownCircle,
  Code,
  Layers,
  Filter,
  SlidersHorizontal,
  BarChart3,
  PieChart,
  Award,
  Percent,
  Activity,
  Calculator,
  Trophy,
  Skull
} from "lucide-react"

// Helper function to generate TradingView PineScript code for Foreign Candle Order Block visualization
function generateFcObPineScript(
  symbol: string,
  alert: {
    fc_ob_1h_found?: boolean
    fc_ob_1h_zone_high?: number | null
    fc_ob_1h_zone_low?: number | null
    fc_ob_1h_datetime?: string | null
    fc_ob_1h_type?: string | null
    fc_ob_1h_strength?: number | null
    fc_ob_1h_retest?: boolean
    fc_ob_1h_in_zone?: number
    fc_ob_1h_retested?: number
    fc_ob_4h_found?: boolean
    fc_ob_4h_zone_high?: number | null
    fc_ob_4h_zone_low?: number | null
    fc_ob_4h_datetime?: string | null
    fc_ob_4h_type?: string | null
    fc_ob_4h_strength?: number | null
    fc_ob_4h_retest?: boolean
    fc_ob_4h_in_zone?: number
    fc_ob_4h_retested?: number
    entry_price?: number | null
    v3_retest_price?: number | null
    alert_datetime?: string
  }
): string {
  if (!alert.fc_ob_1h_found && !alert.fc_ob_4h_found) {
    return '// No Foreign Candle Order Block data available'
  }

  const lines = [
    '//@version=5',
    `indicator("MEGA BUY FC OB - ${symbol}", overlay=true)`,
    '',
    '// ══════════════════════════════════════════════════════════════',
    '// MEGA BUY AI - Foreign Candle Order Block Visualization',
    `// Symbol: ${symbol}`,
    `// Alert: ${alert.alert_datetime ? new Date(alert.alert_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'} UTC`,
    `// Entry Price: ${alert.entry_price?.toFixed(5) || 'N/A'}`,
    `// Retest Price: ${alert.v3_retest_price?.toFixed(5) || 'N/A'}`,
    '// ══════════════════════════════════════════════════════════════',
    '',
  ]

  // 1H Order Block
  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high && alert.fc_ob_1h_zone_low) {
    const ob1hTime = alert.fc_ob_1h_datetime ? new Date(alert.fc_ob_1h_datetime).getTime() : 0
    const ob1hDateStr = alert.fc_ob_1h_datetime ? new Date(alert.fc_ob_1h_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'

    lines.push('// ═══════════ 1H ORDER BLOCK ═══════════')
    lines.push(`// DateTime: ${ob1hDateStr} UTC`)
    lines.push(`// Type: ${alert.fc_ob_1h_type || 'BULLISH'} (${alert.fc_ob_1h_type === 'BULLISH' ? 'Demand Zone' : 'Supply Zone'})`)
    lines.push(`// Strength: ${alert.fc_ob_1h_strength || 0} candles`)
    lines.push(`// Retest: ${alert.fc_ob_1h_retest ? 'YES ✓' : 'NO'}`)
    lines.push(`// OBs in zone: ${alert.fc_ob_1h_retested || 0}/${alert.fc_ob_1h_in_zone || 0} retested`)
    lines.push('')
    lines.push('// 1H OB Zone coordinates')
    lines.push(`ob_1h_time = ${ob1hTime}`)
    lines.push(`ob_1h_high = ${alert.fc_ob_1h_zone_high}`)
    lines.push(`ob_1h_low = ${alert.fc_ob_1h_zone_low}`)
    lines.push(`ob_1h_mid = ${(alert.fc_ob_1h_zone_high + alert.fc_ob_1h_zone_low) / 2}`)
    lines.push(`ob_1h_retested = ${alert.fc_ob_1h_retest ? 'true' : 'false'}`)
    lines.push('')
  }

  // 4H Order Block
  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high && alert.fc_ob_4h_zone_low) {
    const ob4hTime = alert.fc_ob_4h_datetime ? new Date(alert.fc_ob_4h_datetime).getTime() : 0
    const ob4hDateStr = alert.fc_ob_4h_datetime ? new Date(alert.fc_ob_4h_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'

    lines.push('// ═══════════ 4H ORDER BLOCK ═══════════')
    lines.push(`// DateTime: ${ob4hDateStr} UTC`)
    lines.push(`// Type: ${alert.fc_ob_4h_type || 'BULLISH'} (${alert.fc_ob_4h_type === 'BULLISH' ? 'Demand Zone' : 'Supply Zone'})`)
    lines.push(`// Strength: ${alert.fc_ob_4h_strength || 0} candles`)
    lines.push(`// Retest: ${alert.fc_ob_4h_retest ? 'YES ✓' : 'NO'}`)
    lines.push(`// OBs in zone: ${alert.fc_ob_4h_retested || 0}/${alert.fc_ob_4h_in_zone || 0} retested`)
    lines.push('')
    lines.push('// 4H OB Zone coordinates')
    lines.push(`ob_4h_time = ${ob4hTime}`)
    lines.push(`ob_4h_high = ${alert.fc_ob_4h_zone_high}`)
    lines.push(`ob_4h_low = ${alert.fc_ob_4h_zone_low}`)
    lines.push(`ob_4h_mid = ${(alert.fc_ob_4h_zone_high + alert.fc_ob_4h_zone_low) / 2}`)
    lines.push(`ob_4h_retested = ${alert.fc_ob_4h_retest ? 'true' : 'false'}`)
    lines.push('')
  }

  // Drawing code
  lines.push('// ═══════════ DRAWING ═══════════')
  lines.push('if barstate.islast')

  // Draw 1H OB Box
  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high && alert.fc_ob_1h_zone_low) {
    const color1h = alert.fc_ob_1h_retest ? 'color.new(color.green, 70)' : 'color.new(color.teal, 80)'
    const borderColor1h = alert.fc_ob_1h_retest ? 'color.green' : 'color.teal'
    lines.push(`    // 1H Order Block Box`)
    lines.push(`    box.new(left=ob_1h_time, top=ob_1h_high, right=time, bottom=ob_1h_low, border_color=${borderColor1h}, border_width=2, border_style=line.style_solid, extend=extend.right, xloc=xloc.bar_time, bgcolor=${color1h})`)
    lines.push(`    label.new(ob_1h_time, ob_1h_high, "OB 1H\\n${alert.fc_ob_1h_retest ? 'RETESTED ✓' : ''}\\nStrength: ${alert.fc_ob_1h_strength}", xloc.bar_time, yloc.price, color.teal, label.style_label_down, color.white, size.small)`)
  }

  // Draw 4H OB Box
  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high && alert.fc_ob_4h_zone_low) {
    const color4h = alert.fc_ob_4h_retest ? 'color.new(color.lime, 70)' : 'color.new(color.purple, 80)'
    const borderColor4h = alert.fc_ob_4h_retest ? 'color.lime' : 'color.purple'
    lines.push(`    // 4H Order Block Box`)
    lines.push(`    box.new(left=ob_4h_time, top=ob_4h_high, right=time, bottom=ob_4h_low, border_color=${borderColor4h}, border_width=3, border_style=line.style_solid, extend=extend.right, xloc=xloc.bar_time, bgcolor=${color4h})`)
    lines.push(`    label.new(ob_4h_time, ob_4h_high, "OB 4H\\n${alert.fc_ob_4h_retest ? 'RETESTED ✓' : ''}\\nStrength: ${alert.fc_ob_4h_strength}", xloc.bar_time, yloc.price, color.purple, label.style_label_down, color.white, size.normal)`)
  }

  // Draw entry/retest price lines
  if (alert.entry_price) {
    lines.push('')
    lines.push(`    // Entry Price Line`)
    lines.push(`    line.new(bar_index - 50, ${alert.entry_price}, bar_index, ${alert.entry_price}, color=color.blue, style=line.style_dashed, width=1)`)
    lines.push(`    label.new(bar_index, ${alert.entry_price}, "Entry: ${alert.entry_price.toFixed(5)}", xloc.bar_index, yloc.price, color.blue, label.style_label_left, color.white, size.tiny)`)
  }

  if (alert.v3_retest_price) {
    lines.push('')
    lines.push(`    // Retest Price Line`)
    lines.push(`    line.new(bar_index - 50, ${alert.v3_retest_price}, bar_index, ${alert.v3_retest_price}, color=color.orange, style=line.style_dotted, width=1)`)
    lines.push(`    label.new(bar_index, ${alert.v3_retest_price}, "Retest: ${alert.v3_retest_price.toFixed(5)}", xloc.bar_index, yloc.price, color.orange, label.style_label_left, color.white, size.tiny)`)
  }

  // Horizontal reference lines for OB zones
  lines.push('')
  lines.push('// Reference Lines (OB Zone boundaries)')
  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high && alert.fc_ob_1h_zone_low) {
    lines.push(`hline(ob_1h_high, "OB 1H High", color.new(color.teal, 50), hline.style_dotted)`)
    lines.push(`hline(ob_1h_low, "OB 1H Low", color.new(color.teal, 50), hline.style_dotted)`)
  }
  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high && alert.fc_ob_4h_zone_low) {
    lines.push(`hline(ob_4h_high, "OB 4H High", color.new(color.purple, 50), hline.style_dotted)`)
    lines.push(`hline(ob_4h_low, "OB 4H Low", color.new(color.purple, 50), hline.style_dotted)`)
  }

  // Info table
  lines.push('')
  lines.push('// Info Table')
  lines.push('var table obTable = table.new(position.top_right, 2, 6, bgcolor=color.new(color.black, 80), border_width=1)')
  lines.push('if barstate.islast')
  lines.push('    table.cell(obTable, 0, 0, "FC Order Blocks", text_color=color.white, text_size=size.small)')
  lines.push('    table.merge_cells(obTable, 0, 0, 1, 0)')

  if (alert.fc_ob_1h_found) {
    lines.push(`    table.cell(obTable, 0, 1, "1H Zone", text_color=color.teal)`)
    lines.push(`    table.cell(obTable, 1, 1, "${alert.fc_ob_1h_zone_high?.toFixed(4)} - ${alert.fc_ob_1h_zone_low?.toFixed(4)}", text_color=color.white)`)
    lines.push(`    table.cell(obTable, 0, 2, "1H Status", text_color=color.teal)`)
    lines.push(`    table.cell(obTable, 1, 2, "${alert.fc_ob_1h_retest ? 'RETESTED ✓' : 'Not retested'}", text_color=${alert.fc_ob_1h_retest ? 'color.green' : 'color.gray'})`)
  }

  if (alert.fc_ob_4h_found) {
    lines.push(`    table.cell(obTable, 0, 3, "4H Zone", text_color=color.purple)`)
    lines.push(`    table.cell(obTable, 1, 3, "${alert.fc_ob_4h_zone_high?.toFixed(4)} - ${alert.fc_ob_4h_zone_low?.toFixed(4)}", text_color=color.white)`)
    lines.push(`    table.cell(obTable, 0, 4, "4H Status", text_color=color.purple)`)
    lines.push(`    table.cell(obTable, 1, 4, "${alert.fc_ob_4h_retest ? 'RETESTED ✓' : 'Not retested'}", text_color=${alert.fc_ob_4h_retest ? 'color.green' : 'color.gray'})`)
  }

  if (alert.fc_ob_1h_retest && alert.fc_ob_4h_retest) {
    lines.push(`    table.cell(obTable, 0, 5, "CONFLUENCE", text_color=color.lime, text_size=size.normal)`)
    lines.push(`    table.cell(obTable, 1, 5, "1H + 4H ✓", text_color=color.lime)`)
  }

  return lines.join('\n')
}

// Helper function to generate COMBINED TradingView PineScript (Trendline + Order Blocks + Volume Profile)
function generateCombinedPineScript(
  symbol: string,
  alert: {
    // Trendline fields
    tl_p1_date?: string | null
    tl_p1_price?: number | null
    tl_p2_date?: string | null
    tl_p2_price?: number | null
    tl_break_datetime?: string | null
    tl_break_price?: number | null
    tl_retest_count?: number | null
    // FC OB fields
    fc_ob_1h_found?: boolean
    fc_ob_1h_zone_high?: number | null
    fc_ob_1h_zone_low?: number | null
    fc_ob_1h_datetime?: string | null
    fc_ob_1h_type?: string | null
    fc_ob_1h_strength?: number | null
    fc_ob_1h_retest?: boolean
    fc_ob_1h_in_zone?: number
    fc_ob_1h_retested?: number
    fc_ob_4h_found?: boolean
    fc_ob_4h_zone_high?: number | null
    fc_ob_4h_zone_low?: number | null
    fc_ob_4h_datetime?: string | null
    fc_ob_4h_type?: string | null
    fc_ob_4h_strength?: number | null
    fc_ob_4h_retest?: boolean
    fc_ob_4h_in_zone?: number
    fc_ob_4h_retested?: number
    // Volume Profile fields
    vp_score?: number | null
    vp_grade?: string | null
    vp_poc_1h?: number | null
    vp_vah_1h?: number | null
    vp_val_1h?: number | null
    vp_poc_4h?: number | null
    vp_vah_4h?: number | null
    vp_val_4h?: number | null
    vp_entry_position_1h?: string | null
    vp_entry_position_4h?: string | null
    vp_sl_near_hvn?: boolean
    vp_sl_hvn_level?: number | null
    vp_hvn_levels_1h?: number[] | null
    vp_lvn_levels_1h?: number[] | null
    vp_label?: string | null
    // VP Retest Detection
    vp_val_retested?: boolean
    vp_val_retest_rejected?: boolean
    vp_val_retest_dt?: string | null
    vp_poc_retested?: boolean
    vp_poc_retest_rejected?: boolean
    vp_poc_retest_dt?: string | null
    vp_ob_confluence?: boolean
    vp_ob_confluence_tf?: string | null
    vp_pullback_completed?: boolean
    vp_pullback_level?: string | null
    vp_pullback_quality?: string | null
    // Trade fields
    entry_price?: number | null
    entry_datetime?: string | null
    v3_entry_price?: number | null
    v3_entry_datetime?: string | null
    v3_sl_price?: number | null
    v3_retest_price?: number | null
    alert_datetime?: string
  }
): string {
  const hasTrendline = alert.tl_p1_date && alert.tl_p1_price && alert.tl_p2_date && alert.tl_p2_price
  const hasOB = alert.fc_ob_1h_found || alert.fc_ob_4h_found
  const hasVP = alert.vp_poc_1h !== null && alert.vp_poc_1h !== undefined

  if (!hasTrendline && !hasOB && !hasVP) {
    return '// No trendline, Order Block or Volume Profile data available'
  }

  const lines = [
    '//@version=5',
    `indicator("MEGA BUY Analysis - ${symbol}", overlay=true)`,
    '',
    '// ══════════════════════════════════════════════════════════════════════════════',
    '// MEGA BUY AI - Complete Trade Analysis (Trendline + Order Blocks)',
    `// Symbol: ${symbol}`,
    `// Alert: ${alert.alert_datetime ? new Date(alert.alert_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'} UTC`,
    `// Entry: ${alert.entry_price?.toFixed(5) || 'N/A'}`,
    '// ══════════════════════════════════════════════════════════════════════════════',
    '',
  ]

  // ==================== TRENDLINE SECTION ====================
  if (hasTrendline) {
    const p1Time = new Date(alert.tl_p1_date!).getTime()
    const p2Time = new Date(alert.tl_p2_date!).getTime()
    const breakTime = alert.tl_break_datetime ? new Date(alert.tl_break_datetime).getTime() : 0
    const breakPriceVal = alert.tl_break_price || 0
    const retestCount = alert.tl_retest_count || 0
    const p1DateStr = new Date(alert.tl_p1_date!).toISOString().slice(0, 16).replace('T', ' ')
    const p2DateStr = new Date(alert.tl_p2_date!).toISOString().slice(0, 16).replace('T', ' ')
    const breakDateStr = alert.tl_break_datetime ? new Date(alert.tl_break_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'
    const retestStrength = retestCount >= 3 ? 'STRONG' : retestCount >= 1 ? 'MODERATE' : 'WEAK'

    lines.push('// ═══════════════════ TRENDLINE ═══════════════════')
    lines.push(`// P1: ${p1DateStr} UTC @ ${alert.tl_p1_price}`)
    lines.push(`// P2: ${p2DateStr} UTC @ ${alert.tl_p2_price}`)
    lines.push(`// Break: ${breakDateStr} UTC @ ${breakPriceVal || 'N/A'}`)
    lines.push(`// Retests: ${retestCount}x (${retestStrength})`)
    lines.push('')
    lines.push('// Trendline coordinates')
    lines.push(`tl_p1_time = ${p1Time}`)
    lines.push(`tl_p1_price = ${alert.tl_p1_price}`)
    lines.push(`tl_p2_time = ${p2Time}`)
    lines.push(`tl_p2_price = ${alert.tl_p2_price}`)
    lines.push(`tl_break_time = ${breakTime}`)
    lines.push(`tl_break_price = ${breakPriceVal}`)
    lines.push(`tl_retest_count = ${retestCount}`)
    lines.push('')
  }

  // ==================== ORDER BLOCKS SECTION ====================
  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high && alert.fc_ob_1h_zone_low) {
    const ob1hTime = alert.fc_ob_1h_datetime ? new Date(alert.fc_ob_1h_datetime).getTime() : 0
    const ob1hDateStr = alert.fc_ob_1h_datetime ? new Date(alert.fc_ob_1h_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'

    lines.push('// ═══════════════════ 1H ORDER BLOCK ═══════════════════')
    lines.push(`// DateTime: ${ob1hDateStr} UTC`)
    lines.push(`// Type: ${alert.fc_ob_1h_type || 'BULLISH'} | Strength: ${alert.fc_ob_1h_strength || 0} candles`)
    lines.push(`// Retested: ${alert.fc_ob_1h_retest ? 'YES ✓' : 'NO'} | OBs: ${alert.fc_ob_1h_retested || 0}/${alert.fc_ob_1h_in_zone || 0}`)
    lines.push('')
    lines.push(`ob_1h_time = ${ob1hTime}`)
    lines.push(`ob_1h_high = ${alert.fc_ob_1h_zone_high}`)
    lines.push(`ob_1h_low = ${alert.fc_ob_1h_zone_low}`)
    lines.push(`ob_1h_mid = ${(alert.fc_ob_1h_zone_high + alert.fc_ob_1h_zone_low) / 2}`)
    lines.push('')
  }

  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high && alert.fc_ob_4h_zone_low) {
    const ob4hTime = alert.fc_ob_4h_datetime ? new Date(alert.fc_ob_4h_datetime).getTime() : 0
    const ob4hDateStr = alert.fc_ob_4h_datetime ? new Date(alert.fc_ob_4h_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'

    lines.push('// ═══════════════════ 4H ORDER BLOCK ═══════════════════')
    lines.push(`// DateTime: ${ob4hDateStr} UTC`)
    lines.push(`// Type: ${alert.fc_ob_4h_type || 'BULLISH'} | Strength: ${alert.fc_ob_4h_strength || 0} candles`)
    lines.push(`// Retested: ${alert.fc_ob_4h_retest ? 'YES ✓' : 'NO'} | OBs: ${alert.fc_ob_4h_retested || 0}/${alert.fc_ob_4h_in_zone || 0}`)
    lines.push('')
    lines.push(`ob_4h_time = ${ob4hTime}`)
    lines.push(`ob_4h_high = ${alert.fc_ob_4h_zone_high}`)
    lines.push(`ob_4h_low = ${alert.fc_ob_4h_zone_low}`)
    lines.push(`ob_4h_mid = ${(alert.fc_ob_4h_zone_high + alert.fc_ob_4h_zone_low) / 2}`)
    lines.push('')
  }

  // ==================== VOLUME PROFILE SECTION ====================
  if (hasVP) {
    const gradeColor = alert.vp_grade === 'A+' || alert.vp_grade === 'A' ? '🟢' :
                       alert.vp_grade === 'B+' || alert.vp_grade === 'B' ? '🔵' :
                       alert.vp_grade === 'C' ? '🟡' : '🔴'

    lines.push('// ═══════════════════ VOLUME PROFILE ═══════════════════')
    lines.push(`// Grade: ${alert.vp_grade || 'N/A'} ${gradeColor} (Score: ${alert.vp_score || 0}/100)`)
    lines.push(`// Label: ${alert.vp_label || 'N/A'}`)
    lines.push(`// Entry Position 1H: ${alert.vp_entry_position_1h || 'N/A'}`)
    lines.push(`// Entry Position 4H: ${alert.vp_entry_position_4h || 'N/A'}`)
    lines.push(`// SL Protected by HVN: ${alert.vp_sl_near_hvn ? 'YES ✓' : 'NO'}`)
    lines.push('')

    // 1H VP Levels
    lines.push('// 1H Volume Profile Levels')
    lines.push(`vp_poc_1h = ${alert.vp_poc_1h || 0}`)
    lines.push(`vp_vah_1h = ${alert.vp_vah_1h || 0}`)
    lines.push(`vp_val_1h = ${alert.vp_val_1h || 0}`)

    // 4H VP Levels (if available)
    if (alert.vp_poc_4h) {
      lines.push('')
      lines.push('// 4H Volume Profile Levels')
      lines.push(`vp_poc_4h = ${alert.vp_poc_4h}`)
      lines.push(`vp_vah_4h = ${alert.vp_vah_4h || 0}`)
      lines.push(`vp_val_4h = ${alert.vp_val_4h || 0}`)
    }

    // HVN Level for SL protection
    if (alert.vp_sl_near_hvn && alert.vp_sl_hvn_level) {
      lines.push('')
      lines.push('// HVN Support Level (SL Protection)')
      lines.push(`vp_hvn_sl = ${alert.vp_sl_hvn_level}`)
    }
    lines.push('')
  }

  // ==================== DRAWING CODE ====================
  lines.push('// ═══════════════════ DRAWING ═══════════════════')
  lines.push('if barstate.islast')

  // Draw Trendline
  if (hasTrendline) {
    lines.push('    // Trendline')
    lines.push('    line.new(tl_p1_time, tl_p1_price, tl_p2_time, tl_p2_price, xloc.bar_time, extend.right, color.orange, line.style_solid, 2)')
    lines.push('    label.new(tl_p1_time, tl_p1_price, "P1", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)')
    lines.push('    label.new(tl_p2_time, tl_p2_price, "P2", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)')
    if (alert.tl_break_datetime && alert.tl_break_price) {
      lines.push(`    label.new(tl_break_time, tl_break_price, "BREAK\\n${alert.tl_retest_count || 0}x", xloc.bar_time, yloc.price, color.green, label.style_label_up, color.white, size.small)`)
    }
  }

  // Draw 1H OB Box
  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high && alert.fc_ob_1h_zone_low) {
    const color1h = alert.fc_ob_1h_retest ? 'color.new(color.green, 70)' : 'color.new(color.teal, 80)'
    const borderColor1h = alert.fc_ob_1h_retest ? 'color.green' : 'color.teal'
    lines.push('    // 1H Order Block')
    lines.push(`    box.new(left=ob_1h_time, top=ob_1h_high, right=time, bottom=ob_1h_low, border_color=${borderColor1h}, border_width=2, border_style=line.style_solid, extend=extend.right, xloc=xloc.bar_time, bgcolor=${color1h})`)
    lines.push(`    label.new(ob_1h_time, ob_1h_mid, "OB 1H${alert.fc_ob_1h_retest ? ' ✓' : ''}", xloc.bar_time, yloc.price, color.teal, label.style_label_right, color.white, size.small)`)
  }

  // Draw 4H OB Box
  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high && alert.fc_ob_4h_zone_low) {
    const color4h = alert.fc_ob_4h_retest ? 'color.new(color.lime, 70)' : 'color.new(color.purple, 80)'
    const borderColor4h = alert.fc_ob_4h_retest ? 'color.lime' : 'color.purple'
    lines.push('    // 4H Order Block')
    lines.push(`    box.new(left=ob_4h_time, top=ob_4h_high, right=time, bottom=ob_4h_low, border_color=${borderColor4h}, border_width=3, border_style=line.style_solid, extend=extend.right, xloc=xloc.bar_time, bgcolor=${color4h})`)
    lines.push(`    label.new(ob_4h_time, ob_4h_mid, "OB 4H${alert.fc_ob_4h_retest ? ' ✓' : ''}", xloc.bar_time, yloc.price, color.purple, label.style_label_right, color.white, size.normal)`)
  }

  // Draw Entry Candle Marker (exact candle, not just a line)
  const entryDt = alert.v3_entry_datetime || alert.entry_datetime
  const entryPx = alert.v3_entry_price || alert.entry_price
  if (entryPx && entryDt) {
    const entryTime = new Date(entryDt).getTime()
    const entryDateStr = new Date(entryDt).toISOString().slice(0, 16).replace('T', ' ')

    lines.push('    // ═══════════════════ ENTRY CANDLE MARKER ═══════════════════')
    lines.push(`    // Entry: ${entryDateStr} UTC @ ${entryPx.toFixed(5)}`)
    lines.push(`    entry_time = ${entryTime}`)
    lines.push(`    entry_price = ${entryPx}`)
    lines.push('')

    // Vertical line at entry candle (full height)
    lines.push('    // Vertical line marking the EXACT entry candle')
    lines.push(`    line.new(entry_time, 0, entry_time, entry_price * 1.5, xloc=xloc.bar_time, color=color.new(color.blue, 30), style=line.style_solid, width=3)`)
    lines.push('')

    // Entry arrow pointing to the candle
    lines.push('    // Entry arrow (pointing UP to the candle)')
    lines.push(`    label.new(entry_time, entry_price * 0.995, "▲\\nENTRY\\n${entryPx.toFixed(4)}\\n${entryDateStr.slice(5, 16)}", xloc.bar_time, yloc.price, color.blue, label.style_label_up, color.white, size.large)`)
    lines.push('')

    // Horizontal entry price line
    lines.push('    // Entry price horizontal reference')
    lines.push(`    line.new(entry_time - 86400000 * 3, entry_price, entry_time + 86400000 * 5, entry_price, xloc=xloc.bar_time, color=color.blue, style=line.style_dashed, width=2)`)
    lines.push(`    label.new(entry_time + 86400000 * 5, entry_price, "ENTRY ${entryPx.toFixed(5)}", xloc.bar_time, yloc.price, color.blue, label.style_label_left, color.white, size.normal)`)
    lines.push('')
  } else if (entryPx) {
    // Fallback if no datetime (use bar_index)
    lines.push('    // Entry Price (no exact time)')
    lines.push(`    line.new(bar_index - 100, ${entryPx}, bar_index, ${entryPx}, color=color.blue, style=line.style_dashed, width=1)`)
    lines.push(`    label.new(bar_index, ${entryPx}, "Entry ${entryPx.toFixed(4)}", xloc.bar_index, yloc.price, color.blue, label.style_label_left, color.white, size.tiny)`)
  }

  // Draw Volume Profile Zones (Clear visual zones)
  if (hasVP) {
    const entryPrice = alert.v3_entry_price || alert.entry_price || 0
    const slPrice = alert.v3_sl_price || (entryPrice * 0.95)
    const pocPrice = alert.vp_poc_1h || 0
    const vahPrice = alert.vp_vah_1h || 0
    const valPrice = alert.vp_val_1h || 0

    // Determine POC position relative to entry
    const pocAboveEntry = pocPrice > entryPrice
    const pocDistancePct = entryPrice > 0 ? Math.abs(pocPrice - entryPrice) / entryPrice * 100 : 0
    const valProtectsSL = valPrice > slPrice && valPrice < entryPrice

    lines.push('    // ═══════════════════ VOLUME PROFILE ZONES ═══════════════════')
    lines.push('')

    // 1. VALUE AREA BOX (Institutional Zone)
    lines.push('    // 📦 VALUE AREA - Zone Institutionnelle')
    lines.push(`    box.new(left=bar_index - 150, top=vp_vah_1h, right=bar_index + 50, bottom=vp_val_1h, border_color=color.new(color.fuchsia, 30), border_width=2, border_style=line.style_solid, bgcolor=color.new(color.fuchsia, 85), extend=extend.right)`)
    lines.push(`    label.new(bar_index - 150, (vp_vah_1h + vp_val_1h) / 2, "VALUE AREA\\n(Zone Institutionnelle)", xloc.bar_index, yloc.price, color.new(color.fuchsia, 20), label.style_label_center, color.white, size.small)`)
    lines.push('')

    // 2. POC LINE (Point of Control - Most traded price)
    lines.push('    // 🎯 POC - Point of Control (Prix le plus tradé)')
    lines.push(`    line.new(bar_index - 200, vp_poc_1h, bar_index + 100, vp_poc_1h, color=color.fuchsia, style=line.style_solid, width=3, extend=extend.right)`)

    // POC Support Zone (when POC is above entry)
    if (pocAboveEntry && pocDistancePct < 5) {
      lines.push('')
      lines.push('    // 🛡️ POC SUPPORT ZONE - Le prix revient ici sur pullback!')
      lines.push(`    box.new(left=bar_index - 100, top=vp_poc_1h * 1.005, right=bar_index + 50, bottom=vp_poc_1h * 0.995, border_color=color.lime, border_width=2, border_style=line.style_solid, bgcolor=color.new(color.lime, 80), extend=extend.right)`)
      lines.push(`    label.new(bar_index + 50, vp_poc_1h, "POC SUPPORT 🎯\\n(Pullback Zone)\\n${pocDistancePct.toFixed(1)}% above entry", xloc.bar_index, yloc.price, color.lime, label.style_label_left, color.white, size.normal)`)
    } else {
      lines.push(`    label.new(bar_index - 200, vp_poc_1h, "POC 1H", xloc.bar_index, yloc.price, color.fuchsia, label.style_label_right, color.white, size.small)`)
    }
    lines.push('')

    // 3. VAH LINE (Value Area High)
    lines.push('    // 📈 VAH - Value Area High (Résistance)')
    lines.push(`    line.new(bar_index - 200, vp_vah_1h, bar_index + 50, vp_vah_1h, color=color.new(color.red, 30), style=line.style_dashed, width=2, extend=extend.right)`)
    lines.push(`    label.new(bar_index - 200, vp_vah_1h, "VAH (Résistance)", xloc.bar_index, yloc.price, color.new(color.red, 30), label.style_label_right, color.white, size.tiny)`)
    lines.push('')

    // 4. VAL LINE (Value Area Low)
    lines.push('    // 📉 VAL - Value Area Low (Support)')
    lines.push(`    line.new(bar_index - 200, vp_val_1h, bar_index + 50, vp_val_1h, color=color.new(color.green, 30), style=line.style_dashed, width=2, extend=extend.right)`)

    // VAL Protection Zone (when VAL is between SL and Entry)
    if (valProtectsSL) {
      lines.push('')
      lines.push('    // 🛡️ VAL PROTECTION - Support naturel au-dessus du SL!')
      lines.push(`    box.new(left=bar_index - 100, top=vp_val_1h * 1.003, right=bar_index + 50, bottom=vp_val_1h * 0.997, border_color=color.green, border_width=2, border_style=line.style_solid, bgcolor=color.new(color.green, 80), extend=extend.right)`)
      lines.push(`    label.new(bar_index - 200, vp_val_1h, "VAL SUPPORT 🛡️\\n(Protège le SL)", xloc.bar_index, yloc.price, color.green, label.style_label_right, color.white, size.small)`)
    } else {
      lines.push(`    label.new(bar_index - 200, vp_val_1h, "VAL (Support)", xloc.bar_index, yloc.price, color.new(color.green, 30), label.style_label_right, color.white, size.tiny)`)
    }
    lines.push('')

    // 6. VP RETEST DETECTION - Pullback Labels
    const hasRetestInfo = alert.vp_val_retested || alert.vp_poc_retested || alert.vp_pullback_completed
    if (hasRetestInfo) {
      lines.push('    // ═══════════════════ VP RETEST / PULLBACK DETECTION ═══════════════════')
      lines.push('')

      // VAL Retest Label
      if (alert.vp_val_retested) {
        const valRetestStatus = alert.vp_val_retest_rejected ? '✓ REJECTED' : '⚠ Touched'
        const valRetestColor = alert.vp_val_retest_rejected ? 'color.lime' : 'color.yellow'
        const valRetestDt = alert.vp_val_retest_dt ? new Date(alert.vp_val_retest_dt).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
        lines.push('    // 🔄 VAL RETEST Detection')
        lines.push(`    label.new(bar_index - 50, vp_val_1h, "VAL RETEST ${valRetestStatus}\\n${valRetestDt}", xloc.bar_index, yloc.price, ${valRetestColor}, label.style_label_up, color.white, size.normal)`)
        lines.push('')
      }

      // POC Retest Label
      if (alert.vp_poc_retested) {
        const pocRetestStatus = alert.vp_poc_retest_rejected ? '✓ REJECTED' : '⚠ Touched'
        const pocRetestColor = alert.vp_poc_retest_rejected ? 'color.lime' : 'color.yellow'
        const pocRetestDt = alert.vp_poc_retest_dt ? new Date(alert.vp_poc_retest_dt).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
        lines.push('    // 🔄 POC RETEST Detection')
        lines.push(`    label.new(bar_index - 30, vp_poc_1h, "POC RETEST ${pocRetestStatus}\\n${pocRetestDt}", xloc.bar_index, yloc.price, ${pocRetestColor}, label.style_label_up, color.white, size.normal)`)
        lines.push('')
      }

      // OB Confluence Badge
      if (alert.vp_ob_confluence) {
        const obTf = alert.vp_ob_confluence_tf || 'OB'
        lines.push('    // 🎯 OB + VP CONFLUENCE')
        lines.push(`    label.new(bar_index + 30, vp_val_1h, "🎯 CONFLUENCE\\nVP + ${obTf}\\n(Ultra-Strong)", xloc.bar_index, yloc.price, color.aqua, label.style_label_left, color.white, size.normal)`)
        lines.push('')
      }

      // Pullback Completed Summary Label
      if (alert.vp_pullback_completed) {
        const pullbackLevel = alert.vp_pullback_level || 'VP'
        const pullbackQuality = alert.vp_pullback_quality || ''
        const qualityEmoji = pullbackQuality === 'STRONG' ? '💪' : pullbackQuality === 'GOOD' ? '✓' : '📍'
        const qualityColor = pullbackQuality === 'STRONG' ? 'color.lime' : pullbackQuality === 'GOOD' ? 'color.green' : 'color.yellow'
        lines.push('    // ✅ PULLBACK COMPLETED')
        lines.push(`    label.new(bar_index + 80, (vp_vah_1h + vp_val_1h) / 2, "${qualityEmoji} PULLBACK ${pullbackQuality}\\nRetest ${pullbackLevel}\\nBefore Entry ✓", xloc.bar_index, yloc.price, ${qualityColor}, label.style_label_left, color.white, size.large)`)
        lines.push('')
      }
    }

    // 7. Entry, SL, TP levels for context
    lines.push('    // ═══════════════════ ENTRY / SL / TP LEVELS ═══════════════════')
    lines.push('    // 📍 ENTRY / SL / TP Levels')
    lines.push(`    line.new(bar_index - 100, ${entryPrice}, bar_index + 50, ${entryPrice}, color=color.blue, style=line.style_solid, width=2, extend=extend.right)`)
    lines.push(`    label.new(bar_index + 50, ${entryPrice}, "ENTRY ${entryPrice.toFixed(5)}", xloc.bar_index, yloc.price, color.blue, label.style_label_left, color.white, size.small)`)
    lines.push(`    line.new(bar_index - 50, ${slPrice}, bar_index + 50, ${slPrice}, color=color.red, style=line.style_dotted, width=1, extend=extend.right)`)
    lines.push(`    label.new(bar_index + 50, ${slPrice}, "SL ${slPrice.toFixed(5)}", xloc.bar_index, yloc.price, color.red, label.style_label_left, color.white, size.tiny)`)
    lines.push('')

    // HVN Support for SL
    if (alert.vp_sl_near_hvn && alert.vp_sl_hvn_level) {
      lines.push('    // 🛡️ HVN Support Level (SL Protection)')
      lines.push(`    line.new(bar_index - 150, vp_hvn_sl, bar_index + 50, vp_hvn_sl, color=color.lime, style=line.style_solid, width=2, extend=extend.right)`)
      lines.push(`    label.new(bar_index - 150, vp_hvn_sl, "HVN SUPPORT 🛡️", xloc.bar_index, yloc.price, color.lime, label.style_label_right, color.white, size.small)`)
      lines.push('')
    }

    // 4H POC (if different from 1H - shows multi-TF confluence)
    if (alert.vp_poc_4h && Math.abs((alert.vp_poc_4h - (alert.vp_poc_1h || 0)) / (alert.vp_poc_1h || 1)) > 0.02) {
      lines.push('    // 🎯 POC 4H (Multi-TF Confluence)')
      lines.push(`    line.new(bar_index - 200, vp_poc_4h, bar_index + 50, vp_poc_4h, color=color.yellow, style=line.style_solid, width=2, extend=extend.right)`)
      lines.push(`    label.new(bar_index - 200, vp_poc_4h, "POC 4H", xloc.bar_index, yloc.price, color.yellow, label.style_label_right, color.white, size.small)`)
    }
  }

  // ==================== REFERENCE LINES ====================
  lines.push('')
  lines.push('// Reference Lines')

  if (hasTrendline) {
    lines.push('hline(tl_p1_price, "TL P1", color.new(color.orange, 70), hline.style_dotted)')
    lines.push('hline(tl_p2_price, "TL P2", color.new(color.orange, 70), hline.style_dotted)')
    if (alert.tl_break_price) {
      lines.push('hline(tl_break_price, "TL Break", color.new(color.green, 70), hline.style_dotted)')
    }
  }

  if (alert.fc_ob_1h_found && alert.fc_ob_1h_zone_high) {
    lines.push('hline(ob_1h_high, "OB 1H High", color.new(color.teal, 60), hline.style_dotted)')
    lines.push('hline(ob_1h_low, "OB 1H Low", color.new(color.teal, 60), hline.style_dotted)')
  }

  if (alert.fc_ob_4h_found && alert.fc_ob_4h_zone_high) {
    lines.push('hline(ob_4h_high, "OB 4H High", color.new(color.purple, 60), hline.style_dotted)')
    lines.push('hline(ob_4h_low, "OB 4H Low", color.new(color.purple, 60), hline.style_dotted)')
  }

  if (hasVP) {
    lines.push('hline(vp_poc_1h, "VP POC 1H", color.new(color.fuchsia, 40), hline.style_solid)')
    lines.push('hline(vp_vah_1h, "VP VAH 1H", color.new(color.fuchsia, 70), hline.style_dotted)')
    lines.push('hline(vp_val_1h, "VP VAL 1H", color.new(color.fuchsia, 70), hline.style_dotted)')
  }

  // ==================== INFO TABLE ====================
  lines.push('')
  lines.push('// Info Table')
  const hasRetestInfo = alert.vp_val_retested || alert.vp_poc_retested || alert.vp_pullback_completed
  const retestRows = hasRetestInfo ? (
    (alert.vp_val_retested ? 1 : 0) +
    (alert.vp_poc_retested ? 1 : 0) +
    (alert.vp_ob_confluence ? 1 : 0) +
    (alert.vp_pullback_completed ? 1 : 0)
  ) : 0
  const tableRows = 2 + (hasTrendline ? 3 : 0) + (alert.fc_ob_1h_found ? 2 : 0) + (alert.fc_ob_4h_found ? 2 : 0) + (hasVP ? 7 : 0) + retestRows
  lines.push(`var table infoTbl = table.new(position.top_right, 2, ${tableRows}, bgcolor=color.new(color.black, 80), border_width=1)`)
  lines.push('if barstate.islast')
  lines.push('    table.cell(infoTbl, 0, 0, "MEGA BUY Analysis", text_color=color.white, text_size=size.small)')
  lines.push('    table.merge_cells(infoTbl, 0, 0, 1, 0)')

  let row = 1
  if (hasTrendline) {
    lines.push(`    table.cell(infoTbl, 0, ${row}, "TL P1→P2", text_color=color.orange)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.tl_p1_price} → ${alert.tl_p2_price}", text_color=color.white)`)
    row++
    lines.push(`    table.cell(infoTbl, 0, ${row}, "TL Break", text_color=color.green)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.tl_break_price || 'N/A'}", text_color=color.white)`)
    row++
    const retestColor = (alert.tl_retest_count || 0) >= 3 ? 'color.lime' : (alert.tl_retest_count || 0) >= 1 ? 'color.yellow' : 'color.gray'
    lines.push(`    table.cell(infoTbl, 0, ${row}, "Retests", text_color=${retestColor})`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.tl_retest_count || 0}x", text_color=${retestColor})`)
    row++
  }

  if (alert.fc_ob_1h_found) {
    lines.push(`    table.cell(infoTbl, 0, ${row}, "OB 1H", text_color=color.teal)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.fc_ob_1h_zone_high?.toFixed(4)}-${alert.fc_ob_1h_zone_low?.toFixed(4)}", text_color=color.white)`)
    row++
    lines.push(`    table.cell(infoTbl, 0, ${row}, "1H Status", text_color=color.teal)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.fc_ob_1h_retest ? 'RETESTED ✓' : 'Not tested'}", text_color=${alert.fc_ob_1h_retest ? 'color.green' : 'color.gray'})`)
    row++
  }

  if (alert.fc_ob_4h_found) {
    lines.push(`    table.cell(infoTbl, 0, ${row}, "OB 4H", text_color=color.purple)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.fc_ob_4h_zone_high?.toFixed(4)}-${alert.fc_ob_4h_zone_low?.toFixed(4)}", text_color=color.white)`)
    row++
    lines.push(`    table.cell(infoTbl, 0, ${row}, "4H Status", text_color=color.purple)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.fc_ob_4h_retest ? 'RETESTED ✓' : 'Not tested'}", text_color=${alert.fc_ob_4h_retest ? 'color.green' : 'color.gray'})`)
    row++
  }

  // Volume Profile rows - Enhanced with zone information
  if (hasVP) {
    const entryPrice = alert.v3_entry_price || alert.entry_price || 0
    const slPrice = alert.v3_sl_price || (entryPrice * 0.95)
    const pocPrice = alert.vp_poc_1h || 0
    const valPrice = alert.vp_val_1h || 0

    const pocAboveEntry = pocPrice > entryPrice
    const pocDistancePct = entryPrice > 0 ? Math.abs(pocPrice - entryPrice) / entryPrice * 100 : 0
    const valProtectsSL = valPrice > slPrice && valPrice < entryPrice

    const vpGradeColor = alert.vp_grade === 'A+' || alert.vp_grade === 'A' ? 'color.lime' :
                         alert.vp_grade === 'B+' || alert.vp_grade === 'B' ? 'color.blue' :
                         alert.vp_grade === 'C' ? 'color.yellow' : 'color.red'

    // VP Grade + Label
    lines.push(`    table.cell(infoTbl, 0, ${row}, "VP Grade", text_color=color.fuchsia)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.vp_grade || 'N/A'} (${alert.vp_score || 0}/100)", text_color=${vpGradeColor})`)
    row++

    // VP Label (POC SUPPORT ZONE, etc.)
    lines.push(`    table.cell(infoTbl, 0, ${row}, "VP Label", text_color=color.fuchsia)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.vp_label || 'N/A'}", text_color=color.white)`)
    row++

    // POC Position (Above/Below Entry)
    const pocPosColor = pocAboveEntry ? 'color.lime' : 'color.white'
    const pocPosText = pocAboveEntry ? `ABOVE Entry (+${pocDistancePct.toFixed(1)}%) 🎯` : `BELOW Entry (-${pocDistancePct.toFixed(1)}%)`
    lines.push(`    table.cell(infoTbl, 0, ${row}, "POC 1H", text_color=color.fuchsia)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${pocPosText}", text_color=${pocPosColor})`)
    row++

    // Value Area Range
    lines.push(`    table.cell(infoTbl, 0, ${row}, "Value Area", text_color=color.fuchsia)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.vp_val_1h?.toFixed(5) || 'N/A'} - ${alert.vp_vah_1h?.toFixed(5) || 'N/A'}", text_color=color.white)`)
    row++

    // Entry Position in VA
    const entryPosColor = alert.vp_entry_position_1h === 'IN_VA' ? 'color.lime' : 'color.yellow'
    lines.push(`    table.cell(infoTbl, 0, ${row}, "Entry Pos", text_color=color.fuchsia)`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${alert.vp_entry_position_1h || 'N/A'}", text_color=${entryPosColor})`)
    row++

    // VAL Protection (Support above SL)
    const valProtColor = valProtectsSL ? 'color.lime' : 'color.gray'
    const valProtText = valProtectsSL ? `VAL Protects SL ✓` : 'No VAL Protection'
    lines.push(`    table.cell(infoTbl, 0, ${row}, "SL Prot.", text_color=${valProtColor})`)
    lines.push(`    table.cell(infoTbl, 1, ${row}, "${valProtText}", text_color=${valProtColor})`)
    row++

    // VP Retest Detection rows
    if (alert.vp_val_retested) {
      const valRetestStatus = alert.vp_val_retest_rejected ? 'RETESTED ✓ REJECTED' : 'RETESTED (not rejected)'
      const valRetestColor = alert.vp_val_retest_rejected ? 'color.lime' : 'color.yellow'
      lines.push(`    table.cell(infoTbl, 0, ${row}, "VAL Retest", text_color=color.green)`)
      lines.push(`    table.cell(infoTbl, 1, ${row}, "${valRetestStatus}", text_color=${valRetestColor})`)
      row++
    }

    if (alert.vp_poc_retested) {
      const pocRetestStatus = alert.vp_poc_retest_rejected ? 'RETESTED ✓ REJECTED' : 'RETESTED (not rejected)'
      const pocRetestColor = alert.vp_poc_retest_rejected ? 'color.lime' : 'color.yellow'
      lines.push(`    table.cell(infoTbl, 0, ${row}, "POC Retest", text_color=color.fuchsia)`)
      lines.push(`    table.cell(infoTbl, 1, ${row}, "${pocRetestStatus}", text_color=${pocRetestColor})`)
      row++
    }

    if (alert.vp_ob_confluence) {
      lines.push(`    table.cell(infoTbl, 0, ${row}, "Confluence", text_color=color.aqua)`)
      lines.push(`    table.cell(infoTbl, 1, ${row}, "VP + ${alert.vp_ob_confluence_tf || 'OB'} ✓", text_color=color.aqua)`)
      row++
    }

    if (alert.vp_pullback_completed) {
      const pullbackQuality = alert.vp_pullback_quality || ''
      const pullbackColor = pullbackQuality === 'STRONG' ? 'color.lime' : pullbackQuality === 'GOOD' ? 'color.green' : 'color.yellow'
      lines.push(`    table.cell(infoTbl, 0, ${row}, "Pullback", text_color=${pullbackColor})`)
      lines.push(`    table.cell(infoTbl, 1, ${row}, "${pullbackQuality} (${alert.vp_pullback_level || 'VP'}) ✓", text_color=${pullbackColor})`)
      row++
    }
  }

  return lines.join('\n')
}

// Helper function to generate TradingView PineScript code for trendline visualization
function generateTrendlinePineScript(
  symbol: string,
  tl_p1_date: string | null,
  tl_p1_price: number | null,
  tl_p2_date: string | null,
  tl_p2_price: number | null,
  tl_break_datetime: string | null,
  tl_break_price: number | null,
  tl_retest_count: number | null
): string {
  if (!tl_p1_date || !tl_p1_price || !tl_p2_date || !tl_p2_price) {
    return '// No trendline data available'
  }

  // Convert ISO date to Unix timestamp (milliseconds for TradingView)
  const p1Time = new Date(tl_p1_date).getTime()
  const p2Time = new Date(tl_p2_date).getTime()
  const breakTime = tl_break_datetime ? new Date(tl_break_datetime).getTime() : 0
  const breakPriceVal = tl_break_price || 0
  const retestCount = tl_retest_count || 0

  // Format dates for comments
  const p1DateStr = new Date(tl_p1_date).toISOString().slice(0, 16).replace('T', ' ')
  const p2DateStr = new Date(tl_p2_date).toISOString().slice(0, 16).replace('T', ' ')
  const breakDateStr = tl_break_datetime ? new Date(tl_break_datetime).toISOString().slice(0, 16).replace('T', ' ') : 'N/A'

  // Determine retest strength
  const retestStrength = retestCount >= 3 ? 'STRONG' : retestCount >= 1 ? 'MODERATE' : 'WEAK'

  const lines = [
    '//@version=5',
    `indicator("MEGA BUY TL - ${symbol}", overlay=true)`,
    '',
    '// ==========================================',
    '// MEGA BUY AI - Trendline Visualization',
    `// Symbol: ${symbol}`,
    `// P1: ${p1DateStr} UTC @ ${tl_p1_price}`,
    `// P2: ${p2DateStr} UTC @ ${tl_p2_price}`,
    `// Break: ${breakDateStr} UTC @ ${breakPriceVal || 'N/A'}`,
    `// Retests: ${retestCount}x (${retestStrength})`,
    '// ==========================================',
    '',
    '// Trendline Points (timestamps in ms)',
    `p1_time = ${p1Time}`,
    `p1_price = ${tl_p1_price}`,
    `p2_time = ${p2Time}`,
    `p2_price = ${tl_p2_price}`,
    `break_time = ${breakTime}`,
    `break_price = ${breakPriceVal}`,
    `retest_count = ${retestCount}`,
    '',
    '// Draw trendline on last bar',
    'if barstate.islast',
    '    line.new(p1_time, p1_price, p2_time, p2_price, xloc.bar_time, extend.right, color.orange, line.style_solid, 2)',
    '    label.new(p1_time, p1_price, "P1", xloc.bar_time, yloc.price, color.blue, label.style_label_down, color.white, size.small)',
    '    label.new(p2_time, p2_price, "P2", xloc.bar_time, yloc.price, color.blue, label.style_label_down, color.white, size.small)',
  ]

  // Add break point label with retest count if exists
  if (breakTime > 0 && breakPriceVal > 0) {
    lines.push(`    label.new(break_time, break_price, "BREAK\\n${retestCount}x retests", xloc.bar_time, yloc.price, color.green, label.style_label_up, color.white, size.normal)`)
  }

  lines.push('')
  lines.push('// Reference lines')
  lines.push('hline(p1_price, "P1", color.new(color.blue, 70), hline.style_dotted)')
  lines.push('hline(p2_price, "P2", color.new(color.blue, 70), hline.style_dotted)')

  if (breakPriceVal > 0) {
    lines.push('hline(break_price, "Break", color.new(color.green, 70), hline.style_dotted)')
  }

  // Add info table with retest count
  lines.push('')
  lines.push('// Info table')
  lines.push('var table infoTbl = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 80))')
  lines.push('if barstate.islast')
  lines.push('    table.cell(infoTbl, 0, 0, "P1", text_color=color.blue)')
  lines.push(`    table.cell(infoTbl, 1, 0, "${tl_p1_price}", text_color=color.white)`)
  lines.push('    table.cell(infoTbl, 0, 1, "P2", text_color=color.blue)')
  lines.push(`    table.cell(infoTbl, 1, 1, "${tl_p2_price}", text_color=color.white)`)
  lines.push('    table.cell(infoTbl, 0, 2, "Break", text_color=color.green)')
  lines.push(`    table.cell(infoTbl, 1, 2, "${breakPriceVal || 'N/A'}", text_color=color.white)`)
  lines.push(`    table.cell(infoTbl, 0, 3, "Retests", text_color=${retestCount >= 3 ? 'color.lime' : retestCount >= 1 ? 'color.yellow' : 'color.gray'})`)
  lines.push(`    table.cell(infoTbl, 1, 3, "${retestCount}x", text_color=${retestCount >= 3 ? 'color.lime' : retestCount >= 1 ? 'color.yellow' : 'color.gray'})`)

  return lines.join('\n')
}

interface BacktestRun {
  id: number
  symbol: string
  start_date: string
  end_date: string
  total_alerts: number
  valid_entries: number
  total_trades: number
  pnl_strategy_c: number
  pnl_strategy_d: number
  avg_pnl_c: number
  avg_pnl_d: number
  created_at: string
  stc_validated: number
  rejected_15m_alone: number
  with_tl_break: number
  delay_respected: number
  expired: number
  waiting: number
  strategy_version?: string  // v1 = legacy, v2 = optimized, v3 = golden box, v4 = optimized filters
  v2_rejected_count?: number
  v2_rejection_reasons?: Record<string, number>
  trade_scores?: number[]
  // V3 Golden Box Stats
  v3_entries_found?: number
  v3_rejected_count?: number
  v3_rejection_reasons?: Record<string, number>
  v3_avg_hours_to_entry?: number
  v3_avg_sl_distance?: number
  v3_avg_quality_score?: number
}

interface Alert {
  id: number
  alert_datetime: string
  timeframe: string
  price_open: number
  price_high: number
  price_low: number
  price_close: number
  volume: number
  score: number
  conditions: Record<string, boolean>
  indicators_15m: Record<string, number | null>
  indicators_30m: Record<string, number | null>
  indicators_1h: Record<string, number | null>
  stc_validated: boolean
  stc_valid_tfs: string
  is_15m_alone: boolean
  combo_tfs: string
  has_trendline: boolean
  tl_type: string | null
  tl_price_at_alert: number | null
  tl_p1_date: string | null
  tl_p1_price: number | null
  tl_p2_date: string | null
  tl_p2_price: number | null
  has_tl_break: boolean
  tl_break_datetime: string | null
  tl_break_price: number | null
  tl_break_delay_hours: number | null
  tl_retest_count: number | null
  delay_exceeded: boolean
  has_entry: boolean
  entry_datetime: string | null
  entry_price: number | null
  entry_diff_vs_alert: number | null
  entry_diff_vs_break: number | null
  // Progressive Conditions - Indicator VALUES
  prog_ema100_1h: number | null
  prog_ema20_4h: number | null
  prog_cloud_1h: number | null
  prog_cloud_30m: number | null
  prog_choch_bos_datetime: string | null
  prog_choch_bos_sh_price: number | null
  // Progressive Conditions - Price VALUES used
  prog_price_1h: number | null
  prog_price_30m: number | null
  prog_price_4h: number | null
  // Progressive Conditions - Validation RESULTS
  prog_valid_ema100_1h: boolean
  prog_valid_ema20_4h: boolean
  prog_valid_cloud_1h: boolean
  prog_valid_cloud_30m: boolean
  prog_choch_bos_valid: boolean
  // Fibonacci Bonus (4H)
  fib_bonus: boolean
  fib_swing_high: number | null
  fib_swing_low: number | null
  fib_levels: Record<string, { price: number; break: boolean; distance_pct: number }> | null
  // Fibonacci (1H)
  fib_swing_high_1h: number | null
  fib_swing_low_1h: number | null
  fib_levels_1h: Record<string, { price: number; break: boolean; distance_pct: number }> | null
  // Order Block (SMC) - 1H
  ob_bonus: boolean
  ob_zone_high: number | null
  ob_zone_low: number | null
  ob_datetime: string | null
  ob_distance_pct: number | null
  ob_position: string | null  // INSIDE, ABOVE, BELOW
  ob_strength: string | null  // STRONG, MODERATE, WEAK
  ob_impulse_pct: number | null
  ob_age_bars: number | null
  ob_mitigated: boolean
  ob_data: Record<string, unknown> | null
  // Order Block (SMC) - 4H
  ob_bonus_4h: boolean
  ob_zone_high_4h: number | null
  ob_zone_low_4h: number | null
  ob_datetime_4h: string | null
  ob_distance_pct_4h: number | null
  ob_position_4h: string | null
  ob_strength_4h: string | null
  ob_impulse_pct_4h: number | null
  ob_age_bars_4h: number | null
  ob_mitigated_4h: boolean
  ob_data_4h: Record<string, unknown> | null
  // BTC Correlation BONUS - 1H
  btc_corr_bonus_1h: boolean
  btc_price_1h: number | null
  btc_ema20_1h: number | null
  btc_ema50_1h: number | null
  btc_rsi_1h: number | null
  btc_trend_1h: string | null  // BULLISH, BEARISH, NEUTRAL
  // BTC Correlation BONUS - 4H
  btc_corr_bonus_4h: boolean
  btc_price_4h: number | null
  btc_ema20_4h: number | null
  btc_ema50_4h: number | null
  btc_rsi_4h: number | null
  btc_trend_4h: string | null  // BULLISH, BEARISH, NEUTRAL
  // ETH Correlation BONUS - 1H
  eth_corr_bonus_1h: boolean
  eth_price_1h: number | null
  eth_ema20_1h: number | null
  eth_ema50_1h: number | null
  eth_rsi_1h: number | null
  eth_trend_1h: string | null  // BULLISH, BEARISH, NEUTRAL
  // ETH Correlation BONUS - 4H
  eth_corr_bonus_4h: boolean
  eth_price_4h: number | null
  eth_ema20_4h: number | null
  eth_ema50_4h: number | null
  eth_rsi_4h: number | null
  eth_trend_4h: string | null  // BULLISH, BEARISH, NEUTRAL
  // Fair Value Gap (FVG) BONUS - 1H
  fvg_bonus_1h: boolean
  fvg_zone_high_1h: number | null
  fvg_zone_low_1h: number | null
  fvg_datetime_1h: string | null
  fvg_distance_pct_1h: number | null
  fvg_position_1h: string | null  // INSIDE, ABOVE, BELOW
  fvg_filled_pct_1h: number | null
  fvg_size_pct_1h: number | null
  fvg_age_bars_1h: number | null
  fvg_data_1h: Record<string, unknown> | null
  // Fair Value Gap (FVG) BONUS - 4H
  fvg_bonus_4h: boolean
  fvg_zone_high_4h: number | null
  fvg_zone_low_4h: number | null
  fvg_datetime_4h: string | null
  fvg_distance_pct_4h: number | null
  fvg_position_4h: string | null  // INSIDE, ABOVE, BELOW
  fvg_filled_pct_4h: number | null
  fvg_size_pct_4h: number | null
  fvg_age_bars_4h: number | null
  fvg_data_4h: Record<string, unknown> | null
  // Volume Spike BONUS - 1H
  vol_spike_bonus_1h: boolean
  vol_current_1h: number | null
  vol_avg_1h: number | null
  vol_ratio_1h: number | null
  vol_spike_level_1h: string | null  // NORMAL, HIGH, VERY_HIGH
  // Volume Spike BONUS - 4H
  vol_spike_bonus_4h: boolean
  vol_current_4h: number | null
  vol_avg_4h: number | null
  vol_ratio_4h: number | null
  vol_spike_level_4h: string | null  // NORMAL, HIGH, VERY_HIGH
  // RSI Multi-TF Alignment BONUS
  rsi_mtf_bonus: boolean
  rsi_1h: number | null
  rsi_4h: number | null
  rsi_daily: number | null
  rsi_aligned_count: number | null  // 0-3
  rsi_mtf_trend: string | null  // BULLISH, MIXED, BEARISH
  // ADX Trend Strength BONUS - 1H
  adx_bonus_1h: boolean
  adx_value_1h: number | null
  adx_plus_di_1h: number | null
  adx_minus_di_1h: number | null
  adx_strength_1h: string | null  // STRONG, MODERATE, WEAK
  // ADX Trend Strength BONUS - 4H
  adx_bonus_4h: boolean
  adx_value_4h: number | null
  adx_plus_di_4h: number | null
  adx_minus_di_4h: number | null
  adx_strength_4h: string | null  // STRONG, MODERATE, WEAK
  // MACD Momentum BONUS - 1H
  macd_bonus_1h: boolean
  macd_line_1h: number | null
  macd_signal_1h: number | null
  macd_histogram_1h: number | null
  macd_hist_growing_1h: boolean | null
  macd_trend_1h: string | null  // BULLISH, BEARISH, NEUTRAL
  // MACD Momentum BONUS - 4H
  macd_bonus_4h: boolean
  macd_line_4h: number | null
  macd_signal_4h: number | null
  macd_histogram_4h: number | null
  macd_hist_growing_4h: boolean | null
  macd_trend_4h: string | null  // BULLISH, BEARISH, NEUTRAL
  // Bollinger Squeeze BONUS - 1H
  bb_squeeze_bonus_1h: boolean
  bb_upper_1h: number | null
  bb_middle_1h: number | null
  bb_lower_1h: number | null
  bb_width_pct_1h: number | null
  bb_squeeze_1h: boolean | null
  bb_breakout_1h: string | null  // UP, DOWN, NONE
  // Bollinger Squeeze BONUS - 4H
  bb_squeeze_bonus_4h: boolean
  bb_upper_4h: number | null
  bb_middle_4h: number | null
  bb_lower_4h: number | null
  bb_width_pct_4h: number | null
  bb_squeeze_4h: boolean | null
  bb_breakout_4h: string | null  // UP, DOWN, NONE
  // Stochastic RSI BONUS - 1H
  stoch_rsi_bonus_1h: boolean
  stoch_rsi_k_1h: number | null
  stoch_rsi_d_1h: number | null
  stoch_rsi_zone_1h: string | null  // OVERSOLD, OVERBOUGHT, NEUTRAL
  stoch_rsi_cross_1h: string | null  // BULLISH, BEARISH, NONE
  // Stochastic RSI BONUS - 4H
  stoch_rsi_bonus_4h: boolean
  stoch_rsi_k_4h: number | null
  stoch_rsi_d_4h: number | null
  stoch_rsi_zone_4h: string | null  // OVERSOLD, OVERBOUGHT, NEUTRAL
  stoch_rsi_cross_4h: string | null  // BULLISH, BEARISH, NONE
  // EMA Stack BONUS - 1H
  ema_stack_bonus_1h: boolean
  ema8_1h: number | null
  ema21_1h: number | null
  ema50_1h: number | null
  ema100_1h_stack: number | null
  ema_stack_count_1h: number | null  // 0-3
  ema_stack_trend_1h: string | null  // PERFECT, PARTIAL, INVERSE, MIXED
  // EMA Stack BONUS - 4H
  ema_stack_bonus_4h: boolean
  ema8_4h: number | null
  ema21_4h: number | null
  ema50_4h: number | null
  ema100_4h_stack: number | null
  ema_stack_count_4h: number | null  // 0-3
  ema_stack_trend_4h: string | null  // PERFECT, PARTIAL, INVERSE, MIXED
  // V3 Golden Box Retest
  v3_entry_found: boolean | null
  v3_entry_datetime: string | null
  v3_entry_price: number | null
  v3_sl_price: number | null
  v3_box_high: number | null
  v3_box_low: number | null
  v3_box_range_pct: number | null
  v3_hours_to_entry: number | null
  v3_sl_distance_pct: number | null
  v3_quality_score: number | null
  v3_breakout_dt: string | null
  v3_breakout_high: number | null
  v3_distance_before_retest: number | null
  v3_rejected: boolean | null
  v3_rejection_reason: string | null
  // V3 Progressive conditions at retest time
  v3_prog_valid_ema100_1h: boolean | null
  v3_prog_valid_ema20_4h: boolean | null
  v3_prog_valid_cloud_1h: boolean | null
  v3_prog_valid_cloud_30m: boolean | null
  v3_prog_choch_bos_valid: boolean | null
  v3_prog_count: number | null
  v3_prog_ema100_1h_val: number | null
  v3_prog_ema20_4h_val: number | null
  v3_prog_cloud_1h_val: number | null
  v3_prog_cloud_30m_val: number | null
  v3_retest_price: number | null
  v3_retest_datetime: string | null
  // V3 Retest vs TL Break
  v3_retest_vs_tl_break: string | null  // 'BEFORE_TL', 'AFTER_TL', 'NO_TL_BREAK'
  v3_tl_break_datetime: string | null
  v3_hours_retest_vs_tl: number | null
  // V3 Risk Indicators
  v3_risk_level: string | null  // LOW, MEDIUM, HIGH, CRITICAL
  v3_risk_score: number | null
  v3_risk_reasons: Array<{
    factor: string
    message: string
    severity: string
    value: number
  }> | null
  // GB Power Score
  gb_power_score: number | null
  gb_power_grade: string | null  // A, B, C, D, F
  gb_volume_score: number | null
  gb_adx_score: number | null
  gb_ema_alignment_score: number | null
  gb_macd_momentum_score: number | null
  gb_fib_position_score: number | null
  gb_retest_quality_score: number | null
  gb_dmi_spread_score: number | null
  gb_rsi_strength_score: number | null
  gb_btc_correlation_score: number | null
  gb_confluence_score: number | null
  gb_dmi_spread: number | null
  // CVD (Cumulative Volume Delta) Analysis
  cvd_bonus: boolean
  cvd_score: number | null
  cvd_label: string | null  // STRONG BUY, BUY, NEUTRAL, WEAK, AVOID
  cvd_description: string | null
  cvd_at_break: number | null
  cvd_at_break_trend: string | null  // RISING, FALLING, FLAT
  cvd_at_break_signal: string | null  // BULLISH, BEARISH, NEUTRAL
  cvd_at_breakout: number | null
  cvd_at_breakout_spike: boolean
  cvd_at_breakout_signal: string | null  // STRONG_BUY, BUY, NEUTRAL, SELL
  cvd_at_retest: number | null
  cvd_at_retest_trend: string | null
  cvd_at_retest_signal: string | null  // ACCUMULATION, DISTRIBUTION, NEUTRAL
  cvd_at_entry: number | null
  cvd_at_entry_trend: string | null
  cvd_at_entry_signal: string | null  // CONFIRMED, WARNING, DANGER
  cvd_divergence: boolean
  cvd_divergence_type: string | null  // BULLISH, BEARISH, NONE
  vol_at_break_ratio: number | null
  vol_at_breakout_ratio: number | null
  vol_at_retest_ratio: number | null
  vol_at_entry_ratio: number | null
  // CVD 4H (Cumulative Volume Delta - 4H timeframe)
  cvd_4h_bonus: boolean
  cvd_4h_score: number | null
  cvd_4h_label: string | null
  cvd_4h_description: string | null
  cvd_4h_at_break: number | null
  cvd_4h_at_break_trend: string | null
  cvd_4h_at_break_signal: string | null
  cvd_4h_at_breakout: number | null
  cvd_4h_at_breakout_spike: boolean
  cvd_4h_at_breakout_signal: string | null
  cvd_4h_at_retest: number | null
  cvd_4h_at_retest_trend: string | null
  cvd_4h_at_retest_signal: string | null
  cvd_4h_at_entry: number | null
  cvd_4h_at_entry_trend: string | null
  cvd_4h_at_entry_signal: string | null
  cvd_4h_divergence: boolean
  cvd_4h_divergence_type: string | null
  vol_4h_at_break_ratio: number | null
  vol_4h_at_breakout_ratio: number | null
  vol_4h_at_retest_ratio: number | null
  vol_4h_at_entry_ratio: number | null
  // ADX/DI Analysis (1H)
  adx_di_1h_bonus: boolean
  adx_di_1h_score: number | null
  adx_di_1h_label: string | null
  adx_1h_at_break: number | null
  di_plus_1h_at_break: number | null
  di_minus_1h_at_break: number | null
  di_spread_1h_at_break: number | null
  adx_di_1h_at_break_signal: string | null
  adx_1h_at_breakout: number | null
  di_plus_1h_at_breakout: number | null
  di_minus_1h_at_breakout: number | null
  di_spread_1h_at_breakout: number | null
  adx_di_1h_at_breakout_signal: string | null
  adx_1h_at_retest: number | null
  di_plus_1h_at_retest: number | null
  di_minus_1h_at_retest: number | null
  di_spread_1h_at_retest: number | null
  adx_di_1h_at_retest_signal: string | null
  adx_1h_at_entry: number | null
  di_plus_1h_at_entry: number | null
  di_minus_1h_at_entry: number | null
  di_spread_1h_at_entry: number | null
  adx_di_1h_at_entry_signal: string | null
  di_plus_1h_overbought: boolean
  di_minus_1h_oversold: boolean
  // ADX/DI Analysis (4H)
  adx_di_4h_bonus: boolean
  adx_di_4h_score: number | null
  adx_di_4h_label: string | null
  adx_4h_at_break: number | null
  di_plus_4h_at_break: number | null
  di_minus_4h_at_break: number | null
  di_spread_4h_at_break: number | null
  adx_di_4h_at_break_signal: string | null
  adx_4h_at_breakout: number | null
  di_plus_4h_at_breakout: number | null
  di_minus_4h_at_breakout: number | null
  di_spread_4h_at_breakout: number | null
  adx_di_4h_at_breakout_signal: string | null
  adx_4h_at_retest: number | null
  di_plus_4h_at_retest: number | null
  di_minus_4h_at_retest: number | null
  di_spread_4h_at_retest: number | null
  adx_di_4h_at_retest_signal: string | null
  adx_4h_at_entry: number | null
  di_plus_4h_at_entry: number | null
  di_minus_4h_at_entry: number | null
  di_spread_4h_at_entry: number | null
  adx_di_4h_at_entry_signal: string | null
  di_plus_4h_overbought: boolean
  di_minus_4h_oversold: boolean

  // AI Agent Decision
  agent_decision: string | null
  agent_confidence: number | null
  agent_score: number | null
  agent_grade: string | null
  agent_bullish_count: number | null
  agent_bearish_count: number | null
  agent_neutral_count: number | null
  agent_bullish_factors: string | null
  agent_bearish_factors: string | null
  agent_reasoning: string | null
  agent_cvd_score: number | null
  agent_adx_score: number | null
  agent_trend_score: number | null
  agent_momentum_score: number | null
  agent_volume_score: number | null
  agent_confluence_score: number | null

  // Foreign Candle Order Block
  fc_ob_1h_found: boolean
  fc_ob_1h_count: number | null
  fc_ob_1h_type: string | null
  fc_ob_1h_zone_high: number | null
  fc_ob_1h_zone_low: number | null
  fc_ob_1h_strength: number | null
  fc_ob_1h_retest: boolean
  fc_ob_1h_distance_pct: number | null
  fc_ob_1h_datetime: string | null
  fc_ob_1h_in_zone: number
  fc_ob_1h_retested: number
  fc_ob_4h_found: boolean
  fc_ob_4h_count: number | null
  fc_ob_4h_type: string | null
  fc_ob_4h_zone_high: number | null
  fc_ob_4h_zone_low: number | null
  fc_ob_4h_strength: number | null
  fc_ob_4h_retest: boolean
  fc_ob_4h_distance_pct: number | null
  fc_ob_4h_datetime: string | null
  fc_ob_4h_in_zone: number
  fc_ob_4h_retested: number
  fc_ob_bonus: boolean
  fc_ob_score: number | null
  fc_ob_label: string | null
  // V4 Optimized Strategy
  v4_score: number | null
  v4_grade: string | null  // A+, A, B+, B, C, D
  v4_rejected: boolean
  v4_rejection_reason: string | null
  // V5 VP Trajectory Filter
  v5_score: number | null
  v5_grade: string | null
  v5_rejected: boolean
  v5_rejection_reason: string | null
  v5_val_bounce: boolean
  v5_poc_bounce: boolean
  v5_trajectory_strength: string | null  // STRONG, MODERATE, WEAK
  // V6 Advanced Scoring Strategy
  v6_score: number | null
  v6_grade: string | null  // A, B, C, F (A = 75.5% WR)
  v6_rejected: boolean
  v6_rejection_reason: string | null
  v6_retest_hours: number | null
  v6_entry_hours: number | null
  v6_distance_pct: number | null
  v6_rsi_at_entry: number | null
  v6_adx_at_entry: number | null
  v6_potential_pct: number | null
  v6_has_cvd_divergence: boolean
  v6_timing_adj: number | null
  v6_momentum_adj: number | null
  // Volume Profile Analysis
  vp_bonus: boolean
  vp_score: number | null
  vp_grade: string | null  // A+, A, B+, B, C, D
  vp_poc_1h: number | null
  vp_vah_1h: number | null
  vp_val_1h: number | null
  vp_hvn_levels_1h: number[] | null
  vp_lvn_levels_1h: number[] | null
  vp_total_volume_1h: number | null
  vp_poc_4h: number | null
  vp_vah_4h: number | null
  vp_val_4h: number | null
  vp_hvn_levels_4h: number[] | null
  vp_lvn_levels_4h: number[] | null
  vp_total_volume_4h: number | null
  vp_entry_position_1h: string | null  // AT_POC, IN_VA, ABOVE_VAH, BELOW_VAL
  vp_entry_position_4h: string | null
  vp_entry_vs_poc_pct_1h: number | null
  vp_entry_vs_poc_pct_4h: number | null
  vp_sl_near_hvn: boolean
  vp_sl_hvn_level: number | null
  vp_sl_hvn_distance_pct: number | null
  vp_sl_optimized: number | null
  vp_naked_poc_1h: boolean
  vp_naked_poc_level_1h: number | null
  vp_naked_poc_4h: boolean
  vp_naked_poc_level_4h: number | null
  vp_label: string | null
  vp_recommendation: string | null
  vp_details: object | null

  // VP Retest Detection
  vp_val_retested: boolean
  vp_val_retest_rejected: boolean
  vp_val_retest_dt: string | null
  vp_poc_retested: boolean
  vp_poc_retest_rejected: boolean
  vp_poc_retest_dt: string | null
  vp_vah_retested: boolean
  vp_hvn_retested: boolean
  vp_hvn_retest_level: number | null
  vp_ob_confluence: boolean
  vp_ob_confluence_tf: string | null
  vp_pullback_completed: boolean
  vp_pullback_level: string | null
  vp_pullback_quality: string | null

  // MEGA BUY Full Details (DMI Moves, RSI Moves, Volume %, LazyBar, EC RSI per TF)
  mega_buy_details: {
    dmi: Record<string, { di_plus_move: number | null; di_minus_move: number | null; adx_move: number | null; di_plus: number | null; di_minus: number | null; adx: number | null }>
    rsi: Record<string, { rsi_move: number | null; rsi_value: number | null; rsi_signal: string | number | null }>
    volume: Record<string, { vol_pct: number | null }>
    lazybar: Record<string, { lz_value: string | null; lz_raw: number | null; lz_color: string | null; lz_move: string | null }>
    ec: Record<string, { ec_move: number | null }>
  } | null

  status: string
}

interface Trade {
  id: number
  alert_datetime: string
  timeframe: string
  alert_price: number
  entry_price: number
  entry_datetime: string
  sl_price: number
  tp1_price: number
  tp2_price: number
  pnl_c: number
  pnl_d: number
  exit_reason_c: string
  exit_reason_d: string
  // Post-SL Recovery Analysis
  sl_then_recovered: boolean
  post_sl_max_price: number | null
  post_sl_max_gain_pct: number | null
  post_sl_fib_levels: Record<string, {
    price: number
    broken_before_sl: boolean
    broken_after_sl: boolean
    post_sl_max: number
  }> | null
  post_sl_monitoring_hours: number | null
  post_sl_would_have_won: boolean
  // V3 Golden Box
  strategy_version: string | null
  v3_box_high: number | null
  v3_box_low: number | null
  v3_hours_to_entry: number | null
  v3_sl_distance_pct: number | null
  v3_quality_score: number | null
  v3_breakout_dt: string | null
  v3_breakout_high: number | null
  v3_retest_datetime: string | null
  v3_retest_price: number | null
  v3_prog_count: number | null
  // MEGA BUY Details
  mega_buy_details: {
    dmi: Record<string, { di_plus_move: number | null; di_minus_move: number | null; adx_move: number | null; di_plus: number | null; di_minus: number | null; adx: number | null }>
    rsi: Record<string, { rsi_move: number | null; rsi_value: number | null; rsi_signal: string | number | null }>
    volume: Record<string, { vol_pct: number | null }>
    lazybar: Record<string, { lz_value: string | null; lz_raw: number | null; lz_color: string | null; lz_move: string | null }>
    ec: Record<string, { ec_move: number | null }>
  } | null
}

interface GroupedTrade {
  ids: number[]
  alert_datetimes: string[]
  timeframes: string[]
  alert_prices: number[]
  entry_price: number
  entry_datetime: string
  sl_price: number
  tp1_price: number
  tp2_price: number
  pnl_c: number
  pnl_d: number
  exit_reason_c: string
  exit_reason_d: string
  is_combined: boolean
  // Post-SL Recovery Analysis
  sl_then_recovered: boolean
  post_sl_max_price: number | null
  post_sl_max_gain_pct: number | null
  post_sl_fib_levels: Record<string, {
    price: number
    broken_before_sl: boolean
    broken_after_sl: boolean
    post_sl_max: number
  }> | null
  post_sl_monitoring_hours: number | null
  post_sl_would_have_won: boolean
  // V3 Golden Box
  strategy_version: string | null
  v3_box_high: number | null
  v3_box_low: number | null
  v3_hours_to_entry: number | null
  v3_sl_distance_pct: number | null
  v3_quality_score: number | null
  v3_breakout_dt: string | null
  v3_breakout_high: number | null
  v3_retest_datetime: string | null
  v3_retest_price: number | null
  v3_prog_count: number | null
  // MEGA BUY Details
  mega_buy_details: {
    dmi: Record<string, { di_plus_move: number | null; di_minus_move: number | null; adx_move: number | null; di_plus: number | null; di_minus: number | null; adx: number | null }>
    rsi: Record<string, { rsi_move: number | null; rsi_value: number | null; rsi_signal: string | number | null }>
    volume: Record<string, { vol_pct: number | null }>
    lazybar: Record<string, { lz_value: string | null; lz_raw: number | null; lz_color: string | null; lz_move: string | null }>
    ec: Record<string, { ec_move: number | null }>
  } | null
}

// Group trades by entry (same entry_datetime and entry_price)
function groupTradesByEntry(trades: Trade[]): GroupedTrade[] {
  const groups = new Map<string, Trade[]>()

  for (const trade of trades) {
    // Key by entry_datetime and entry_price
    const key = `${trade.entry_datetime}_${trade.entry_price}`
    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key)!.push(trade)
  }

  const result: GroupedTrade[] = []
  for (const [, groupTrades] of groups) {
    // Sort by timeframe (15m < 30m < 1h < 4h)
    const tfOrder = { '15m': 1, '30m': 2, '1h': 3, '4h': 4 }
    groupTrades.sort((a, b) => (tfOrder[a.timeframe as keyof typeof tfOrder] || 5) - (tfOrder[b.timeframe as keyof typeof tfOrder] || 5))

    const first = groupTrades[0]
    result.push({
      ids: groupTrades.map(t => t.id),
      alert_datetimes: groupTrades.map(t => t.alert_datetime),
      timeframes: groupTrades.map(t => t.timeframe),
      alert_prices: groupTrades.map(t => t.alert_price),
      entry_price: first.entry_price,
      entry_datetime: first.entry_datetime,
      sl_price: first.sl_price,
      tp1_price: first.tp1_price,
      tp2_price: first.tp2_price,
      pnl_c: first.pnl_c, // Same entry = same P&L
      pnl_d: first.pnl_d,
      exit_reason_c: first.exit_reason_c,
      exit_reason_d: first.exit_reason_d,
      is_combined: groupTrades.length > 1,
      // Post-SL Recovery Analysis
      sl_then_recovered: first.sl_then_recovered,
      post_sl_max_price: first.post_sl_max_price,
      post_sl_max_gain_pct: first.post_sl_max_gain_pct,
      post_sl_fib_levels: first.post_sl_fib_levels,
      post_sl_monitoring_hours: first.post_sl_monitoring_hours,
      post_sl_would_have_won: first.post_sl_would_have_won,
      // V3 Golden Box
      strategy_version: first.strategy_version,
      v3_box_high: first.v3_box_high,
      v3_box_low: first.v3_box_low,
      v3_hours_to_entry: first.v3_hours_to_entry,
      v3_sl_distance_pct: first.v3_sl_distance_pct,
      v3_quality_score: first.v3_quality_score,
      v3_breakout_dt: first.v3_breakout_dt,
      v3_breakout_high: first.v3_breakout_high,
      v3_retest_datetime: first.v3_retest_datetime,
      v3_retest_price: first.v3_retest_price,
      v3_prog_count: first.v3_prog_count,
      // MEGA BUY Details
      mega_buy_details: first.mega_buy_details
    })
  }

  // Sort by entry datetime
  result.sort((a, b) => new Date(a.entry_datetime).getTime() - new Date(b.entry_datetime).getTime())

  return result
}

// Condition Badge Component
function ConditionBadge({ valid, label, value }: { valid: boolean; label: string; value?: string | number | null }) {
  return (
    <div className={`flex items-center justify-between p-2 rounded-lg ${valid ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
      <div className="flex items-center gap-2">
        {valid ? (
          <CheckCircle className="w-4 h-4 text-green-400" />
        ) : (
          <XCircle className="w-4 h-4 text-red-400" />
        )}
        <span className={`text-sm font-medium ${valid ? 'text-green-400' : 'text-red-400'}`}>{label}</span>
      </div>
      {value !== undefined && value !== null && (
        <span className="text-xs text-gray-400 font-mono">{typeof value === 'number' ? value.toFixed(4) : value}</span>
      )}
    </div>
  )
}

// TradingView Code Block Component (Combined: TL + OB + VP)
function TradingViewCodeBlock({
  symbol,
  alert
}: {
  symbol: string
  alert: {
    // Trendline fields
    tl_p1_date?: string | null
    tl_p1_price?: number | null
    tl_p2_date?: string | null
    tl_p2_price?: number | null
    tl_break_datetime?: string | null
    tl_break_price?: number | null
    tl_retest_count?: number | null
    // FC OB fields
    fc_ob_1h_found?: boolean
    fc_ob_1h_zone_high?: number | null
    fc_ob_1h_zone_low?: number | null
    fc_ob_1h_datetime?: string | null
    fc_ob_1h_type?: string | null
    fc_ob_1h_strength?: number | null
    fc_ob_1h_retest?: boolean
    fc_ob_1h_in_zone?: number
    fc_ob_1h_retested?: number
    fc_ob_4h_found?: boolean
    fc_ob_4h_zone_high?: number | null
    fc_ob_4h_zone_low?: number | null
    fc_ob_4h_datetime?: string | null
    fc_ob_4h_type?: string | null
    fc_ob_4h_strength?: number | null
    fc_ob_4h_retest?: boolean
    fc_ob_4h_in_zone?: number
    fc_ob_4h_retested?: number
    // Volume Profile fields
    vp_score?: number | null
    vp_grade?: string | null
    vp_poc_1h?: number | null
    vp_vah_1h?: number | null
    vp_val_1h?: number | null
    vp_poc_4h?: number | null
    vp_vah_4h?: number | null
    vp_val_4h?: number | null
    vp_entry_position_1h?: string | null
    vp_entry_position_4h?: string | null
    vp_sl_near_hvn?: boolean
    vp_sl_hvn_level?: number | null
    vp_hvn_levels_1h?: number[] | null
    vp_lvn_levels_1h?: number[] | null
    vp_label?: string | null
    // Trade fields
    entry_price?: number | null
    v3_retest_price?: number | null
    alert_datetime?: string
  }
}) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const pineScript = generateCombinedPineScript(symbol, alert)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(pineScript)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="mt-4 border border-orange-500/30 rounded-lg bg-orange-500/5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-orange-500/10 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          <span className="text-orange-400 font-mono text-sm">📊</span>
          <span className="text-sm font-medium text-orange-400">TradingView PineScript Code</span>
          <span className="text-xs text-gray-500">(Click to {expanded ? 'collapse' : 'expand'})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleCopy()
            }}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              copied
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-orange-500/20 text-orange-400 border border-orange-500/30 hover:bg-orange-500/30'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3 h-3" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy Code
              </>
            )}
          </button>
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="p-3 border-t border-orange-500/20">
          <div className="bg-gray-900 rounded-lg p-3 overflow-x-auto">
            <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">
              {pineScript}
            </pre>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            <strong>Instructions:</strong> Copy this code → Open TradingView → Pine Editor → Create new script → Paste → Add to chart
          </div>
        </div>
      )}
    </div>
  )
}

// Alert Detail Modal
function AlertDetailModal({ alert, onClose }: { alert: Alert; onClose: () => void }) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString("fr-FR")
  }

  const formatNumber = (num: number | null | undefined, decimals = 4) => {
    if (num === null || num === undefined) return '-'
    return num.toFixed(decimals)
  }

  // MEGA BUY Conditions mapping
  const megaBuyConditions = [
    { key: 'RSI_surge', label: 'RSI Surge (>=12)', mandatory: true },
    { key: 'DI+_surge', label: 'DI+ Surge (>=10)', mandatory: true },
    { key: 'AST_flip', label: 'AST SuperTrend Flip', mandatory: true },
    { key: 'CHoCH', label: 'CHoCH/BOS', mandatory: false },
    { key: 'Green_Zone', label: 'Green Zone (ATR+Vol)', mandatory: false },
    { key: 'LazyBar', label: 'LazyBar Spike', mandatory: false },
    { key: 'Volume', label: 'Volume Spike', mandatory: false },
    { key: 'ST_break', label: 'SuperTrend Break', mandatory: false },
    { key: 'PP_buy', label: 'PP SuperTrend Buy', mandatory: false },
    { key: 'Entry_Confirm', label: 'Entry Confirmation', mandatory: false },
  ]

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Info className="w-5 h-5 text-purple-400" />
              Alert Details - {alert.timeframe}
            </h2>
            <p className="text-sm text-gray-400">{formatDate(alert.alert_datetime)}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">Price Close</div>
              <div className="text-lg font-mono text-white">{formatNumber(alert.price_close, 6)}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">Score</div>
              <div className={`text-lg font-bold ${alert.score >= 8 ? 'text-green-400' : alert.score >= 7 ? 'text-yellow-400' : 'text-red-400'}`}>
                {alert.score}/10
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">Status</div>
              <div className={`text-lg font-medium ${
                alert.status === 'VALID' ? 'text-green-400' :
                alert.status === 'WAITING' ? 'text-yellow-400' :
                'text-red-400'
              }`}>{alert.status}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">Timeframes</div>
              <div className="text-lg font-medium text-blue-400">{alert.combo_tfs}</div>
            </div>
          </div>

          {/* Bonus Filters Summary */}
          {alert.has_entry && (
            <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-400" />
                Bonus Filters
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {/* Fibonacci 4H */}
                <div className={`p-2 rounded-lg border ${alert.fib_bonus ? 'bg-green-500/10 border-green-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Fibonacci 4H</div>
                  <div className={`text-sm font-bold ${alert.fib_bonus ? 'text-green-400' : 'text-gray-500'}`}>
                    {alert.fib_bonus ? '38.2% BREAK' : 'NO BREAK'}
                  </div>
                </div>
                {/* Order Block 1H */}
                <div className={`p-2 rounded-lg border ${alert.ob_bonus ? 'bg-purple-500/10 border-purple-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Order Block 1H</div>
                  <div className={`text-sm font-bold ${alert.ob_bonus ? 'text-purple-400' : 'text-gray-500'}`}>
                    {alert.ob_bonus ? `${alert.ob_position} (${alert.ob_strength})` : 'NO OB'}
                  </div>
                </div>
                {/* Order Block 4H */}
                <div className={`p-2 rounded-lg border ${alert.ob_bonus_4h ? 'bg-orange-500/10 border-orange-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Order Block 4H</div>
                  <div className={`text-sm font-bold ${alert.ob_bonus_4h ? 'text-orange-400' : 'text-gray-500'}`}>
                    {alert.ob_bonus_4h ? `${alert.ob_position_4h} (${alert.ob_strength_4h})` : 'NO OB'}
                  </div>
                </div>
                {/* BTC Correlation 1H */}
                <div className={`p-2 rounded-lg border ${alert.btc_corr_bonus_1h ? 'bg-green-500/10 border-green-500/30' : alert.btc_trend_1h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BTC 1H</div>
                  <div className={`text-sm font-bold ${alert.btc_corr_bonus_1h ? 'text-green-400' : alert.btc_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {alert.btc_trend_1h || 'N/A'}
                    {alert.btc_rsi_1h && <span className="text-xs ml-1 text-gray-400">RSI {alert.btc_rsi_1h.toFixed(0)}</span>}
                  </div>
                </div>
                {/* BTC Correlation 4H */}
                <div className={`p-2 rounded-lg border ${alert.btc_corr_bonus_4h ? 'bg-emerald-500/10 border-emerald-500/30' : alert.btc_trend_4h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BTC 4H</div>
                  <div className={`text-sm font-bold ${alert.btc_corr_bonus_4h ? 'text-emerald-400' : alert.btc_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {alert.btc_trend_4h || 'N/A'}
                    {alert.btc_rsi_4h && <span className="text-xs ml-1 text-gray-400">RSI {alert.btc_rsi_4h.toFixed(0)}</span>}
                  </div>
                </div>
                {/* ETH Correlation 1H */}
                <div className={`p-2 rounded-lg border ${alert.eth_corr_bonus_1h ? 'bg-indigo-500/10 border-indigo-500/30' : alert.eth_trend_1h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ETH 1H</div>
                  <div className={`text-sm font-bold ${alert.eth_corr_bonus_1h ? 'text-indigo-400' : alert.eth_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {alert.eth_trend_1h || 'N/A'}
                    {alert.eth_rsi_1h && <span className="text-xs ml-1 text-gray-400">RSI {alert.eth_rsi_1h.toFixed(0)}</span>}
                  </div>
                </div>
                {/* ETH Correlation 4H */}
                <div className={`p-2 rounded-lg border ${alert.eth_corr_bonus_4h ? 'bg-violet-500/10 border-violet-500/30' : alert.eth_trend_4h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ETH 4H</div>
                  <div className={`text-sm font-bold ${alert.eth_corr_bonus_4h ? 'text-violet-400' : alert.eth_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {alert.eth_trend_4h || 'N/A'}
                    {alert.eth_rsi_4h && <span className="text-xs ml-1 text-gray-400">RSI {alert.eth_rsi_4h.toFixed(0)}</span>}
                  </div>
                </div>
                {/* FVG 1H */}
                <div className={`p-2 rounded-lg border ${alert.fvg_bonus_1h ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">FVG 1H</div>
                  <div className={`text-sm font-bold ${alert.fvg_bonus_1h ? 'text-cyan-400' : 'text-gray-500'}`}>
                    {alert.fvg_bonus_1h ? `${alert.fvg_position_1h} ${alert.fvg_size_pct_1h?.toFixed(1)}%` : 'NO FVG'}
                  </div>
                </div>
                {/* FVG 4H */}
                <div className={`p-2 rounded-lg border ${alert.fvg_bonus_4h ? 'bg-teal-500/10 border-teal-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">FVG 4H</div>
                  <div className={`text-sm font-bold ${alert.fvg_bonus_4h ? 'text-teal-400' : 'text-gray-500'}`}>
                    {alert.fvg_bonus_4h ? `${alert.fvg_position_4h} ${alert.fvg_size_pct_4h?.toFixed(1)}%` : 'NO FVG'}
                  </div>
                </div>
                {/* Volume Spike 1H */}
                <div className={`p-2 rounded-lg border ${alert.vol_spike_bonus_1h ? 'bg-amber-500/10 border-amber-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Vol 1H</div>
                  <div className={`text-sm font-bold ${alert.vol_spike_bonus_1h ? 'text-amber-400' : 'text-gray-500'}`}>
                    {alert.vol_spike_bonus_1h ? `${alert.vol_spike_level_1h} ${alert.vol_ratio_1h?.toFixed(1)}x` : 'NORMAL'}
                  </div>
                </div>
                {/* Volume Spike 4H */}
                <div className={`p-2 rounded-lg border ${alert.vol_spike_bonus_4h ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Vol 4H</div>
                  <div className={`text-sm font-bold ${alert.vol_spike_bonus_4h ? 'text-yellow-400' : 'text-gray-500'}`}>
                    {alert.vol_spike_bonus_4h ? `${alert.vol_spike_level_4h} ${alert.vol_ratio_4h?.toFixed(1)}x` : 'NORMAL'}
                  </div>
                </div>
                {/* RSI Multi-TF */}
                <div className={`p-2 rounded-lg border ${alert.rsi_mtf_bonus ? 'bg-rose-500/10 border-rose-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">RSI MTF</div>
                  <div className={`text-sm font-bold ${alert.rsi_mtf_bonus ? 'text-rose-400' : alert.rsi_mtf_trend === 'BEARISH' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.rsi_mtf_trend || 'N/A'} {alert.rsi_aligned_count !== null ? `(${alert.rsi_aligned_count}/3)` : ''}
                  </div>
                </div>
                {/* ADX 1H */}
                <div className={`p-2 rounded-lg border ${alert.adx_bonus_1h ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ADX 1H</div>
                  <div className={`text-sm font-bold ${alert.adx_bonus_1h ? 'text-indigo-400' : alert.adx_strength_1h === 'WEAK' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.adx_strength_1h || 'N/A'} {alert.adx_value_1h !== null ? `(${alert.adx_value_1h?.toFixed(0)})` : ''}
                  </div>
                </div>
                {/* ADX 4H */}
                <div className={`p-2 rounded-lg border ${alert.adx_bonus_4h ? 'bg-violet-500/10 border-violet-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ADX 4H</div>
                  <div className={`text-sm font-bold ${alert.adx_bonus_4h ? 'text-violet-400' : alert.adx_strength_4h === 'WEAK' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.adx_strength_4h || 'N/A'} {alert.adx_value_4h !== null ? `(${alert.adx_value_4h?.toFixed(0)})` : ''}
                  </div>
                </div>
                {/* MACD 1H */}
                <div className={`p-2 rounded-lg border ${alert.macd_bonus_1h ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">MACD 1H</div>
                  <div className={`text-sm font-bold ${alert.macd_bonus_1h ? 'text-emerald-400' : alert.macd_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.macd_trend_1h || 'N/A'} {alert.macd_hist_growing_1h ? '↑' : ''}
                  </div>
                </div>
                {/* MACD 4H */}
                <div className={`p-2 rounded-lg border ${alert.macd_bonus_4h ? 'bg-teal-500/10 border-teal-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">MACD 4H</div>
                  <div className={`text-sm font-bold ${alert.macd_bonus_4h ? 'text-teal-400' : alert.macd_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.macd_trend_4h || 'N/A'} {alert.macd_hist_growing_4h ? '↑' : ''}
                  </div>
                </div>
                {/* BB Squeeze 1H */}
                <div className={`p-2 rounded-lg border ${alert.bb_squeeze_bonus_1h ? 'bg-fuchsia-500/10 border-fuchsia-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BB 1H</div>
                  <div className={`text-sm font-bold ${alert.bb_squeeze_bonus_1h ? 'text-fuchsia-400' : alert.bb_breakout_1h === 'DOWN' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.bb_squeeze_1h ? 'SQZ' : ''}{alert.bb_breakout_1h === 'UP' ? '↑' : alert.bb_breakout_1h === 'DOWN' ? '↓' : ''} {alert.bb_width_pct_1h?.toFixed(1)}%
                  </div>
                </div>
                {/* BB Squeeze 4H */}
                <div className={`p-2 rounded-lg border ${alert.bb_squeeze_bonus_4h ? 'bg-pink-500/10 border-pink-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BB 4H</div>
                  <div className={`text-sm font-bold ${alert.bb_squeeze_bonus_4h ? 'text-pink-400' : alert.bb_breakout_4h === 'DOWN' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.bb_squeeze_4h ? 'SQZ' : ''}{alert.bb_breakout_4h === 'UP' ? '↑' : alert.bb_breakout_4h === 'DOWN' ? '↓' : ''} {alert.bb_width_pct_4h?.toFixed(1)}%
                  </div>
                </div>
                {/* StochRSI 1H */}
                <div className={`p-2 rounded-lg border ${alert.stoch_rsi_bonus_1h ? 'bg-sky-500/10 border-sky-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">StochRSI 1H</div>
                  <div className={`text-sm font-bold ${alert.stoch_rsi_bonus_1h ? 'text-sky-400' : alert.stoch_rsi_zone_1h === 'OVERBOUGHT' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.stoch_rsi_zone_1h || 'N/A'} {alert.stoch_rsi_cross_1h === 'BULLISH' ? '↑' : ''}
                  </div>
                </div>
                {/* StochRSI 4H */}
                <div className={`p-2 rounded-lg border ${alert.stoch_rsi_bonus_4h ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">StochRSI 4H</div>
                  <div className={`text-sm font-bold ${alert.stoch_rsi_bonus_4h ? 'text-cyan-400' : alert.stoch_rsi_zone_4h === 'OVERBOUGHT' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.stoch_rsi_zone_4h || 'N/A'} {alert.stoch_rsi_cross_4h === 'BULLISH' ? '↑' : ''}
                  </div>
                </div>
                {/* EMA Stack 1H */}
                <div className={`p-2 rounded-lg border ${alert.ema_stack_bonus_1h ? 'bg-lime-500/10 border-lime-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">EMA Stack 1H</div>
                  <div className={`text-sm font-bold ${alert.ema_stack_bonus_1h ? 'text-lime-400' : alert.ema_stack_trend_1h === 'INVERSE' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.ema_stack_trend_1h || 'N/A'} {alert.ema_stack_count_1h !== null ? `(${alert.ema_stack_count_1h}/3)` : ''}
                  </div>
                </div>
                {/* EMA Stack 4H */}
                <div className={`p-2 rounded-lg border ${alert.ema_stack_bonus_4h ? 'bg-green-500/10 border-green-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">EMA Stack 4H</div>
                  <div className={`text-sm font-bold ${alert.ema_stack_bonus_4h ? 'text-green-400' : alert.ema_stack_trend_4h === 'INVERSE' ? 'text-red-400' : 'text-gray-500'}`}>
                    {alert.ema_stack_trend_4h || 'N/A'} {alert.ema_stack_count_4h !== null ? `(${alert.ema_stack_count_4h}/3)` : ''}
                  </div>
                </div>
                {/* Bonus Count */}
                <div className="p-2 rounded-lg border bg-gray-700/30 border-gray-600">
                  <div className="text-xs text-gray-400">Total Bonus</div>
                  <div className="text-sm font-bold text-white">
                    {[alert.fib_bonus, alert.ob_bonus, alert.ob_bonus_4h, alert.btc_corr_bonus_1h, alert.btc_corr_bonus_4h, alert.eth_corr_bonus_1h, alert.eth_corr_bonus_4h, alert.fvg_bonus_1h, alert.fvg_bonus_4h, alert.vol_spike_bonus_1h, alert.vol_spike_bonus_4h, alert.rsi_mtf_bonus, alert.adx_bonus_1h, alert.adx_bonus_4h, alert.macd_bonus_1h, alert.macd_bonus_4h, alert.bb_squeeze_bonus_1h, alert.bb_squeeze_bonus_4h, alert.stoch_rsi_bonus_1h, alert.stoch_rsi_bonus_4h, alert.ema_stack_bonus_1h, alert.ema_stack_bonus_4h].filter(Boolean).length}/22
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* MEGA BUY 10 Conditions */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Target className="w-4 h-4 text-purple-400" />
              MEGA BUY Conditions ({alert.score}/10)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {megaBuyConditions.map(cond => (
                <ConditionBadge
                  key={cond.key}
                  valid={alert.conditions[cond.key] || false}
                  label={`${cond.mandatory ? '* ' : ''}${cond.label}`}
                />
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">* = Condition obligatoire</p>
          </div>

          {/* STC Validation */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">STC Oversold Validation</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <ConditionBadge
                valid={alert.stc_validated}
                label="STC Oversold (<0.2)"
                value={alert.stc_valid_tfs || 'None'}
              />
              <ConditionBadge
                valid={!alert.is_15m_alone}
                label="15m Combo Filter"
                value={alert.is_15m_alone ? 'REJECTED (15m alone)' : `OK (${alert.combo_tfs})`}
              />
            </div>
          </div>

          {/* Indicators by Timeframe */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Indicators by Timeframe</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 15m */}
              <div className="bg-gray-800/30 rounded-lg p-3">
                <div className="text-xs font-medium text-blue-400 mb-2">15m</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">STC</span>
                    <span className={`font-mono ${(alert.indicators_15m?.stc ?? 1) < 0.2 ? 'text-green-400' : 'text-gray-300'}`}>
                      {formatNumber(alert.indicators_15m?.stc)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">RSI</span>
                    <span className="font-mono text-gray-300">{formatNumber(alert.indicators_15m?.rsi, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI+</span>
                    <span className="font-mono text-green-400">{formatNumber(alert.indicators_15m?.di_plus, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI-</span>
                    <span className="font-mono text-red-400">{formatNumber(alert.indicators_15m?.di_minus, 2)}</span>
                  </div>
                </div>
              </div>

              {/* 30m */}
              <div className="bg-gray-800/30 rounded-lg p-3">
                <div className="text-xs font-medium text-blue-400 mb-2">30m</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">STC</span>
                    <span className={`font-mono ${(alert.indicators_30m?.stc ?? 1) < 0.2 ? 'text-green-400' : 'text-gray-300'}`}>
                      {formatNumber(alert.indicators_30m?.stc)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">RSI</span>
                    <span className="font-mono text-gray-300">{formatNumber(alert.indicators_30m?.rsi, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI+</span>
                    <span className="font-mono text-green-400">{formatNumber(alert.indicators_30m?.di_plus, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI-</span>
                    <span className="font-mono text-red-400">{formatNumber(alert.indicators_30m?.di_minus, 2)}</span>
                  </div>
                </div>
              </div>

              {/* 1h */}
              <div className="bg-gray-800/30 rounded-lg p-3">
                <div className="text-xs font-medium text-blue-400 mb-2">1h</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">STC</span>
                    <span className={`font-mono ${(alert.indicators_1h?.stc ?? 1) < 0.2 ? 'text-green-400' : 'text-gray-300'}`}>
                      {formatNumber(alert.indicators_1h?.stc)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">RSI</span>
                    <span className="font-mono text-gray-300">{formatNumber(alert.indicators_1h?.rsi, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI+</span>
                    <span className="font-mono text-green-400">{formatNumber(alert.indicators_1h?.di_plus, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DI-</span>
                    <span className="font-mono text-red-400">{formatNumber(alert.indicators_1h?.di_minus, 2)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MEGA BUY Full Details (DMI Moves, RSI Moves, Volume %, LazyBar, EC RSI per TF) */}
          {alert.mega_buy_details && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-400" />
                MEGA BUY Full Details
              </h3>

              {/* DMI Moves Table */}
              <div className="bg-gray-800/30 rounded-lg p-3 mb-3">
                <div className="text-xs font-medium text-yellow-400 mb-2">DMI Moves</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-gray-400 py-1 px-2">Metric</th>
                        <th className="text-center text-blue-400 py-1 px-2">15m</th>
                        <th className="text-center text-blue-400 py-1 px-2">30m</th>
                        <th className="text-center text-blue-400 py-1 px-2">1h</th>
                        <th className="text-center text-blue-400 py-1 px-2">4h</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-400 py-1 px-2">DI+ Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.dmi?.[tf]?.di_plus_move
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val >= 10 ? 'text-green-400' : val != null && val >= 0 ? 'text-gray-300' : val != null ? 'text-red-400' : 'text-gray-500'}`}>
                              {val != null ? val.toFixed(1) : '-'}
                            </td>
                          )
                        })}
                      </tr>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-400 py-1 px-2">DI- Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.dmi?.[tf]?.di_minus_move
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val <= -5 ? 'text-green-400' : val != null && val <= 0 ? 'text-gray-300' : val != null ? 'text-red-400' : 'text-gray-500'}`}>
                              {val != null ? val.toFixed(1) : '-'}
                            </td>
                          )
                        })}
                      </tr>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-400 py-1 px-2">ADX Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.dmi?.[tf]?.adx_move
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val > 0 ? 'text-green-400' : 'text-gray-300'}`}>
                              {val != null ? val.toFixed(1) : '-'}
                            </td>
                          )
                        })}
                      </tr>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-500 py-1 px-2">DI+ 4H</td>
                        <td colSpan={4} className="text-center font-mono py-1 px-2 text-green-400">
                          {alert.mega_buy_details?.dmi?.['4h']?.di_plus?.toFixed(1) || '-'}
                        </td>
                      </tr>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-500 py-1 px-2">DI- 4H</td>
                        <td colSpan={4} className="text-center font-mono py-1 px-2 text-red-400">
                          {alert.mega_buy_details?.dmi?.['4h']?.di_minus?.toFixed(1) || '-'}
                        </td>
                      </tr>
                      <tr>
                        <td className="text-gray-500 py-1 px-2">ADX 4H</td>
                        <td colSpan={4} className="text-center font-mono py-1 px-2 text-yellow-400">
                          {alert.mega_buy_details?.dmi?.['4h']?.adx?.toFixed(1) || '-'}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* RSI Moves Table */}
              <div className="bg-gray-800/30 rounded-lg p-3 mb-3">
                <div className="text-xs font-medium text-cyan-400 mb-2">RSI Moves</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-gray-400 py-1 px-2">Metric</th>
                        <th className="text-center text-blue-400 py-1 px-2">15m</th>
                        <th className="text-center text-blue-400 py-1 px-2">30m</th>
                        <th className="text-center text-blue-400 py-1 px-2">1h</th>
                        <th className="text-center text-blue-400 py-1 px-2">4h</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-400 py-1 px-2">RSI Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.rsi?.[tf]?.rsi_move
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val >= 12 ? 'text-green-400' : val != null && val >= 0 ? 'text-gray-300' : val != null ? 'text-red-400' : 'text-gray-500'}`}>
                              {val != null ? val.toFixed(1) : '-'}
                            </td>
                          )
                        })}
                      </tr>
                      <tr>
                        <td className="text-gray-500 py-1 px-2">RSI Signal</td>
                        <td colSpan={4} className="text-center font-mono py-1 px-2 text-purple-400">
                          {alert.mega_buy_details?.rsi?.['4h']?.rsi_signal || '-'}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Volume % Table */}
              <div className="bg-gray-800/30 rounded-lg p-3 mb-3">
                <div className="text-xs font-medium text-amber-400 mb-2">Volume %</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-gray-400 py-1 px-2">Metric</th>
                        <th className="text-center text-blue-400 py-1 px-2">15m</th>
                        <th className="text-center text-blue-400 py-1 px-2">30m</th>
                        <th className="text-center text-blue-400 py-1 px-2">1h</th>
                        <th className="text-center text-blue-400 py-1 px-2">4h</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="text-gray-400 py-1 px-2">Vol %</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.volume?.[tf]?.vol_pct
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val >= 150 ? 'text-green-400' : val != null && val >= 100 ? 'text-yellow-400' : 'text-gray-300'}`}>
                              {val != null ? `${val}%` : '-'}
                            </td>
                          )
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* LazyBar Table */}
              <div className="bg-gray-800/30 rounded-lg p-3 mb-3">
                <div className="text-xs font-medium text-orange-400 mb-2">LazyBar</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-gray-400 py-1 px-2">Metric</th>
                        <th className="text-center text-blue-400 py-1 px-2">15m</th>
                        <th className="text-center text-blue-400 py-1 px-2">30m</th>
                        <th className="text-center text-blue-400 py-1 px-2">1h</th>
                        <th className="text-center text-blue-400 py-1 px-2">4h</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-gray-800">
                        <td className="text-gray-400 py-1 px-2">LZ Value</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const data = alert.mega_buy_details?.lazybar?.[tf]
                          const color = data?.lz_color
                          const colorClass = color === 'Orange' ? 'text-orange-400' : color === 'Yellow' ? 'text-yellow-400' : color === 'Green' ? 'text-green-400' : color === 'Red' ? 'text-red-400' : 'text-gray-500'
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${colorClass}`}>
                              {data?.lz_value || '-'} {color && <span className="text-xs opacity-70">{color}</span>}
                            </td>
                          )
                        })}
                      </tr>
                      <tr>
                        <td className="text-gray-400 py-1 px-2">LZ Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const move = alert.mega_buy_details?.lazybar?.[tf]?.lz_move
                          return (
                            <td key={tf} className="text-center py-1 px-2">
                              {move || '-'}
                            </td>
                          )
                        })}
                      </tr>
                      <tr>
                        <td className="text-gray-500 py-1 px-2">LZ Bar 4H</td>
                        <td colSpan={4} className="text-center font-mono py-1 px-2 text-orange-400">
                          {alert.mega_buy_details?.lazybar?.['4h']?.lz_raw?.toFixed(1) || '-'}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* EC RSI Move Table */}
              <div className="bg-gray-800/30 rounded-lg p-3">
                <div className="text-xs font-medium text-pink-400 mb-2">EC RSI Move</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-gray-400 py-1 px-2">Metric</th>
                        <th className="text-center text-blue-400 py-1 px-2">15m</th>
                        <th className="text-center text-blue-400 py-1 px-2">30m</th>
                        <th className="text-center text-blue-400 py-1 px-2">1h</th>
                        <th className="text-center text-blue-400 py-1 px-2">4h</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="text-gray-400 py-1 px-2">EC Move</td>
                        {['15m', '30m', '1h', '4h'].map(tf => {
                          const val = alert.mega_buy_details?.ec?.[tf]?.ec_move
                          return (
                            <td key={tf} className={`text-center font-mono py-1 px-2 ${val != null && val >= 4 ? 'text-green-400' : val != null && val >= 0 ? 'text-gray-300' : val != null ? 'text-red-400' : 'text-gray-500'}`}>
                              {val != null ? val.toFixed(1) : '-'}
                            </td>
                          )
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Trendline Info */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Trendline Conditions</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <ConditionBadge
                valid={alert.has_trendline}
                label="Trendline Found"
                value={alert.tl_type ? `Type: ${alert.tl_type}` : null}
              />
              <ConditionBadge
                valid={alert.has_tl_break}
                label="TL Break Detected"
                value={alert.tl_break_price ? formatNumber(alert.tl_break_price, 6) : null}
              />
              <ConditionBadge
                valid={alert.has_tl_break && !alert.delay_exceeded}
                label="Delay <= 72h"
                value={alert.tl_break_delay_hours ? `${alert.tl_break_delay_hours.toFixed(1)}h` : null}
              />
              {alert.has_trendline && (
                <div className="bg-gray-800/30 rounded-lg p-2 text-xs">
                  <div className="text-gray-400">TL Price @ Alert: <span className="text-white font-mono">{formatNumber(alert.tl_price_at_alert, 6)}</span></div>
                </div>
              )}
            </div>
          </div>

          {/* Progressive Entry Conditions */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Progressive Entry Conditions (5 Required)</h3>
            <div className="space-y-2">
              {/* EMA100 1H */}
              <div className={`p-3 rounded-lg border ${alert.prog_valid_ema100_1h ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {alert.prog_valid_ema100_1h ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-sm font-medium ${alert.prog_valid_ema100_1h ? 'text-green-400' : 'text-red-400'}`}>
                      Price 1H &gt; EMA100 (1H)
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-400 font-mono">
                  {formatNumber(alert.prog_price_1h, 6)} &gt; {formatNumber(alert.prog_ema100_1h, 6)}
                </div>
              </div>

              {/* EMA20 4H */}
              <div className={`p-3 rounded-lg border ${alert.prog_valid_ema20_4h ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {alert.prog_valid_ema20_4h ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-sm font-medium ${alert.prog_valid_ema20_4h ? 'text-green-400' : 'text-red-400'}`}>
                      Price 4H &gt; EMA20 (4H)
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-400 font-mono">
                  {formatNumber(alert.prog_price_4h, 6)} &gt; {formatNumber(alert.prog_ema20_4h, 6)}
                </div>
              </div>

              {/* Cloud 1H */}
              <div className={`p-3 rounded-lg border ${alert.prog_valid_cloud_1h ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {alert.prog_valid_cloud_1h ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-sm font-medium ${alert.prog_valid_cloud_1h ? 'text-green-400' : 'text-red-400'}`}>
                      Price 1H &gt; Cloud Top (1H)
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-400 font-mono">
                  {formatNumber(alert.prog_price_1h, 6)} &gt; {formatNumber(alert.prog_cloud_1h, 6)}
                </div>
              </div>

              {/* Cloud 30m */}
              <div className={`p-3 rounded-lg border ${alert.prog_valid_cloud_30m ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {alert.prog_valid_cloud_30m ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-sm font-medium ${alert.prog_valid_cloud_30m ? 'text-green-400' : 'text-red-400'}`}>
                      Price 30m &gt; Cloud Top (30m)
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-400 font-mono">
                  {formatNumber(alert.prog_price_30m, 6)} &gt; {formatNumber(alert.prog_cloud_30m, 6)}
                </div>
              </div>

              {/* CHoCH/BOS */}
              <div className={`p-3 rounded-lg border ${alert.prog_choch_bos_valid ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {alert.prog_choch_bos_valid ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-sm font-medium ${alert.prog_choch_bos_valid ? 'text-green-400' : 'text-red-400'}`}>
                      CHoCH/BOS Confirmed
                    </span>
                  </div>
                </div>
                {alert.prog_choch_bos_sh_price && (
                  <div className="mt-1 text-xs text-gray-400 font-mono">
                    Swing High: {formatNumber(alert.prog_choch_bos_sh_price, 6)} @ {formatDate(alert.prog_choch_bos_datetime)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Fibonacci Levels (4H) */}
          {alert.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-400" />
                Fibonacci Retracement (4H)
                <span className={`text-xs px-2 py-0.5 rounded ${alert.fib_bonus ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                  {alert.fib_bonus ? '38.2% BREAK' : 'NO 38.2% BREAK'}
                </span>
              </h3>
              <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                {alert.fib_levels && Object.keys(alert.fib_levels).length > 0 ? (
                  <>
                    {/* Swing Range Info */}
                    <div className="flex items-center gap-4 mb-4 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-400">Swing High:</span>
                        <span className="text-green-400 font-mono">{formatNumber(alert.fib_swing_high, 6)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-400">Swing Low:</span>
                        <span className="text-red-400 font-mono">{formatNumber(alert.fib_swing_low, 6)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-400">Entry 4H:</span>
                        <span className="text-white font-mono font-bold">{formatNumber(alert.prog_price_4h, 6)}</span>
                      </div>
                    </div>
                    {/* All Fibonacci Levels */}
                    <div className="space-y-2">
                      {['0.786', '0.618', '0.5', '0.382', '0.236'].map((level) => {
                        const fibLevel = alert.fib_levels?.[level]
                        if (!fibLevel) return null
                        const levelPct = (parseFloat(level) * 100).toFixed(1)
                        const isBreak = fibLevel.break
                        return (
                          <div
                            key={level}
                            className={`flex items-center justify-between p-2 rounded ${
                              isBreak ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              {isBreak ? (
                                <CheckCircle className="w-4 h-4 text-green-400" />
                              ) : (
                                <XCircle className="w-4 h-4 text-red-400" />
                              )}
                              <span className={`text-sm font-bold ${level === '0.382' ? 'text-yellow-400' : 'text-white'}`}>
                                Fib {levelPct}%
                                {level === '0.382' && <span className="text-xs text-yellow-400 ml-1">(BONUS)</span>}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-xs font-mono">
                              <span className="text-gray-400">Prix: <span className="text-yellow-400">{formatNumber(fibLevel.price, 6)}</span></span>
                              <span className={isBreak ? 'text-green-400' : 'text-red-400'}>
                                {isBreak ? 'BREAK ✓' : 'NO BREAK ✗'}
                              </span>
                              <span className="text-gray-500">
                                ({fibLevel.distance_pct > 0 ? '+' : ''}{fibLevel.distance_pct.toFixed(2)}%)
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-gray-500">
                    Fibonacci data not available (insufficient 4H data or range too small)
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Fibonacci Levels (1H) */}
          {alert.has_entry && alert.fib_levels_1h && Object.keys(alert.fib_levels_1h).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                Fibonacci Retracement (1H)
              </h3>
              <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                {/* Swing Range Info */}
                <div className="flex items-center gap-4 mb-4 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Swing High:</span>
                    <span className="text-green-400 font-mono">{formatNumber(alert.fib_swing_high_1h, 6)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Swing Low:</span>
                    <span className="text-red-400 font-mono">{formatNumber(alert.fib_swing_low_1h, 6)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Entry 1H:</span>
                    <span className="text-white font-mono font-bold">{formatNumber(alert.entry_price, 6)}</span>
                  </div>
                </div>
                {/* All Fibonacci Levels 1H */}
                <div className="grid grid-cols-5 gap-1 text-xs">
                  {['0.236', '0.382', '0.5', '0.618', '0.786'].map((level) => {
                    const fibLevel = alert.fib_levels_1h?.[level]
                    if (!fibLevel) return null
                    const levelPct = (parseFloat(level) * 100).toFixed(1)
                    const isBreak = fibLevel.break
                    return (
                      <div
                        key={level}
                        className={`p-1.5 rounded text-center ${
                          isBreak ? 'bg-green-500/20 border border-green-500/30' : 'bg-red-500/20 border border-red-500/30'
                        }`}
                      >
                        <div className="font-bold text-white">{levelPct}%</div>
                        <div className="text-gray-400 font-mono text-[10px]">{formatNumber(fibLevel.price, 4)}</div>
                        <div className={`text-[10px] ${isBreak ? 'text-green-400' : 'text-red-400'}`}>
                          {isBreak ? '✓' : '✗'}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Order Block (SMC) - 1H & 4H */}
          {alert.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${(alert.ob_bonus || alert.ob_bonus_4h) ? 'bg-purple-500' : 'bg-gray-600'}`} />
                Order Block (SMC)
                {alert.ob_bonus && (
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full border border-purple-500/30">
                    1H
                  </span>
                )}
                {alert.ob_bonus_4h && (
                  <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full border border-orange-500/30">
                    4H
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* OB 1H */}
                <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-xs font-semibold text-purple-400 mb-2">Order Block 1H</div>
                  {alert.ob_bonus && alert.ob_zone_high ? (
                    <>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Zone:</span>{' '}
                          <span className="text-purple-400 font-mono">{formatNumber(alert.ob_zone_low, 4)} - {formatNumber(alert.ob_zone_high, 4)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">Position:</span>{' '}
                          <span className={`font-bold ${
                            alert.ob_position === 'INSIDE' ? 'text-green-400' :
                            alert.ob_position === 'ABOVE' ? 'text-yellow-400' : 'text-red-400'
                          }`}>{alert.ob_position}</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Strength:</span>{' '}
                          <span className={`font-bold ${
                            alert.ob_strength === 'STRONG' ? 'text-green-400' :
                            alert.ob_strength === 'MODERATE' ? 'text-yellow-400' : 'text-red-400'
                          }`}>{alert.ob_strength}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">Distance:</span>{' '}
                          <span className="text-white font-mono">{alert.ob_distance_pct?.toFixed(2)}%</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-gray-500">No OB found</div>
                  )}
                </div>
                {/* OB 4H */}
                <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-xs font-semibold text-orange-400 mb-2">Order Block 4H</div>
                  {alert.ob_bonus_4h && alert.ob_zone_high_4h ? (
                    <>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Zone:</span>{' '}
                          <span className="text-orange-400 font-mono">{formatNumber(alert.ob_zone_low_4h, 4)} - {formatNumber(alert.ob_zone_high_4h, 4)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">Position:</span>{' '}
                          <span className={`font-bold ${
                            alert.ob_position_4h === 'INSIDE' ? 'text-green-400' :
                            alert.ob_position_4h === 'ABOVE' ? 'text-yellow-400' : 'text-red-400'
                          }`}>{alert.ob_position_4h}</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Strength:</span>{' '}
                          <span className={`font-bold ${
                            alert.ob_strength_4h === 'STRONG' ? 'text-green-400' :
                            alert.ob_strength_4h === 'MODERATE' ? 'text-yellow-400' : 'text-red-400'
                          }`}>{alert.ob_strength_4h}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">Distance:</span>{' '}
                          <span className="text-white font-mono">{alert.ob_distance_pct_4h?.toFixed(2)}%</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-gray-500">No OB found</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* BTC Correlation BONUS - 1H & 4H */}
          {alert.has_entry && (alert.btc_trend_1h || alert.btc_trend_4h) && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${(alert.btc_corr_bonus_1h || alert.btc_corr_bonus_4h) ? 'bg-yellow-500' : 'bg-gray-600'}`} />
                BTC Correlation
                {alert.btc_corr_bonus_1h && (
                  <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full border border-green-500/30">
                    1H BULLISH
                  </span>
                )}
                {alert.btc_corr_bonus_4h && (
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full border border-emerald-500/30">
                    4H BULLISH
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* BTC 1H */}
                <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-xs font-semibold text-yellow-400 mb-2">BTC 1H</div>
                  {alert.btc_trend_1h ? (
                    <>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Trend:</span>{' '}
                          <span className={`font-bold ${
                            alert.btc_trend_1h === 'BULLISH' ? 'text-green-400' :
                            alert.btc_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'
                          }`}>{alert.btc_trend_1h}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">RSI:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_rsi_1h || 0) > 50 ? 'text-green-400' : 'text-red-400'
                          }`}>{alert.btc_rsi_1h?.toFixed(1)}</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Price:</span>{' '}
                          <span className="text-white font-mono">${alert.btc_price_1h?.toFixed(0)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">EMA20:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_price_1h || 0) > (alert.btc_ema20_1h || 0) ? 'text-green-400' : 'text-red-400'
                          }`}>${alert.btc_ema20_1h?.toFixed(0)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">EMA50:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_price_1h || 0) > (alert.btc_ema50_1h || 0) ? 'text-green-400' : 'text-red-400'
                          }`}>${alert.btc_ema50_1h?.toFixed(0)}</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-gray-500">N/A (BTCUSDT)</div>
                  )}
                </div>
                {/* BTC 4H */}
                <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-xs font-semibold text-amber-400 mb-2">BTC 4H</div>
                  {alert.btc_trend_4h ? (
                    <>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Trend:</span>{' '}
                          <span className={`font-bold ${
                            alert.btc_trend_4h === 'BULLISH' ? 'text-green-400' :
                            alert.btc_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'
                          }`}>{alert.btc_trend_4h}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">RSI:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_rsi_4h || 0) > 50 ? 'text-green-400' : 'text-red-400'
                          }`}>{alert.btc_rsi_4h?.toFixed(1)}</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="text-xs">
                          <span className="text-gray-400">Price:</span>{' '}
                          <span className="text-white font-mono">${alert.btc_price_4h?.toFixed(0)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">EMA20:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_price_4h || 0) > (alert.btc_ema20_4h || 0) ? 'text-green-400' : 'text-red-400'
                          }`}>${alert.btc_ema20_4h?.toFixed(0)}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-400">EMA50:</span>{' '}
                          <span className={`font-mono ${
                            (alert.btc_price_4h || 0) > (alert.btc_ema50_4h || 0) ? 'text-green-400' : 'text-red-400'
                          }`}>${alert.btc_ema50_4h?.toFixed(0)}</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-gray-500">N/A (BTCUSDT)</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Entry Info */}
          {alert.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                Entry Point
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Entry Price</div>
                  <div className="text-lg font-mono text-green-400">{formatNumber(alert.entry_price, 6)}</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Entry Time</div>
                  <div className="text-sm text-white">{formatDate(alert.entry_datetime)}</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Diff vs Alert</div>
                  <div className={`text-lg font-mono ${(alert.entry_diff_vs_alert || 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {alert.entry_diff_vs_alert?.toFixed(2)}%
                  </div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Diff vs Break</div>
                  <div className={`text-lg font-mono ${(alert.entry_diff_vs_break || 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {alert.entry_diff_vs_break?.toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* V6 ADVANCED SCORING */}
          {alert.v6_score !== null && alert.v6_score !== undefined && (
            <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${
                  alert.v6_grade === 'A' ? 'bg-green-500' :
                  alert.v6_grade === 'B' ? 'bg-yellow-500' :
                  alert.v6_grade === 'C' ? 'bg-orange-500' :
                  'bg-red-500'
                }`} />
                V6 Advanced Scoring
                <span className={`px-2 py-0.5 text-xs rounded-full border ${
                  alert.v6_grade === 'A' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  alert.v6_grade === 'B' ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' :
                  alert.v6_grade === 'C' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' :
                  'bg-red-500/20 text-red-400 border-red-500/30'
                }`}>
                  Grade {alert.v6_grade} ({alert.v6_score} pts)
                </span>
                {alert.v6_rejected && (
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full border border-red-500/30">
                    REJECTED
                  </span>
                )}
              </h3>

              {/* V6 Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                {/* Retest Hours */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Retest Time</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_retest_hours || 0) <= 6 ? 'text-green-400' :
                    (alert.v6_retest_hours || 0) <= 24 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {alert.v6_retest_hours?.toFixed(1) || '0'}h
                  </div>
                </div>
                {/* Entry Hours */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Entry Time</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_entry_hours || 0) <= 12 ? 'text-green-400' :
                    (alert.v6_entry_hours || 0) <= 48 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {alert.v6_entry_hours?.toFixed(1) || '0'}h
                  </div>
                </div>
                {/* Distance % */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Distance</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_distance_pct || 0) <= 10 ? 'text-green-400' :
                    (alert.v6_distance_pct || 0) <= 15 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {alert.v6_distance_pct?.toFixed(1) || '0'}%
                  </div>
                </div>
                {/* Potential % */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Potential</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_potential_pct || 0) >= 15 ? 'text-green-400' :
                    (alert.v6_potential_pct || 0) >= 8 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    +{alert.v6_potential_pct?.toFixed(1) || '0'}%
                  </div>
                </div>
              </div>

              {/* V6 Momentum Metrics */}
              <div className="grid grid-cols-3 md:grid-cols-5 gap-3 mb-3">
                {/* RSI at Entry */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">RSI Entry</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_rsi_at_entry || 0) >= 50 ? 'text-green-400' :
                    (alert.v6_rsi_at_entry || 0) >= 40 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {alert.v6_rsi_at_entry?.toFixed(1) || 'N/A'}
                  </div>
                </div>
                {/* ADX at Entry */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">ADX Entry</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_adx_at_entry || 0) >= 25 ? 'text-green-400' :
                    (alert.v6_adx_at_entry || 0) >= 15 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {alert.v6_adx_at_entry?.toFixed(1) || 'N/A'}
                  </div>
                </div>
                {/* Timing Adjustment */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Timing Adj</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_timing_adj || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {(alert.v6_timing_adj || 0) >= 0 ? '+' : ''}{alert.v6_timing_adj || 0}
                  </div>
                </div>
                {/* Momentum Adjustment */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">Momentum Adj</div>
                  <div className={`text-sm font-mono ${
                    (alert.v6_momentum_adj || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {(alert.v6_momentum_adj || 0) >= 0 ? '+' : ''}{alert.v6_momentum_adj || 0}
                  </div>
                </div>
                {/* CVD Divergence */}
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <div className="text-xs text-gray-400">CVD</div>
                  <div className={`text-sm font-mono ${
                    alert.v6_has_cvd_divergence ? 'text-red-400' : 'text-green-400'
                  }`}>
                    {alert.v6_has_cvd_divergence ? 'DIV' : 'OK'}
                  </div>
                </div>
              </div>

              {/* V6 Rejection Reason */}
              {alert.v6_rejected && alert.v6_rejection_reason && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="text-sm font-semibold text-red-400">Rejection Reason</div>
                  <div className="text-xs text-red-300 mt-1">{alert.v6_rejection_reason}</div>
                </div>
              )}
            </div>
          )}

          {/* OHLCV */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">OHLCV Data</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-gray-800/30 rounded-lg p-2">
                <div className="text-xs text-gray-400">Open</div>
                <div className="text-sm font-mono text-white">{formatNumber(alert.price_open, 6)}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-2">
                <div className="text-xs text-gray-400">High</div>
                <div className="text-sm font-mono text-green-400">{formatNumber(alert.price_high, 6)}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-2">
                <div className="text-xs text-gray-400">Low</div>
                <div className="text-sm font-mono text-red-400">{formatNumber(alert.price_low, 6)}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-2">
                <div className="text-xs text-gray-400">Close</div>
                <div className="text-sm font-mono text-white">{formatNumber(alert.price_close, 6)}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-2">
                <div className="text-xs text-gray-400">Volume</div>
                <div className="text-sm font-mono text-blue-400">{alert.volume?.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Trade Detail Modal - Shows all related alerts for a trade entry
function TradeDetailModal({
  trade,
  relatedAlerts,
  onClose,
  symbol
}: {
  trade: GroupedTrade
  relatedAlerts: Alert[]
  onClose: () => void
  symbol: string
}) {
  const [showFcObModal, setShowFcObModal] = useState(false)
  const [fcObModalAlert, setFcObModalAlert] = useState<Alert | null>(null)
  const [showFcObPineScript, setShowFcObPineScript] = useState(false)
  const [fcObPineScriptCopied, setFcObPineScriptCopied] = useState(false)

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString("fr-FR")
  }

  const formatNumber = (num: number | null | undefined, decimals = 4) => {
    if (num === null || num === undefined) return '-'
    return num.toFixed(decimals)
  }

  const megaBuyConditions = [
    { key: 'RSI_surge', label: 'RSI Surge (>=12)', mandatory: true },
    { key: 'DI+_surge', label: 'DI+ Surge (>=10)', mandatory: true },
    { key: 'AST_flip', label: 'AST SuperTrend Flip', mandatory: true },
    { key: 'CHoCH', label: 'CHoCH/BOS', mandatory: false },
    { key: 'Green_Zone', label: 'Green Zone (ATR+Vol)', mandatory: false },
    { key: 'LazyBar', label: 'LazyBar Spike', mandatory: false },
    { key: 'Volume', label: 'Volume Spike', mandatory: false },
    { key: 'ST_break', label: 'SuperTrend Break', mandatory: false },
    { key: 'PP_buy', label: 'PP SuperTrend Buy', mandatory: false },
    { key: 'Entry_Confirm', label: 'Entry Confirmation', mandatory: false },
  ]

  // Use the first alert that has entry data for progressive conditions
  // For V3, check v3_entry_found instead of has_entry
  const primaryAlert = relatedAlerts.find(a => a.has_entry || a.v3_entry_found) || relatedAlerts[0]

  // Guard against empty relatedAlerts
  if (!primaryAlert) {
    return (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
          <p className="text-gray-400">No alert data available</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-700 rounded-lg text-white">Close</button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Trade Details {trade.is_combined && <span className="px-2 py-0.5 bg-yellow-500/30 text-yellow-400 rounded text-xs">COMBO</span>}
            </h2>
            <p className="text-sm text-gray-400">
              Entry: {formatDate(trade.entry_datetime)} @ {formatNumber(trade.entry_price, 6)}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Trade Summary */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">Timeframes</div>
              <div className="flex flex-wrap gap-1 mt-1">
                {trade.timeframes.map((tf, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs">{tf}</span>
                ))}
              </div>
            </div>
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3">
              <div className="text-xs text-gray-400">Entry Date & Time</div>
              <div className="text-sm font-medium text-cyan-400">{formatDate(trade.entry_datetime)}</div>
            </div>
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <div className="text-xs text-gray-400">Entry Price</div>
              <div className="text-lg font-mono text-blue-400">{formatNumber(trade.entry_price, 6)}</div>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <div className="text-xs text-gray-400">Stop Loss</div>
              <div className="text-lg font-mono text-red-400">{formatNumber(trade.sl_price, 6)}</div>
            </div>
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
              <div className="text-xs text-gray-400">TP1 / TP2</div>
              <div className="text-sm font-mono text-green-400">
                {formatNumber(trade.tp1_price, 6)} / {formatNumber(trade.tp2_price, 6)}
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-400">P&L</div>
              <div className={`text-lg font-bold ${trade.pnl_c >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                C: {trade.pnl_c?.toFixed(2)}% | D: {trade.pnl_d?.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* V3 Golden Box Strategy Section */}
          {trade.strategy_version === 'v3' && primaryAlert && (
            <div className="bg-cyan-500/10 rounded-lg p-4 border border-cyan-500/30">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className="w-4 h-4 bg-cyan-500 rounded" />
                V3 Golden Box Strategy
                <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 text-xs rounded">
                  Quality: {trade.v3_quality_score || 0}/10
                </span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  (primaryAlert.v3_prog_count || 0) >= 5
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  Conditions: {primaryAlert.v3_prog_count || 0}/5
                </span>
              </h3>

              {/* Golden Box Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Box High</div>
                  <div className="text-lg font-mono text-cyan-400">{formatNumber(trade.v3_box_high, 6)}</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Box Low</div>
                  <div className="text-lg font-mono text-orange-400">{formatNumber(trade.v3_box_low, 6)}</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Box Range</div>
                  <div className="text-lg font-mono text-white">{primaryAlert.v3_box_range_pct?.toFixed(2)}%</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">SL Distance</div>
                  <div className="text-lg font-mono text-red-400">{trade.v3_sl_distance_pct?.toFixed(2)}%</div>
                </div>
              </div>

              {/* Breakout & Retest Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Breakout Time</div>
                  <div className="text-sm font-medium text-yellow-400">{formatDate(trade.v3_breakout_dt)}</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Breakout High</div>
                  <div className="text-lg font-mono text-yellow-400">{formatNumber(trade.v3_breakout_high, 6)}</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Retest Time</div>
                  <div className="text-sm font-medium text-green-400">{formatDate(primaryAlert.v3_retest_datetime || trade.v3_retest_datetime)}</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Retest Price (Low)</div>
                  <div className="text-lg font-mono text-green-400">{formatNumber(primaryAlert.v3_retest_price || trade.v3_retest_price, 6)}</div>
                </div>
              </div>

              {/* Distance & Hours Info */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Hours to Entry</div>
                  <div className="text-lg font-mono text-white">{trade.v3_hours_to_entry?.toFixed(1)}h</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Distance Before Retest</div>
                  <div className="text-lg font-mono text-white">{primaryAlert.v3_distance_before_retest?.toFixed(2)}%</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Quality Score</div>
                  <div className={`text-lg font-mono ${(trade.v3_quality_score || 0) >= 7 ? 'text-green-400' : (trade.v3_quality_score || 0) >= 4 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {trade.v3_quality_score || 0}/10
                  </div>
                </div>
              </div>

              {/* Retest vs TL Break */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                <div className={`rounded-lg p-3 border ${
                  primaryAlert.v3_retest_vs_tl_break === 'AFTER_TL'
                    ? 'bg-green-500/10 border-green-500/30'
                    : primaryAlert.v3_retest_vs_tl_break === 'BEFORE_TL'
                      ? 'bg-orange-500/10 border-orange-500/30'
                      : 'bg-gray-900/50 border-gray-700'
                }`}>
                  <div className="text-xs text-gray-400">Retest vs TL Break 1H</div>
                  <div className={`text-lg font-bold ${
                    primaryAlert.v3_retest_vs_tl_break === 'AFTER_TL'
                      ? 'text-green-400'
                      : primaryAlert.v3_retest_vs_tl_break === 'BEFORE_TL'
                        ? 'text-orange-400'
                        : 'text-gray-400'
                  }`}>
                    {primaryAlert.v3_retest_vs_tl_break === 'AFTER_TL' && 'APRES TL Break'}
                    {primaryAlert.v3_retest_vs_tl_break === 'BEFORE_TL' && 'AVANT TL Break'}
                    {primaryAlert.v3_retest_vs_tl_break === 'NO_TL_BREAK' && 'Pas de TL Break'}
                    {!primaryAlert.v3_retest_vs_tl_break && '-'}
                  </div>
                </div>
                {primaryAlert.v3_tl_break_datetime && (
                  <div className="bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400">TL Break 1H</div>
                    <div className="text-sm font-medium text-blue-400">{formatDate(primaryAlert.v3_tl_break_datetime)}</div>
                  </div>
                )}
                {primaryAlert.v3_hours_retest_vs_tl !== null && primaryAlert.v3_hours_retest_vs_tl !== undefined && (
                  <div className="bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400">Diff Retest / TL Break</div>
                    <div className={`text-lg font-mono ${primaryAlert.v3_hours_retest_vs_tl >= 0 ? 'text-green-400' : 'text-orange-400'}`}>
                      {primaryAlert.v3_hours_retest_vs_tl >= 0 ? '+' : ''}{primaryAlert.v3_hours_retest_vs_tl?.toFixed(1)}h
                    </div>
                  </div>
                )}
              </div>

              {/* GB Power Score */}
              {primaryAlert.gb_power_score !== null && primaryAlert.gb_power_score !== undefined && (
                <div className="border-t border-gray-700 pt-4 mt-4">
                  <h4 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-2">
                    Golden Box Power Score
                    <span className={`px-3 py-1 rounded-full text-lg font-bold ${
                      primaryAlert.gb_power_grade === 'A' ? 'bg-green-500/30 text-green-400' :
                      primaryAlert.gb_power_grade === 'B' ? 'bg-blue-500/30 text-blue-400' :
                      primaryAlert.gb_power_grade === 'C' ? 'bg-yellow-500/30 text-yellow-400' :
                      primaryAlert.gb_power_grade === 'D' ? 'bg-orange-500/30 text-orange-400' :
                      'bg-red-500/30 text-red-400'
                    }`}>
                      Grade {primaryAlert.gb_power_grade}: {primaryAlert.gb_power_score}/100
                    </span>
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">Volume</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_volume_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_volume_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_volume_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">ADX</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_adx_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_adx_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_adx_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">EMA Stack</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_ema_alignment_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_ema_alignment_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_ema_alignment_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">MACD</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_macd_momentum_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_macd_momentum_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_macd_momentum_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">Fibonacci</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_fib_position_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_fib_position_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_fib_position_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">DMI Spread</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_dmi_spread_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_dmi_spread_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_dmi_spread_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">RSI MTF</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_rsi_strength_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_rsi_strength_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_rsi_strength_score || 0}
                      </div>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-400">BTC Corr</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_btc_correlation_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_btc_correlation_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_btc_correlation_score || 0}
                      </div>
                    </div>
                    {primaryAlert.gb_retest_quality_score !== null && primaryAlert.gb_retest_quality_score !== undefined && (
                      <div className="bg-cyan-900/50 rounded-lg p-2 text-center border border-cyan-500/30">
                        <div className="text-xs text-cyan-300">Retest</div>
                        <div className={`text-lg font-bold ${(primaryAlert.gb_retest_quality_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_retest_quality_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                          {primaryAlert.gb_retest_quality_score || 0}
                        </div>
                      </div>
                    )}
                    <div className="bg-purple-900/50 rounded-lg p-2 text-center border border-purple-500/30">
                      <div className="text-xs text-purple-300">Confluence</div>
                      <div className={`text-lg font-bold ${(primaryAlert.gb_confluence_score || 0) >= 70 ? 'text-green-400' : (primaryAlert.gb_confluence_score || 0) >= 40 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {primaryAlert.gb_confluence_score || 0}
                      </div>
                    </div>
                  </div>
                  {primaryAlert.gb_dmi_spread !== null && primaryAlert.gb_dmi_spread !== undefined && (
                    <div className="mt-2 text-xs text-gray-500">
                      DMI Spread: DMI+ - DMI- = {primaryAlert.gb_dmi_spread?.toFixed(1)}
                    </div>
                  )}
                </div>
              )}

              {/* V3 Risk Warning */}
              {primaryAlert.v3_risk_level && primaryAlert.v3_risk_score !== null && primaryAlert.v3_risk_score > 0 && (
                <div className={`border-t pt-4 mt-4 ${
                  primaryAlert.v3_risk_level === 'CRITICAL' ? 'border-red-500' :
                  primaryAlert.v3_risk_level === 'HIGH' ? 'border-orange-500' :
                  primaryAlert.v3_risk_level === 'MEDIUM' ? 'border-yellow-500' :
                  'border-gray-700'
                }`}>
                  <div className={`rounded-lg p-4 ${
                    primaryAlert.v3_risk_level === 'CRITICAL' ? 'bg-red-500/20 border border-red-500/50' :
                    primaryAlert.v3_risk_level === 'HIGH' ? 'bg-orange-500/20 border border-orange-500/50' :
                    primaryAlert.v3_risk_level === 'MEDIUM' ? 'bg-yellow-500/20 border border-yellow-500/50' :
                    'bg-gray-800/50 border border-gray-700'
                  }`}>
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <span className={`text-2xl ${
                        primaryAlert.v3_risk_level === 'CRITICAL' ? 'text-red-400' :
                        primaryAlert.v3_risk_level === 'HIGH' ? 'text-orange-400' :
                        primaryAlert.v3_risk_level === 'MEDIUM' ? 'text-yellow-400' :
                        'text-gray-400'
                      }`}>⚠️</span>
                      <span className={`${
                        primaryAlert.v3_risk_level === 'CRITICAL' ? 'text-red-400' :
                        primaryAlert.v3_risk_level === 'HIGH' ? 'text-orange-400' :
                        primaryAlert.v3_risk_level === 'MEDIUM' ? 'text-yellow-400' :
                        'text-gray-300'
                      }`}>
                        Risk Level: {primaryAlert.v3_risk_level}
                      </span>
                      <span className={`ml-auto px-3 py-1 rounded-full text-sm font-bold ${
                        primaryAlert.v3_risk_level === 'CRITICAL' ? 'bg-red-500/30 text-red-300' :
                        primaryAlert.v3_risk_level === 'HIGH' ? 'bg-orange-500/30 text-orange-300' :
                        primaryAlert.v3_risk_level === 'MEDIUM' ? 'bg-yellow-500/30 text-yellow-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        Risk Score: {primaryAlert.v3_risk_score}/100
                      </span>
                    </h4>
                    {primaryAlert.v3_risk_reasons && primaryAlert.v3_risk_reasons.length > 0 && (
                      <div className="space-y-2 mt-3">
                        {primaryAlert.v3_risk_reasons.map((reason, idx) => (
                          <div key={idx} className={`flex items-start gap-2 p-2 rounded ${
                            reason.severity === 'CRITICAL' ? 'bg-red-900/30' :
                            reason.severity === 'HIGH' ? 'bg-orange-900/30' :
                            reason.severity === 'MEDIUM' ? 'bg-yellow-900/30' :
                            'bg-gray-900/30'
                          }`}>
                            <span className={`text-sm font-bold ${
                              reason.severity === 'CRITICAL' ? 'text-red-400' :
                              reason.severity === 'HIGH' ? 'text-orange-400' :
                              reason.severity === 'MEDIUM' ? 'text-yellow-400' :
                              'text-gray-400'
                            }`}>
                              {reason.severity === 'CRITICAL' ? '🚨' :
                               reason.severity === 'HIGH' ? '⚠️' :
                               reason.severity === 'MEDIUM' ? '⚡' : 'ℹ️'}
                            </span>
                            <span className="text-sm text-gray-300">{reason.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* V3 Progressive Conditions at Retest Time */}
              <div className="border-t border-gray-700 pt-4 mt-4">
                <h4 className="text-xs font-semibold text-gray-300 mb-2">Progressive Conditions at Retest Time (5/5 Required)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  <ConditionBadge
                    valid={!!primaryAlert.v3_prog_valid_ema100_1h}
                    label="Price > EMA100 1H"
                    value={primaryAlert.v3_prog_ema100_1h_val ? `> ${formatNumber(primaryAlert.v3_prog_ema100_1h_val, 4)}` : null}
                  />
                  <ConditionBadge
                    valid={!!primaryAlert.v3_prog_valid_ema20_4h}
                    label="Price > EMA20 4H"
                    value={primaryAlert.v3_prog_ema20_4h_val ? `> ${formatNumber(primaryAlert.v3_prog_ema20_4h_val, 4)}` : null}
                  />
                  <ConditionBadge
                    valid={!!primaryAlert.v3_prog_valid_cloud_1h}
                    label="Price > Cloud 1H"
                    value={primaryAlert.v3_prog_cloud_1h_val ? `> ${formatNumber(primaryAlert.v3_prog_cloud_1h_val, 4)}` : null}
                  />
                  <ConditionBadge
                    valid={!!primaryAlert.v3_prog_valid_cloud_30m}
                    label="Price > Cloud 30m"
                    value={primaryAlert.v3_prog_cloud_30m_val ? `> ${formatNumber(primaryAlert.v3_prog_cloud_30m_val, 4)}` : null}
                  />
                  <ConditionBadge
                    valid={!!primaryAlert.v3_prog_choch_bos_valid}
                    label="CHoCH/BOS Confirmed"
                  />
                </div>
              </div>
            </div>
          )}

          {/* V4 Optimized Strategy Section */}
          {trade.strategy_version === 'v4' && primaryAlert && (
            <div className="bg-amber-500/10 rounded-lg p-4 border border-amber-500/30">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className="w-4 h-4 bg-amber-500 rounded" />
                V4 Optimized Strategy
                {primaryAlert.v4_score !== null && primaryAlert.v4_score !== undefined && (
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    primaryAlert.v4_grade === 'A+' ? 'bg-green-500/20 text-green-400' :
                    primaryAlert.v4_grade === 'A' ? 'bg-green-500/20 text-green-400' :
                    primaryAlert.v4_grade === 'B+' ? 'bg-yellow-500/20 text-yellow-400' :
                    primaryAlert.v4_grade === 'B' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    Grade: {primaryAlert.v4_grade} ({primaryAlert.v4_score}/100)
                  </span>
                )}
                {primaryAlert.v4_rejected && (
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                    REJECTED
                  </span>
                )}
              </h3>

              {/* V4 Filter Results */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">V3 Quality</div>
                  <div className={`text-lg font-mono ${(trade.v3_quality_score || 0) >= 6 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.v3_quality_score || 0}/10 {(trade.v3_quality_score || 0) >= 6 ? '✓' : '✗'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">TL Break Delay</div>
                  <div className={`text-lg font-mono ${(primaryAlert.tl_break_delay_hours || 0) <= 24 ? 'text-green-400' : 'text-red-400'}`}>
                    {primaryAlert.tl_break_delay_hours?.toFixed(1)}h {(primaryAlert.tl_break_delay_hours || 0) <= 24 ? '✓' : '✗'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">STC Timeframes</div>
                  <div className={`text-lg font-mono ${primaryAlert.stc_valid_tfs?.includes('1h') ? 'text-green-400' : 'text-red-400'}`}>
                    {primaryAlert.stc_valid_tfs || 'N/A'} {primaryAlert.stc_valid_tfs?.includes('1h') ? '✓' : '✗'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">OB Score</div>
                  <div className={`text-lg font-mono ${(primaryAlert.fc_ob_score || 0) >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                    {primaryAlert.fc_ob_score || 0} {(primaryAlert.fc_ob_score || 0) >= 50 ? '✓' : '✗'}
                  </div>
                </div>
              </div>

              {/* V4 Rejection Reason */}
              {primaryAlert.v4_rejected && primaryAlert.v4_rejection_reason && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-red-400 text-lg">⚠️</span>
                    <div>
                      <div className="text-sm font-semibold text-red-400">Trade Rejected by V4 Filters</div>
                      <div className="text-xs text-red-300 mt-1">{primaryAlert.v4_rejection_reason}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* V5 VP Trajectory Filter Section */}
          {['v5', 'v6'].includes(trade.strategy_version || '') && primaryAlert && (
            <div className="bg-pink-500/10 rounded-lg p-4 border border-pink-500/30">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className="w-4 h-4 bg-pink-500 rounded" />
                V5 VP Trajectory Filter
                {primaryAlert.v5_score !== null && primaryAlert.v5_score !== undefined && (
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    primaryAlert.v5_grade === 'A+' ? 'bg-green-500/20 text-green-400' :
                    primaryAlert.v5_grade === 'A' ? 'bg-green-500/20 text-green-400' :
                    primaryAlert.v5_grade === 'B+' ? 'bg-yellow-500/20 text-yellow-400' :
                    primaryAlert.v5_grade === 'B' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    Score: {primaryAlert.v5_score}
                  </span>
                )}
                {primaryAlert.v5_rejected && (
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                    REJECTED
                  </span>
                )}
              </h3>

              {/* V5 Filter Results */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">VAL Bounce</div>
                  <div className={`text-lg font-mono ${primaryAlert.v5_val_bounce ? 'text-green-400' : 'text-gray-500'}`}>
                    {primaryAlert.v5_val_bounce ? '✓ REBOND' : '✗ NON'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">POC Bounce</div>
                  <div className={`text-lg font-mono ${primaryAlert.v5_poc_bounce ? 'text-green-400' : 'text-gray-500'}`}>
                    {primaryAlert.v5_poc_bounce ? '✓ REBOND' : '✗ NON'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">VP Position</div>
                  <div className={`text-lg font-mono ${
                    primaryAlert.vp_entry_position_1h === 'ABOVE_VAH' ? 'text-green-400' :
                    primaryAlert.vp_entry_position_1h === 'IN_VA' ? 'text-yellow-400' :
                    primaryAlert.vp_entry_position_1h === 'AT_POC' ? 'text-cyan-400' :
                    'text-red-400'
                  }`}>
                    {primaryAlert.vp_entry_position_1h || 'N/A'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Trajectory</div>
                  <div className={`text-lg font-mono ${
                    primaryAlert.v5_trajectory_strength === 'STRONG' ? 'text-green-400' :
                    primaryAlert.v5_trajectory_strength === 'MODERATE' ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {primaryAlert.v5_trajectory_strength || 'N/A'}
                  </div>
                </div>
              </div>

              {/* V5 Rejection Reason */}
              {primaryAlert.v5_rejected && primaryAlert.v5_rejection_reason && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-red-400 text-lg">⚠️</span>
                    <div>
                      <div className="text-sm font-semibold text-red-400">Trade Rejected by V5 VP Filter</div>
                      <div className="text-xs text-red-300 mt-1">{primaryAlert.v5_rejection_reason}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* V6 Advanced Scoring Section */}
          {['v5', 'v6'].includes(trade.strategy_version || '') && primaryAlert && primaryAlert.v6_score !== null && (
            <div className="bg-purple-500/10 rounded-lg p-4 border border-purple-500/30">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <div className="w-4 h-4 bg-purple-500 rounded" />
                V6 Advanced Scoring
                <span className={`px-2 py-0.5 text-xs rounded ${
                  primaryAlert.v6_grade === 'A' ? 'bg-green-500/20 text-green-400' :
                  primaryAlert.v6_grade === 'B' ? 'bg-yellow-500/20 text-yellow-400' :
                  primaryAlert.v6_grade === 'C' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  Grade: {primaryAlert.v6_grade} ({primaryAlert.v6_score} pts)
                </span>
                {primaryAlert.v6_rejected && (
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                    REJECTED
                  </span>
                )}
              </h3>

              {/* V6 Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Retest Timing</div>
                  <div className={`text-lg font-mono ${
                    (primaryAlert.v6_retest_hours || 0) <= 6 ? 'text-green-400' :
                    (primaryAlert.v6_retest_hours || 0) <= 24 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {primaryAlert.v6_retest_hours?.toFixed(1) || '0'}h
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Distance %</div>
                  <div className={`text-lg font-mono ${
                    (primaryAlert.v6_distance_pct || 0) <= 10 ? 'text-green-400' :
                    (primaryAlert.v6_distance_pct || 0) <= 15 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {primaryAlert.v6_distance_pct?.toFixed(1) || '0'}%
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">RSI @ Entry</div>
                  <div className={`text-lg font-mono ${
                    (primaryAlert.v6_rsi_at_entry || 0) >= 50 ? 'text-green-400' :
                    (primaryAlert.v6_rsi_at_entry || 0) >= 40 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {primaryAlert.v6_rsi_at_entry?.toFixed(1) || 'N/A'}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Potential</div>
                  <div className={`text-lg font-mono ${
                    (primaryAlert.v6_potential_pct || 0) >= 15 ? 'text-green-400' :
                    (primaryAlert.v6_potential_pct || 0) >= 8 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    +{primaryAlert.v6_potential_pct?.toFixed(1) || '0'}%
                  </div>
                </div>
              </div>

              {/* V6 Score Breakdown */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                <div className="bg-gray-900/50 rounded p-2 text-center">
                  <div className="text-xs text-gray-400">Timing</div>
                  <div className={`text-sm font-mono ${(primaryAlert.v6_timing_adj || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(primaryAlert.v6_timing_adj || 0) >= 0 ? '+' : ''}{primaryAlert.v6_timing_adj || 0}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded p-2 text-center">
                  <div className="text-xs text-gray-400">Momentum</div>
                  <div className={`text-sm font-mono ${(primaryAlert.v6_momentum_adj || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(primaryAlert.v6_momentum_adj || 0) >= 0 ? '+' : ''}{primaryAlert.v6_momentum_adj || 0}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded p-2 text-center">
                  <div className="text-xs text-gray-400">CVD</div>
                  <div className={`text-sm font-mono ${primaryAlert.v6_has_cvd_divergence ? 'text-red-400' : 'text-green-400'}`}>
                    {primaryAlert.v6_has_cvd_divergence ? '⚠️ DIV' : '✓ OK'}
                  </div>
                </div>
              </div>

              {/* V6 Rejection Reason */}
              {primaryAlert.v6_rejected && primaryAlert.v6_rejection_reason && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-red-400 text-lg">⚠️</span>
                    <div>
                      <div className="text-sm font-semibold text-red-400">Trade Rejected by V6 Filters</div>
                      <div className="text-xs text-red-300 mt-1">{primaryAlert.v6_rejection_reason}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Bonus Filters Summary */}
          {primaryAlert && (
            <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-400" />
                Bonus Filters
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {/* Fibonacci 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.fib_bonus ? 'bg-green-500/10 border-green-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Fib 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.fib_bonus ? 'text-green-400' : 'text-gray-500'}`}>
                    {primaryAlert.fib_bonus ? '38.2%' : 'NO'}
                  </div>
                </div>
                {/* Order Block 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.ob_bonus ? 'bg-purple-500/10 border-purple-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">OB 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.ob_bonus ? 'text-purple-400' : 'text-gray-500'}`}>
                    {primaryAlert.ob_bonus ? primaryAlert.ob_strength : 'NO'}
                  </div>
                </div>
                {/* Order Block 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.ob_bonus_4h ? 'bg-orange-500/10 border-orange-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">OB 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.ob_bonus_4h ? 'text-orange-400' : 'text-gray-500'}`}>
                    {primaryAlert.ob_bonus_4h ? primaryAlert.ob_strength_4h : 'NO'}
                  </div>
                </div>
                {/* BTC 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.btc_corr_bonus_1h ? 'bg-green-500/10 border-green-500/30' : primaryAlert.btc_trend_1h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BTC 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.btc_corr_bonus_1h ? 'text-green-400' : primaryAlert.btc_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {primaryAlert.btc_trend_1h || 'N/A'}
                  </div>
                </div>
                {/* BTC 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.btc_corr_bonus_4h ? 'bg-emerald-500/10 border-emerald-500/30' : primaryAlert.btc_trend_4h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BTC 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.btc_corr_bonus_4h ? 'text-emerald-400' : primaryAlert.btc_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {primaryAlert.btc_trend_4h || 'N/A'}
                  </div>
                </div>
                {/* ETH 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.eth_corr_bonus_1h ? 'bg-indigo-500/10 border-indigo-500/30' : primaryAlert.eth_trend_1h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ETH 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.eth_corr_bonus_1h ? 'text-indigo-400' : primaryAlert.eth_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {primaryAlert.eth_trend_1h || 'N/A'}
                  </div>
                </div>
                {/* ETH 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.eth_corr_bonus_4h ? 'bg-violet-500/10 border-violet-500/30' : primaryAlert.eth_trend_4h === 'BEARISH' ? 'bg-red-500/10 border-red-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ETH 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.eth_corr_bonus_4h ? 'text-violet-400' : primaryAlert.eth_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {primaryAlert.eth_trend_4h || 'N/A'}
                  </div>
                </div>
                {/* FVG 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.fvg_bonus_1h ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">FVG 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.fvg_bonus_1h ? 'text-cyan-400' : 'text-gray-500'}`}>
                    {primaryAlert.fvg_bonus_1h ? primaryAlert.fvg_position_1h : 'NO'}
                  </div>
                </div>
                {/* FVG 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.fvg_bonus_4h ? 'bg-teal-500/10 border-teal-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">FVG 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.fvg_bonus_4h ? 'text-teal-400' : 'text-gray-500'}`}>
                    {primaryAlert.fvg_bonus_4h ? primaryAlert.fvg_position_4h : 'NO'}
                  </div>
                </div>
                {/* Volume 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.vol_spike_bonus_1h ? 'bg-amber-500/10 border-amber-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Vol 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.vol_spike_bonus_1h ? 'text-amber-400' : 'text-gray-500'}`}>
                    {primaryAlert.vol_spike_bonus_1h ? `${primaryAlert.vol_ratio_1h?.toFixed(1)}x` : 'NO'}
                  </div>
                </div>
                {/* Volume 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.vol_spike_bonus_4h ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">Vol 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.vol_spike_bonus_4h ? 'text-yellow-400' : 'text-gray-500'}`}>
                    {primaryAlert.vol_spike_bonus_4h ? `${primaryAlert.vol_ratio_4h?.toFixed(1)}x` : 'NO'}
                  </div>
                </div>
                {/* RSI MTF */}
                <div className={`p-2 rounded-lg border ${primaryAlert.rsi_mtf_bonus ? 'bg-rose-500/10 border-rose-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">RSI MTF</div>
                  <div className={`text-sm font-bold ${primaryAlert.rsi_mtf_bonus ? 'text-rose-400' : 'text-gray-500'}`}>
                    {primaryAlert.rsi_mtf_bonus ? `${primaryAlert.rsi_aligned_count}/3` : 'NO'}
                  </div>
                </div>
                {/* ADX 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.adx_bonus_1h ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ADX 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.adx_bonus_1h ? 'text-indigo-400' : 'text-gray-500'}`}>
                    {primaryAlert.adx_bonus_1h ? `${primaryAlert.adx_value_1h?.toFixed(0)}` : 'NO'}
                  </div>
                </div>
                {/* ADX 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.adx_bonus_4h ? 'bg-violet-500/10 border-violet-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">ADX 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.adx_bonus_4h ? 'text-violet-400' : 'text-gray-500'}`}>
                    {primaryAlert.adx_bonus_4h ? `${primaryAlert.adx_value_4h?.toFixed(0)}` : 'NO'}
                  </div>
                </div>
                {/* MACD 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.macd_bonus_1h ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">MACD 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.macd_bonus_1h ? 'text-emerald-400' : 'text-gray-500'}`}>
                    {primaryAlert.macd_bonus_1h ? '↑' : 'NO'}
                  </div>
                </div>
                {/* MACD 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.macd_bonus_4h ? 'bg-teal-500/10 border-teal-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">MACD 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.macd_bonus_4h ? 'text-teal-400' : 'text-gray-500'}`}>
                    {primaryAlert.macd_bonus_4h ? '↑' : 'NO'}
                  </div>
                </div>
                {/* BB 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.bb_squeeze_bonus_1h ? 'bg-fuchsia-500/10 border-fuchsia-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BB 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.bb_squeeze_bonus_1h ? 'text-fuchsia-400' : 'text-gray-500'}`}>
                    {primaryAlert.bb_squeeze_bonus_1h ? 'SQZ↑' : 'NO'}
                  </div>
                </div>
                {/* BB 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.bb_squeeze_bonus_4h ? 'bg-pink-500/10 border-pink-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">BB 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.bb_squeeze_bonus_4h ? 'text-pink-400' : 'text-gray-500'}`}>
                    {primaryAlert.bb_squeeze_bonus_4h ? 'SQZ↑' : 'NO'}
                  </div>
                </div>
                {/* StochRSI 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.stoch_rsi_bonus_1h ? 'bg-sky-500/10 border-sky-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">StochRSI 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.stoch_rsi_bonus_1h ? 'text-sky-400' : 'text-gray-500'}`}>
                    {primaryAlert.stoch_rsi_bonus_1h ? '↑' : 'NO'}
                  </div>
                </div>
                {/* StochRSI 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.stoch_rsi_bonus_4h ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">StochRSI 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.stoch_rsi_bonus_4h ? 'text-cyan-400' : 'text-gray-500'}`}>
                    {primaryAlert.stoch_rsi_bonus_4h ? '↑' : 'NO'}
                  </div>
                </div>
                {/* EMA Stack 1H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.ema_stack_bonus_1h ? 'bg-lime-500/10 border-lime-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">EMA 1H</div>
                  <div className={`text-sm font-bold ${primaryAlert.ema_stack_bonus_1h ? 'text-lime-400' : 'text-gray-500'}`}>
                    {primaryAlert.ema_stack_bonus_1h ? 'PERFECT' : 'NO'}
                  </div>
                </div>
                {/* EMA Stack 4H */}
                <div className={`p-2 rounded-lg border ${primaryAlert.ema_stack_bonus_4h ? 'bg-green-500/10 border-green-500/30' : 'bg-gray-700/30 border-gray-600'}`}>
                  <div className="text-xs text-gray-400">EMA 4H</div>
                  <div className={`text-sm font-bold ${primaryAlert.ema_stack_bonus_4h ? 'text-green-400' : 'text-gray-500'}`}>
                    {primaryAlert.ema_stack_bonus_4h ? 'PERFECT' : 'NO'}
                  </div>
                </div>
                {/* Total */}
                <div className="p-2 rounded-lg border bg-gray-700/30 border-gray-600">
                  <div className="text-xs text-gray-400">Total</div>
                  <div className="text-sm font-bold text-white">
                    {[primaryAlert.fib_bonus, primaryAlert.ob_bonus, primaryAlert.ob_bonus_4h, primaryAlert.btc_corr_bonus_1h, primaryAlert.btc_corr_bonus_4h, primaryAlert.eth_corr_bonus_1h, primaryAlert.eth_corr_bonus_4h, primaryAlert.fvg_bonus_1h, primaryAlert.fvg_bonus_4h, primaryAlert.vol_spike_bonus_1h, primaryAlert.vol_spike_bonus_4h, primaryAlert.rsi_mtf_bonus, primaryAlert.adx_bonus_1h, primaryAlert.adx_bonus_4h, primaryAlert.macd_bonus_1h, primaryAlert.macd_bonus_4h, primaryAlert.bb_squeeze_bonus_1h, primaryAlert.bb_squeeze_bonus_4h, primaryAlert.stoch_rsi_bonus_1h, primaryAlert.stoch_rsi_bonus_4h, primaryAlert.ema_stack_bonus_1h, primaryAlert.ema_stack_bonus_4h].filter(Boolean).length}/22
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Exit Info */}
          <div className="bg-gray-800/30 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-white mb-2">Exit Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-400 mb-1">Strategy C (Trailing Stop)</div>
                <div className={`text-sm ${trade.pnl_c >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {trade.exit_reason_c}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-1">Strategy D (Multi-TP)</div>
                <div className={`text-sm ${trade.pnl_d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {trade.exit_reason_d || '-'}
                </div>
              </div>
            </div>
          </div>

          {/* Post-SL Recovery Analysis - Only show for losing trades that hit initial SL */}
          {trade.pnl_c < 0 && trade.post_sl_max_price && (
            <div className={`rounded-lg p-4 border ${trade.sl_then_recovered ? 'bg-orange-500/10 border-orange-500/30' : 'bg-gray-800/30 border-gray-700'}`}>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <AlertCircle className={`w-4 h-4 ${trade.sl_then_recovered ? 'text-orange-400' : 'text-gray-400'}`} />
                Post-SL Recovery Analysis
                {trade.sl_then_recovered && (
                  <span className="px-2 py-0.5 bg-orange-500/30 text-orange-400 rounded text-xs">
                    PRIX REMONTÉ
                  </span>
                )}
                {trade.post_sl_would_have_won && (
                  <span className="px-2 py-0.5 bg-red-500/30 text-red-400 rounded text-xs">
                    AURAIT ÉTÉ GAGNANT
                  </span>
                )}
              </h3>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Prix Max Post-SL</div>
                  <div className={`text-lg font-mono ${trade.sl_then_recovered ? 'text-orange-400' : 'text-gray-300'}`}>
                    {trade.post_sl_max_price?.toFixed(6)}
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Gain Max Potentiel</div>
                  <div className={`text-lg font-mono ${(trade.post_sl_max_gain_pct || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.post_sl_max_gain_pct?.toFixed(2)}%
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Monitoring</div>
                  <div className="text-lg font-mono text-gray-300">
                    {trade.post_sl_monitoring_hours?.toFixed(1)}h
                  </div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">TP1 Atteint?</div>
                  <div className={`text-lg font-mono ${trade.post_sl_would_have_won ? 'text-green-400' : 'text-gray-400'}`}>
                    {trade.post_sl_would_have_won ? 'OUI' : 'NON'}
                  </div>
                </div>
              </div>

              {/* Comparison bar */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                  <span>Entry: {formatNumber(trade.entry_price, 6)}</span>
                  <span>SL: {formatNumber(trade.sl_price, 6)}</span>
                  <span>Post-SL Max: {formatNumber(trade.post_sl_max_price, 6)}</span>
                  <span>TP1: {formatNumber(trade.tp1_price, 6)}</span>
                </div>
                <div className="relative h-4 bg-gray-800 rounded-full overflow-hidden">
                  {/* SL zone */}
                  <div
                    className="absolute h-full bg-red-500/30"
                    style={{ left: '0%', width: '20%' }}
                  />
                  {/* Entry point */}
                  <div
                    className="absolute h-full w-1 bg-blue-500"
                    style={{ left: '20%' }}
                  />
                  {/* Post-SL recovery zone */}
                  {trade.sl_then_recovered && (
                    <div
                      className="absolute h-full bg-orange-500/50"
                      style={{
                        left: '20%',
                        width: `${Math.min(60, (trade.post_sl_max_gain_pct || 0) * 2)}%`
                      }}
                    />
                  )}
                  {/* TP1 line */}
                  <div
                    className="absolute h-full w-1 bg-green-500"
                    style={{ left: '50%' }}
                  />
                </div>
                <div className="flex items-center justify-between text-[10px] text-gray-500 mt-1">
                  <span>SL (-5%)</span>
                  <span>Entry</span>
                  <span>TP1 (+15%)</span>
                </div>
              </div>

              {/* Fib levels broken after SL */}
              {trade.post_sl_fib_levels && Object.keys(trade.post_sl_fib_levels).length > 0 && (
                <div>
                  <div className="text-xs text-gray-400 mb-2">Niveaux Fibonacci cassés APRÈS le SL:</div>
                  <div className="grid grid-cols-5 gap-1 text-xs">
                    {['0.236', '0.382', '0.5', '0.618', '0.786'].map((level) => {
                      const fibLevel = trade.post_sl_fib_levels?.[level]
                      if (!fibLevel) return null
                      const levelPct = (parseFloat(level) * 100).toFixed(1)
                      const brokenAfterSL = fibLevel.broken_after_sl && !fibLevel.broken_before_sl
                      return (
                        <div
                          key={level}
                          className={`p-1.5 rounded text-center ${
                            brokenAfterSL
                              ? 'bg-orange-500/20 border border-orange-500/50'
                              : fibLevel.broken_before_sl
                                ? 'bg-green-500/20 border border-green-500/30'
                                : 'bg-gray-700/30 border border-gray-700'
                          }`}
                        >
                          <div className={`font-bold ${level === '0.382' ? 'text-yellow-400' : 'text-white'}`}>{levelPct}%</div>
                          <div className="text-gray-400 font-mono text-[10px]">{formatNumber(fibLevel.price, 4)}</div>
                          <div className={`text-[10px] ${
                            brokenAfterSL
                              ? 'text-orange-400 font-bold'
                              : fibLevel.broken_before_sl
                                ? 'text-green-400'
                                : 'text-gray-500'
                          }`}>
                            {brokenAfterSL ? 'APRÈS SL!' : fibLevel.broken_before_sl ? 'avant SL' : '✗'}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Warning message */}
              {trade.post_sl_would_have_won && (
                <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <div className="flex items-center gap-2 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span className="font-medium">Stop Loss trop serré!</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Le prix a atteint TP1 ({formatNumber(trade.tp1_price, 6)}) après avoir touché le SL.
                    Considérer un SL plus large ou une meilleure entrée.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Prerequisites (from primary alert) */}
          {primaryAlert && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3">Prerequisites (3 conditions)</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div className={`p-3 rounded-lg border ${primaryAlert.stc_validated ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-lg ${primaryAlert.stc_validated ? 'text-green-400' : 'text-red-400'}`}>
                      {primaryAlert.stc_validated ? '✓' : '✗'}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">STC Oversold (&lt;0.2)</div>
                      <div className="text-xs text-gray-400">Valid on: {primaryAlert.stc_valid_tfs || 'None'}</div>
                    </div>
                  </div>
                </div>
                <div className={`p-3 rounded-lg border ${!primaryAlert.is_15m_alone ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-lg ${!primaryAlert.is_15m_alone ? 'text-green-400' : 'text-red-400'}`}>
                      {!primaryAlert.is_15m_alone ? '✓' : '✗'}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">Not 15m Alone</div>
                      <div className="text-xs text-gray-400">{primaryAlert.combo_tfs || primaryAlert.timeframe}</div>
                    </div>
                  </div>
                </div>
                <div className={`p-3 rounded-lg border ${primaryAlert.has_trendline ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-lg ${primaryAlert.has_trendline ? 'text-green-400' : 'text-red-400'}`}>
                      {primaryAlert.has_trendline ? '✓' : '✗'}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">Trendline Exists</div>
                      <div className="text-xs text-gray-400">{primaryAlert.tl_type || 'None'}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TL Break Information (from primary alert) */}
          {primaryAlert && primaryAlert.has_tl_break && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3">Entry Condition #1: Trendline Break</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">TL Type</div>
                  <div className="text-sm font-medium text-cyan-400">{primaryAlert.tl_type || '-'}</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Break Time</div>
                  <div className="text-sm font-medium text-white">{primaryAlert.tl_break_datetime ? formatDate(primaryAlert.tl_break_datetime) : '-'}</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Break Price</div>
                  <div className="text-sm font-medium text-white">{primaryAlert.tl_break_price ? formatNumber(primaryAlert.tl_break_price, 6) : '-'}</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">Delay from Alert</div>
                  <div className={`text-sm font-medium ${primaryAlert.delay_exceeded ? 'text-red-400' : 'text-green-400'}`}>
                    {primaryAlert.tl_break_delay_hours ? `${primaryAlert.tl_break_delay_hours.toFixed(1)}h` : '-'}
                    {primaryAlert.delay_exceeded && <span className="text-xs ml-1">(exceeded)</span>}
                  </div>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                  <div className="text-xs text-purple-400 mb-1">TL Retests</div>
                  <div className={`text-sm font-bold ${(primaryAlert.tl_retest_count || 0) >= 3 ? 'text-green-400' : (primaryAlert.tl_retest_count || 0) >= 1 ? 'text-yellow-400' : 'text-gray-400'}`}>
                    {primaryAlert.tl_retest_count || 0}x
                    {(primaryAlert.tl_retest_count || 0) >= 3 && <span className="text-xs ml-1 text-green-400">(strong)</span>}
                  </div>
                </div>
              </div>

              {/* TradingView PineScript Code Generator (TL + OB + VP) */}
              {(primaryAlert.tl_p1_date || primaryAlert.fc_ob_1h_found || primaryAlert.fc_ob_4h_found || primaryAlert.vp_poc_1h) && (
                <TradingViewCodeBlock
                  symbol={symbol}
                  alert={primaryAlert}
                />
              )}
            </div>
          )}

          {/* AI AGENT DECISION - Prominent Display at Top */}
          {primaryAlert && primaryAlert.agent_decision && (
            <div className="mt-4">
              <div className={`p-4 rounded-lg border-2 ${
                primaryAlert.agent_decision === 'STRONG_BUY' ? 'border-green-500 bg-gradient-to-r from-green-500/20 to-green-600/10' :
                primaryAlert.agent_decision === 'BUY' ? 'border-green-400/70 bg-gradient-to-r from-green-400/15 to-green-500/5' :
                primaryAlert.agent_decision === 'HOLD' ? 'border-yellow-500/70 bg-gradient-to-r from-yellow-500/15 to-yellow-600/5' :
                'border-red-500/70 bg-gradient-to-r from-red-500/15 to-red-600/5'
              }`}>
                {/* Header with Decision */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      primaryAlert.agent_decision === 'STRONG_BUY' ? 'bg-green-500/30' :
                      primaryAlert.agent_decision === 'BUY' ? 'bg-green-400/20' :
                      primaryAlert.agent_decision === 'HOLD' ? 'bg-yellow-500/20' :
                      'bg-red-500/20'
                    }`}>
                      <Brain className={`w-6 h-6 ${
                        primaryAlert.agent_decision === 'STRONG_BUY' ? 'text-green-400' :
                        primaryAlert.agent_decision === 'BUY' ? 'text-green-300' :
                        primaryAlert.agent_decision === 'HOLD' ? 'text-yellow-400' :
                        'text-red-400'
                      }`} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">AI Agent Decision</h3>
                      <p className="text-xs text-gray-400">Meta-analysis de tous les indicateurs</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Grade Badge */}
                    <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
                      primaryAlert.agent_grade === 'A+' ? 'bg-green-500/40 text-green-300 border border-green-400' :
                      primaryAlert.agent_grade === 'A' ? 'bg-green-400/30 text-green-300 border border-green-400/70' :
                      primaryAlert.agent_grade === 'B+' ? 'bg-lime-400/30 text-lime-300 border border-lime-400/70' :
                      primaryAlert.agent_grade === 'B' ? 'bg-yellow-400/30 text-yellow-300 border border-yellow-400/70' :
                      primaryAlert.agent_grade === 'C' ? 'bg-orange-400/30 text-orange-300 border border-orange-400/70' :
                      primaryAlert.agent_grade === 'D' ? 'bg-red-400/30 text-red-300 border border-red-400/70' :
                      'bg-red-500/40 text-red-300 border border-red-400'
                    }`}>
                      Grade {primaryAlert.agent_grade}
                    </span>
                    {/* Decision Badge */}
                    <span className={`px-4 py-1.5 rounded-lg text-sm font-bold uppercase ${
                      primaryAlert.agent_decision === 'STRONG_BUY' ? 'bg-green-500 text-white' :
                      primaryAlert.agent_decision === 'BUY' ? 'bg-green-400/80 text-white' :
                      primaryAlert.agent_decision === 'HOLD' ? 'bg-yellow-500 text-black' :
                      'bg-red-500 text-white'
                    }`}>
                      {primaryAlert.agent_decision === 'STRONG_BUY' ? '🚀 ACHAT FORT' :
                       primaryAlert.agent_decision === 'BUY' ? '✅ ACHAT' :
                       primaryAlert.agent_decision === 'HOLD' ? '⏸️ ATTENDRE' :
                       '❌ ÉVITER'}
                    </span>
                  </div>
                </div>

                {/* Score and Confidence */}
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50 text-center">
                    <div className="text-xs text-gray-400">Score Global</div>
                    <div className={`text-xl font-bold ${
                      (primaryAlert.agent_score || 0) >= 70 ? 'text-green-400' :
                      (primaryAlert.agent_score || 0) >= 50 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {primaryAlert.agent_score}/100
                    </div>
                  </div>
                  <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50 text-center">
                    <div className="text-xs text-gray-400">Confiance</div>
                    <div className={`text-xl font-bold ${
                      (primaryAlert.agent_confidence || 0) >= 70 ? 'text-green-400' :
                      (primaryAlert.agent_confidence || 0) >= 50 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {primaryAlert.agent_confidence}%
                    </div>
                  </div>
                  <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50 text-center">
                    <div className="text-xs text-gray-400">Facteurs</div>
                    <div className="flex items-center justify-center gap-2 text-sm">
                      <span className="text-green-400 flex items-center gap-0.5">
                        <ArrowUpCircle className="w-3 h-3" />
                        {primaryAlert.agent_bullish_count}
                      </span>
                      <span className="text-gray-500">/</span>
                      <span className="text-red-400 flex items-center gap-0.5">
                        <ArrowDownCircle className="w-3 h-3" />
                        {primaryAlert.agent_bearish_count}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Component Scores */}
                <div className="grid grid-cols-6 gap-2 mb-3">
                  <div className="p-1.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-center">
                    <div className="text-[9px] text-cyan-400/80 uppercase">CVD</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_cvd_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_cvd_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_cvd_score || 0}</div>
                  </div>
                  <div className="p-1.5 rounded bg-orange-500/10 border border-orange-500/30 text-center">
                    <div className="text-[9px] text-orange-400/80 uppercase">ADX</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_adx_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_adx_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_adx_score || 0}</div>
                  </div>
                  <div className="p-1.5 rounded bg-blue-500/10 border border-blue-500/30 text-center">
                    <div className="text-[9px] text-blue-400/80 uppercase">TREND</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_trend_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_trend_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_trend_score || 0}</div>
                  </div>
                  <div className="p-1.5 rounded bg-purple-500/10 border border-purple-500/30 text-center">
                    <div className="text-[9px] text-purple-400/80 uppercase">MOMENT</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_momentum_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_momentum_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_momentum_score || 0}</div>
                  </div>
                  <div className="p-1.5 rounded bg-green-500/10 border border-green-500/30 text-center">
                    <div className="text-[9px] text-green-400/80 uppercase">VOL</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_volume_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_volume_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_volume_score || 0}</div>
                  </div>
                  <div className="p-1.5 rounded bg-pink-500/10 border border-pink-500/30 text-center">
                    <div className="text-[9px] text-pink-400/80 uppercase">CONF</div>
                    <div className={`text-xs font-bold ${
                      (primaryAlert.agent_confluence_score || 0) >= 60 ? 'text-green-400' :
                      (primaryAlert.agent_confluence_score || 0) >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>{primaryAlert.agent_confluence_score || 0}</div>
                  </div>
                </div>

                {/* Bullish/Bearish Factors */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {/* Bullish Factors */}
                  {primaryAlert.agent_bullish_factors && JSON.parse(primaryAlert.agent_bullish_factors).length > 0 && (
                    <div className="p-2 rounded bg-green-500/5 border border-green-500/20">
                      <div className="text-[10px] text-green-400 uppercase font-semibold mb-1 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Facteurs Haussiers
                      </div>
                      <div className="space-y-0.5">
                        {JSON.parse(primaryAlert.agent_bullish_factors).slice(0, 4).map((factor: string, idx: number) => (
                          <div key={idx} className="text-[10px] text-green-300/80 truncate">• {factor}</div>
                        ))}
                        {JSON.parse(primaryAlert.agent_bullish_factors).length > 4 && (
                          <div className="text-[10px] text-green-400/60">+{JSON.parse(primaryAlert.agent_bullish_factors).length - 4} autres...</div>
                        )}
                      </div>
                    </div>
                  )}
                  {/* Bearish Factors */}
                  {primaryAlert.agent_bearish_factors && JSON.parse(primaryAlert.agent_bearish_factors).length > 0 && (
                    <div className="p-2 rounded bg-red-500/5 border border-red-500/20">
                      <div className="text-[10px] text-red-400 uppercase font-semibold mb-1 flex items-center gap-1">
                        <XCircle className="w-3 h-3" />
                        Facteurs Baissiers
                      </div>
                      <div className="space-y-0.5">
                        {JSON.parse(primaryAlert.agent_bearish_factors).slice(0, 4).map((factor: string, idx: number) => (
                          <div key={idx} className="text-[10px] text-red-300/80 truncate">• {factor}</div>
                        ))}
                        {JSON.parse(primaryAlert.agent_bearish_factors).length > 4 && (
                          <div className="text-[10px] text-red-400/60">+{JSON.parse(primaryAlert.agent_bearish_factors).length - 4} autres...</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Full Reasoning (Collapsible) */}
                {primaryAlert.agent_reasoning && (
                  <details className="group">
                    <summary className="cursor-pointer text-xs text-gray-400 hover:text-white flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      Voir raisonnement complet
                      <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
                    </summary>
                    <div className="mt-2 p-2 rounded bg-gray-800/50 border border-gray-700/30">
                      <pre className="text-[10px] text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                        {primaryAlert.agent_reasoning}
                      </pre>
                    </div>
                  </details>
                )}
              </div>
            </div>
          )}

          {/* CVD (Cumulative Volume Delta) Analysis */}
          {primaryAlert && primaryAlert.has_entry && primaryAlert.cvd_score !== null && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-cyan-400" />
                CVD Analysis (Volume Delta)
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.cvd_label === 'STRONG BUY' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.cvd_label === 'BUY' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                  primaryAlert.cvd_label === 'NEUTRAL' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  primaryAlert.cvd_label === 'WEAK' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {primaryAlert.cvd_label || 'N/A'} ({primaryAlert.cvd_score}/100)
                </span>
                {primaryAlert.cvd_bonus && (
                  <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] rounded">BONUS</span>
                )}
              </h3>

              {/* CVD Description */}
              {primaryAlert.cvd_description && (
                <div className="text-xs text-gray-400 mb-3 italic">
                  {primaryAlert.cvd_description}
                </div>
              )}

              {/* CVD at Key Moments Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                {/* At TL Break */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_at_break_signal === 'BULLISH' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_at_break_signal === 'BEARISH' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At TL Break</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_at_break?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_at_break_trend === 'RISING' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_at_break_trend === 'FALLING' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_at_break_trend || '-'}</span>
                    {primaryAlert.vol_at_break_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_at_break_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Breakout */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_at_breakout_signal === 'STRONG_BUY' ? 'border-green-500/50 bg-green-500/20' :
                  primaryAlert.cvd_at_breakout_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_at_breakout_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Breakout</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_at_breakout?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_at_breakout_spike ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_at_breakout_spike ? 'SPIKE' : 'NORMAL'}</span>
                    {primaryAlert.vol_at_breakout_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_at_breakout_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Retest */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_at_retest_signal === 'ACCUMULATION' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_at_retest_signal === 'DISTRIBUTION' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Retest</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_at_retest?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_at_retest_trend === 'RISING' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_at_retest_trend === 'FALLING' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_at_retest_signal || '-'}</span>
                    {primaryAlert.vol_at_retest_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_at_retest_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Entry */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_at_entry_signal === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_at_entry_signal === 'WARNING' ? 'border-yellow-500/30 bg-yellow-500/10' :
                  primaryAlert.cvd_at_entry_signal === 'DANGER' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Entry</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_at_entry?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_at_entry_signal === 'CONFIRMED' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_at_entry_signal === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' :
                      primaryAlert.cvd_at_entry_signal === 'DANGER' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_at_entry_signal || '-'}</span>
                    {primaryAlert.vol_at_entry_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_at_entry_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Divergence Warning */}
              {primaryAlert.cvd_divergence && (
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_divergence_type === 'BEARISH' ? 'border-red-500/30 bg-red-500/10' : 'border-green-500/30 bg-green-500/10'
                }`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${primaryAlert.cvd_divergence_type === 'BEARISH' ? 'text-red-400' : 'text-green-400'}`} />
                    <span className={`text-xs font-medium ${primaryAlert.cvd_divergence_type === 'BEARISH' ? 'text-red-400' : 'text-green-400'}`}>
                      {primaryAlert.cvd_divergence_type} Divergence Detected
                    </span>
                    <span className="text-[10px] text-gray-500">
                      {primaryAlert.cvd_divergence_type === 'BEARISH'
                        ? 'Price rising but CVD falling - potential weakness'
                        : 'Price falling but CVD rising - potential strength'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* CVD 4H (Cumulative Volume Delta - 4H timeframe) Analysis */}
          {primaryAlert && primaryAlert.has_entry && primaryAlert.cvd_4h_score !== null && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-purple-400" />
                CVD 4H Analysis (Smoother Signal)
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.cvd_4h_label === 'STRONG BUY' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.cvd_4h_label === 'BUY' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                  primaryAlert.cvd_4h_label === 'NEUTRAL' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  primaryAlert.cvd_4h_label === 'WEAK' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {primaryAlert.cvd_4h_label || 'N/A'} ({primaryAlert.cvd_4h_score}/100)
                </span>
                {primaryAlert.cvd_4h_bonus && (
                  <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 text-[10px] rounded">BONUS 4H</span>
                )}
              </h3>

              {/* CVD 4H at Key Moments Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                {/* At TL Break */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_4h_at_break_signal === 'BULLISH' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_4h_at_break_signal === 'BEARISH' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At TL Break (4H)</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_4h_at_break?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_4h_at_break_trend === 'RISING' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_4h_at_break_trend === 'FALLING' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_4h_at_break_trend || '-'}</span>
                    {primaryAlert.vol_4h_at_break_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_4h_at_break_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Breakout */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_4h_at_breakout_signal === 'STRONG_BUY' ? 'border-green-500/50 bg-green-500/20' :
                  primaryAlert.cvd_4h_at_breakout_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_4h_at_breakout_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Breakout (4H)</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_4h_at_breakout?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_4h_at_breakout_spike ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_4h_at_breakout_spike ? 'SPIKE' : 'NORMAL'}</span>
                    {primaryAlert.vol_4h_at_breakout_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_4h_at_breakout_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Retest */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_4h_at_retest_signal === 'ACCUMULATION' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_4h_at_retest_signal === 'DISTRIBUTION' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Retest (4H)</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_4h_at_retest?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_4h_at_retest_trend === 'RISING' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_4h_at_retest_trend === 'FALLING' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_4h_at_retest_signal || '-'}</span>
                    {primaryAlert.vol_4h_at_retest_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_4h_at_retest_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>

                {/* At Entry */}
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_4h_at_entry_signal === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.cvd_4h_at_entry_signal === 'WARNING' ? 'border-yellow-500/30 bg-yellow-500/10' :
                  primaryAlert.cvd_4h_at_entry_signal === 'DANGER' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Entry (4H)</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.cvd_4h_at_entry?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.cvd_4h_at_entry_signal === 'CONFIRMED' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.cvd_4h_at_entry_signal === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' :
                      primaryAlert.cvd_4h_at_entry_signal === 'DANGER' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.cvd_4h_at_entry_signal || '-'}</span>
                    {primaryAlert.vol_4h_at_entry_ratio && (
                      <span className="text-[10px] text-gray-500">Vol: {primaryAlert.vol_4h_at_entry_ratio.toFixed(1)}x</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Divergence Warning 4H */}
              {primaryAlert.cvd_4h_divergence && (
                <div className={`p-2 rounded border ${
                  primaryAlert.cvd_4h_divergence_type === 'BEARISH' ? 'border-red-500/30 bg-red-500/10' : 'border-green-500/30 bg-green-500/10'
                }`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${primaryAlert.cvd_4h_divergence_type === 'BEARISH' ? 'text-red-400' : 'text-green-400'}`} />
                    <span className={`text-xs font-medium ${primaryAlert.cvd_4h_divergence_type === 'BEARISH' ? 'text-red-400' : 'text-green-400'}`}>
                      {primaryAlert.cvd_4h_divergence_type} Divergence 4H
                    </span>
                    <span className="text-[10px] text-gray-500">
                      {primaryAlert.cvd_4h_divergence_type === 'BEARISH'
                        ? 'Price rising but CVD 4H falling - potential weakness'
                        : 'Price falling but CVD 4H rising - potential strength'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Volume Profile Analysis */}
          {primaryAlert && primaryAlert.has_entry && primaryAlert.vp_score !== null && primaryAlert.vp_score !== undefined && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-indigo-400" />
                Volume Profile Analysis
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.vp_grade === 'A+' || primaryAlert.vp_grade === 'A' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.vp_grade === 'B+' || primaryAlert.vp_grade === 'B' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' :
                  primaryAlert.vp_grade === 'C' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {primaryAlert.vp_grade || 'N/A'} ({primaryAlert.vp_score}/100)
                </span>
                {primaryAlert.vp_bonus && (
                  <span className="px-1.5 py-0.5 bg-indigo-500/20 text-indigo-400 text-[10px] rounded">BONUS</span>
                )}
              </h3>

              {/* VP Label */}
              {primaryAlert.vp_label && (
                <div className="text-xs text-indigo-300 mb-3 font-medium">
                  {primaryAlert.vp_label}
                </div>
              )}

              {/* VP Key Levels Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                {/* POC 1H */}
                <div className={`p-2 rounded border ${
                  primaryAlert.vp_entry_position_1h === 'AT_POC' || primaryAlert.vp_entry_position_1h === 'IN_VA'
                    ? 'border-green-500/30 bg-green-500/10'
                    : primaryAlert.vp_entry_position_1h === 'ABOVE_VAH'
                    ? 'border-orange-500/30 bg-orange-500/10'
                    : 'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">POC 1H</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.vp_poc_1h?.toFixed(5) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.vp_entry_position_1h === 'AT_POC' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.vp_entry_position_1h === 'IN_VA' ? 'bg-blue-500/20 text-blue-400' :
                      primaryAlert.vp_entry_position_1h === 'ABOVE_VAH' ? 'bg-orange-500/20 text-orange-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.vp_entry_position_1h || '-'}</span>
                    {primaryAlert.vp_entry_vs_poc_pct_1h && (
                      <span className="text-[10px] text-gray-500">{primaryAlert.vp_entry_vs_poc_pct_1h.toFixed(1)}% away</span>
                    )}
                  </div>
                </div>

                {/* VAH 1H */}
                <div className="p-2 rounded border border-gray-600/30 bg-gray-700/20">
                  <div className="text-[10px] text-gray-500 uppercase">VAH 1H</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.vp_vah_1h?.toFixed(5) || '-'}</div>
                  <div className="text-[10px] text-gray-500 mt-1">Upper Value Area</div>
                </div>

                {/* VAL 1H */}
                <div className="p-2 rounded border border-gray-600/30 bg-gray-700/20">
                  <div className="text-[10px] text-gray-500 uppercase">VAL 1H</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.vp_val_1h?.toFixed(5) || '-'}</div>
                  <div className="text-[10px] text-gray-500 mt-1">Lower Value Area</div>
                </div>

                {/* POC 4H */}
                <div className={`p-2 rounded border ${
                  primaryAlert.vp_entry_position_4h === 'AT_POC' || primaryAlert.vp_entry_position_4h === 'IN_VA'
                    ? 'border-green-500/30 bg-green-500/10'
                    : 'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">POC 4H</div>
                  <div className="text-xs font-mono text-white">{primaryAlert.vp_poc_4h?.toFixed(5) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${
                      primaryAlert.vp_entry_position_4h === 'AT_POC' ? 'bg-green-500/20 text-green-400' :
                      primaryAlert.vp_entry_position_4h === 'IN_VA' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{primaryAlert.vp_entry_position_4h || '-'}</span>
                  </div>
                </div>
              </div>

              {/* SL Protection & Naked POC */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                {/* SL Protection by HVN */}
                <div className={`p-2 rounded border ${
                  primaryAlert.vp_sl_near_hvn ? 'border-green-500/30 bg-green-500/10' : 'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="flex items-center gap-2">
                    <Shield className={`w-4 h-4 ${primaryAlert.vp_sl_near_hvn ? 'text-green-400' : 'text-gray-400'}`} />
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase">SL Protection</div>
                      {primaryAlert.vp_sl_near_hvn ? (
                        <>
                          <div className="text-xs text-green-400">HVN at {primaryAlert.vp_sl_hvn_level?.toFixed(5)}</div>
                          <div className="text-[10px] text-gray-500">{primaryAlert.vp_sl_hvn_distance_pct?.toFixed(1)}% from SL</div>
                        </>
                      ) : (
                        <div className="text-xs text-gray-400">No HVN protection</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Naked POC */}
                <div className={`p-2 rounded border ${
                  primaryAlert.vp_naked_poc_1h || primaryAlert.vp_naked_poc_4h ? 'border-cyan-500/30 bg-cyan-500/10' : 'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="flex items-center gap-2">
                    <Target className={`w-4 h-4 ${primaryAlert.vp_naked_poc_1h || primaryAlert.vp_naked_poc_4h ? 'text-cyan-400' : 'text-gray-400'}`} />
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase">Naked POC (Magnet)</div>
                      {primaryAlert.vp_naked_poc_1h && (
                        <div className="text-xs text-cyan-400">1H: {primaryAlert.vp_naked_poc_level_1h?.toFixed(5)}</div>
                      )}
                      {primaryAlert.vp_naked_poc_4h && (
                        <div className="text-xs text-cyan-400">4H: {primaryAlert.vp_naked_poc_level_4h?.toFixed(5)}</div>
                      )}
                      {!primaryAlert.vp_naked_poc_1h && !primaryAlert.vp_naked_poc_4h && (
                        <div className="text-xs text-gray-400">No untested POC above</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* VP Retest Detection */}
              {(primaryAlert.vp_val_retested || primaryAlert.vp_poc_retested || primaryAlert.vp_pullback_completed) && (
                <div className="mb-3 p-3 rounded border border-purple-500/30 bg-purple-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <RefreshCw className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-semibold text-purple-300">Pullback Detection</span>
                    {primaryAlert.vp_pullback_quality && (
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        primaryAlert.vp_pullback_quality === 'STRONG' ? 'bg-green-500/30 text-green-400' :
                        primaryAlert.vp_pullback_quality === 'GOOD' ? 'bg-blue-500/30 text-blue-400' :
                        'bg-yellow-500/30 text-yellow-400'
                      }`}>
                        {primaryAlert.vp_pullback_quality}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {/* VAL Retest */}
                    <div className={`p-2 rounded ${
                      primaryAlert.vp_val_retested && primaryAlert.vp_val_retest_rejected
                        ? 'bg-green-500/10 border border-green-500/30'
                        : primaryAlert.vp_val_retested
                        ? 'bg-yellow-500/10 border border-yellow-500/30'
                        : 'bg-gray-700/30 border border-gray-600/30'
                    }`}>
                      <div className="text-[10px] text-gray-500 uppercase">VAL Retest</div>
                      {primaryAlert.vp_val_retested ? (
                        <>
                          <div className={`font-medium ${primaryAlert.vp_val_retest_rejected ? 'text-green-400' : 'text-yellow-400'}`}>
                            {primaryAlert.vp_val_retest_rejected ? '✓ Retested & Rejected' : '⚠ Retested (not rejected)'}
                          </div>
                          {primaryAlert.vp_val_retest_dt && (
                            <div className="text-[10px] text-gray-500">{new Date(primaryAlert.vp_val_retest_dt).toLocaleString()}</div>
                          )}
                        </>
                      ) : (
                        <div className="text-gray-400">Not retested</div>
                      )}
                    </div>

                    {/* POC Retest */}
                    <div className={`p-2 rounded ${
                      primaryAlert.vp_poc_retested && primaryAlert.vp_poc_retest_rejected
                        ? 'bg-green-500/10 border border-green-500/30'
                        : primaryAlert.vp_poc_retested
                        ? 'bg-yellow-500/10 border border-yellow-500/30'
                        : 'bg-gray-700/30 border border-gray-600/30'
                    }`}>
                      <div className="text-[10px] text-gray-500 uppercase">POC Retest</div>
                      {primaryAlert.vp_poc_retested ? (
                        <>
                          <div className={`font-medium ${primaryAlert.vp_poc_retest_rejected ? 'text-green-400' : 'text-yellow-400'}`}>
                            {primaryAlert.vp_poc_retest_rejected ? '✓ Retested & Rejected' : '⚠ Retested (not rejected)'}
                          </div>
                          {primaryAlert.vp_poc_retest_dt && (
                            <div className="text-[10px] text-gray-500">{new Date(primaryAlert.vp_poc_retest_dt).toLocaleString()}</div>
                          )}
                        </>
                      ) : (
                        <div className="text-gray-400">Not retested</div>
                      )}
                    </div>
                  </div>

                  {/* OB Confluence */}
                  {primaryAlert.vp_ob_confluence && (
                    <div className="mt-2 p-2 rounded bg-cyan-500/10 border border-cyan-500/30">
                      <div className="flex items-center gap-2">
                        <Layers className="w-3 h-3 text-cyan-400" />
                        <span className="text-xs text-cyan-400 font-medium">
                          OB Confluence: {primaryAlert.vp_ob_confluence_tf || 'Multiple TF'}
                        </span>
                        <span className="text-[10px] text-cyan-300">
                          (VP level coincides with Order Block zone)
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Pullback Summary */}
                  {primaryAlert.vp_pullback_completed && (
                    <div className="mt-2 text-xs text-purple-300">
                      <span className="text-green-400">✓</span> Pullback completed to{' '}
                      <span className="font-mono font-medium">{primaryAlert.vp_pullback_level || 'VP level'}</span>
                      {' '}before entry
                    </div>
                  )}
                </div>
              )}

              {/* VP Recommendation */}
              {primaryAlert.vp_recommendation && (
                <div className="p-2 rounded border border-indigo-500/30 bg-indigo-500/10">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs text-indigo-300">{primaryAlert.vp_recommendation}</span>
                  </div>
                </div>
              )}

              {/* Optimized SL */}
              {primaryAlert.vp_sl_optimized && (
                <div className="mt-2 p-2 rounded border border-yellow-500/30 bg-yellow-500/10">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-yellow-400" />
                    <span className="text-xs text-yellow-300">Optimized SL: {primaryAlert.vp_sl_optimized.toFixed(5)} (based on HVN)</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ADX/DI 1H Analysis */}
          {primaryAlert && primaryAlert.has_entry && primaryAlert.adx_di_1h_score !== null && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-orange-400" />
                ADX/DI 1H (Trend Strength)
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.adx_di_1h_label === 'STRONG TREND' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.adx_di_1h_label === 'TREND' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                  primaryAlert.adx_di_1h_label === 'WEAK TREND' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  primaryAlert.adx_di_1h_label === 'RANGING' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                }`}>
                  {primaryAlert.adx_di_1h_label || 'N/A'} ({primaryAlert.adx_di_1h_score}/100)
                </span>
                {primaryAlert.adx_di_1h_bonus && (
                  <span className="px-1.5 py-0.5 bg-orange-500/20 text-orange-400 text-[10px] rounded">BONUS</span>
                )}
              </h3>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                {/* At TL Break */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_1h_at_break_signal === 'STRONG_BUY' || primaryAlert.adx_di_1h_at_break_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_1h_at_break_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At TL Break</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_1h_at_break?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_1h_at_break?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_1h_at_break?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_1h_at_break || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_1h_at_break?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Breakout */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_1h_at_breakout_signal === 'STRONG_BUY' || primaryAlert.adx_di_1h_at_breakout_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_1h_at_breakout_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Breakout</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_1h_at_breakout?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_1h_at_breakout?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_1h_at_breakout?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_1h_at_breakout || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_1h_at_breakout?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Retest */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_1h_at_retest_signal === 'ACCUMULATION' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_1h_at_retest_signal === 'DISTRIBUTION' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Retest</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_1h_at_retest?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_1h_at_retest?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_1h_at_retest?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_1h_at_retest || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_1h_at_retest?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Entry */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_1h_at_entry_signal === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_1h_at_entry_signal === 'WARNING' ? 'border-yellow-500/30 bg-yellow-500/10' :
                  primaryAlert.adx_di_1h_at_entry_signal === 'DANGER' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Entry</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_1h_at_entry?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_1h_at_entry?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_1h_at_entry?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_1h_at_entry || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_1h_at_entry?.toFixed(1) || '-'}
                  </div>
                </div>
              </div>

              {/* Extreme Zones */}
              {(primaryAlert.di_plus_1h_overbought || primaryAlert.di_minus_1h_oversold) && (
                <div className={`p-2 rounded border ${primaryAlert.di_plus_1h_overbought ? 'border-orange-500/30 bg-orange-500/10' : 'border-lime-500/30 bg-lime-500/10'}`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${primaryAlert.di_plus_1h_overbought ? 'text-orange-400' : 'text-lime-400'}`} />
                    <span className={`text-xs font-medium ${primaryAlert.di_plus_1h_overbought ? 'text-orange-400' : 'text-lime-400'}`}>
                      {primaryAlert.di_plus_1h_overbought ? 'DI+ > 60: Momentum extrême haussier' : 'DI- > 60: Pression vendeuse extrême'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ADX/DI 4H Analysis */}
          {primaryAlert && primaryAlert.has_entry && primaryAlert.adx_di_4h_score !== null && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-400" />
                ADX/DI 4H (Smoother Trend)
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.adx_di_4h_label === 'STRONG TREND' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.adx_di_4h_label === 'TREND' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                  primaryAlert.adx_di_4h_label === 'WEAK TREND' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  primaryAlert.adx_di_4h_label === 'RANGING' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                }`}>
                  {primaryAlert.adx_di_4h_label || 'N/A'} ({primaryAlert.adx_di_4h_score}/100)
                </span>
                {primaryAlert.adx_di_4h_bonus && (
                  <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] rounded">BONUS 4H</span>
                )}
              </h3>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                {/* At TL Break */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_4h_at_break_signal === 'STRONG_BUY' || primaryAlert.adx_di_4h_at_break_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_4h_at_break_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At TL Break (4H)</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_4h_at_break?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_4h_at_break?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_4h_at_break?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_4h_at_break || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_4h_at_break?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Breakout */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_4h_at_breakout_signal === 'STRONG_BUY' || primaryAlert.adx_di_4h_at_breakout_signal === 'BUY' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_4h_at_breakout_signal === 'SELL' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Breakout (4H)</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_4h_at_breakout?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_4h_at_breakout?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_4h_at_breakout?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_4h_at_breakout || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_4h_at_breakout?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Retest */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_4h_at_retest_signal === 'ACCUMULATION' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_4h_at_retest_signal === 'DISTRIBUTION' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Retest (4H)</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_4h_at_retest?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_4h_at_retest?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_4h_at_retest?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_4h_at_retest || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_4h_at_retest?.toFixed(1) || '-'}
                  </div>
                </div>

                {/* At Entry */}
                <div className={`p-2 rounded border ${
                  primaryAlert.adx_di_4h_at_entry_signal === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10' :
                  primaryAlert.adx_di_4h_at_entry_signal === 'WARNING' ? 'border-yellow-500/30 bg-yellow-500/10' :
                  primaryAlert.adx_di_4h_at_entry_signal === 'DANGER' ? 'border-red-500/30 bg-red-500/10' :
                  'border-gray-600/30 bg-gray-700/20'
                }`}>
                  <div className="text-[10px] text-gray-500 uppercase">At Entry (4H)</div>
                  <div className="text-xs font-mono text-white">ADX: {primaryAlert.adx_4h_at_entry?.toFixed(0) || '-'}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-green-400">DI+: {primaryAlert.di_plus_4h_at_entry?.toFixed(0) || '-'}</span>
                    <span className="text-[10px] text-red-400">DI-: {primaryAlert.di_minus_4h_at_entry?.toFixed(0) || '-'}</span>
                  </div>
                  <div className={`text-[10px] mt-1 ${(primaryAlert.di_spread_4h_at_entry || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Spread: {primaryAlert.di_spread_4h_at_entry?.toFixed(1) || '-'}
                  </div>
                </div>
              </div>

              {/* Extreme Zones 4H */}
              {(primaryAlert.di_plus_4h_overbought || primaryAlert.di_minus_4h_oversold) && (
                <div className={`p-2 rounded border ${primaryAlert.di_plus_4h_overbought ? 'border-orange-500/30 bg-orange-500/10' : 'border-lime-500/30 bg-lime-500/10'}`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${primaryAlert.di_plus_4h_overbought ? 'text-orange-400' : 'text-lime-400'}`} />
                    <span className={`text-xs font-medium ${primaryAlert.di_plus_4h_overbought ? 'text-orange-400' : 'text-lime-400'}`}>
                      {primaryAlert.di_plus_4h_overbought ? 'DI+ > 60 (4H): Momentum extrême haussier' : 'DI- > 60 (4H): Pression vendeuse extrême'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Foreign Candle Order Block (SMC Pattern) */}
          {primaryAlert && (primaryAlert.fc_ob_1h_found || primaryAlert.fc_ob_4h_found) && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Target className="w-4 h-4 text-teal-400" />
                Foreign Candle Order Block (SMC)
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
                  primaryAlert.fc_ob_label === 'STRONG RETEST' ? 'bg-green-500/30 text-green-400 border border-green-500/50' :
                  primaryAlert.fc_ob_label === 'RETEST 1H' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                  primaryAlert.fc_ob_label === 'RETEST 4H' ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30' :
                  primaryAlert.fc_ob_label === 'OB NEARBY' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                }`}>
                  {primaryAlert.fc_ob_label || 'N/A'} ({primaryAlert.fc_ob_score || 0}/100)
                </span>
                {primaryAlert.fc_ob_bonus && (
                  <span className="px-1.5 py-0.5 bg-teal-500/20 text-teal-400 text-[10px] rounded">BONUS</span>
                )}
              </h3>

              {/* Explanation */}
              <div className="text-xs text-gray-400 mb-3 italic">
                Bougie de couleur opposée dans une séquence de bougies (ex: rouge dans vert) = zone de demande institutionnelle
              </div>

              {/* OB Grid */}
              <div className="grid grid-cols-2 gap-3">
                {/* 1H Foreign Candle OB */}
                {primaryAlert.fc_ob_1h_found && (
                  <div className={`p-3 rounded border ${
                    primaryAlert.fc_ob_1h_retest ? 'border-green-500/50 bg-green-500/10' : 'border-teal-500/30 bg-teal-500/5'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-teal-400">Order Block 1H</span>
                      {primaryAlert.fc_ob_1h_retest && (
                        <span className="px-1.5 py-0.5 bg-green-500/30 text-green-400 text-[10px] rounded">RETEST ✓</span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div>
                        <span className="text-gray-500">Zone High:</span>
                        <span className="ml-1 text-white font-mono">{primaryAlert.fc_ob_1h_zone_high?.toFixed(4) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Zone Low:</span>
                        <span className="ml-1 text-white font-mono">{primaryAlert.fc_ob_1h_zone_low?.toFixed(4) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Strength:</span>
                        <span className={`ml-1 ${(primaryAlert.fc_ob_1h_strength || 0) >= 5 ? 'text-green-400' : 'text-yellow-400'}`}>
                          {primaryAlert.fc_ob_1h_strength || '-'} candles
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Distance:</span>
                        <span className={`ml-1 ${(primaryAlert.fc_ob_1h_distance_pct || 100) < 3 ? 'text-green-400' : 'text-yellow-400'}`}>
                          {primaryAlert.fc_ob_1h_distance_pct?.toFixed(2) || '-'}%
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-[10px] text-gray-400 flex items-center justify-between">
                      <div>
                        Type: <span className={primaryAlert.fc_ob_1h_type === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                          {primaryAlert.fc_ob_1h_type || '-'}
                        </span>
                      </div>
                      {((primaryAlert.fc_ob_1h_in_zone || 0) > 0 || (primaryAlert.fc_ob_1h_count || 0) > 0) && (
                        <button
                          onClick={() => { setFcObModalAlert(primaryAlert); setShowFcObModal(true); }}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold cursor-pointer hover:scale-105 transition-transform ${
                            (primaryAlert.fc_ob_1h_retested || 0) > 0 ? 'bg-green-500/30 text-green-400 hover:bg-green-500/50' : 'bg-gray-500/30 text-gray-400 hover:bg-gray-500/50'
                          }`}
                          title="Cliquez pour voir les détails des Order Blocks"
                        >
                          {primaryAlert.fc_ob_1h_retested || 0}/{primaryAlert.fc_ob_1h_in_zone || primaryAlert.fc_ob_1h_count || 0} OBs 🔍
                        </button>
                      )}
                    </div>
                    {primaryAlert.fc_ob_1h_datetime && (
                      <div className="mt-1 text-[10px]">
                        <span className="text-gray-500">Date/Time:</span>
                        <span className="ml-1 text-cyan-400 font-mono">{new Date(primaryAlert.fc_ob_1h_datetime).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* 4H Foreign Candle OB */}
                {primaryAlert.fc_ob_4h_found && (
                  <div className={`p-3 rounded border ${
                    primaryAlert.fc_ob_4h_retest ? 'border-green-500/50 bg-green-500/10' : 'border-purple-500/30 bg-purple-500/5'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-purple-400">Order Block 4H</span>
                      {primaryAlert.fc_ob_4h_retest && (
                        <span className="px-1.5 py-0.5 bg-green-500/30 text-green-400 text-[10px] rounded">RETEST ✓</span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div>
                        <span className="text-gray-500">Zone High:</span>
                        <span className="ml-1 text-white font-mono">{primaryAlert.fc_ob_4h_zone_high?.toFixed(4) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Zone Low:</span>
                        <span className="ml-1 text-white font-mono">{primaryAlert.fc_ob_4h_zone_low?.toFixed(4) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Strength:</span>
                        <span className={`ml-1 ${(primaryAlert.fc_ob_4h_strength || 0) >= 4 ? 'text-green-400' : 'text-yellow-400'}`}>
                          {primaryAlert.fc_ob_4h_strength || '-'} candles
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Distance:</span>
                        <span className={`ml-1 ${(primaryAlert.fc_ob_4h_distance_pct || 100) < 5 ? 'text-green-400' : 'text-yellow-400'}`}>
                          {primaryAlert.fc_ob_4h_distance_pct?.toFixed(2) || '-'}%
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-[10px] text-gray-400 flex items-center justify-between">
                      <div>
                        Type: <span className={primaryAlert.fc_ob_4h_type === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                          {primaryAlert.fc_ob_4h_type || '-'}
                        </span>
                      </div>
                      {((primaryAlert.fc_ob_4h_in_zone || 0) > 0 || (primaryAlert.fc_ob_4h_count || 0) > 0) && (
                        <button
                          onClick={() => { setFcObModalAlert(primaryAlert); setShowFcObModal(true); }}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold cursor-pointer hover:scale-105 transition-transform ${
                            (primaryAlert.fc_ob_4h_retested || 0) > 0 ? 'bg-green-500/30 text-green-400 hover:bg-green-500/50' : 'bg-gray-500/30 text-gray-400 hover:bg-gray-500/50'
                          }`}
                          title="Cliquez pour voir les détails des Order Blocks"
                        >
                          {primaryAlert.fc_ob_4h_retested || 0}/{primaryAlert.fc_ob_4h_in_zone || primaryAlert.fc_ob_4h_count || 0} OBs 🔍
                        </button>
                      )}
                    </div>
                    {primaryAlert.fc_ob_4h_datetime && (
                      <div className="mt-1 text-[10px]">
                        <span className="text-gray-500">Date/Time:</span>
                        <span className="ml-1 text-cyan-400 font-mono">{new Date(primaryAlert.fc_ob_4h_datetime).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Retest Confirmation Banner */}
              {(primaryAlert.fc_ob_1h_retest || primaryAlert.fc_ob_4h_retest) && (
                <div className="mt-3 p-2 rounded bg-green-500/10 border border-green-500/30">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span className="text-xs text-green-400 font-medium">
                      Prix a retesté la zone Foreign Candle OB - Zone de demande institutionnelle confirmée!
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Progressive Entry Conditions (from primary alert) */}
          {primaryAlert && primaryAlert.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-3">Entry Conditions #2-6 (Progressive)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                <ConditionBadge
                  valid={primaryAlert.prog_valid_ema100_1h}
                  label="Price 1H > EMA100"
                  value={`${formatNumber(primaryAlert.prog_price_1h, 4)} > ${formatNumber(primaryAlert.prog_ema100_1h, 4)}`}
                />
                <ConditionBadge
                  valid={primaryAlert.prog_valid_ema20_4h}
                  label="Price 4H > EMA20"
                  value={`${formatNumber(primaryAlert.prog_price_4h, 4)} > ${formatNumber(primaryAlert.prog_ema20_4h, 4)}`}
                />
                <ConditionBadge
                  valid={primaryAlert.prog_valid_cloud_1h}
                  label="Price 1H > Cloud"
                  value={`${formatNumber(primaryAlert.prog_price_1h, 4)} > ${formatNumber(primaryAlert.prog_cloud_1h, 4)}`}
                />
                <ConditionBadge
                  valid={primaryAlert.prog_valid_cloud_30m}
                  label="Price 30m > Cloud"
                  value={`${formatNumber(primaryAlert.prog_price_30m, 4)} > ${formatNumber(primaryAlert.prog_cloud_30m, 4)}`}
                />
                <ConditionBadge
                  valid={primaryAlert.prog_choch_bos_valid}
                  label="CHoCH/BOS Confirmed"
                  value={primaryAlert.prog_choch_bos_datetime ? formatDate(primaryAlert.prog_choch_bos_datetime) : null}
                />
              </div>
            </div>
          )}

          {/* Fibonacci Levels (4H) - Compact for COMBO */}
          {primaryAlert?.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-400" />
                Fibonacci (4H)
                <span className="text-xs text-gray-400">Entry: {formatNumber(primaryAlert.entry_price, 6)}</span>
              </h3>
              <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                {primaryAlert.fib_levels && Object.keys(primaryAlert.fib_levels).length > 0 ? (
                  <div className="grid grid-cols-5 gap-1 text-xs">
                    {['0.236', '0.382', '0.5', '0.618', '0.786'].map((level) => {
                      const fibLevel = primaryAlert.fib_levels?.[level]
                      if (!fibLevel) return null
                      const levelPct = (parseFloat(level) * 100).toFixed(1)
                      const isBreak = fibLevel.break
                      return (
                        <div
                          key={level}
                          className={`p-1.5 rounded text-center ${
                            isBreak ? 'bg-green-500/20 border border-green-500/30' : 'bg-red-500/20 border border-red-500/30'
                          }`}
                        >
                          <div className={`font-bold ${level === '0.382' ? 'text-yellow-400' : 'text-white'}`}>{levelPct}%</div>
                          <div className="text-gray-400 font-mono text-[10px]">{formatNumber(fibLevel.price, 4)}</div>
                          <div className={`text-[10px] ${isBreak ? 'text-green-400' : 'text-red-400'}`}>
                            {isBreak ? '✓' : '✗'}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500">Fibonacci data not available</div>
                )}
              </div>
            </div>
          )}

          {/* Fibonacci Levels (1H) - Compact for COMBO */}
          {primaryAlert.has_entry && primaryAlert.fib_levels_1h && Object.keys(primaryAlert.fib_levels_1h).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                Fibonacci (1H)
                <span className="text-xs text-gray-400">Entry: {formatNumber(primaryAlert.entry_price, 6)}</span>
              </h3>
              <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                <div className="grid grid-cols-5 gap-1 text-xs">
                  {['0.236', '0.382', '0.5', '0.618', '0.786'].map((level) => {
                    const fibLevel = primaryAlert.fib_levels_1h?.[level]
                    if (!fibLevel) return null
                    const levelPct = (parseFloat(level) * 100).toFixed(1)
                    const isBreak = fibLevel.break
                    return (
                      <div
                        key={level}
                        className={`p-1.5 rounded text-center ${
                          isBreak ? 'bg-green-500/20 border border-green-500/30' : 'bg-red-500/20 border border-red-500/30'
                        }`}
                      >
                        <div className="font-bold text-white">{levelPct}%</div>
                        <div className="text-gray-400 font-mono text-[10px]">{formatNumber(fibLevel.price, 4)}</div>
                        <div className={`text-[10px] ${isBreak ? 'text-green-400' : 'text-red-400'}`}>
                          {isBreak ? '✓' : '✗'}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Order Block (SMC) - Compact for COMBO */}
          {primaryAlert.has_entry && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${(primaryAlert.ob_bonus || primaryAlert.ob_bonus_4h) ? 'bg-purple-500' : 'bg-gray-600'}`} />
                Order Block (SMC)
                {primaryAlert.ob_bonus && (
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full border border-purple-500/30">
                    1H
                  </span>
                )}
                {primaryAlert.ob_bonus_4h && (
                  <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full border border-orange-500/30">
                    4H
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {/* OB 1H Compact */}
                <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-[10px] font-semibold text-purple-400 mb-1">1H</div>
                  {primaryAlert.ob_bonus && primaryAlert.ob_zone_high ? (
                    <div className="text-xs space-y-1">
                      <div><span className="text-gray-400">Zone:</span> <span className="text-purple-400 font-mono">{formatNumber(primaryAlert.ob_zone_low, 2)}-{formatNumber(primaryAlert.ob_zone_high, 2)}</span></div>
                      <div><span className="text-gray-400">Pos:</span> <span className={primaryAlert.ob_position === 'INSIDE' ? 'text-green-400' : primaryAlert.ob_position === 'ABOVE' ? 'text-yellow-400' : 'text-red-400'}>{primaryAlert.ob_position}</span> <span className="text-gray-400">Str:</span> <span className={primaryAlert.ob_strength === 'STRONG' ? 'text-green-400' : primaryAlert.ob_strength === 'MODERATE' ? 'text-yellow-400' : 'text-red-400'}>{primaryAlert.ob_strength}</span></div>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-500">No OB</div>
                  )}
                </div>
                {/* OB 4H Compact */}
                <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-[10px] font-semibold text-orange-400 mb-1">4H</div>
                  {primaryAlert.ob_bonus_4h && primaryAlert.ob_zone_high_4h ? (
                    <div className="text-xs space-y-1">
                      <div><span className="text-gray-400">Zone:</span> <span className="text-orange-400 font-mono">{formatNumber(primaryAlert.ob_zone_low_4h, 2)}-{formatNumber(primaryAlert.ob_zone_high_4h, 2)}</span></div>
                      <div><span className="text-gray-400">Pos:</span> <span className={primaryAlert.ob_position_4h === 'INSIDE' ? 'text-green-400' : primaryAlert.ob_position_4h === 'ABOVE' ? 'text-yellow-400' : 'text-red-400'}>{primaryAlert.ob_position_4h}</span> <span className="text-gray-400">Str:</span> <span className={primaryAlert.ob_strength_4h === 'STRONG' ? 'text-green-400' : primaryAlert.ob_strength_4h === 'MODERATE' ? 'text-yellow-400' : 'text-red-400'}>{primaryAlert.ob_strength_4h}</span></div>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-500">No OB</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* BTC Correlation BONUS - Compact for COMBO */}
          {primaryAlert.has_entry && (primaryAlert.btc_trend_1h || primaryAlert.btc_trend_4h) && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${(primaryAlert.btc_corr_bonus_1h || primaryAlert.btc_corr_bonus_4h) ? 'bg-yellow-500' : 'bg-gray-600'}`} />
                BTC Correlation
                {primaryAlert.btc_corr_bonus_1h && (
                  <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full border border-green-500/30">
                    1H
                  </span>
                )}
                {primaryAlert.btc_corr_bonus_4h && (
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full border border-emerald-500/30">
                    4H
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {/* BTC 1H Compact */}
                <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-[10px] font-semibold text-yellow-400 mb-1">1H</div>
                  {primaryAlert.btc_trend_1h ? (
                    <div className="text-xs space-y-1">
                      <div><span className="text-gray-400">Trend:</span> <span className={primaryAlert.btc_trend_1h === 'BULLISH' ? 'text-green-400' : primaryAlert.btc_trend_1h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}>{primaryAlert.btc_trend_1h}</span></div>
                      <div><span className="text-gray-400">RSI:</span> <span className={`font-mono ${(primaryAlert.btc_rsi_1h || 0) > 50 ? 'text-green-400' : 'text-red-400'}`}>{primaryAlert.btc_rsi_1h?.toFixed(1)}</span> <span className="text-gray-400">P:</span> <span className="font-mono text-white">${primaryAlert.btc_price_1h?.toFixed(0)}</span></div>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-500">N/A</div>
                  )}
                </div>
                {/* BTC 4H Compact */}
                <div className="p-2 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="text-[10px] font-semibold text-amber-400 mb-1">4H</div>
                  {primaryAlert.btc_trend_4h ? (
                    <div className="text-xs space-y-1">
                      <div><span className="text-gray-400">Trend:</span> <span className={primaryAlert.btc_trend_4h === 'BULLISH' ? 'text-green-400' : primaryAlert.btc_trend_4h === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}>{primaryAlert.btc_trend_4h}</span></div>
                      <div><span className="text-gray-400">RSI:</span> <span className={`font-mono ${(primaryAlert.btc_rsi_4h || 0) > 50 ? 'text-green-400' : 'text-red-400'}`}>{primaryAlert.btc_rsi_4h?.toFixed(1)}</span> <span className="text-gray-400">P:</span> <span className="font-mono text-white">${primaryAlert.btc_price_4h?.toFixed(0)}</span></div>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-500">N/A</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Related Alerts - Show each alert's MEGA BUY conditions */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">
              Alert Conditions ({relatedAlerts.length} alert{relatedAlerts.length > 1 ? 's' : ''})
            </h3>
            <div className="space-y-4">
              {relatedAlerts.map((alert, alertIdx) => (
                <div key={alert.id} className="bg-gray-800/30 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                        {alert.timeframe}
                      </span>
                      <span className="text-sm text-gray-400">{formatDate(alert.alert_datetime)}</span>
                      <span className={`text-sm font-medium ${alert.score >= 8 ? 'text-green-400' : alert.score >= 7 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {alert.score}/10
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">Price: {formatNumber(alert.price_close, 6)}</span>
                  </div>

                  {/* MEGA BUY 10 Conditions */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-1.5">
                    {megaBuyConditions.map(cond => (
                      <div
                        key={cond.key}
                        className={`px-2 py-1 rounded text-xs flex items-center gap-1 ${
                          alert.conditions[cond.key]
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-700/30 text-gray-500'
                        }`}
                      >
                        {alert.conditions[cond.key] ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        <span className="truncate">{cond.label.replace(/\s*\([^)]*\)/g, '')}</span>
                      </div>
                    ))}
                  </div>

                  {/* STC & TL Info */}
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className={`px-2 py-0.5 rounded ${alert.stc_validated ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      STC: {alert.stc_valid_tfs || 'None'}
                    </span>
                    {alert.has_trendline && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
                        TL: {alert.tl_type}
                      </span>
                    )}
                    {alert.has_tl_break && (
                      <span className={`px-2 py-0.5 rounded ${alert.delay_exceeded ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                        Break: {alert.tl_break_delay_hours?.toFixed(1)}h
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* FC OB Details Modal */}
      {showFcObModal && fcObModalAlert && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4">
          <div className="bg-gray-900 rounded-xl border border-teal-500/30 max-w-2xl w-full max-h-[85vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 sticky top-0 bg-gray-900">
              <div className="flex items-center gap-3">
                <Target className="w-5 h-5 text-teal-400" />
                <h2 className="text-lg font-bold text-white">Foreign Candle Order Blocks</h2>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  fcObModalAlert.fc_ob_label?.includes('STRONG') ? 'bg-green-500/30 text-green-400' :
                  fcObModalAlert.fc_ob_label?.includes('RETEST') ? 'bg-teal-500/30 text-teal-400' :
                  'bg-gray-500/30 text-gray-400'
                }`}>
                  {fcObModalAlert.fc_ob_label} ({fcObModalAlert.fc_ob_score}/100)
                </span>
              </div>
              <button
                onClick={() => setShowFcObModal(false)}
                className="p-1 hover:bg-gray-700 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 space-y-4">
              {/* Trade Context */}
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Contexte du Trade</h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Alert:</span>
                    <span className="ml-2 text-white">{new Date(fcObModalAlert.alert_datetime).toLocaleString('fr-FR')}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Status:</span>
                    <span className={`ml-2 ${fcObModalAlert.status.includes('VALID') ? 'text-green-400' : 'text-yellow-400'}`}>
                      {fcObModalAlert.status}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Entry Price:</span>
                    <span className="ml-2 text-cyan-400 font-mono">{fcObModalAlert.entry_price?.toFixed(5) || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Retest Price:</span>
                    <span className="ml-2 text-purple-400 font-mono">{fcObModalAlert.v3_retest_price?.toFixed(5) || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* 1H Order Blocks */}
              {fcObModalAlert.fc_ob_1h_found && (
                <div className="p-3 rounded-lg bg-teal-500/5 border border-teal-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-teal-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-teal-400"></span>
                      Order Blocks 1H
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Total: {fcObModalAlert.fc_ob_1h_count}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        (fcObModalAlert.fc_ob_1h_retested || 0) > 0 ? 'bg-green-500/30 text-green-400' : 'bg-gray-500/30 text-gray-400'
                      }`}>
                        {fcObModalAlert.fc_ob_1h_retested}/{fcObModalAlert.fc_ob_1h_in_zone} retestés
                      </span>
                    </div>
                  </div>

                  {/* Best OB Details */}
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-white">Meilleur Order Block (plus proche)</span>
                      {fcObModalAlert.fc_ob_1h_retest && (
                        <span className="px-2 py-0.5 bg-green-500/30 text-green-400 text-[10px] rounded flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> RETESTÉ
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone High:</span>
                          <span className="text-green-400 font-mono">{fcObModalAlert.fc_ob_1h_zone_high?.toFixed(5)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone Low:</span>
                          <span className="text-red-400 font-mono">{fcObModalAlert.fc_ob_1h_zone_low?.toFixed(5)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone Range:</span>
                          <span className="text-white font-mono">
                            {fcObModalAlert.fc_ob_1h_zone_high && fcObModalAlert.fc_ob_1h_zone_low
                              ? ((fcObModalAlert.fc_ob_1h_zone_high - fcObModalAlert.fc_ob_1h_zone_low) / fcObModalAlert.fc_ob_1h_zone_low * 100).toFixed(2) + '%'
                              : '-'}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Type:</span>
                          <span className={fcObModalAlert.fc_ob_1h_type === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                            {fcObModalAlert.fc_ob_1h_type}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Strength:</span>
                          <span className={`${(fcObModalAlert.fc_ob_1h_strength || 0) >= 5 ? 'text-green-400' : 'text-yellow-400'}`}>
                            {fcObModalAlert.fc_ob_1h_strength} candles
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Distance:</span>
                          <span className={`${(fcObModalAlert.fc_ob_1h_distance_pct || 100) < 3 ? 'text-green-400' : 'text-yellow-400'}`}>
                            {fcObModalAlert.fc_ob_1h_distance_pct?.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                    {/* DateTime */}
                    <div className="mt-3 pt-2 border-t border-gray-700">
                      <div className="flex items-center gap-2 text-xs">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-gray-500">Date/Time:</span>
                        <span className="text-cyan-400 font-mono">
                          {fcObModalAlert.fc_ob_1h_datetime
                            ? new Date(fcObModalAlert.fc_ob_1h_datetime).toLocaleString('fr-FR', {
                                weekday: 'short',
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })
                            : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="mt-3 text-[10px] text-gray-400 italic">
                    {fcObModalAlert.fc_ob_1h_in_zone} Order Block(s) trouvé(s) dans la zone de retest, dont {fcObModalAlert.fc_ob_1h_retested} retesté(s).
                    {(fcObModalAlert.fc_ob_1h_retested || 0) >= 2 && (
                      <span className="text-green-400 not-italic font-medium ml-1">
                        🎯 Multiple OBs confluence = zone de demande forte!
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* 4H Order Blocks */}
              {fcObModalAlert.fc_ob_4h_found && (
                <div className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-purple-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                      Order Blocks 4H
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Total: {fcObModalAlert.fc_ob_4h_count}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        (fcObModalAlert.fc_ob_4h_retested || 0) > 0 ? 'bg-green-500/30 text-green-400' : 'bg-gray-500/30 text-gray-400'
                      }`}>
                        {fcObModalAlert.fc_ob_4h_retested}/{fcObModalAlert.fc_ob_4h_in_zone} retestés
                      </span>
                    </div>
                  </div>

                  {/* Best OB Details */}
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-white">Meilleur Order Block (plus proche)</span>
                      {fcObModalAlert.fc_ob_4h_retest && (
                        <span className="px-2 py-0.5 bg-green-500/30 text-green-400 text-[10px] rounded flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> RETESTÉ
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone High:</span>
                          <span className="text-green-400 font-mono">{fcObModalAlert.fc_ob_4h_zone_high?.toFixed(5)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone Low:</span>
                          <span className="text-red-400 font-mono">{fcObModalAlert.fc_ob_4h_zone_low?.toFixed(5)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Zone Range:</span>
                          <span className="text-white font-mono">
                            {fcObModalAlert.fc_ob_4h_zone_high && fcObModalAlert.fc_ob_4h_zone_low
                              ? ((fcObModalAlert.fc_ob_4h_zone_high - fcObModalAlert.fc_ob_4h_zone_low) / fcObModalAlert.fc_ob_4h_zone_low * 100).toFixed(2) + '%'
                              : '-'}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Type:</span>
                          <span className={fcObModalAlert.fc_ob_4h_type === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                            {fcObModalAlert.fc_ob_4h_type}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Strength:</span>
                          <span className={`${(fcObModalAlert.fc_ob_4h_strength || 0) >= 4 ? 'text-green-400' : 'text-yellow-400'}`}>
                            {fcObModalAlert.fc_ob_4h_strength} candles
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Distance:</span>
                          <span className={`${(fcObModalAlert.fc_ob_4h_distance_pct || 100) < 5 ? 'text-green-400' : 'text-yellow-400'}`}>
                            {fcObModalAlert.fc_ob_4h_distance_pct?.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                    {/* DateTime */}
                    <div className="mt-3 pt-2 border-t border-gray-700">
                      <div className="flex items-center gap-2 text-xs">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-gray-500">Date/Time:</span>
                        <span className="text-cyan-400 font-mono">
                          {fcObModalAlert.fc_ob_4h_datetime
                            ? new Date(fcObModalAlert.fc_ob_4h_datetime).toLocaleString('fr-FR', {
                                weekday: 'short',
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })
                            : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="mt-3 text-[10px] text-gray-400 italic">
                    {fcObModalAlert.fc_ob_4h_in_zone} Order Block(s) trouvé(s) dans la zone de retest, dont {fcObModalAlert.fc_ob_4h_retested} retesté(s).
                    {(fcObModalAlert.fc_ob_4h_retested || 0) >= 2 && (
                      <span className="text-green-400 not-italic font-medium ml-1">
                        🎯 Multiple OBs confluence = zone de demande forte!
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Multi-TF Confluence */}
              {fcObModalAlert.fc_ob_1h_retest && fcObModalAlert.fc_ob_4h_retest && (
                <div className="p-3 rounded-lg bg-gradient-to-r from-teal-500/10 to-purple-500/10 border border-green-500/50">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <span className="text-sm font-bold text-green-400">Confluence Multi-Timeframe!</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-300">
                    Le prix a retesté des zones Order Block sur 1H ET 4H. Cette confluence renforce significativement
                    la probabilité d&apos;un rebond depuis cette zone de demande institutionnelle.
                  </p>
                </div>
              )}

              {/* Legend */}
              <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-700">
                <h4 className="text-xs font-semibold text-gray-400 mb-2">Légende</h4>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-500">
                  <div><span className="text-green-400">●</span> BULLISH OB = Bougie rouge dans séquence verte (zone de demande)</div>
                  <div><span className="text-red-400">●</span> BEARISH OB = Bougie verte dans séquence rouge (zone de supply)</div>
                  <div><span className="text-yellow-400">●</span> Strength = Nombre de bougies environnantes</div>
                  <div><span className="text-cyan-400">●</span> Distance = % entre prix et zone OB</div>
                </div>
              </div>
            </div>

            {/* PineScript Section */}
            {showFcObPineScript && fcObModalAlert && (
              <div className="p-4 border-t border-gray-700 bg-gray-900/50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-orange-400 flex items-center gap-2">
                    <Code className="w-4 h-4" />
                    PineScript TradingView - Trendline + Order Blocks
                  </h3>
                  <button
                    onClick={() => {
                      const pineScript = generateCombinedPineScript(symbol, fcObModalAlert)
                      navigator.clipboard.writeText(pineScript)
                      setFcObPineScriptCopied(true)
                      setTimeout(() => setFcObPineScriptCopied(false), 2000)
                    }}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      fcObPineScriptCopied
                        ? 'bg-green-500/30 text-green-400'
                        : 'bg-orange-500/20 hover:bg-orange-500/30 text-orange-400'
                    }`}
                  >
                    {fcObPineScriptCopied ? (
                      <>
                        <CheckCircle className="w-3.5 h-3.5" />
                        Copié!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        Copier le code
                      </>
                    )}
                  </button>
                </div>
                <div className="relative">
                  <pre className="bg-gray-950 p-3 rounded-lg text-[10px] font-mono text-gray-300 overflow-x-auto max-h-64 overflow-y-auto border border-gray-700">
                    {generateCombinedPineScript(symbol, fcObModalAlert)}
                  </pre>
                  <div className="absolute bottom-2 right-2 text-[9px] text-gray-500 bg-gray-950/80 px-2 py-1 rounded">
                    Pine Script v5
                  </div>
                </div>
                <p className="mt-2 text-[10px] text-gray-500">
                  Copiez ce code et collez-le dans TradingView: Pine Editor → Nouveau → Coller → Ajouter au graphique
                </p>
              </div>
            )}

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-700 flex justify-between items-center">
              <button
                onClick={() => setShowFcObPineScript(!showFcObPineScript)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  showFcObPineScript
                    ? 'bg-orange-500/30 text-orange-400 border border-orange-500/50'
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                }`}
              >
                <Code className="w-4 h-4" />
                {showFcObPineScript ? 'Masquer PineScript' : '📊 Voir sur TradingView'}
              </button>
              <button
                onClick={() => {
                  setShowFcObModal(false)
                  setShowFcObPineScript(false)
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface RunningBacktest {
  id: string
  symbol: string
  status: 'running' | 'completed' | 'error'
  progress: string
}

export default function BacktestPage() {
  const [backtests, setBacktests] = useState<BacktestRun[]>([])
  const [loading, setLoading] = useState(true)
  const [runningBacktests, setRunningBacktests] = useState<RunningBacktest[]>([])
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [selectedTrade, setSelectedTrade] = useState<GroupedTrade | null>(null)

  // Form state
  const [symbol, setSymbol] = useState("ENSOUSDT")
  const [startDate, setStartDate] = useState("2026-02-01")
  const [endDate, setEndDate] = useState("2026-02-28")
  const [strategyVersion, setStrategyVersion] = useState<"v1" | "v2" | "v3" | "v4" | "v5">("v5")

  // Advanced Filters State
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [filterSymbol, setFilterSymbol] = useState<string>("")
  const [filterVersion, setFilterVersion] = useState<string>("all")
  const [filterDateFrom, setFilterDateFrom] = useState<string>("")
  const [filterDateTo, setFilterDateTo] = useState<string>("")
  const [filterMinPnl, setFilterMinPnl] = useState<string>("")
  const [filterMaxPnl, setFilterMaxPnl] = useState<string>("")
  const [filterMinTrades, setFilterMinTrades] = useState<string>("")
  const [filterWinOnly, setFilterWinOnly] = useState(false)
  const [filterLossOnly, setFilterLossOnly] = useState(false)

  // Pagination for Top/Bottom symbols
  const [topSymbolsPage, setTopSymbolsPage] = useState(0)
  const [bottomSymbolsPage, setBottomSymbolsPage] = useState(0)
  const SYMBOLS_PER_PAGE = 5

  // Compute filtered backtests
  const filteredBacktests = useMemo(() => {
    return backtests.filter(bt => {
      // PRIMARY: Filter by selected strategy version (from form)
      // This ensures we only show backtests of the selected version
      if ((bt.strategy_version || 'v1') !== strategyVersion) {
        return false
      }
      // Symbol filter
      if (filterSymbol && !bt.symbol.toLowerCase().includes(filterSymbol.toLowerCase())) {
        return false
      }
      // Version filter (advanced panel - for additional filtering within selected version)
      if (filterVersion !== "all" && bt.strategy_version !== filterVersion) {
        return false
      }
      // Date filters
      if (filterDateFrom && new Date(bt.start_date) < new Date(filterDateFrom)) {
        return false
      }
      if (filterDateTo && new Date(bt.end_date) > new Date(filterDateTo)) {
        return false
      }
      // PnL filters
      if (filterMinPnl && bt.pnl_strategy_c < parseFloat(filterMinPnl)) {
        return false
      }
      if (filterMaxPnl && bt.pnl_strategy_c > parseFloat(filterMaxPnl)) {
        return false
      }
      // Min trades filter
      if (filterMinTrades && bt.total_trades < parseInt(filterMinTrades)) {
        return false
      }
      // Win/Loss only
      if (filterWinOnly && bt.pnl_strategy_c <= 0) {
        return false
      }
      if (filterLossOnly && bt.pnl_strategy_c >= 0) {
        return false
      }
      return true
    })
  }, [backtests, strategyVersion, filterSymbol, filterVersion, filterDateFrom, filterDateTo, filterMinPnl, filterMaxPnl, filterMinTrades, filterWinOnly, filterLossOnly])

  // Compute comprehensive statistics
  const statistics = useMemo(() => {
    const bt = filteredBacktests
    if (bt.length === 0) return null

    // Basic stats
    const totalBacktests = bt.length
    const totalTrades = bt.reduce((sum, b) => sum + b.total_trades, 0)
    const totalAlerts = bt.reduce((sum, b) => sum + b.total_alerts, 0)

    // IMPORTANT: Only consider backtests WITH trades for win/loss calculation
    const backtestsWithTrades = bt.filter(b => b.total_trades > 0)
    const backtestsWithoutTrades = bt.filter(b => b.total_trades === 0)

    // PnL stats - only for backtests with trades
    const winningBt = backtestsWithTrades.filter(b => b.pnl_strategy_c > 0)
    const losingBt = backtestsWithTrades.filter(b => b.pnl_strategy_c < 0)
    const breakEvenBt = backtestsWithTrades.filter(b => b.pnl_strategy_c === 0)

    const totalPnlC = bt.reduce((sum, b) => sum + b.pnl_strategy_c, 0)
    const totalPnlD = bt.reduce((sum, b) => sum + b.pnl_strategy_d, 0)

    // Average PnL only for backtests with trades
    const avgPnlC = backtestsWithTrades.length > 0
      ? backtestsWithTrades.reduce((sum, b) => sum + b.pnl_strategy_c, 0) / backtestsWithTrades.length
      : 0
    const avgPnlD = backtestsWithTrades.length > 0
      ? backtestsWithTrades.reduce((sum, b) => sum + b.pnl_strategy_d, 0) / backtestsWithTrades.length
      : 0

    // Win/Loss rates - based on backtests WITH trades only
    const winRate = backtestsWithTrades.length > 0
      ? (winningBt.length / backtestsWithTrades.length) * 100
      : 0
    const lossRate = backtestsWithTrades.length > 0
      ? (losingBt.length / backtestsWithTrades.length) * 100
      : 0

    // Average win/loss per backtest
    const avgWin = winningBt.length > 0
      ? winningBt.reduce((sum, b) => sum + b.pnl_strategy_c, 0) / winningBt.length
      : 0
    const avgLoss = losingBt.length > 0
      ? losingBt.reduce((sum, b) => sum + b.pnl_strategy_c, 0) / losingBt.length
      : 0

    // Average PnL per trade (more accurate)
    const avgPnlPerTrade = totalTrades > 0 ? totalPnlC / totalTrades : 0

    // Best/Worst - only from backtests with trades
    const pnlsWithTrades = backtestsWithTrades.map(b => b.pnl_strategy_c)
    const bestPnl = pnlsWithTrades.length > 0 ? Math.max(...pnlsWithTrades) : 0
    const worstPnl = pnlsWithTrades.length > 0 ? Math.min(...pnlsWithTrades) : 0
    const bestBacktest = backtestsWithTrades.find(b => b.pnl_strategy_c === bestPnl)
    const worstBacktest = backtestsWithTrades.find(b => b.pnl_strategy_c === worstPnl)

    // Profit Factor
    const grossProfit = winningBt.reduce((sum, b) => sum + b.pnl_strategy_c, 0)
    const grossLoss = Math.abs(losingBt.reduce((sum, b) => sum + b.pnl_strategy_c, 0))
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0

    // Expectancy (per backtest)
    const expectancy = backtestsWithTrades.length > 0
      ? (winRate / 100 * avgWin) + ((100 - winRate) / 100 * avgLoss)
      : 0

    // By Strategy Version - only backtests with trades
    const byVersion: Record<string, { count: number; trades: number; pnl: number; winRate: number; withTrades: number }> = {}
    bt.forEach(b => {
      const v = b.strategy_version || 'v1'
      if (!byVersion[v]) {
        byVersion[v] = { count: 0, trades: 0, pnl: 0, winRate: 0, withTrades: 0 }
      }
      byVersion[v].count++
      byVersion[v].trades += b.total_trades
      byVersion[v].pnl += b.pnl_strategy_c
      if (b.total_trades > 0) byVersion[v].withTrades++
    })
    Object.keys(byVersion).forEach(v => {
      const vBtWithTrades = bt.filter(b => (b.strategy_version || 'v1') === v && b.total_trades > 0)
      const vWins = vBtWithTrades.filter(b => b.pnl_strategy_c > 0).length
      byVersion[v].winRate = vBtWithTrades.length > 0 ? (vWins / vBtWithTrades.length) * 100 : 0
    })

    // By Symbol (top 10) - only consider backtests with trades
    const bySymbol: Record<string, { count: number; trades: number; pnl: number; winRate: number; withTrades: number }> = {}
    bt.forEach(b => {
      if (!bySymbol[b.symbol]) {
        bySymbol[b.symbol] = { count: 0, trades: 0, pnl: 0, winRate: 0, withTrades: 0 }
      }
      bySymbol[b.symbol].count++
      bySymbol[b.symbol].trades += b.total_trades
      bySymbol[b.symbol].pnl += b.pnl_strategy_c
      if (b.total_trades > 0) bySymbol[b.symbol].withTrades++
    })
    Object.keys(bySymbol).forEach(s => {
      const sBtWithTrades = bt.filter(b => b.symbol === s && b.total_trades > 0)
      const sWins = sBtWithTrades.filter(b => b.pnl_strategy_c > 0).length
      bySymbol[s].winRate = sBtWithTrades.length > 0 ? (sWins / sBtWithTrades.length) * 100 : 0
    })
    const topSymbols = Object.entries(bySymbol)
      .filter(([, data]) => data.trades > 0)  // Only symbols with trades
      .sort((a, b) => b[1].pnl - a[1].pnl)
      .slice(0, 20)
    const bottomSymbols = Object.entries(bySymbol)
      .filter(([, data]) => data.trades > 0)  // Only symbols with trades
      .sort((a, b) => a[1].pnl - b[1].pnl)
      .slice(0, 20)

    // Unique symbols
    const uniqueSymbols = [...new Set(bt.map(b => b.symbol))]

    return {
      totalBacktests,
      totalTrades,
      totalAlerts,
      backtestsWithTrades: backtestsWithTrades.length,
      backtestsWithoutTrades: backtestsWithoutTrades.length,
      winningCount: winningBt.length,
      losingCount: losingBt.length,
      breakEvenCount: breakEvenBt.length,
      totalPnlC,
      totalPnlD,
      avgPnlC,
      avgPnlD,
      avgPnlPerTrade,
      winRate,
      lossRate,
      avgWin,
      avgLoss,
      bestPnl,
      worstPnl,
      bestBacktest,
      worstBacktest,
      profitFactor,
      expectancy,
      byVersion,
      topSymbols,
      bottomSymbols,
      uniqueSymbols,
      // Best/Worst symbol by total PnL (not single backtest)
      bestSymbol: topSymbols.length > 0 ? { symbol: topSymbols[0][0], ...topSymbols[0][1] } : null,
      worstSymbol: bottomSymbols.length > 0 ? { symbol: bottomSymbols[0][0], ...bottomSymbols[0][1] } : null
    }
  }, [filteredBacktests])

  const fetchBacktests = async () => {
    try {
      const res = await fetch("/api/backtest")
      const data = await res.json()
      setBacktests(data.backtests || [])
    } catch (err) {
      console.error("Failed to fetch backtests:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBacktests()
  }, [])

  const runBacktest = async () => {
    // Auto-add USDT if not present
    const fullSymbol = symbol.endsWith("USDT") ? symbol : `${symbol}USDT`
    const runId = `${fullSymbol}-${Date.now()}`

    // Add to running list
    const newRunning: RunningBacktest = {
      id: runId,
      symbol: fullSymbol,
      status: 'running',
      progress: 'Starting...'
    }
    setRunningBacktests(prev => [...prev, newRunning])

    // Clear input for next backtest
    setSymbol("")

    // Run backtest async (non-blocking)
    try {
      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: fullSymbol, start_date: startDate, end_date: endDate, strategy_version: strategyVersion })
      })

      const data = await res.json()

      if (data.error) {
        setRunningBacktests(prev => prev.map(r =>
          r.id === runId ? { ...r, status: 'error' as const, progress: `Error: ${data.error}` } : r
        ))
      } else {
        setRunningBacktests(prev => prev.map(r =>
          r.id === runId ? { ...r, status: 'completed' as const, progress: `✓ ${data.trades} trades, P&L: ${data.pnl_c?.toFixed(1)}%` } : r
        ))
        fetchBacktests()
      }
    } catch (err) {
      setRunningBacktests(prev => prev.map(r =>
        r.id === runId ? { ...r, status: 'error' as const, progress: `Error: ${err}` } : r
      ))
    }

    // Auto-remove completed/error after 10 seconds
    setTimeout(() => {
      setRunningBacktests(prev => prev.filter(r => r.id !== runId))
    }, 10000)
  }

  const deleteBacktest = async (id: number) => {
    if (!confirm("Delete this backtest?")) return

    try {
      await fetch(`/api/backtest?id=${id}`, { method: "DELETE" })
      fetchBacktests()
      if (expandedId === id) {
        setExpandedId(null)
        setAlerts([])
        setTrades([])
      }
    } catch (err) {
      console.error("Failed to delete:", err)
    }
  }

  const toggleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null)
      setAlerts([])
      setTrades([])
      return
    }

    setExpandedId(id)
    setLoadingDetails(true)

    try {
      const [alertsRes, tradesRes] = await Promise.all([
        fetch(`/api/backtest/alerts?id=${id}`),
        fetch(`/api/backtest/trades?id=${id}`)
      ])

      const alertsData = await alertsRes.json()
      const tradesData = await tradesRes.json()

      setAlerts(alertsData.alerts || [])
      setTrades(tradesData.trades || [])
    } catch (err) {
      console.error("Failed to fetch details:", err)
    } finally {
      setLoadingDetails(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  }

  const getPnlColor = (pnl: number) => {
    if (pnl > 0) return "text-green-400"
    if (pnl < 0) return "text-red-400"
    return "text-gray-400"
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "VALID":
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case "WAITING":
        return <Clock className="w-4 h-4 text-yellow-400" />
      case "EXPIRED":
        return <XCircle className="w-4 h-4 text-gray-400" />
      default:
        return <AlertCircle className="w-4 h-4 text-red-400" />
    }
  }

  // Count valid conditions for quick display
  const countValidConditions = (conditions: Record<string, boolean>) => {
    return Object.values(conditions).filter(v => v).length
  }

  return (
    <div className="space-y-6">
      {/* Alert Detail Modal */}
      {selectedAlert && (
        <AlertDetailModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}

      {/* Trade Detail Modal */}
      {selectedTrade && (
        <TradeDetailModal
          trade={selectedTrade}
          relatedAlerts={alerts.filter(a => {
            // V1/V2: Check standard entry fields
            const v1Match = a.has_entry &&
              a.entry_datetime === selectedTrade.entry_datetime &&
              Math.abs((a.entry_price || 0) - selectedTrade.entry_price) < 0.00000001
            // V3: Check V3 entry fields
            const v3Match = a.v3_entry_found &&
              a.v3_entry_datetime === selectedTrade.entry_datetime &&
              Math.abs((a.v3_entry_price || 0) - selectedTrade.entry_price) < 0.00000001
            return v1Match || v3Match
          })}
          onClose={() => setSelectedTrade(null)}
          symbol={backtests.find(b => b.id === expandedId)?.symbol || ''}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FlaskConical className="w-7 h-7 text-purple-400" />
            Backtest
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            1H Trendline Break Strategy - Test and analyze trading signals
          </p>
        </div>
        <button
          onClick={fetchBacktests}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* New Backtest Form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Run New Backtest</h2>

        {/* Strategy Version Selector */}
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">Strategy Version</label>
          <div className="flex gap-2">
            <button
              onClick={() => setStrategyVersion("v1")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v1"
                  ? "bg-gray-700 border-gray-500 text-white"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600"
              }`}
            >
              <div className="text-sm font-bold">V1 - Legacy</div>
              <div className="text-xs text-gray-500 mt-1">Sans filtres optimisés (47% WR)</div>
            </button>
            <button
              onClick={() => setStrategyVersion("v2")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v2"
                  ? "bg-green-900/50 border-green-500 text-green-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-green-700"
              }`}
            >
              <div className="text-sm font-bold">V2 - Optimisé</div>
              <div className="text-xs text-gray-500 mt-1">Avec filtres avancés (65-75% WR)</div>
            </button>
            <button
              onClick={() => setStrategyVersion("v3")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v3"
                  ? "bg-cyan-900/50 border-cyan-500 text-cyan-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-cyan-700"
              }`}
            >
              <div className="text-sm font-bold">V3 - Golden Box</div>
              <div className="text-xs text-gray-500 mt-1">Breakout + Retest (SL optimisé)</div>
            </button>
            <button
              onClick={() => setStrategyVersion("v4")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v4"
                  ? "bg-amber-900/50 border-amber-500 text-amber-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-amber-700"
              }`}
            >
              <div className="text-sm font-bold">V4 - Optimized</div>
              <div className="text-xs text-gray-500 mt-1">V3 + Filtres ML (50%+ WR)</div>
            </button>
            <button
              onClick={() => setStrategyVersion("v5")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v5"
                  ? "bg-pink-900/50 border-pink-500 text-pink-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-pink-700"
              }`}
            >
              <div className="text-sm font-bold">V5 - VP Filter</div>
              <div className="text-xs text-gray-500 mt-1">V4 + Filtre Trajectoire VP</div>
            </button>
            <button
              onClick={() => setStrategyVersion("v6")}
              className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                strategyVersion === "v6"
                  ? "bg-purple-900/50 border-purple-500 text-purple-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-purple-700"
              }`}
            >
              <div className="text-sm font-bold">V6 - Advanced</div>
              <div className="text-xs text-gray-500 mt-1">V5 + Timing/Scoring (72%+ WR)</div>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Symbol <span className="text-gray-600">(USDT auto)</span></label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && symbol && runBacktest()}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
              placeholder="BTC, SOL, ENSO..."
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={runBacktest}
              disabled={!symbol}
              className={`w-full flex items-center justify-center gap-2 px-4 py-2 ${
                strategyVersion === "v6" ? "bg-purple-600 hover:bg-purple-700" :
                strategyVersion === "v5" ? "bg-pink-600 hover:bg-pink-700" :
                strategyVersion === "v4" ? "bg-amber-600 hover:bg-amber-700" :
                strategyVersion === "v3" ? "bg-cyan-600 hover:bg-cyan-700" :
                strategyVersion === "v2" ? "bg-green-600 hover:bg-green-700" : "bg-purple-600 hover:bg-purple-700"
              } disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors`}
            >
              <Play className="w-4 h-4" />
              Run {strategyVersion.toUpperCase()}
            </button>
          </div>
        </div>
        {/* Running Backtests Queue */}
        {runningBacktests.length > 0 && (
          <div className="mt-4 space-y-2">
            {runningBacktests.map(rb => (
              <div
                key={rb.id}
                className={`p-3 rounded-lg text-sm flex items-center gap-3 ${
                  rb.status === 'running' ? 'bg-blue-900/30 border border-blue-700' :
                  rb.status === 'completed' ? 'bg-green-900/30 border border-green-700' :
                  'bg-red-900/30 border border-red-700'
                }`}
              >
                {rb.status === 'running' && <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />}
                {rb.status === 'completed' && <CheckCircle className="w-4 h-4 text-green-400" />}
                {rb.status === 'error' && <XCircle className="w-4 h-4 text-red-400" />}
                <span className="font-mono font-bold text-white">{rb.symbol}</span>
                <span className="text-gray-400">{rb.progress}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Advanced Filters Panel */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
              <SlidersHorizontal className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="text-left">
              <h2 className="text-lg font-semibold text-white">Filtres Avancés & Statistiques</h2>
              <p className="text-sm text-gray-400">
                {filteredBacktests.length} / {backtests.length} backtests
                {filterSymbol || filterVersion !== 'all' || filterDateFrom || filterDateTo || filterMinPnl || filterMaxPnl || filterMinTrades || filterWinOnly || filterLossOnly
                  ? ' (filtré)'
                  : ''}
              </p>
            </div>
          </div>
          {showAdvancedFilters ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {showAdvancedFilters && (
          <div className="border-t border-gray-800 p-4 space-y-6">
            {/* Filter Controls */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {/* Symbol Filter */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Symbol</label>
                <input
                  type="text"
                  value={filterSymbol}
                  onChange={(e) => setFilterSymbol(e.target.value.toUpperCase())}
                  placeholder="Rechercher..."
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Version Filter */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Version</label>
                <select
                  value={filterVersion}
                  onChange={(e) => setFilterVersion(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="all">Toutes</option>
                  <option value="v1">V1 - Legacy</option>
                  <option value="v2">V2 - Optimisé</option>
                  <option value="v3">V3 - Golden Box</option>
                  <option value="v4">V4 - Optimized</option>
                  <option value="v5">V5 - VP Filter</option>
                  <option value="v6">V6 - Advanced</option>
                </select>
              </div>

              {/* Date From */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Date Début</label>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Date To */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Date Fin</label>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Min PnL */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">PnL Min (%)</label>
                <input
                  type="number"
                  value={filterMinPnl}
                  onChange={(e) => setFilterMinPnl(e.target.value)}
                  placeholder="-100"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Max PnL */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">PnL Max (%)</label>
                <input
                  type="number"
                  value={filterMaxPnl}
                  onChange={(e) => setFilterMaxPnl(e.target.value)}
                  placeholder="100"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Second row filters */}
            <div className="flex flex-wrap items-center gap-4">
              {/* Min Trades */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-400">Min Trades:</label>
                <input
                  type="number"
                  value={filterMinTrades}
                  onChange={(e) => setFilterMinTrades(e.target.value)}
                  placeholder="0"
                  className="w-20 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Win Only Toggle */}
              <button
                onClick={() => { setFilterWinOnly(!filterWinOnly); if (!filterWinOnly) setFilterLossOnly(false); }}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
                  filterWinOnly
                    ? 'bg-green-500/20 border-green-500 text-green-400'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-green-700'
                }`}
              >
                <Trophy className="w-4 h-4" />
                Gagnants uniquement
              </button>

              {/* Loss Only Toggle */}
              <button
                onClick={() => { setFilterLossOnly(!filterLossOnly); if (!filterLossOnly) setFilterWinOnly(false); }}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
                  filterLossOnly
                    ? 'bg-red-500/20 border-red-500 text-red-400'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-red-700'
                }`}
              >
                <Skull className="w-4 h-4" />
                Perdants uniquement
              </button>

              {/* Clear Filters */}
              <button
                onClick={() => {
                  setFilterSymbol("")
                  setFilterVersion("all")
                  setFilterDateFrom("")
                  setFilterDateTo("")
                  setFilterMinPnl("")
                  setFilterMaxPnl("")
                  setFilterMinTrades("")
                  setFilterWinOnly(false)
                  setFilterLossOnly(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
                Réinitialiser
              </button>
            </div>

            {/* Statistics Panel */}
            {statistics && (
              <div className="border-t border-gray-800 pt-6 space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-indigo-400" />
                    Statistiques Globales
                  </h3>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-400">
                      <span className="text-white font-medium">{statistics.backtestsWithTrades}</span> backtests avec trades
                    </span>
                    <span className="text-gray-500">|</span>
                    <span className="text-gray-400">
                      <span className="text-white font-medium">{statistics.totalTrades}</span> trades total
                    </span>
                    {statistics.backtestsWithoutTrades > 0 && (
                      <>
                        <span className="text-gray-500">|</span>
                        <span className="text-gray-500">
                          {statistics.backtestsWithoutTrades} sans trades
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Main Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                  {/* Win Rate */}
                  <div className="bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-green-400 mb-2">
                      <Trophy className="w-4 h-4" />
                      <span className="text-xs font-medium">Win Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-green-400">{statistics.winRate.toFixed(1)}%</div>
                    <div className="text-xs text-gray-400 mt-1">{statistics.winningCount}/{statistics.backtestsWithTrades} bt</div>
                  </div>

                  {/* Loss Rate */}
                  <div className="bg-gradient-to-br from-red-500/10 to-red-500/5 border border-red-500/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-red-400 mb-2">
                      <Skull className="w-4 h-4" />
                      <span className="text-xs font-medium">Loss Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-red-400">{statistics.lossRate.toFixed(1)}%</div>
                    <div className="text-xs text-gray-400 mt-1">{statistics.losingCount}/{statistics.backtestsWithTrades} bt</div>
                  </div>

                  {/* Total PnL */}
                  <div className={`bg-gradient-to-br ${statistics.totalPnlC >= 0 ? 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/30' : 'from-rose-500/10 to-rose-500/5 border-rose-500/30'} border rounded-xl p-4`}>
                    <div className="flex items-center gap-2 text-gray-300 mb-2">
                      <Activity className="w-4 h-4" />
                      <span className="text-xs font-medium">PnL Total</span>
                    </div>
                    <div className={`text-2xl font-bold ${statistics.totalPnlC >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {statistics.totalPnlC >= 0 ? '+' : ''}{statistics.totalPnlC.toFixed(1)}%
                    </div>
                  </div>

                  {/* Avg PnL per Backtest */}
                  <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-300 mb-2">
                      <Calculator className="w-4 h-4" />
                      <span className="text-xs font-medium">Moy/Backtest</span>
                    </div>
                    <div className={`text-2xl font-bold ${statistics.avgPnlC >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {statistics.avgPnlC >= 0 ? '+' : ''}{statistics.avgPnlC.toFixed(2)}%
                    </div>
                  </div>

                  {/* Avg PnL per Trade */}
                  <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-300 mb-2">
                      <Target className="w-4 h-4" />
                      <span className="text-xs font-medium">Moy/Trade</span>
                    </div>
                    <div className={`text-2xl font-bold ${statistics.avgPnlPerTrade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {statistics.avgPnlPerTrade >= 0 ? '+' : ''}{statistics.avgPnlPerTrade.toFixed(2)}%
                    </div>
                  </div>

                  {/* Profit Factor */}
                  <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-300 mb-2">
                      <Percent className="w-4 h-4" />
                      <span className="text-xs font-medium">Profit Factor</span>
                    </div>
                    <div className={`text-2xl font-bold ${statistics.profitFactor >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                      {statistics.profitFactor === Infinity ? '∞' : statistics.profitFactor.toFixed(2)}
                    </div>
                  </div>

                  {/* Expectancy */}
                  <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-300 mb-2">
                      <Brain className="w-4 h-4" />
                      <span className="text-xs font-medium">Expectancy</span>
                    </div>
                    <div className={`text-2xl font-bold ${statistics.expectancy >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {statistics.expectancy >= 0 ? '+' : ''}{statistics.expectancy.toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Win/Loss Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Winners Details */}
                  <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4">
                    <h4 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Trades Gagnants
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-xs text-gray-400">Avg Win</div>
                        <div className="text-lg font-bold text-green-400">+{statistics.avgWin.toFixed(2)}%</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">Best Symbol</div>
                        <div className="text-lg font-bold text-green-400">
                          +{statistics.bestSymbol ? statistics.bestSymbol.pnl.toFixed(2) : statistics.bestPnl.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">Symbol</div>
                        <div className="text-sm font-bold text-white">
                          {statistics.bestSymbol?.symbol || statistics.bestBacktest?.symbol || '-'}
                          {statistics.bestSymbol && statistics.bestSymbol.count > 1 && (
                            <span className="text-xs text-gray-500 ml-1">({statistics.bestSymbol.count} bt)</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Losers Details */}
                  <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4">
                    <h4 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                      <TrendingDown className="w-4 h-4" />
                      Trades Perdants
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-xs text-gray-400">Avg Loss</div>
                        <div className="text-lg font-bold text-red-400">{statistics.avgLoss.toFixed(2)}%</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">Worst Symbol</div>
                        <div className="text-lg font-bold text-red-400">
                          {statistics.worstSymbol ? statistics.worstSymbol.pnl.toFixed(2) : statistics.worstPnl.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">Symbol</div>
                        <div className="text-sm font-bold text-white">
                          {statistics.worstSymbol?.symbol || statistics.worstBacktest?.symbol || '-'}
                          {statistics.worstSymbol && statistics.worstSymbol.count > 1 && (
                            <span className="text-xs text-gray-500 ml-1">({statistics.worstSymbol.count} bt)</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* By Version Stats */}
                {Object.keys(statistics.byVersion).length > 0 && (
                  <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4">
                    <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                      <Layers className="w-4 h-4 text-purple-400" />
                      Performance par Version
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      {Object.entries(statistics.byVersion).sort((a, b) => a[0].localeCompare(b[0])).map(([version, data]) => (
                        <div
                          key={version}
                          className={`p-3 rounded-lg border ${
                            version === 'v5' ? 'bg-pink-500/10 border-pink-500/30' :
                            version === 'v4' ? 'bg-amber-500/10 border-amber-500/30' :
                            version === 'v3' ? 'bg-cyan-500/10 border-cyan-500/30' :
                            version === 'v2' ? 'bg-green-500/10 border-green-500/30' :
                            'bg-gray-500/10 border-gray-500/30'
                          }`}
                        >
                          <div className={`text-sm font-bold ${
                            version === 'v5' ? 'text-pink-400' :
                            version === 'v4' ? 'text-amber-400' :
                            version === 'v3' ? 'text-cyan-400' :
                            version === 'v2' ? 'text-green-400' :
                            'text-gray-400'
                          }`}>{version.toUpperCase()}</div>
                          <div className="text-xs text-gray-400 mt-1">
                            {data.withTrades}/{data.count} bt avec trades
                          </div>
                          <div className="text-xs text-gray-400">{data.trades} trades total</div>
                          <div className={`text-sm font-bold mt-1 ${data.winRate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                            WR: {data.winRate.toFixed(1)}%
                          </div>
                          <div className={`text-sm font-bold ${data.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {data.pnl >= 0 ? '+' : ''}{data.pnl.toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top/Bottom Symbols with Pagination */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Top Symbols */}
                  <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Award className="w-4 h-4 text-yellow-400" />
                        Top {statistics.topSymbols.length} Symbols
                      </h4>
                      {statistics.topSymbols.length > SYMBOLS_PER_PAGE && (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setTopSymbolsPage(p => Math.max(0, p - 1))}
                            disabled={topSymbolsPage === 0}
                            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded transition-colors"
                          >
                            ←
                          </button>
                          <span className="text-xs text-gray-400 px-2">
                            {topSymbolsPage + 1}/{Math.ceil(statistics.topSymbols.length / SYMBOLS_PER_PAGE)}
                          </span>
                          <button
                            onClick={() => setTopSymbolsPage(p => Math.min(Math.ceil(statistics.topSymbols.length / SYMBOLS_PER_PAGE) - 1, p + 1))}
                            disabled={topSymbolsPage >= Math.ceil(statistics.topSymbols.length / SYMBOLS_PER_PAGE) - 1}
                            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded transition-colors"
                          >
                            →
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      {statistics.topSymbols
                        .slice(topSymbolsPage * SYMBOLS_PER_PAGE, (topSymbolsPage + 1) * SYMBOLS_PER_PAGE)
                        .map(([symbol, data], idx) => {
                          const globalIdx = topSymbolsPage * SYMBOLS_PER_PAGE + idx
                          return (
                            <div key={symbol} className="flex items-center justify-between p-2 bg-gray-900/50 rounded-lg">
                              <div className="flex items-center gap-2">
                                <span className={`w-6 h-5 flex items-center justify-center rounded text-xs font-bold ${
                                  globalIdx === 0 ? 'bg-yellow-500 text-black' :
                                  globalIdx === 1 ? 'bg-gray-400 text-black' :
                                  globalIdx === 2 ? 'bg-amber-600 text-white' :
                                  'bg-gray-700 text-gray-300'
                                }`}>{globalIdx + 1}</span>
                                <span className="font-mono text-white text-sm">{symbol}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-gray-400">{data.count} bt</span>
                                <span className={`font-bold text-sm ${data.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {data.pnl >= 0 ? '+' : ''}{data.pnl.toFixed(2)}%
                                </span>
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  </div>

                  {/* Bottom Symbols */}
                  <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        Bottom {statistics.bottomSymbols.length} Symbols
                      </h4>
                      {statistics.bottomSymbols.length > SYMBOLS_PER_PAGE && (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setBottomSymbolsPage(p => Math.max(0, p - 1))}
                            disabled={bottomSymbolsPage === 0}
                            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded transition-colors"
                          >
                            ←
                          </button>
                          <span className="text-xs text-gray-400 px-2">
                            {bottomSymbolsPage + 1}/{Math.ceil(statistics.bottomSymbols.length / SYMBOLS_PER_PAGE)}
                          </span>
                          <button
                            onClick={() => setBottomSymbolsPage(p => Math.min(Math.ceil(statistics.bottomSymbols.length / SYMBOLS_PER_PAGE) - 1, p + 1))}
                            disabled={bottomSymbolsPage >= Math.ceil(statistics.bottomSymbols.length / SYMBOLS_PER_PAGE) - 1}
                            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded transition-colors"
                          >
                            →
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      {statistics.bottomSymbols
                        .slice(bottomSymbolsPage * SYMBOLS_PER_PAGE, (bottomSymbolsPage + 1) * SYMBOLS_PER_PAGE)
                        .map(([symbol, data], idx) => {
                          const globalIdx = bottomSymbolsPage * SYMBOLS_PER_PAGE + idx
                          return (
                            <div key={symbol} className="flex items-center justify-between p-2 bg-gray-900/50 rounded-lg">
                              <div className="flex items-center gap-2">
                                <span className="w-6 h-5 flex items-center justify-center rounded text-xs font-bold bg-red-500/30 text-red-400">
                                  {globalIdx + 1}
                                </span>
                                <span className="font-mono text-white text-sm">{symbol}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-gray-400">{data.count} bt</span>
                                <span className={`font-bold text-sm ${data.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {data.pnl >= 0 ? '+' : ''}{data.pnl.toFixed(2)}%
                                </span>
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Backtests List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            Backtest History
            <span className={`px-2 py-0.5 text-xs rounded-full border ${
              strategyVersion === 'v5' ? 'bg-pink-500/20 text-pink-400 border-pink-500/30' :
              strategyVersion === 'v4' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
              strategyVersion === 'v3' ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' :
              strategyVersion === 'v2' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
              'bg-gray-500/20 text-gray-400 border-gray-500/30'
            }`}>
              {strategyVersion.toUpperCase()}
            </span>
            <span className="text-sm font-normal text-gray-400">
              ({filteredBacktests.length} backtests)
            </span>
          </h2>
          {(filterSymbol || filterDateFrom || filterDateTo || filterMinPnl || filterMaxPnl || filterMinTrades || filterWinOnly || filterLossOnly) && (
            <span className="px-2 py-1 text-xs bg-indigo-500/20 text-indigo-400 rounded-lg">
              + Filtres
            </span>
          )}
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading...
          </div>
        ) : filteredBacktests.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            {backtests.length === 0
              ? "No backtests yet. Run your first backtest above."
              : "Aucun backtest ne correspond aux filtres sélectionnés."}
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {filteredBacktests.map((bt) => (
              <div key={bt.id} className="bg-gray-900/50">
                {/* Main row */}
                <div
                  className="p-4 hover:bg-gray-800/50 cursor-pointer transition-colors"
                  onClick={() => toggleExpand(bt.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                        <Target className="w-5 h-5 text-purple-400" />
                      </div>
                      <div>
                        <div className="font-semibold text-white flex items-center gap-2">
                          {bt.symbol}
                          {bt.strategy_version === 'v6' ? (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                              V6
                            </span>
                          ) : bt.strategy_version === 'v5' ? (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-pink-500/20 text-pink-400 border border-pink-500/30">
                              V5
                            </span>
                          ) : bt.strategy_version === 'v4' ? (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                              V4
                            </span>
                          ) : bt.strategy_version === 'v3' ? (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                              V3
                            </span>
                          ) : bt.strategy_version === 'v2' ? (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                              V2
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-gray-500/20 text-gray-400 border border-gray-500/30">
                              V1
                            </span>
                          )}
                          {(bt.v2_rejected_count ?? 0) > 0 && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-orange-500/20 text-orange-400">
                              -{bt.v2_rejected_count} filtered
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-400">
                          {formatDate(bt.start_date)} - {formatDate(bt.end_date)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-center">
                        <div className="text-sm text-gray-400">Alerts</div>
                        <div className="text-white font-medium">{bt.total_alerts}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-gray-400">Trades</div>
                        <div className="text-white font-medium">{bt.total_trades}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-gray-400">P&L C</div>
                        <div className={`font-medium flex items-center gap-1 ${getPnlColor(bt.pnl_strategy_c)}`}>
                          {bt.pnl_strategy_c > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                          {bt.pnl_strategy_c?.toFixed(2)}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-gray-400">P&L D</div>
                        <div className={`font-medium flex items-center gap-1 ${getPnlColor(bt.pnl_strategy_d)}`}>
                          {bt.pnl_strategy_d > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                          {bt.pnl_strategy_d?.toFixed(2)}%
                        </div>
                      </div>

                      <button
                        onClick={(e) => { e.stopPropagation(); deleteBacktest(bt.id); }}
                        className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>

                      {expandedId === bt.id ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded details */}
                {expandedId === bt.id && (
                  <div className="border-t border-gray-800 bg-gray-950/50 p-4">
                    {loadingDetails ? (
                      <div className="text-center py-4 text-gray-400">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                        Loading details...
                      </div>
                    ) : (
                      <div className="space-y-6">
                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">STC Validated</div>
                            <div className="text-lg font-medium text-white">{bt.stc_validated}</div>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">15m Alone Rejected</div>
                            <div className="text-lg font-medium text-white">{bt.rejected_15m_alone}</div>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">TL Break</div>
                            <div className="text-lg font-medium text-white">{bt.with_tl_break}</div>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">Delay OK</div>
                            <div className="text-lg font-medium text-green-400">{bt.delay_respected}</div>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">Valid Entries</div>
                            <div className="text-lg font-medium text-green-400">{bt.valid_entries}</div>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs text-gray-400">Expired/Waiting</div>
                            <div className="text-lg font-medium text-gray-400">{bt.expired}/{bt.waiting}</div>
                          </div>
                        </div>

                        {/* Trades Table */}
                        {trades.length > 0 && (() => {
                          const groupedTrades = groupTradesByEntry(trades)
                          return (
                          <div>
                            <h3 className="text-sm font-semibold text-white mb-2">
                              Trades ({groupedTrades.length} entries, {trades.length} alerts)
                            </h3>
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="text-gray-400 border-b border-gray-800">
                                    <th className="text-left py-2 px-2">Alert Time</th>
                                    <th className="text-left py-2 px-2">TF</th>
                                    <th className="text-right py-2 px-2">Alert Price</th>
                                    <th className="text-right py-2 px-2">Entry</th>
                                    <th className="text-right py-2 px-2">SL</th>
                                    <th className="text-right py-2 px-2">TP1/TP2</th>
                                    <th className="text-right py-2 px-2">P&L C</th>
                                    <th className="text-right py-2 px-2">P&L D</th>
                                    <th className="text-left py-2 px-2">Exit C</th>
                                    <th className="text-center py-2 px-2">Post-SL</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {groupedTrades.map((trade) => (
                                    <tr
                                      key={trade.ids.join('-')}
                                      className={`border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer ${trade.is_combined ? 'bg-purple-900/10' : ''}`}
                                      onClick={() => setSelectedTrade(trade)}
                                    >
                                      <td className="py-2 px-2 text-gray-300">
                                        {trade.is_combined ? (
                                          <div className="flex flex-col gap-0.5">
                                            {trade.alert_datetimes.map((dt, idx) => (
                                              <span key={idx} className="text-xs">{formatDate(dt)}</span>
                                            ))}
                                          </div>
                                        ) : (
                                          formatDate(trade.alert_datetimes[0])
                                        )}
                                      </td>
                                      <td className="py-2 px-2">
                                        <div className="flex flex-wrap gap-1">
                                          {trade.timeframes.map((tf, idx) => (
                                            <span key={idx} className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs">
                                              {tf}
                                            </span>
                                          ))}
                                          {trade.is_combined && (
                                            <span className="px-1.5 py-0.5 bg-yellow-500/30 text-yellow-400 rounded text-xs font-semibold">
                                              COMBO
                                            </span>
                                          )}
                                        </div>
                                      </td>
                                      <td className="py-2 px-2 text-right text-gray-300">
                                        {trade.is_combined ? (
                                          <div className="flex flex-col gap-0.5">
                                            {trade.alert_prices.map((price, idx) => (
                                              <span key={idx} className="text-xs font-mono">{price?.toFixed(6)}</span>
                                            ))}
                                          </div>
                                        ) : (
                                          trade.alert_prices[0]?.toFixed(6)
                                        )}
                                      </td>
                                      <td className="py-2 px-2 text-right text-blue-400">{trade.entry_price?.toFixed(6)}</td>
                                      <td className="py-2 px-2 text-right text-red-400">{trade.sl_price?.toFixed(6)}</td>
                                      <td className="py-2 px-2 text-right text-green-400">
                                        {trade.tp1_price?.toFixed(6)} / {trade.tp2_price?.toFixed(6)}
                                      </td>
                                      <td className={`py-2 px-2 text-right font-medium ${getPnlColor(trade.pnl_c)}`}>
                                        {trade.pnl_c?.toFixed(2)}%
                                      </td>
                                      <td className={`py-2 px-2 text-right font-medium ${getPnlColor(trade.pnl_d)}`}>
                                        {trade.pnl_d?.toFixed(2)}%
                                      </td>
                                      <td className="py-2 px-2 text-gray-400 text-xs max-w-[200px] truncate">
                                        {trade.exit_reason_c}
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        {trade.pnl_c < 0 && trade.sl_then_recovered && (
                                          <span
                                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                              trade.post_sl_would_have_won
                                                ? 'bg-red-500/30 text-red-400'
                                                : 'bg-orange-500/30 text-orange-400'
                                            }`}
                                            title={`Prix remonté à ${trade.post_sl_max_price?.toFixed(4)} (+${trade.post_sl_max_gain_pct?.toFixed(1)}%)`}
                                          >
                                            {trade.post_sl_would_have_won ? 'SL EARLY!' : 'RÉCUP'}
                                          </span>
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                          )
                        })()}

                        {/* Alerts Table */}
                        {alerts.length > 0 && (
                          <div>
                            <h3 className="text-sm font-semibold text-white mb-2">All Alerts ({alerts.length}) - Click for details</h3>
                            <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                              <table className="w-full text-sm">
                                <thead className="sticky top-0 bg-gray-950">
                                  <tr className="text-gray-400 border-b border-gray-800">
                                    <th className="text-left py-2 px-2">Time</th>
                                    <th className="text-left py-2 px-2">TF</th>
                                    <th className="text-right py-2 px-2">Price</th>
                                    <th className="text-center py-2 px-2">Score</th>
                                    <th className="text-center py-2 px-2">Conditions</th>
                                    <th className="text-center py-2 px-2">STC</th>
                                    <th className="text-center py-2 px-2">TL</th>
                                    <th className="text-center py-2 px-2">Break</th>
                                    <th className="text-center py-2 px-2">Entry</th>
                                    <th className="text-center py-2 px-2">Status</th>
                                    <th className="text-center py-2 px-2">Details</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {alerts.map((alert) => (
                                    <tr
                                      key={alert.id}
                                      className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                                      onClick={() => setSelectedAlert(alert)}
                                    >
                                      <td className="py-2 px-2 text-gray-300">{formatDate(alert.alert_datetime)}</td>
                                      <td className="py-2 px-2">
                                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                                          {alert.timeframe}
                                        </span>
                                      </td>
                                      <td className="py-2 px-2 text-right text-gray-300 font-mono">{alert.price_close?.toFixed(6)}</td>
                                      <td className="py-2 px-2 text-center">
                                        <span className={`font-medium ${alert.score >= 8 ? 'text-green-400' : alert.score >= 7 ? 'text-yellow-400' : 'text-gray-400'}`}>
                                          {alert.score}/10
                                        </span>
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        <div className="flex justify-center gap-0.5">
                                          {Object.entries(alert.conditions || {}).slice(0, 10).map(([key, valid], i) => (
                                            <div
                                              key={i}
                                              className={`w-2 h-2 rounded-full ${valid ? 'bg-green-400' : 'bg-red-400'}`}
                                              title={`${key}: ${valid ? 'Yes' : 'No'}`}
                                            />
                                          ))}
                                        </div>
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        {alert.stc_validated ? (
                                          <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                                        ) : (
                                          <XCircle className="w-4 h-4 text-red-400 mx-auto" />
                                        )}
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        {alert.has_trendline ? (
                                          <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                                        ) : (
                                          <XCircle className="w-4 h-4 text-red-400 mx-auto" />
                                        )}
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        {alert.has_tl_break ? (
                                          <span className={`text-xs ${alert.delay_exceeded ? 'text-yellow-400' : 'text-green-400'}`}>
                                            {alert.tl_break_delay_hours?.toFixed(0)}h
                                          </span>
                                        ) : (
                                          <XCircle className="w-4 h-4 text-gray-500 mx-auto" />
                                        )}
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        {alert.has_entry ? (
                                          <span className="text-green-400 text-xs font-mono">{alert.entry_price?.toFixed(4)}</span>
                                        ) : (
                                          <XCircle className="w-4 h-4 text-gray-500 mx-auto" />
                                        )}
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        <div className="flex items-center justify-center gap-1">
                                          {getStatusIcon(alert.status)}
                                          <span className={`text-xs ${
                                            alert.status === 'VALID' ? 'text-green-400' :
                                            alert.status === 'WAITING' ? 'text-yellow-400' :
                                            'text-gray-400'
                                          }`}>
                                            {alert.status?.replace('REJECTED_', '')}
                                          </span>
                                        </div>
                                      </td>
                                      <td className="py-2 px-2 text-center">
                                        <button className="p-1 hover:bg-gray-700 rounded">
                                          <Info className="w-4 h-4 text-purple-400" />
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
