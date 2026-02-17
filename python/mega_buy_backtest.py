"""
📊 MEGA BUY Backtester v3 — Multi-TF + 4H Grouping
Teste les performances du signal MEGA BUY sur l'historique d'une paire
Multi-TF : détecte les signaux sur 15m/30m/1h/4h groupés par bougie 4H
Score /10 — EC + CHoCH + Candle Pump Filter

Auteur: ASSYIN-2026
"""

import requests
import numpy as np
import pandas as pd
import time
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════
# ⚙️ TELEGRAM
# ═══════════════════════════════════════════════════════
TELEGRAM_TOKEN = "8577547027:AAEtfLHY0RlGISvN_RpwoLMtIVmrGVV74mo"
TELEGRAM_CHAT_ID = "308638133"

# ═══════════════════════════════════════════════════════
# ⚙️ CONFIGURATION DU BACKTEST
# ═══════════════════════════════════════════════════════
SYMBOL = "BTCUSDT"
DATE_START = "2025-01-01"
DATE_END   = "2026-02-15"
TIMEFRAMES = ["15m", "30m", "1h", "4h"]

TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT   = 2.5
MAX_HOLD_BARS   = 48     # Bougies 4H (0 = désactivé)

INITIAL_CAPITAL = 1000.0
POSITION_SIZE_PCT = 10.0

# ═══════════════════════════════════════════════════════
# ⚙️ PARAMÈTRES INDICATEURS (identiques PineScript v7)
# ═══════════════════════════════════════════════════════
RSI_LENGTH = 14; RSI_MIN_MOVE_BUY = 12.0
DMI_LENGTH = 14; DMI_ADX_SMOOTH = 14; DMI_MIN_MOVE_PLUS = 10.0
AST_FACTOR = 3.0; AST_PERIOD = 10
ST_FACTOR = 3.0; ST_PERIOD = 10
PP_PIVOT_PERIOD = 2; PP_ATR_FACTOR = 3.0; PP_ATR_PERIOD = 10
AV_ATR_LENGTH = 14; AV_ATR_SMOOTH = 10; AV_ATR_THRESHOLD = 1.2
AV_VOL_LENGTH = 20; AV_VOL_THRESHOLD = 1.5; AV_MIN_MOVE = 250.0
LB_SPIKE_THRESH = 6.0
EC_RSI_PERIOD = 50; EC_SLOW_MA_PERIOD = 50
EC_MIN_MOVE_RSI = 3.0; EC_MIN_MOVE_SLOW_MA = 1.5
EC_PIVOT_LB = 5; EC_BULL_DIV_MEMORY = 10
CHOCH_PIVOT_LEFT = 10; CHOCH_PIVOT_RIGHT = 5; CHOCH_BREAK_WINDOW = 6
COMBO_WINDOW = 3; COMBO_THRESHOLD_PCT = 50; MAX_CANDLE_MOVE_PCT = 15.0

# ═══════════════════════════════════════════════════════
# 📡 BINANCE API
# ═══════════════════════════════════════════════════════
BINANCE_BASE = "https://api.binance.com"
TF_TO_MS = {
    "1m": 60000, "5m": 300000, "15m": 900000, "30m": 1800000,
    "1h": 3600000, "4h": 14400000, "1d": 86400000
}

