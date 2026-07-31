"""The whole design language in one static stylesheet.

Rule: colour encodes outcome (done / missed); the blue line is the only glowing
spine; chrome stays cold slate.  Motion is pure CSS so it survives Streamlit's
no-JS markdown sandbox.
"""

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
:root{
  --canvas:#070B14;--panel:#0E1422;--panel-2:#121A2B;--hair:#1C2740;--hair-2:#2A3858;
  --ink:#E8EDF7;--ink-2:#B6C0D4;--mute:#69748C;
  --win:#34D399;--win-soft:rgba(52,211,153,.14);--loss:#F0556B;--loss-soft:rgba(240,85,107,.14);
  --accent:#4C8DFF;--accent-soft:rgba(76,141,255,.16);--jewel:#D946EF;
  --disp:'Space Grotesk',system-ui,sans-serif;--body:'Manrope',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,monospace;
}
html,body,.stApp{background:var(--canvas);color:var(--ink);font-family:var(--body);}
.stApp{overflow-x:hidden;}
.stApp::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(900px 520px at 8% -8%,rgba(76,141,255,.10),transparent 62%),
  radial-gradient(820px 520px at 97% 2%,rgba(52,211,153,.06),transparent 62%),
  radial-gradient(760px 640px at 84% 106%,rgba(217,70,239,.05),transparent 62%);
  animation:tw-drift 26s ease-in-out infinite alternate;}
