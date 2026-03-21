# PineScript - 1INCHUSDT Trade Analysis (Clean Version)

Copiez le code ci-dessous dans TradingView:

```pinescript
//@version=5
indicator("MEGA BUY - 1INCHUSDT Clean", overlay=true, max_lines_count=500, max_labels_count=500, max_boxes_count=100)

// ══════════════════════════════════════════════════════════════════════════════
// MEGA BUY AI - Clean Trade Analysis
// Symbol: 1INCHUSDT | Alert: 2026-02-25 01:00 UTC
// Entry: 0.090681 | SL: 0.086922 | Max: 0.0988 (+8.9%)
// Result: -4.15% (SL Hit) | Issue: BE +10% not reached (only +8.9%)
// ══════════════════════════════════════════════════════════════════════════════

// ═══════════════════ INPUTS ═══════════════════
grp1 = "Display Options"
i_showTL      = input.bool(true, "Show Trendline", group=grp1)
i_showOB      = input.bool(true, "Show Order Blocks", group=grp1)
i_showVP      = input.bool(true, "Show Volume Profile", group=grp1)
i_showEntry   = input.bool(true, "Show Entry/SL/TP", group=grp1)
i_showTable   = input.bool(true, "Show Info Table", group=grp1)
i_smallLabels = input.bool(true, "Use Small Labels", group=grp1)

// ═══════════════════ TRADE DATA ═══════════════════
// Timestamps (milliseconds)
tl_p1_time = 1768122000000
tl_p2_time = 1771664400000
tl_break_time = 1771984800000
ob_1h_time = 1771988400000
ob_4h_time = 1773000000000
entry_time = 1772020800000
alert_time = 1771981200000
sl_hit_time = 1772258400000

// Prices
tl_p1_price = 0.1568
tl_p2_price = 0.0954
tl_break_price = 0.09
entry_price = 0.090681
sl_price = 0.086922
tp1_price = 0.104283
be_price = 0.099749
max_reached = 0.0988

// Order Blocks
ob_1h_high = 0.0901
ob_1h_low = 0.0892
ob_4h_high = 0.0916
ob_4h_low = 0.0891

// Volume Profile
vp_poc_1h = 0.089649
vp_vah_1h = 0.090939
vp_val_1h = 0.088961

// Label size based on input
lblSize = i_smallLabels ? size.tiny : size.small

// ═══════════════════ MEGA BUY SIGNAL MARKER ═══════════════════
// Small triangle at alert time - no text clutter
if barstate.islast
    label.new(alert_time, low * 0.996, "", xloc.bar_time, yloc.price, color.lime, label.style_triangleup, color.lime, size.small)

// ═══════════════════ TRENDLINE ═══════════════════
if i_showTL and barstate.islast
    line.new(tl_p1_time, tl_p1_price, tl_p2_time, tl_p2_price, xloc.bar_time, extend.right, color.orange, line.style_solid, 2)
    label.new(tl_p1_time, tl_p1_price, "P1", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)
    label.new(tl_p2_time, tl_p2_price, "P2", xloc.bar_time, yloc.price, color.orange, label.style_circle, color.white, size.tiny)
    label.new(tl_break_time, tl_break_price, "BRK", xloc.bar_time, yloc.price, color.green, label.style_label_up, color.white, size.tiny)

// ═══════════════════ ORDER BLOCKS ═══════════════════
if i_showOB and barstate.islast
    // 1H OB - starts at OB time, extends right (NOT left)
    box.new(ob_1h_time, ob_1h_high, time + 86400000*3, ob_1h_low, xloc.bar_time, color.new(color.green, 40), 1, line.style_solid, extend.none, color.new(color.green, 85))
    label.new(ob_1h_time, (ob_1h_high + ob_1h_low) / 2, "1H", xloc.bar_time, yloc.price, color.new(color.green, 50), label.style_label_right, color.white, size.tiny)

    // 4H OB
    box.new(ob_4h_time, ob_4h_high, time + 86400000*3, ob_4h_low, xloc.bar_time, color.new(color.purple, 40), 2, line.style_solid, extend.none, color.new(color.purple, 85))
    label.new(ob_4h_time, (ob_4h_high + ob_4h_low) / 2, "4H", xloc.bar_time, yloc.price, color.new(color.purple, 50), label.style_label_right, color.white, size.tiny)

// ═══════════════════ VOLUME PROFILE ═══════════════════
// VP starts at alert time - NOT extended to the left infinitely
if i_showVP and barstate.islast
    vp_start = alert_time - 86400000 * 7
    vp_end = time

    // Value Area Box - starts 7 days before alert
    box.new(vp_start, vp_vah_1h, vp_end, vp_val_1h, xloc.bar_time, color.new(color.fuchsia, 60), 1, line.style_solid, extend.none, color.new(color.fuchsia, 90))

    // POC Line - from VP start to current
    line.new(vp_start, vp_poc_1h, vp_end, vp_poc_1h, xloc.bar_time, extend.none, color.fuchsia, line.style_solid, 2)
    label.new(vp_start, vp_poc_1h, "POC", xloc.bar_time, yloc.price, color.fuchsia, label.style_label_right, color.white, size.tiny)

    // VAH Line
    line.new(vp_start, vp_vah_1h, vp_end, vp_vah_1h, xloc.bar_time, extend.none, color.new(color.red, 50), line.style_dashed, 1)
    label.new(vp_start, vp_vah_1h, "VAH", xloc.bar_time, yloc.price, color.new(color.red, 50), label.style_label_right, color.white, size.tiny)

    // VAL Line
    line.new(vp_start, vp_val_1h, vp_end, vp_val_1h, xloc.bar_time, extend.none, color.new(color.green, 50), line.style_dashed, 1)
    label.new(vp_start, vp_val_1h, "VAL", xloc.bar_time, yloc.price, color.new(color.green, 50), label.style_label_right, color.white, size.tiny)

// ═══════════════════ ENTRY MARKER ═══════════════════
// Clean entry marker - vertical line + horizontal line + small arrow
if i_showEntry and barstate.islast
    // Vertical line at entry (dotted, subtle)
    line.new(entry_time, sl_price * 0.98, entry_time, tp1_price, xloc.bar_time, extend.none, color.new(color.blue, 50), line.style_dotted, 1)

    // Entry horizontal line
    line.new(entry_time, entry_price, time + 86400000*5, entry_price, xloc.bar_time, extend.none, color.blue, line.style_solid, 1)
    label.new(time + 86400000*5, entry_price, "E", xloc.bar_time, yloc.price, color.blue, label.style_label_left, color.white, size.tiny)

    // SL line (red dashed)
    line.new(entry_time, sl_price, time + 86400000*5, sl_price, xloc.bar_time, extend.none, color.red, line.style_dashed, 1)
    label.new(time + 86400000*5, sl_price, "SL", xloc.bar_time, yloc.price, color.red, label.style_label_left, color.white, size.tiny)

    // TP1 line (green dashed)
    line.new(entry_time, tp1_price, time + 86400000*5, tp1_price, xloc.bar_time, extend.none, color.green, line.style_dashed, 1)
    label.new(time + 86400000*5, tp1_price, "TP1", xloc.bar_time, yloc.price, color.green, label.style_label_left, color.white, size.tiny)

    // BE +10% line (orange dotted) - the level that was NOT reached
    line.new(entry_time, be_price, time + 86400000*5, be_price, xloc.bar_time, extend.none, color.orange, line.style_dotted, 1)
    label.new(time + 86400000*5, be_price, "BE", xloc.bar_time, yloc.price, color.orange, label.style_label_left, color.white, size.tiny)

    // MAX reached +8.9% (aqua solid) - shows how close we got
    line.new(entry_time, max_reached, time + 86400000*5, max_reached, xloc.bar_time, extend.none, color.aqua, line.style_solid, 2)
    label.new(time + 86400000*5, max_reached, "MAX", xloc.bar_time, yloc.price, color.aqua, label.style_label_left, color.black, size.tiny)

    // SL Hit marker
    label.new(sl_hit_time, sl_price * 1.01, "X", xloc.bar_time, yloc.price, color.red, label.style_label_down, color.white, size.small)

// ═══════════════════ COMPACT INFO TABLE ═══════════════════
if i_showTable
    var table tbl = table.new(position.top_right, 2, 8, bgcolor=color.new(color.black, 85), border_width=1)

    if barstate.islast
        table.cell(tbl, 0, 0, "1INCHUSDT", text_color=color.white, text_size=size.tiny)
        table.cell(tbl, 1, 0, "25/02/26", text_color=color.gray, text_size=size.tiny)

        table.cell(tbl, 0, 1, "Entry", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 1, "0.0907", text_color=color.blue, text_size=size.tiny)

        table.cell(tbl, 0, 2, "SL", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 2, "0.0869", text_color=color.red, text_size=size.tiny)

        table.cell(tbl, 0, 3, "Max", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 3, "+8.9%", text_color=color.aqua, text_size=size.tiny)

        table.cell(tbl, 0, 4, "BE Req", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 4, "+10%", text_color=color.orange, text_size=size.tiny)

        table.cell(tbl, 0, 5, "Gap", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 5, "-1.1%", text_color=color.orange, text_size=size.tiny)

        table.cell(tbl, 0, 6, "VP", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 6, "IN_VA", text_color=color.fuchsia, text_size=size.tiny)

        table.cell(tbl, 0, 7, "Result", text_color=color.gray, text_size=size.tiny)
        table.cell(tbl, 1, 7, "-4.15%", text_color=color.red, text_size=size.tiny)
```

---

## Changements par rapport à l'ancien script:

1. **MEGA BUY Signal**: Petit triangle vert sans texte (ne cache pas les bougies)

2. **Volume Profile**:
   - Commence 7 jours AVANT l'alerte (pas étendu infiniment à gauche)
   - Se termine au temps actuel
   - Labels "POC", "VAH", "VAL" en `size.tiny`

3. **Entry Marker**:
   - Ligne verticale pointillée (subtile)
   - Lignes horizontales fines
   - Labels minimalistes: "E", "SL", "TP1", "BE", "MAX" (tiny)

4. **Order Blocks**:
   - Commencent à leur temps de création (pas étendus à gauche)
   - Labels "1H" et "4H" seulement (tiny)

5. **Table Info**:
   - Compacte en haut à droite
   - Toutes les infos essentielles en format tiny

6. **Option "Use Small Labels"**:
   - Toggle pour choisir entre tiny et small

---

## Utilisation:

1. Ouvrez TradingView sur **1INCHUSDT** en **1H**
2. Allez sur la date **25 février 2026**
3. Ajoutez l'indicateur
4. Utilisez les checkboxes pour activer/désactiver les éléments