def date_to_ms(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

def get_full_history(symbol, interval, start_date, end_date):
    start_ms = date_to_ms(start_date)
    end_ms = date_to_ms(end_date)
    warmup_ms = TF_TO_MS.get(interval, 1800000) * 200
    all_klines = []
    cur = start_ms - warmup_ms
    print(f"📥 {symbol} {interval} : {start_date} → {end_date}")
    while cur < end_ms:
        try:
            resp = requests.get(f"{BINANCE_BASE}/api/v3/klines",
                                params={"symbol": symbol, "interval": interval,
                                        "startTime": cur, "endTime": end_ms, "limit": 1000},
                                timeout=30)
            data = resp.json()
        except Exception as e:
            print(f"   ⚠️ {e}"); time.sleep(1); continue
        if not isinstance(data, list) or not data: break
        all_klines.extend(data)
        cur = data[-1][6] + 1
        print(f"   📊 {len(all_klines)} bougies...", end="\r")
        time.sleep(0.12)
    print(f"   ✅ {len(all_klines)} bougies          ")
    if not all_klines: return None
    df = pd.DataFrame(all_klines, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"])
    for c in ["open","high","low","close","volume"]: df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    return df.drop_duplicates(subset="open_time").reset_index(drop=True)

# ═══════════════════════════════════════════════════════
# 📡 TELEGRAM
# ═══════════════════════════════════════════════════════
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                                  "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=10)
    except Exception as e:
        print(f"  ⚠️ Telegram: {e}")

# ═══════════════════════════════════════════════════════
# 📊 FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════
def rma(s, l):
    a = 1.0/l; r = np.zeros(len(s)); r[0] = s[0]
    for i in range(1,len(s)): r[i] = a*s[i]+(1-a)*r[i-1]
    return r

def ema(s, l):
    a = 2.0/(l+1); r = np.zeros(len(s)); r[0] = s[0]
    for i in range(1,len(s)): r[i] = a*s[i]+(1-a)*r[i-1]
    return r

def sma(s, l):
    r = np.full(len(s), np.nan)
    for i in range(l-1, len(s)): r[i] = np.mean(s[i-l+1:i+1])
    return r

def true_range(h, l, c):
    tr = np.zeros(len(h)); tr[0] = h[0]-l[0]
    for i in range(1,len(h)): tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    return tr

# ═══════════════════════════════════════════════════════
# 📊 INDICATEURS
# ═══════════════════════════════════════════════════════
def calc_rsi(close, length=14):
    delta = np.diff(close, prepend=close[0])
    g = np.maximum(delta,0); lo = -np.minimum(delta,0)
    ag = rma(g,length); al = rma(lo,length)
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(al==0,100,ag/al)
        return np.where(al==0,100,100-(100/(1+rs)))

def calc_dmi(high, low, close, length=14, adx_smooth=14):
    n = len(high); pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1,n):
        u = high[i]-high[i-1]; d = low[i-1]-low[i]
        pdm[i] = u if (u>d and u>0) else 0
        mdm[i] = d if (d>u and d>0) else 0
    tr = true_range(high,low,close); atr = rma(tr,length)
    asf = np.where(atr==0,1,atr)
    pdi = 100*rma(pdm,length)/asf; mdi = 100*rma(mdm,length)/asf
    ds = pdi+mdi; dx = 100*np.abs(pdi-mdi)/np.where(ds==0,1,ds)
    return pdi, mdi, rma(dx,adx_smooth)

def calc_supertrend(high, low, close, factor=3.0, period=10):
    n = len(high); tr = true_range(high,low,close); atr = rma(tr,period)
    hl2 = (high+low)/2; up = hl2+factor*atr; lo = hl2-factor*atr
    d = np.ones(n); fu = np.copy(up); fl = np.copy(lo)
    for i in range(1,n):
        if close[i-1]>fu[i-1]: d[i]=-1
        elif close[i-1]<fl[i-1]: d[i]=1
        else: d[i]=d[i-1]
        if d[i]==-1: fl[i]=max(lo[i],fl[i-1]) if close[i-1]>fl[i-1] else lo[i]
        else: fu[i]=min(up[i],fu[i-1]) if close[i-1]<fu[i-1] else up[i]
    return d

def calc_assyin_st(high, low, close, factor=3.0, period=10):
    n = len(high); tr = true_range(high,low,close); atr = rma(tr,period)
    hl2 = (high+low)/2; ur = hl2+factor*atr; lr = hl2-factor*atr
    ub = np.copy(ur); lb = np.copy(lr); ad = np.ones(n)
    for i in range(1,n):
        lb[i] = max(lr[i],lb[i-1]) if close[i-1]>lb[i-1] else lr[i]
        ub[i] = min(ur[i],ub[i-1]) if close[i-1]<ub[i-1] else ur[i]
        if ad[i-1]==-1: ad[i]=1 if close[i]<lb[i] else -1
        else: ad[i]=-1 if close[i]>ub[i] else 1
    return ad

def calc_pp_st(high, low, close, prd=2, factor=3.0, atr_period=10):
    n = len(high); center = np.full(n,np.nan); trend = np.ones(n,dtype=int)
    tup = np.zeros(n); tdn = np.zeros(n)
    tr = true_range(high,low,close); atr = rma(tr,atr_period); lpp = np.nan
    for i in range(prd, n-prd):
        iph = all(high[i]>high[i-j] and high[i]>high[i+j] for j in range(1,prd+1) if i+j<n and i-j>=0)
        ipl = all(low[i]<low[i-j] and low[i]<low[i+j] for j in range(1,prd+1) if i+j<n and i-j>=0)
        if iph: lpp=high[i]
        if ipl: lpp=low[i]
        if not np.isnan(lpp):
            center[i] = lpp if np.isnan(center[i-1]) else (center[i-1]*2+lpp)/3
    for i in range(1,n):
        if np.isnan(center[i]) and not np.isnan(center[i-1]): center[i]=center[i-1]
    for i in range(1,n):
        if np.isnan(center[i]): continue
        uv=center[i]-factor*atr[i]; dv=center[i]+factor*atr[i]
        tup[i]=max(uv,tup[i-1]) if close[i-1]>tup[i-1] else uv
        tdn[i]=min(dv,tdn[i-1]) if close[i-1]<tdn[i-1] else dv
        if close[i]>tdn[i-1]: trend[i]=1
        elif close[i]<tup[i-1]: trend[i]=-1
        else: trend[i]=trend[i-1]
    return trend

def calc_atr_vol(high, low, close, volume):
    n = len(high); tr = true_range(high,low,close)
    ar = rma(tr,AV_ATR_LENGTH); asm = ema(ar,AV_ATR_SMOOTH)
    asl = np.zeros(n)
    for i in range(1,n):
        if asm[i-1]!=0: asl[i]=(asm[i]-asm[i-1])/asm[i-1]*100
    areg = np.zeros(n,dtype=int)
    for i in range(n):
        if asl[i]>AV_ATR_THRESHOLD: areg[i]=1
        elif asl[i]<-AV_ATR_THRESHOLD: areg[i]=-1
    vm = sma(volume,AV_VOL_LENGTH); vms = np.where(np.isnan(vm)|(vm==0),1,vm)
    vr = volume/vms; vc = np.zeros(n)
    for i in range(1,n): vc[i]=(volume[i]-volume[i-1])/vms[i]*100
    vreg = np.zeros(n,dtype=int)
    for i in range(n):
        if vr[i]>AV_VOL_THRESHOLD: vreg[i]=1
        elif vr[i]<0.8: vreg[i]=-1
    reg = np.zeros(n,dtype=int)
    for i in range(n):
        if areg[i]==1 and vreg[i]==1: reg[i]=1
        elif areg[i]==-1 and vreg[i]==-1: reg[i]=-1
    return reg, np.abs(vc), vc

def calc_lazybar(high, low, close):
    n = len(high); ht = np.zeros(n)
    for i in range(4,n):
        m = sum(high[i-j]+low[i-j] for j in range(5))/10
        s = sum(high[i-j]-low[i-j] for j in range(5))/5*0.2
        if s!=0: ht[i]=(close[i]-m)/s
    return ht

def calc_ec(close, high, low):
    n = len(close); er = calc_rsi(close,EC_RSI_PERIOD); es = sma(er,EC_SLOW_MA_PERIOD)
    lb = EC_PIVOT_LB; bd = np.zeros(n,dtype=bool); pls = []
    for i in range(lb, n-lb):
        ip = True
        for j in range(1,lb+1):
            if er[i]>=er[i-j] or (i+j<n and er[i]>=er[i+j]): ip=False; break
        if ip: pls.append(i)
    for k in range(1,len(pls)):
        c,p = pls[k],pls[k-1]
        if low[c]<low[p] and er[c]>er[p]: bd[min(c+lb,n-1)]=True
    return er, es, bd

def calc_choch(high, close):
    n = len(high); L=CHOCH_PIVOT_LEFT; R=CHOCH_PIVOT_RIGHT
    lsh = np.nan; lbb = -9999; ca = np.zeros(n,dtype=bool)
    for i in range(L+R, n):
        pb = i-R
        if pb>=L:
            ip = True
            for j in range(1,L+1):
                if pb-j<0 or high[pb]<=high[pb-j]: ip=False; break
            if ip:
                for j in range(1,R+1):
                    if pb+j>=n or high[pb]<=high[pb+j]: ip=False; break
            if ip: lsh=high[pb]
        if not np.isnan(lsh) and close[i]>lsh and close[i-1]<=lsh: lbb=i
        if (i-lbb)<=CHOCH_BREAK_WINDOW: ca[i]=True
    return ca

# ═══════════════════════════════════════════════════════
# 🎯 DETECTION MEGA BUY — Score /10
# ═══════════════════════════════════════════════════════
def compute_all_signals(df, tf_label=""):
    h=df["high"].values; l=df["low"].values; c=df["close"].values
    o=df["open"].values; v=df["volume"].values; n=len(c)
    if n<100: return []
    print(f"  🔧 {tf_label} Calcul indicateurs ({n} bars)...")
    rsi=calc_rsi(c,RSI_LENGTH); pdi,_,_=calc_dmi(h,l,c,DMI_LENGTH,DMI_ADX_SMOOTH)
    std=calc_supertrend(h,l,c,ST_FACTOR,ST_PERIOD)
    asd=calc_assyin_st(h,l,c,AST_FACTOR,AST_PERIOD)
    ppt=calc_pp_st(h,l,c,PP_PIVOT_PERIOD,PP_ATR_FACTOR,PP_ATR_PERIOD)
    reg,vm,vc=calc_atr_vol(h,l,c,v); ht=calc_lazybar(h,l,c)
    er,es,ebd=calc_ec(c,h,l); ca=calc_choch(h,c)
    w=COMBO_WINDOW; win=w*2; cmin=int(np.ceil(10*COMBO_THRESHOLD_PCT/100))
    sigs=[]; lsb=-999
    for idx in range(max(win+20,50), n):
        cm=max(abs(c[idx]-o[idx]),h[idx]-l[idx]); dn=min(o[idx],l[idx])
        if dn<=0: continue
        if cm/dn*100>MAX_CANDLE_MOVE_PCT: continue
        def iw(fn):
            for i in range(max(1,idx-win),idx+1):
                if i<n and fn(i): return True
            return False
        rok=iw(lambda i:(rsi[i]-rsi[i-1])>=RSI_MIN_MOVE_BUY)
        if not rok: continue
        dok=iw(lambda i:(pdi[i]-pdi[i-1])>0 and abs(pdi[i]-pdi[i-1])>=DMI_MIN_MOVE_PLUS)
        if not dok: continue
        aok=iw(lambda i:asd[i]==-1 and asd[i-1]!=-1)
        if not aok: continue
        gok=reg[idx]!=-1
        lok=iw(lambda i:abs(ht[i])>=9.6 or abs(ht[i]-ht[i-1])>=LB_SPIKE_THRESH)
        vok=vm[idx]>=AV_MIN_MOVE and vc[idx]>0
        sok=iw(lambda i:std[i]==-1 and std[i-1]==1)
        pok=iw(lambda i:ppt[i]==1 and ppt[i-1]==-1)
        eok=False
        for i in range(max(0,idx-EC_BULL_DIV_MEMORY),idx+1):
            if ebd[i]: eok=True; break
        if not eok: eok=iw(lambda i:(er[i]-er[i-1])>0 and abs(er[i]-er[i-1])>=EC_MIN_MOVE_RSI)
        if not eok:
            def _sl(i):
                if np.isnan(es[i]) or np.isnan(es[i-1]): return False
                d=es[i]-es[i-1]; return d>0 and abs(d)>=EC_MIN_MOVE_SLOW_MA
            eok=iw(_sl)
        cok=ca[idx]
        conds={"RSI":True,"DMI":True,"AST":True,"CHoCH":cok,"Zone":gok,
               "Lazy":lok,"Vol":vok,"ST":sok,"PP":pok,"EC":eok}
        sc=sum(1 for x in conds.values() if x)
        if sc>=cmin:
            if idx-lsb<=win: continue
            lsb=idx
            sigs.append({"bar_index":idx,"time":df.iloc[idx]["open_time"],
                         "entry_price":c[idx],"score":sc,"rsi":rsi[idx],
                         "di_plus":pdi[idx],"conditions":conds})
    print(f"  🔍 {tf_label} → {len(sigs)} signaux")
    return sigs

# ═══════════════════════════════════════════════════════
# 🔄 GROUPEMENT PAR BOUGIE 4H
# ═══════════════════════════════════════════════════════
def get_4h_key(dt):
    h4=(dt.hour//4)*4
    return f"{dt.strftime('%Y-%m-%d')}_{h4:02d}"

def group_signals_by_4h(all_tf_signals):
    groups={}
    for tf, signals in all_tf_signals.items():
        for sig in signals:
            key=get_4h_key(sig["time"])
            if key not in groups: groups[key]={"4h_key":key,"tfs":{},"time":sig["time"]}
            if tf not in groups[key]["tfs"] or sig["score"]>groups[key]["tfs"][tf]["score"]:
                groups[key]["tfs"][tf]=sig
            if sig["time"]<groups[key]["time"]: groups[key]["time"]=sig["time"]
    result=sorted(groups.values(), key=lambda x:x["time"])
    for g in result:
        g["best_score"]=max(s["score"] for s in g["tfs"].values())
        g["nb_tfs"]=len(g["tfs"])
        g["entry_price"]=max(g["tfs"].values(), key=lambda s:s["score"])["entry_price"]
        if g["nb_tfs"]>=4: g["emotion"]="🔥🔥🔥 LEGENDARY"
        elif g["nb_tfs"]>=3: g["emotion"]="🔥🔥 ULTRA STRONG"
        elif g["nb_tfs"]>=2: g["emotion"]="🔥 STRONG"
        else: g["emotion"]=""
    return result

# ═══════════════════════════════════════════════════════
# 💰 SIMULATION TRADES (sur données 4H)
# ═══════════════════════════════════════════════════════
def simulate_trades(df4h, grouped):
    c=df4h["close"].values; h=df4h["high"].values; l=df4h["low"].values
    t=df4h["open_time"].values; n=len(c); trades=[]
    for grp in grouped:
        et=grp["time"]; eidx=None
        for i in range(n):
            if pd.Timestamp(t[i])>=et: eidx=i; break
        if eidx is None or eidx>=n-1: continue
        ep=c[eidx]; tp=ep*(1+TAKE_PROFIT_PCT/100); sl=ep*(1-STOP_LOSS_PCT/100)
        xi=None; xp=None; xr=None
        mb=min(eidx+MAX_HOLD_BARS+1,n) if MAX_HOLD_BARS>0 else n
        for j in range(eidx+1,mb):
            if l[j]<=sl: xi=j; xp=sl; xr="STOP LOSS"; break
            if h[j]>=tp: xi=j; xp=tp; xr="TAKE PROFIT"; break
        if xi is None:
            if MAX_HOLD_BARS>0 and eidx+MAX_HOLD_BARS<n:
                xi=eidx+MAX_HOLD_BARS; xp=c[xi]; xr="MAX HOLD"
            elif eidx+1<n: xi=n-1; xp=c[xi]; xr="STILL OPEN"
            else: continue
        pnl=(xp-ep)/ep*100
        trades.append({"entry_time":pd.Timestamp(t[eidx]),"exit_time":pd.Timestamp(t[xi]),
                        "entry_price":ep,"exit_price":xp,"pnl_pct":pnl,"exit_reason":xr,
                        "hold_bars":xi-eidx,"score":grp["best_score"],"nb_tfs":grp["nb_tfs"],
                        "emotion":grp["emotion"],"tfs":list(grp["tfs"].keys())})
    return trades

# ═══════════════════════════════════════════════════════
# 📊 RAPPORT
# ═══════════════════════════════════════════════════════
def generate_report(trades, symbol, timeframes, start, end):
    sep="═"*65
    print(f"\n{sep}")
    print(f"  📊 MEGA BUY BACKTEST v3 — RAPPORT MULTI-TF")
    print(f"{sep}\n")
    print(f"📈 Paire: {symbol}  |  TF: {', '.join(timeframes)}")
    print(f"📅 {start} → {end}  |  Score /10  |  TP +{TAKE_PROFIT_PCT}% / SL -{STOP_LOSS_PCT}%")
    if MAX_HOLD_BARS>0: print(f"⏳ Max hold: {MAX_HOLD_BARS} bougies 4H")
    if not trades: print("\n❌ Aucun trade."); return None
    tot=len(trades); wins=[t for t in trades if t["pnl_pct"]>0]
    losses=[t for t in trades if t["pnl_pct"]<=0]; wr=len(wins)/tot*100
    pnls=[t["pnl_pct"] for t in trades]; tpnl=sum(pnls); apnl=np.mean(pnls)
    aw=np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    al=np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    gp=sum(t["pnl_pct"] for t in wins) if wins else 0
    gl=abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.01
    pf=gp/gl if gl>0 else float('inf')
    cap=INITIAL_CAPITAL; mc=cap; mdd=0
    for t in trades:
        p=cap*POSITION_SIZE_PCT/100; cap+=p*t["pnl_pct"]/100
        mc=max(mc,cap); dd=(mc-cap)/mc*100; mdd=max(mdd,dd)
    mcw=mcl=cc=0
    for t in trades:
        if t["pnl_pct"]>0: cc=cc+1 if cc>0 else 1; mcw=max(mcw,cc)
        else: cc=cc-1 if cc<0 else -1; mcl=max(mcl,abs(cc))
    ah=np.mean([t["hold_bars"] for t in trades])
    tpn=sum(1 for t in trades if t["exit_reason"]=="TAKE PROFIT")
    sln=sum(1 for t in trades if t["exit_reason"]=="STOP LOSS")
    mhn=sum(1 for t in trades if t["exit_reason"]=="MAX HOLD")

    print(f"\n{'─'*65}\n  📊 RÉSULTATS GLOBAUX\n{'─'*65}")
    print(f"  Trades: {tot}  |  ✅ {len(wins)} ({wr:.1f}%)  |  ❌ {len(losses)} ({100-wr:.1f}%)")
    print(f"  P&L total: {'+' if tpnl>0 else ''}{tpnl:.2f}%  |  Moyen: {'+' if apnl>0 else ''}{apnl:.2f}%")
    print(f"  Gain moyen: +{aw:.2f}%  |  Perte moyenne: {al:.2f}%")
    print(f"  PF: {pf:.2f}  |  MaxDD: -{mdd:.2f}%  |  Consec: {mcw}W/{mcl}L  |  Hold: {ah:.1f} bars 4H")
    print(f"  TP: {tpn} ({tpn/tot*100:.0f}%)  SL: {sln} ({sln/tot*100:.0f}%)  MH: {mhn}")

    print(f"\n{'─'*65}\n  💰 CAPITAL ({POSITION_SIZE_PCT}% par trade)\n{'─'*65}")
    print(f"  ${INITIAL_CAPITAL:,.0f} → ${cap:,.2f}  ({'+' if cap>INITIAL_CAPITAL else ''}{(cap-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:.2f}%)")

    print(f"\n{'─'*65}\n  📊 PAR SCORE\n{'─'*65}")
    for sc in sorted(set(t["score"] for t in trades), reverse=True):
        st=[t for t in trades if t["score"]==sc]; sw=[t for t in st if t["pnl_pct"]>0]
        print(f"  {sc}/10 : {len(st)} trades | WR {len(sw)/len(st)*100:.0f}% | Avg {'+' if np.mean([t['pnl_pct'] for t in st])>0 else ''}{np.mean([t['pnl_pct'] for t in st]):.2f}%")

    print(f"\n{'─'*65}\n  📊 PAR NOMBRE DE TF\n{'─'*65}")
    for nt in sorted(set(t["nb_tfs"] for t in trades), reverse=True):
        st=[t for t in trades if t["nb_tfs"]==nt]; sw=[t for t in st if t["pnl_pct"]>0]
        em="🔥🔥🔥" if nt>=4 else ("🔥🔥" if nt>=3 else ("🔥" if nt>=2 else ""))
        print(f"  {nt} TF {em}: {len(st)} trades | WR {len(sw)/len(st)*100:.0f}% | Avg {'+' if np.mean([t['pnl_pct'] for t in st])>0 else ''}{np.mean([t['pnl_pct'] for t in st]):.2f}%")

    print(f"\n{'─'*65}\n  📋 DÉTAIL DES TRADES\n{'─'*65}")
    print(f"  {'#':>3} {'Date':>16} {'Sc':>4} {'TFs':>14} {'Entry':>12} {'P&L':>8} {'Exit':>12} {'4H':>4}")
    print(f"  {'─'*3} {'─'*16} {'─'*4} {'─'*14} {'─'*12} {'─'*8} {'─'*12} {'─'*4}")
    for i,t in enumerate(trades):
        ic="✅" if t["pnl_pct"]>0 else "❌"
        ps=f"{'+' if t['pnl_pct']>0 else ''}{t['pnl_pct']:.2f}%"
        print(f"  {i+1:>3} {t['entry_time'].strftime('%Y-%m-%d %H:%M'):>16} {t['score']:>2}/10 {','.join(t['tfs']):>14} "
              f"{t['entry_price']:>12.2f} {ic}{ps:>7} {t['exit_reason']:>12} {t['hold_bars']:>4}")

    best=max(trades,key=lambda t:t["pnl_pct"]); worst=min(trades,key=lambda t:t["pnl_pct"])
    print(f"\n  🏆 Best: +{best['pnl_pct']:.2f}% {best['entry_time'].strftime('%m-%d %H:%M')} ({','.join(best['tfs'])})")
    print(f"  💀 Worst: {worst['pnl_pct']:.2f}% {worst['entry_time'].strftime('%m-%d %H:%M')} ({','.join(worst['tfs'])})")

    csv_f=f"backtest_{symbol}_MTF_{start}_{end}.csv"
    pd.DataFrame(trades).to_csv(csv_f, index=False)
    print(f"\n  💾 {csv_f}")
    print(f"\n{sep}\n  FIN DU RAPPORT\n{sep}\n")

    # ── TELEGRAM REPORT ──
    tg = (
        f"📊 <b>BACKTEST {symbol} — Multi-TF</b>\n"
        f"⏱️ {', '.join(timeframes)} | {start} → {end}\n"
        f"🎯 TP +{TAKE_PROFIT_PCT}% / SL -{STOP_LOSS_PCT}%\n"
        f"{'─'*28}\n\n"
        f"📈 <b>Trades: {tot}</b>  |  ✅ {len(wins)} ({wr:.1f}%)  |  ❌ {len(losses)}\n"
        f"💰 P&L: <b>{'+' if tpnl>0 else ''}{tpnl:.2f}%</b>  |  Moyen: {'+' if apnl>0 else ''}{apnl:.2f}%\n"
        f"🏆 PF: {pf:.2f}  |  📉 MaxDD: -{mdd:.2f}%\n"
        f"⏳ Hold: {ah:.1f} bars 4H  |  Consec: {mcw}W/{mcl}L\n"
        f"💵 ${INITIAL_CAPITAL:,.0f} → <b>${cap:,.2f}</b>\n\n"
    )

    # Par score
    tg += "<b>📊 Par Score:</b>\n"
    for sc in sorted(set(t["score"] for t in trades), reverse=True):
        st=[t for t in trades if t["score"]==sc]; sw=[t for t in st if t["pnl_pct"]>0]
        sa=np.mean([t["pnl_pct"] for t in st])
        tg += f"  {sc}/10: {len(st)}t WR {len(sw)/len(st)*100:.0f}% Avg {'+' if sa>0 else ''}{sa:.2f}%\n"

    # Par nombre de TF
    tg += "\n<b>📊 Par TF:</b>\n"
    for nt in sorted(set(t["nb_tfs"] for t in trades), reverse=True):
        st=[t for t in trades if t["nb_tfs"]==nt]; sw=[t for t in st if t["pnl_pct"]>0]
        sa=np.mean([t["pnl_pct"] for t in st])
        em="🔥🔥🔥" if nt>=4 else ("🔥🔥" if nt>=3 else ("🔥" if nt>=2 else ""))
        tg += f"  {nt}TF {em}: {len(st)}t WR {len(sw)/len(st)*100:.0f}% Avg {'+' if sa>0 else ''}{sa:.2f}%\n"

    tg += f"\n🏆 Best: +{best['pnl_pct']:.2f}% ({','.join(best['tfs'])})\n"
    tg += f"💀 Worst: {worst['pnl_pct']:.2f}% ({','.join(worst['tfs'])})"

    send_telegram(tg)

    # Envoyer aussi les trades détaillés (par pages de 20)
    for page in range(0, len(trades), 20):
        batch = trades[page:page+20]
        msg = f"📋 <b>Trades {page+1}-{page+len(batch)}/{tot}</b>\n\n"
        for i, t in enumerate(batch):
            ic = "✅" if t["pnl_pct"] > 0 else "❌"
            ps = f"{'+' if t['pnl_pct']>0 else ''}{t['pnl_pct']:.2f}%"
            msg += (f"{ic} {t['entry_time'].strftime('%m-%d %H:%M')} "
                    f"<b>{t['score']}/10</b> [{','.join(t['tfs'])}] "
                    f"{ps} {t['exit_reason']}\n")
        send_telegram(msg)
        time.sleep(0.3)

    print("  ✅ Rapport envoyé sur Telegram")

    return {"total_trades":tot,"win_rate":wr,"total_pnl":tpnl,"profit_factor":pf,"max_drawdown":mdd,"final_capital":cap}

# ═══════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════
def main():
    global TAKE_PROFIT_PCT, STOP_LOSS_PCT
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     📊 MEGA BUY Backtester v3                    ║
    ║     Multi-TF + 4H Grouping — Score /10           ║
    ║     EC + CHoCH + Pump Filter                     ║
    ║     ASSYIN-2026                                  ║
    ╚═══════════════════════════════════════════════════╝
    """)
    print(f"📋 Config: {SYMBOL} | {','.join(TIMEFRAMES)} | {DATE_START}→{DATE_END}")
    print(f"   TP +{TAKE_PROFIT_PCT}% / SL -{STOP_LOSS_PCT}% | Seuil {COMBO_THRESHOLD_PCT}%\n")

    sym=input(f"📈 Paire [{SYMBOL}] : ").strip() or SYMBOL
    start=input(f"📅 Début [{DATE_START}] : ").strip() or DATE_START
    end=input(f"📅 Fin [{DATE_END}] : ").strip() or DATE_END
    tfi=input(f"⏱️  TF [{','.join(TIMEFRAMES)}] : ").strip()
    tfs=[t.strip() for t in tfi.split(",")] if tfi else TIMEFRAMES
    tp=input(f"🎯 TP % [{TAKE_PROFIT_PCT}] : ").strip()
    sl=input(f"🛑 SL % [{STOP_LOSS_PCT}] : ").strip()

    if tp: TAKE_PROFIT_PCT=float(tp)
    if sl: STOP_LOSS_PCT=float(sl)

    print(f"\n{'═'*65}")
    print(f"  🔄 {sym} | {', '.join(tfs)} | {start} → {end}")
    print(f"  Groupement par bougie 4H")
    print(f"{'═'*65}")

    # 1. Charger et analyser chaque TF
    all_tf_sigs={}
    start_dt=pd.Timestamp(start)
    for tf in tfs:
        print(f"\n  ⏱️ {tf}...")
        df=get_full_history(sym, tf, start, end)
        if df is None: print(f"  ❌ Pas de données {tf}"); continue
        sigs=compute_all_signals(df, tf_label=tf)
        sigs=[s for s in sigs if s["time"]>=start_dt]
        all_tf_sigs[tf]=sigs

    total_raw=sum(len(v) for v in all_tf_sigs.values())
    print(f"\n  📊 Total brut: {total_raw} signaux sur {len(all_tf_sigs)} TFs")

    # 2. Grouper par 4H
    grouped=group_signals_by_4h(all_tf_sigs)
    multi=sum(1 for g in grouped if g["nb_tfs"]>=2)
    print(f"  📦 Groupés: {len(grouped)} signaux 4H ({multi} multi-TF)")

    if not grouped: print("\n❌ Aucun signal."); return

    # 3. Données 4H pour sim
    print(f"\n  📥 Chargement 4H pour simulation...")
    df4h=get_full_history(sym, "4h", start, end)
    if df4h is None: print("  ❌ Pas de données 4H"); return

    # 4. Simuler
    trades=simulate_trades(df4h, grouped)
    print(f"  💰 {len(trades)} trades simulés")

    # 5. Rapport
    generate_report(trades, sym, tfs, start, end)

if __name__=="__main__":
    main()