.stApp::after{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),
  linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);background-size:46px 46px;
  -webkit-mask-image:radial-gradient(circle at 50% 22%,#000 0%,transparent 82%);
  mask-image:radial-gradient(circle at 50% 22%,#000 0%,transparent 82%);}
@keyframes tw-drift{0%{transform:translate3d(0,0,0) scale(1);}100%{transform:translate3d(-1.4%,-1%,0) scale(1.05);}}
.block-container{position:relative;z-index:1;padding-top:1.3rem;padding-bottom:3rem;max-width:1560px;}
footer{display:none!important;}#MainMenu{opacity:.5;}
.tw-win{color:var(--win)!important;}.tw-loss{color:var(--loss)!important;}.tw-ink{color:var(--ink)!important;}
.tw-accent{color:var(--accent)!important;}.tw-mute{color:var(--mute)!important;}.tw-jewel{color:var(--jewel)!important;}
@keyframes tw-rise{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
@keyframes tw-draw{from{stroke-dashoffset:6000;}to{stroke-dashoffset:0;}}
@keyframes tw-fade{from{opacity:0;}to{opacity:1;}}
@keyframes tw-grow{from{transform:scaleX(0);}to{transform:scaleX(1);}}
@keyframes tw-growY{from{transform:scaleY(0);}to{transform:scaleY(1);}}
@keyframes tw-pulse{0%{box-shadow:0 0 0 0 rgba(52,211,153,.5);}70%{box-shadow:0 0 0 7px rgba(52,211,153,0);}100%{box-shadow:0 0 0 0 rgba(52,211,153,0);}}
@keyframes tw-pulse2{0%{box-shadow:0 0 0 0 var(--accent);}70%{box-shadow:0 0 0 8px transparent;}100%{box-shadow:0 0 0 0 transparent;}}
.tw-rise{animation:tw-rise .55s cubic-bezier(.2,.7,.2,1) both;}
.tw-greet{display:flex;align-items:center;gap:.55rem;padding:.3rem 0 .1rem;}
.tw-greet-hi{font:500 15px/1 var(--body);color:var(--mute);}
.tw-greet-name{font:700 22px/1 var(--disp);color:var(--ink);letter-spacing:-.01em;}
.tw-live{width:8px;height:8px;border-radius:50%;background:var(--win);display:inline-block;animation:tw-pulse 2s infinite;margin-left:.2rem;}
.tw-panel{background:linear-gradient(180deg,var(--panel),var(--panel-2));border:1px solid var(--hair);
  border-radius:12px;padding:16px 18px;animation:tw-rise .55s cubic-bezier(.2,.7,.2,1) both;}
.tw-panel-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.tw-panel-t{font:600 11px/1 var(--disp);letter-spacing:.16em;text-transform:uppercase;color:var(--mute);}
.tw-pill{font:600 11px/1 var(--mono);color:var(--ink-2);background:rgba(255,255,255,.04);border:1px solid var(--hair);border-radius:999px;padding:5px 10px;}
.tw-tiles{display:grid;gap:12px;}
.tw-tile{background:linear-gradient(180deg,var(--panel),var(--panel-2));border:1px solid var(--hair);border-radius:12px;
  padding:14px 16px;animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;transition:.2s;}
.tw-tile:hover{transform:translateY(-3px);border-color:var(--hair-2);box-shadow:0 12px 30px -18px rgba(0,0,0,.8);}
.tw-tile-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.tw-lab{font:600 10px/1 var(--disp);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);}
.tw-chip{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:13px;background:var(--accent-soft);color:var(--accent);}
.tw-chip.tw-win{background:var(--win-soft);}.tw-chip.tw-loss{background:var(--loss-soft);}.tw-chip.tw-jewel{background:rgba(217,70,239,.14);}
.tw-val{font:700 27px/1.05 var(--mono);color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em;}
.tw-sub{font:600 11px/1 var(--mono);color:var(--mute);margin-top:7px;font-variant-numeric:tabular-nums;}
.tw-tagc{display:inline-block;font:700 9px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:3px 8px;border-radius:999px;}
.tw-now{display:grid;grid-template-columns:1.25fr .75fr;gap:22px;align-items:center;}
.tw-now-lab{font:700 11px/1 var(--disp);letter-spacing:.22em;color:var(--accent);}
.tw-now-block{font:700 30px/1.05 var(--disp);color:var(--ink);margin:9px 0 2px;}
.tw-now-time{font:700 42px/1 var(--mono);color:var(--ink);letter-spacing:-.03em;}
.tw-now-bar{height:8px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;margin:14px 0 8px;}
.tw-now-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--win));transform-origin:left;animation:tw-grow 1s ease both;}
.tw-now-next{font:500 12px/1 var(--mono);color:var(--mute);}
.tw-tl-item{display:grid;grid-template-columns:54px 20px 1fr;gap:12px;position:relative;padding:7px 6px;border-radius:10px;transition:.18s;}
.tw-tl-item:hover{background:rgba(255,255,255,.025);}
.tw-tl-time{text-align:right;font:600 11px/1 var(--mono);color:var(--mute);padding-top:3px;}
.tw-tl-rail{position:relative;display:flex;justify-content:center;}
.tw-tl-rail::before{content:"";position:absolute;top:0;bottom:0;width:2px;background:var(--hair);}
.tw-tl-item:first-child .tw-tl-rail::before{top:50%;}
.tw-tl-item:last-child .tw-tl-rail::before{bottom:50%;}
.tw-tl-dot{position:relative;z-index:1;width:11px;height:11px;border-radius:50%;margin-top:3px;background:var(--panel-2);border:2px solid var(--hair-2);}
.tw-tl-label{font:600 13px/1.2 var(--body);color:var(--ink-2);}
.tw-tl-meta{margin-top:5px;}
.tw-tl-item.done .tw-tl-dot{background:var(--win);border-color:var(--win);}
.tw-tl-item.done .tw-tl-rail::before{background:rgba(52,211,153,.35);}
.tw-tl-item.done .tw-tl-label,.tw-tl-item.done .tw-tl-time{color:var(--mute);}
.tw-tl-item.active{background:linear-gradient(90deg,var(--accent-soft),transparent);}
.tw-tl-item.active .tw-tl-dot{background:var(--accent);border-color:var(--accent);animation:tw-pulse2 2s infinite;}
.tw-tl-item.active .tw-tl-label{color:var(--ink);font-weight:800;}
.tw-hhead,.tw-hgrid{display:grid;grid-template-columns:158px 1fr 44px;gap:6px 10px;align-items:center;}
.tw-hhead-days{display:grid;gap:3px;}
.tw-hhead-days span{font:500 8px/1 var(--mono);color:var(--mute);text-align:center;}
.tw-hrow-name{display:flex;align-items:center;gap:8px;font:600 12px/1 var(--body);color:var(--ink-2);}
.tw-hrow-ico{width:18px;text-align:center;font-size:13px;}
.tw-hcells{display:grid;gap:3px;}
.tw-hcell{height:16px;border-radius:3px;border:1px solid var(--hair);background:rgba(255,255,255,.02);transition:.15s;}
.tw-hcell:hover{transform:scale(1.25);}
.tw-hcell.done{background:var(--win);border-color:transparent;opacity:.85;}
.tw-hcell.miss{background:rgba(240,85,107,.5);border-color:transparent;}
.tw-hcell.today{box-shadow:inset 0 0 0 1.5px var(--accent);}
.tw-hcell.future{opacity:.22;}
.tw-hpct{font:700 11px/1 var(--mono);text-align:right;font-variant-numeric:tabular-nums;}
.tw-goal{border:1px solid var(--hair);border-radius:12px;padding:14px 16px;background:linear-gradient(180deg,var(--panel),var(--panel-2));animation:tw-rise .5s ease both;transition:.2s;}
.tw-goal:hover{border-color:var(--hair-2);transform:translateY(-2px);}
.tw-goal-t{font:700 14px/1.2 var(--disp);color:var(--ink);}
.tw-goal-m{font:600 11px/1 var(--mono);color:var(--mute);margin-top:6px;}
.tw-goal-bar{height:8px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;margin:11px 0 7px;}
.tw-goal-fill{height:100%;border-radius:5px;transform-origin:left;animation:tw-grow .9s ease both;}
.tw-goal-foot{display:flex;justify-content:space-between;font:600 11px/1 var(--mono);font-variant-numeric:tabular-nums;}
.tw-eq{width:100%;height:auto;display:block;}
.tw-eq-line{fill:none;stroke:var(--accent);stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 6px rgba(76,141,255,.55));stroke-dasharray:6000;animation:tw-draw 1.1s ease-out both;}
.tw-eq-area{animation:tw-fade 1.2s ease-out both;}
.tw-eq-grid{stroke:var(--hair);stroke-width:1;}
.tw-eq-txt{fill:var(--mute);font:500 11px var(--mono);}
.tw-eq-dot{fill:var(--accent);filter:drop-shadow(0 0 6px rgba(76,141,255,.9));}
.tw-eq-ring{fill:none;stroke:var(--accent);stroke-width:2;opacity:.5;animation:tw-pulse2 2s infinite;}
.tw-bars{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:8px;height:200px;align-items:end;}
.tw-bar-col{position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;}
.tw-bar-track{position:relative;width:60%;max-width:30px;height:78%;}
.tw-bar-zero{position:absolute;left:-30%;right:-30%;top:50%;height:1px;background:var(--hair-2);}
.tw-bar-fill{position:absolute;left:0;right:0;border-radius:4px;transform-origin:center;animation:tw-growY .7s cubic-bezier(.2,.7,.2,1) both;transition:.2s;}
.tw-bar-fill:hover{filter:brightness(1.18);}
.tw-bar-up{background:linear-gradient(180deg,var(--win),rgba(52,211,153,.55));bottom:50%;}
.tw-bar-down{background:linear-gradient(0deg,var(--loss),rgba(240,85,107,.55));top:50%;}
.tw-bar-lab{position:absolute;bottom:-20px;font:500 10px/1 var(--mono);color:var(--mute);}
.tw-cal-head,.tw-cal{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;}
.tw-cal-head span{font:600 10px/1 var(--disp);letter-spacing:.1em;color:var(--mute);text-align:center;padding:2px 0;}
.tw-day{min-height:60px;border:1px solid var(--hair);border-radius:8px;padding:7px 8px;background:rgba(255,255,255,.012);transition:.18s;}
.tw-day:hover{border-color:var(--hair-2);background:rgba(255,255,255,.03);}
.tw-day-num{font:600 11px/1 var(--mono);color:var(--mute);}
.tw-day-pnl{font:700 12px/1 var(--mono);margin-top:8px;font-variant-numeric:tabular-nums;}
.tw-day.up{border-color:rgba(52,211,153,.28);background:var(--win-soft);}
.tw-day.down{border-color:rgba(240,85,107,.28);background:var(--loss-soft);}
.tw-day.empty{background:transparent;border-color:transparent;}
.tw-day.today{box-shadow:inset 0 0 0 1.5px var(--accent);}
.tw-day.future{opacity:.32;}
.tw-donut-wrap{display:flex;align-items:center;gap:18px;flex-wrap:wrap;}
.tw-donut-c1{font:700 11px/1 var(--disp);letter-spacing:.12em;fill:var(--mute);text-transform:uppercase;}
.tw-donut-c2{font:700 19px/1 var(--mono);fill:var(--ink);}
.tw-legend{flex:1 1 170px;display:flex;flex-direction:column;gap:9px;min-width:160px;}
.tw-leg-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;}
.tw-leg-dot{width:9px;height:9px;border-radius:50%;}
.tw-leg-name{font:600 12px/1 var(--body);color:var(--ink-2);}
.tw-leg-val{font:600 12px/1 var(--mono);font-variant-numeric:tabular-nums;}
.tw-leg-pct{font:600 11px/1 var(--mono);color:var(--mute);width:38px;text-align:right;}
.tw-streaks{display:grid;gap:12px;}
.tw-streak{border:1px solid var(--hair);border-radius:10px;padding:14px;text-align:center;background:rgba(255,255,255,.012);animation:tw-rise .5s ease both;}
.tw-streak-n{font:700 30px/1 var(--mono);}
.tw-streak-l{font:600 9px/1 var(--disp);letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-top:8px;}
.tw-table{width:100%;border-collapse:collapse;font:500 12.5px/1.4 var(--body);}
.tw-table thead th{font:600 10px/1 var(--disp);letter-spacing:.12em;text-transform:uppercase;color:var(--mute);text-align:left;padding:0 12px 10px;border-bottom:1px solid var(--hair);}
.tw-table tbody td{padding:11px 12px;border-bottom:1px solid rgba(28,39,64,.6);font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap;}
.tw-table tbody tr{transition:.15s;}.tw-table tbody tr:hover{background:rgba(255,255,255,.03);}
.tw-table .num{font-family:var(--mono);}
.tw-dir{font:700 10px/1 var(--mono);letter-spacing:.08em;padding:3px 8px;border-radius:6px;}
.tw-dir.BUY{color:var(--win);background:var(--win-soft);}.tw-dir.SELL{color:var(--loss);background:var(--loss-soft);}
.tw-stat{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(28,39,64,.55);}
.tw-stat:last-child{border-bottom:none;}
.tw-stat .k{font:500 12px/1 var(--body);color:var(--mute);}
.tw-stat .v{font:700 13px/1 var(--mono);font-variant-numeric:tabular-nums;}
.tw-empty{text-align:center;color:var(--mute);padding:36px 10px;font:500 13px var(--body);}
.tw-scroll{overflow-x:auto;}
.tw-tag{display:inline-block;font:600 11px/1 var(--mono);color:var(--ink-2);background:rgba(255,255,255,.04);border:1px solid var(--hair);border-radius:6px;padding:4px 8px;}
.tw-grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.tw-jcard{border:1px solid var(--hair);border-radius:10px;padding:12px 14px;background:rgba(255,255,255,.012);margin-bottom:10px;}
.tw-jcard .d{font:600 11px/1 var(--mono);color:var(--mute);margin-bottom:7px;}
.tw-jcard .row{font:500 12.5px/1.4 var(--body);color:var(--ink-2);margin:3px 0;}
.tw-jcard .row b{color:var(--mute);font-weight:600;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0A0F1B,#070B14);border-right:1px solid var(--hair);z-index:2;}
.tw-brand{display:flex;align-items:center;gap:11px;padding:4px 6px 14px;}
.tw-brand-n{font:700 17px/1 var(--disp);letter-spacing:.06em;color:var(--ink);}
.tw-brand-s{font:600 9px/1 var(--disp);letter-spacing:.22em;color:var(--mute);margin-top:5px;}
.tw-user{display:flex;align-items:center;gap:11px;padding:12px 8px;margin-top:8px;border-top:1px solid var(--hair);}
.tw-avatar{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;font:700 13px var(--disp);color:var(--ink);background:linear-gradient(135deg,var(--accent),rgba(52,211,153,.7));}
.tw-user-n{font:600 13px/1.2 var(--body);color:var(--ink);}
.tw-user-r{font:500 11px/1.2 var(--body);color:var(--mute);margin-top:3px;}
[data-testid="stSidebar"] [data-testid="stRadio"] > div{gap:2px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label{display:flex;align-items:center;gap:.6rem;padding:.6rem .7rem;border-radius:9px;cursor:pointer;color:var(--mute);font:600 13px/1 var(--disp);margin:0;transition:.18s;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(255,255,255,.04);color:var(--ink);}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:var(--accent-soft);color:var(--ink);box-shadow:inset 2px 0 0 var(--accent);}
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"]{position:absolute;opacity:0;width:0;height:0;}
[data-testid="stSidebar"] [data-testid="stRadio"] label p{margin:0;}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child{display:none;}
.stSelectbox label,.stTextInput label,.stDateInput label,.stNumberInput label,.stTimeInput label,.stMultiSelect label,.stTextArea label{font:600 10px/1 var(--disp)!important;letter-spacing:.12em;text-transform:uppercase;color:var(--mute)!important;}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,.stDateInput input,.stNumberInput input,.stTimeInput input,.stTextInput input,.stTextArea textarea{background:var(--panel)!important;border:1px solid var(--hair)!important;border-radius:9px!important;color:var(--ink)!important;font-family:var(--mono)!important;}
.stTextArea textarea{font-family:var(--mono)!important;font-size:12.5px!important;}
.stButton>button{background:var(--panel-2);border:1px solid var(--hair-2);color:var(--ink);border-radius:9px;font:600 12px var(--disp);transition:.18s;}
.stButton>button:hover{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);}
.stButton>button[kind="primary"]{background:var(--accent);border-color:var(--accent);color:#04101f;}
hr{border-color:var(--hair)!important;}
"""
