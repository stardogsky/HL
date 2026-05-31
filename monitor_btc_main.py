"""Live monitor for bot_HL_Test on mainnet outcome 3.
Refreshes every 15s. Cleaner format than terminal tail."""
import os, time, subprocess, re

LOG = os.path.expanduser('~/.pm2/logs/bot-HL-Test-out.log')

def tail(path, n=300):
    try:
        return subprocess.check_output(['tail', f'-n{n}', path], text=True).splitlines()
    except Exception:
        return []

def find_last(lines, pattern):
    for line in reversed(lines):
        if pattern in line:
            return line
    return None

def find_all(lines, pattern):
    return [L for L in lines if pattern in L]

def extract_field(line, key, sep='|'):
    if not line or key not in line:
        return None
    try:
        s = line.split(key, 1)[1].split(sep, 1)[0].strip()
        return s.strip()
    except Exception:
        return None

while True:
    os.system('clear')
    lines = tail(LOG, 500)
    
    # Last TICK
    last_tick = find_last(lines, '[TICK]')
    last_skew = find_last(lines, '[SKEW]')
    last_pulse = find_last(lines, '[PULSE]')
    last_fill = find_last(lines, 'FILL_CTX')
    last_realized = find_last(lines, 'REALIZED')
    last_toxic = find_last(lines, 'TOXIC_ORIGIN')
    last_shadow = find_last(lines, 'SHADOW_TOXIC')
    last_dcs = find_last(lines, 'DCS_KILL')
    
    # Block counters last 500 lines
    n_pingpong_block = len(find_all(lines, 'PINGPONG_GUARD'))
    n_grid_kill = len(find_all(lines, 'GRID_MGR_KILL'))
    n_dcs = len(find_all(lines, 'DCS_KILL'))
    n_fills_recent = len(find_all(lines, 'FILL_CTX'))
    n_toxic_recent = len(find_all(lines, 'TOXIC_ORIGIN'))
    
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  HL BOT MONITOR  |  bot_HL_Test  |  outcome 3 BTC daily")
    print(f"  {time.strftime('%H:%M:%S UTC', time.gmtime())}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # ─── PRICE & POSITION ─────────────────────────────────────
    if last_tick:
        # Parse: [TICK] BTC=$81,551 | YES=0.700(150)/0.703 NO=0.297(215)/0.300 | bid_sum=1.00 ask_sum=1.00 | pos=Y30/N30 | T-34625s
        tick_part = last_tick.split('[TICK]', 1)[1] if '[TICK]' in last_tick else ''
        print(f"💲 PRICE/POS:")
        print(f"  {tick_part.strip()[:200]}")
    
    # ─── INVENTORY STATE ──────────────────────────────────────
    if last_skew:
        # Extract Pos / Lck / InvPS from SKEW
        pos_y = extract_field(last_skew, 'Pos_Y:')
        pos_n = extract_field(last_skew, 'Pos_N:')
        lck = extract_field(last_skew, 'Lck:')
        invps = extract_field(last_skew, 'InvPS:')
        regime = extract_field(last_skew, 'Reg:', sep='(')
        intent = extract_field(last_skew, 'Intent:')
        cvd_state = extract_field(last_skew, 'CVD:')
        oxy = extract_field(last_skew, 'Oxy:')
        
        print(f"\n📊 INVENTORY:")
        print(f"  Pos_Y:{pos_y}  Pos_N:{pos_n}  Lck:{lck}")
        print(f"  InvPS:{invps}  Regime:{regime}  Intent:{intent}")
        print(f"  CVD:{cvd_state}  Oxygen:{oxy}")
    
    # ─── FILL HISTORY ─────────────────────────────────────────
    print(f"\n📥 FILLS (last 500 log lines): {n_fills_recent}")
    if last_fill:
        # Extract: side, qty, price, FV, Q transition
        match_side = re.search(r'FILL_CTX\] (\w+) (\d+)@([\d.]+)', last_fill)
        match_q = re.search(r'Q:(-?\d+)→(-?\d+)', last_fill)
        match_fv = re.search(r'FV:([\d.]+)', last_fill)
        match_intent = re.search(r'Intent:(\w+)', last_fill)
        
        if match_side and match_q:
            side, qty, px = match_side.groups()
            q_pre, q_post = match_q.groups()
            fv = match_fv.group(1) if match_fv else '?'
            intent = match_intent.group(1) if match_intent else '?'
            print(f"  Last: {side} {qty}@{px} | FV={fv} | Q:{q_pre}→{q_post} | {intent}")
    
    # ─── TOXIC ALERTS ─────────────────────────────────────────
    if last_toxic:
        match_ps = re.search(r'PS_before:([\d.]+) → PS_after:([\d.]+)', last_toxic)
        match_q = re.search(r'Q:(-?\d+)→(-?\d+)', last_toxic)
        if match_ps and match_q:
            ps_pre, ps_post = match_ps.groups()
            q_pre, q_post = match_q.groups()
            print(f"\n☢️  LAST TOXIC ORIGIN:")
            print(f"  PS: {ps_pre} → {ps_post}  |  Q:{q_pre}→{q_post}")
    
    if last_shadow:
        match_ps = re.search(r'PS:\s*([\d.]+)', last_shadow)
        match_lck = re.search(r'Locked:\s*(\d+)', last_shadow)
        if match_ps:
            ps = match_ps.group(1)
            lck = match_lck.group(1) if match_lck else '?'
            print(f"\n💀 SHADOW TOXIC: PS={ps} Locked={lck}")
            print(f"  Любое закрытие замка = минус")
    
    # ─── DEFENSIVE BLOCKS COUNT ──────────────────────────────
    print(f"\n🛡️  BLOCKERS (last 500 lines):")
    print(f"  PINGPONG_GUARD: {n_pingpong_block}")
    print(f"  GRID_MGR_KILL:  {n_grid_kill}")
    print(f"  DCS_KILL:       {n_dcs}")
    print(f"  TOXIC_ORIGIN:   {n_toxic_recent}")
    
    # ─── TIMING ──────────────────────────────────────────────
    if last_tick:
        match_t = re.search(r'T-(\d+)s', last_tick)
        if match_t:
            sec_left = int(match_t.group(1))
            h, rem = divmod(sec_left, 3600)
            m = rem // 60
            print(f"\n⏰ TIME TO SETTLE: {h}h {m}m  ({sec_left}s)")
    
    print(f"\n[refresh in 15s — Ctrl+C to exit]")
    time.sleep(15)
