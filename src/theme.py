"""The whole design language in one static stylesheet - base + premium log
layer + pantry + spirit. One triple-quoted string so brackets can never be
cut by a copy tool. Colour encodes outcome; the blue line is the glowing
spine; the EKG is the heartbeat. Motion is pure CSS. Under 760px every row
stacks for the phone.
"""
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
:root{
--canvas:#070B14;--panel:#0E1422;--panel-2:#121A2B;
--hair:#1C2740;--hair-2:#2A3858;--ink:#E8EDF7;--ink-2:#B6C0D4;
--mute:#69748C;--mute-2:#8893AB;--win:#34D399;--win-soft:rgba(52,211,153,.14);
--loss:#F0556B;--loss-soft:rgba(240,85,107,.14);
--accent:#4C8DFF;--accent-soft:rgba(76,141,255,.16);
--jewel:#D946EF;--out:#FB923C;--out-soft:rgba(251,146,60,.14);
--mpesa:#4CAF50;--mpesa-soft:rgba(76,175,80,.14);
--disp:'Space Grotesk',system-ui,sans-serif;
--body:'Manrope',system-ui,sans-serif;
--mono:'JetBrains Mono',ui-monospace,monospace;}
html,body,.stApp{background:var(--canvas);color:var(--ink);font-family:var(--body);}
.stApp{overflow-x:hidden;}
.stApp::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
background:radial-gradient(900px 520px at 8% -8%,rgba(76,141,255,.10),transparent 62%),
radial-gradient(820px 520px at 97% 2%,rgba(52,211,153,.06),transparent 62%),
radial-gradient(760px 640px at 84% 106%,rgba(217,70,239,.05),transparent 62%);
animation:tw-drift 26s ease-in-out infinite alternate;}
.stApp::after{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),
linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);
background-size:46px 46px;
-webkit-mask-image:radial-gradient(circle at 50% 22%,#000 0%,transparent 82%);
mask-image:radial-gradient(circle at 50% 22%,#000 0%,transparent 82%);}
@keyframes tw-drift{0%{transform:translate3d(0,0,0) scale(1);}
100%{transform:translate3d(-1.4%,-1%,0) scale(1.05);}}
.block-container{position:relative;z-index:1;padding-top:1.3rem;padding-bottom:3rem;max-width:1560px;}
footer{display:none!important;}#MainMenu{opacity:.5;}
.tw-win{color:var(--win)!important;}
.tw-loss{color:var(--loss)!important;}
.tw-ink{color:var(--ink)!important;}
.tw-accent{color:var(--accent)!important;}
.tw-mute{color:var(--mute)!important;}
.tw-jewel{color:var(--jewel)!important;}
@keyframes tw-rise{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
@keyframes tw-draw{from{stroke-dashoffset:6000;}to{stroke-dashoffset:0;}}
@keyframes tw-fade{from{opacity:0;}to{opacity:1;}}
@keyframes tw-grow{from{transform:scaleX(0);}to{transform:scaleX(1);}}
@keyframes tw-growY{from{transform:scaleY(0);}to{transform:scaleY(1);}}
@keyframes tw-pulse{0%{box-shadow:0 0 0 0 rgba(52,211,153,.5);}
70%{box-shadow:0 0 0 7px rgba(52,211,153,0);}100%{box-shadow:0 0 0 0 rgba(52,211,153,0);}}
@keyframes tw-pulse2{0%{box-shadow:0 0 0 0 var(--accent);}
70%{box-shadow:0 0 0 8px transparent;}100%{box-shadow:0 0 0 0 transparent;}}
@keyframes tw-ekg{from{stroke-dashoffset:1240;}to{stroke-dashoffset:0;}}
.tw-ekg{width:100%;height:34px;display:block;margin:-4px 0 10px;}
.tw-ekg-line{fill:none;stroke:var(--accent);stroke-width:2;stroke-linecap:round;
stroke-linejoin:round;filter:drop-shadow(0 0 6px rgba(76,141,255,.7));
stroke-dasharray:300 940;animation:tw-ekg 2.8s linear infinite;}
.tw-greet{display:flex;align-items:center;gap:.55rem;padding:.3rem 0 .1rem;}
.tw-greet-hi{font:500 15px/1 var(--body);color:var(--mute);}
.tw-greet-name{font:700 22px/1 var(--disp);color:var(--ink);letter-spacing:-.01em;}
.tw-live{width:8px;height:8px;border-radius:50%;background:var(--win);
display:inline-block;animation:tw-pulse 2s infinite;margin-left:.2rem;}
.tw-panel{background:linear-gradient(180deg,var(--panel),var(--panel-2));
border:1px solid var(--hair);border-radius:12px;padding:16px 18px;
animation:tw-rise .55s cubic-bezier(.2,.7,.2,1) both;}
.tw-panel-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;gap:8px;}
.tw-panel-t{font:600 11px/1 var(--disp);letter-spacing:.16em;text-transform:uppercase;color:var(--mute);}
.tw-pill{font:600 11px/1 var(--mono);color:var(--ink-2);background:rgba(255,255,255,.04);
border:1px solid var(--hair);border-radius:999px;padding:5px 10px;white-space:nowrap;}
.tw-tiles{display:grid;gap:12px;}
.tw-tile{background:linear-gradient(180deg,var(--panel),var(--panel-2));border:1px solid var(--hair);
border-radius:12px;padding:14px 16px;animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;transition:.2s;}
.tw-tile:hover{transform:translateY(-3px);border-color:var(--hair-2);box-shadow:0 12px 30px -18px rgba(0,0,0,.8);}
.tw-tile-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:6px;}
.tw-lab{font:600 10px/1 var(--disp);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);}
.tw-chip{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;
background:var(--accent-soft);color:var(--accent);flex:0 0 auto;}
.tw-chip svg{width:15px;height:15px;display:block;}
.tw-chip.tw-win{background:var(--win-soft);}
.tw-chip.tw-loss{background:var(--loss-soft);}
.tw-chip.tw-jewel{background:rgba(217,70,239,.14);}
.tw-val{font:700 27px/1.05 var(--mono);color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em;}
.tw-sub{font:600 11px/1 var(--mono);color:var(--mute-2);margin-top:7px;font-variant-numeric:tabular-nums;}
.tw-tagc{display:inline-block;font:700 9px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:3px 8px;border-radius:999px;}
.tw-badge{display:inline-block;font:700 9px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:4px 9px;border-radius:999px;border:1px solid var(--hair);white-space:nowrap;}
.tw-prog{height:9px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;margin:10px 0 6px;}
.tw-prog-fill{height:100%;border-radius:5px;transform-origin:left;animation:tw-grow .9s ease both;}
.tw-now{display:grid;grid-template-columns:1.25fr .75fr;gap:22px;align-items:center;}
.tw-now-lab{font:700 11px/1 var(--disp);letter-spacing:.22em;color:var(--accent);}
.tw-now-block{font:700 30px/1.05 var(--disp);color:var(--ink);margin:9px 0 2px;}
.tw-now-meta{margin:8px 0 2px;}
.tw-now-time{font:700 42px/1 var(--mono);color:var(--ink);letter-spacing:-.03em;}
.tw-now-bar{height:8px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;margin:14px 0 8px;}
.tw-now-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--win));transform-origin:left;animation:tw-grow 1s ease both;}
.tw-now-next{font:500 12px/1 var(--mono);color:var(--mute);}
.tw-tl{display:flex;flex-direction:column;}
.tw-tl-item{display:grid;grid-template-columns:54px 20px 1fr;gap:12px;position:relative;padding:7px 6px;border-radius:10px;transition:.18s;}
.tw-tl-item:hover{background:rgba(255,255,255,.025);}
.tw-tl-time{text-align:right;font:600 11px/1 var(--mono);color:var(--mute);padding-top:3px;}
.tw-tl-rail{position:relative;display:flex;justify-content:center;}
.tw-tl-rail::before{content:'';position:absolute;top:0;bottom:0;width:2px;background:var(--hair);}
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
.tw-hhead,.tw-hgrid{display:grid;grid-template-columns:150px 1fr 44px;gap:6px 10px;align-items:center;}
.tw-hhead-days{display:grid;gap:3px;}
.tw-hhead-days span{font:500 8px/1 var(--mono);color:var(--mute);text-align:center;}
.tw-hrow-name{display:flex;align-items:center;gap:8px;font:600 12px/1 var(--body);color:var(--ink-2);}
.tw-hrow-ico{width:18px;height:18px;border-radius:5px;display:grid;place-items:center;font:700 10px/1 var(--mono);color:var(--accent);background:var(--accent-soft);flex:0 0 auto;}
.tw-hcells{display:grid;gap:3px;}
.tw-hcell{height:16px;border-radius:3px;border:1px solid var(--hair);background:rgba(255,255,255,.02);transition:.15s;}
.tw-hcell:hover{transform:scale(1.25);}
.tw-hcell.done{background:var(--win);border-color:transparent;opacity:.85;}
.tw-hcell.miss{background:rgba(240,85,107,.5);border-color:transparent;}
.tw-hcell.today{box-shadow:inset 0 0 0 1.5px var(--accent);}
.tw-hcell.future{opacity:.22;}
.tw-hpct{font:700 11px/1 var(--mono);text-align:right;font-variant-numeric:tabular-nums;}
.tw-goal{border:1px solid var(--hair);border-radius:12px;padding:14px 16px;background:linear-gradient(180deg,var(--panel),var(--panel-2));animation:tw-rise .5s ease both;transition:.2s;margin-bottom:10px;}
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
.tw-table thead th{font:600 10px/1 var(--disp);letter-spacing:.12em;text-transform:uppercase;color:var(--mute-2);text-align:left;padding:0 12px 10px;border-bottom:1px solid var(--hair);}
.tw-table tbody td{padding:11px 12px;border-bottom:1px solid rgba(28,39,64,.6);font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap;}
.tw-table tbody tr{transition:.15s;position:relative;}
.tw-table tbody tr:hover{background:rgba(255,255,255,.03);}
.tw-table tbody tr:hover td:first-child{box-shadow:inset 3px 0 0 var(--accent);}
.tw-table .num{font-family:var(--mono);}
.tw-stat{display:flex;justify-content:space-between;align-items:center;padding:9px 0;gap:10px;border-bottom:1px solid rgba(28,39,64,.55);}
.tw-stat:last-child{border-bottom:none;}
.tw-stat .k{font:500 12px/1 var(--body);color:var(--mute);}
.tw-stat .v{font:700 13px/1 var(--mono);font-variant-numeric:tabular-nums;text-align:right;}
.tw-empty{text-align:center;color:var(--mute-2);padding:34px 14px;font:500 13px/1.5 var(--body);border:1px dashed var(--hair);border-radius:12px;background:rgba(255,255,255,.012);}
.tw-scroll{overflow-x:auto;}
[data-testid='stSidebar']{background:linear-gradient(180deg,#0A0F1B,#070B14);border-right:1px solid var(--hair);z-index:2;}
.tw-brand{display:flex;align-items:center;gap:11px;padding:4px 6px 14px;}
.tw-brand-n{font:700 17px/1 var(--disp);letter-spacing:.06em;color:var(--ink);}
.tw-brand-s{font:600 9px/1 var(--disp);letter-spacing:.22em;color:var(--mute);margin-top:5px;}
.tw-user{display:flex;align-items:center;gap:11px;padding:12px 8px;margin-top:8px;border-top:1px solid var(--hair);}
.tw-avatar{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;font:700 13px var(--disp);color:var(--ink);background:linear-gradient(135deg,var(--accent),rgba(52,211,153,.7));}
.tw-user-n{font:600 13px/1.2 var(--body);color:var(--ink);}
.tw-user-r{font:500 11px/1.2 var(--body);color:var(--mute);margin-top:3px;}
[data-testid='stSidebar'] [data-testid='stRadio']>div{gap:2px;}
[data-testid='stSidebar'] [data-testid='stRadio'] label{display:flex;align-items:center;gap:.6rem;padding:.55rem .7rem;border-radius:9px;cursor:pointer;color:var(--mute);font:600 13px/1 var(--disp);margin:0;transition:.18s;}
[data-testid='stSidebar'] [data-testid='stRadio'] label:hover{background:rgba(255,255,255,.04);color:var(--ink);}
[data-testid='stSidebar'] [data-testid='stRadio'] label:has(input:checked){background:var(--accent-soft);color:var(--ink);box-shadow:inset 2px 0 0 var(--accent);}
[data-testid='stSidebar'] [data-testid='stRadio'] input[type='radio']{position:absolute;opacity:0;width:0;height:0;}
[data-testid='stSidebar'] [data-testid='stRadio'] label p{margin:0;}
[data-testid='stSidebar'] [data-testid='stRadio'] label>div:first-child{display:none;}
.stExpander{background:var(--panel);border:1px solid var(--hair);border-radius:12px;}
.stTabs [data-baseweb='tab-list']{gap:8px;border-bottom:1px solid var(--hair);}
.stTabs [data-baseweb='tab']{background:var(--panel);border:1px solid var(--hair);border-radius:9px 9px 0 0;color:var(--mute);font:600 12px var(--disp);padding:8px 16px;}
.stTabs [aria-selected='true']{background:var(--accent-soft);color:var(--ink);border-color:var(--accent);}
.stTabs [data-baseweb='tab-highlight']{background:var(--accent);}
.stSelectbox label,.stTextInput label,.stDateInput label,.stNumberInput label,.stTimeInput label,.stMultiSelect label,.stTextArea label{font:600 10px/1 var(--disp)!important;letter-spacing:.12em;text-transform:uppercase;color:var(--mute)!important;}
[data-baseweb='select']>div,[data-baseweb='input']>div,.stDateInput input,.stNumberInput input,.stTimeInput input,.stTextInput input,.stTextArea textarea{background:var(--panel)!important;border:1px solid var(--hair)!important;border-radius:9px!important;color:var(--ink)!important;font-family:var(--mono)!important;}
.stTextArea textarea{font-family:var(--mono)!important;font-size:12.5px!important;}
.stButton>button{background:var(--panel-2);border:1px solid var(--hair-2);color:var(--ink);border-radius:9px;font:600 12px var(--disp);transition:.18s;}
.stButton>button:hover{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);}
.stButton>button[kind='primary']{background:var(--accent);border-color:var(--accent);color:#04101f;}
hr{border-color:var(--hair)!important;}
@media (max-width:760px){
.block-container{padding-top:.7rem;padding-bottom:2rem;}
[data-testid='stHorizontalBlock']{flex-direction:column!important;gap:.6rem!important;}
[data-testid='stHorizontalBlock']>div{width:100%!important;flex:1 1 100%!important;}
.tw-tiles{grid-template-columns:repeat(2,1fr)!important;}
.tw-now{grid-template-columns:1fr!important;gap:12px;}
.tw-hhead,.tw-hgrid{grid-template-columns:96px 1fr 38px!important;}
.tw-hrow-name{font-size:10px;}
.tw-hcell{height:12px;}
.tw-day{min-height:44px;padding:4px 5px;}
.tw-day-pnl{font-size:9px;margin-top:5px;}
.tw-now-time{font-size:32px;}
.tw-now-block{font-size:22px;}
.tw-val{font-size:21px;}
.tw-greet-name{font-size:18px;}
.tw-donut-wrap{justify-content:center;}
.tw-tl-item{grid-template-columns:44px 18px 1fr;gap:8px;}
.tw-log{flex-wrap:wrap;}
.tw-log-amt{width:100%;justify-content:flex-end;}
}
/* ---- premium log rows ---- */
.tw-loglist{display:flex;flex-direction:column;gap:8px;margin-top:4px;}
.tw-loglist-mini{gap:6px;}
.tw-log{position:relative;display:flex;align-items:stretch;gap:13px;padding:11px 15px 11px 17px;border:1px solid var(--hair);border-radius:13px;background:linear-gradient(180deg,var(--panel),var(--panel-2));overflow:hidden;transition:transform .18s,border-color .18s,box-shadow .18s;animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;}
.tw-log:hover{transform:translateY(-2px);border-color:var(--hair-2);box-shadow:0 12px 28px -16px rgba(0,0,0,.85);}
.tw-log-rail{position:absolute;left:0;top:0;bottom:0;width:3px;}
.tw-log.r-in{background:linear-gradient(180deg,rgba(52,211,153,.08),var(--panel-2));}
.tw-log.r-in .tw-log-rail{background:linear-gradient(180deg,var(--win),rgba(52,211,153,.15));box-shadow:0 0 12px rgba(52,211,153,.5);}
.tw-log.r-out{background:linear-gradient(180deg,var(--out-soft),var(--panel-2));}
.tw-log.r-out .tw-log-rail{background:linear-gradient(180deg,var(--out),rgba(251,146,60,.15));box-shadow:0 0 12px rgba(251,146,60,.42);}
.tw-log.r-adj{background:linear-gradient(180deg,rgba(217,70,239,.08),var(--panel-2));}
.tw-log.r-adj .tw-log-rail{background:linear-gradient(180deg,var(--jewel),rgba(217,70,239,.15));box-shadow:0 0 12px rgba(217,70,239,.4);}
.tw-log.r-done{background:linear-gradient(180deg,rgba(52,211,153,.06),var(--panel-2));}
.tw-log.r-done .tw-log-rail{background:linear-gradient(180deg,var(--win),rgba(52,211,153,.12));box-shadow:0 0 10px rgba(52,211,153,.4);}
.tw-log.r-neutral .tw-log-rail{background:var(--hair-2);}
.tw-log-body{flex:1 1 auto;min-width:0;}
.tw-log-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:5px;}
.tw-log-main{font:600 13px/1.4 var(--body);color:var(--ink);word-break:break-word;}
.tw-log-meta{margin-top:4px;}
.tw-log-amt{flex:0 0 auto;display:flex;align-items:center;}
.tw-time{display:inline-flex;align-items:baseline;gap:6px;}
.tw-time-d{font:600 10.5px/1 var(--mono);color:var(--ink-2);letter-spacing:.04em;}
.tw-time-t{font:700 11px/1 var(--mono);color:var(--accent);letter-spacing:.06em;text-shadow:0 0 10px rgba(76,141,255,.35);}
.tw-txid{display:inline-flex;align-items:center;gap:5px;font:600 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);background:rgba(255,255,255,.03);border:1px solid var(--hair-2);border-radius:7px;padding:4px 9px;white-space:nowrap;}
.tw-txid svg{width:12px;height:12px;display:block;flex:0 0 auto;}
.tw-txid-mpesa{color:var(--mpesa);border-color:rgba(76,175,80,.5);background:var(--mpesa-soft);box-shadow:0 0 9px rgba(76,175,80,.22);font-weight:700;letter-spacing:.12em;}
.tw-kind{font:700 9px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;padding:4px 8px;border-radius:999px;border:1px solid transparent;}
.kc-in{color:var(--win);background:var(--win-soft);border-color:rgba(52,211,153,.4);box-shadow:0 0 8px rgba(52,211,153,.25);}
.kc-out{color:var(--out);background:var(--out-soft);border-color:rgba(251,146,60,.45);box-shadow:0 0 8px rgba(251,146,60,.22);}
.kc-adj{color:var(--jewel);background:rgba(217,70,239,.12);border-color:rgba(217,70,239,.4);}
.kc-done{color:var(--win);background:var(--win-soft);border-color:rgba(52,211,153,.4);}
.kc-neutral{color:var(--ink-2);background:rgba(255,255,255,.04);border-color:var(--hair);}
.tw-amt{font:700 15px/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.01em;white-space:nowrap;}
.tw-amt-pos{color:var(--win);text-shadow:0 0 12px rgba(52,211,153,.35);}
.tw-amt-neg{color:var(--out);text-shadow:0 0 12px rgba(251,146,60,.32);}
.tw-amt-flat{color:var(--ink);text-shadow:0 0 10px rgba(232,237,247,.16);}
.tw-pocket{font:600 10px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute);}
.tw-cl{font:600 12px/1.3 var(--body);color:var(--ink-2);padding-top:8px;}
.tw-cl a{color:var(--accent);text-decoration:none;border-bottom:1px dashed rgba(76,141,255,.45);}
.tw-cl a:hover{color:var(--ink);border-bottom-color:var(--accent);}
.tw-pri{font:700 8.5px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;padding:3px 7px;border-radius:6px;border:1px solid var(--hair);}
.pr-h{color:var(--loss);border-color:rgba(240,85,107,.4);background:var(--loss-soft);}
.pr-n{color:var(--ink-2);}
.pr-l{color:var(--mute);}
.tw-check-glyph{color:var(--win);font-size:16px;line-height:1;text-shadow:0 0 10px rgba(52,211,153,.5);}
.tw-kvlist{display:flex;flex-direction:column;}
.tw-kv{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 0 8px 11px;position:relative;border-bottom:1px solid rgba(28,39,64,.5);}
.tw-kv:last-child{border-bottom:none;}
.tw-kv::before{content:'';position:absolute;left:0;top:50%;transform:translateY(-50%);width:3px;height:13px;border-radius:2px;background:var(--accent-soft);}
.tw-kv-k{font:600 10px/1.2 var(--disp);letter-spacing:.12em;text-transform:uppercase;color:var(--mute);}
.tw-kv-v{font:700 12.5px/1.3 var(--mono);color:var(--ink);font-variant-numeric:tabular-nums;text-align:right;}
.tw-card-premium{position:relative;border:1px solid var(--hair);border-radius:14px;padding:14px 16px;background:linear-gradient(180deg,var(--panel),var(--panel-2));overflow:hidden;transition:transform .2s,border-color .2s,box-shadow .2s;animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;margin-bottom:10px;}
.tw-card-premium::before{content:'';position:absolute;left:0;top:0;right:0;height:2px;background:linear-gradient(90deg,var(--card-accent,var(--accent)),transparent 72%);}
.tw-card-premium:hover{transform:translateY(-2px);border-color:var(--hair-2);box-shadow:0 14px 32px -18px rgba(0,0,0,.85);}
.tw-cp-top{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:7px;}
.tw-cp-name{font:700 15px/1.2 var(--disp);color:var(--ink);}
.tw-cp-date{font:700 11px/1 var(--mono);letter-spacing:.08em;color:var(--ink-2);}
.tw-cp-chips{display:inline-flex;gap:6px;flex-wrap:wrap;align-items:center;}
.tw-cp-meta{font:600 11px/1.3 var(--mono);color:var(--mute);margin-bottom:9px;}
.tw-moodpill{font:700 9px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;border:1px solid;border-radius:999px;padding:4px 9px;}
.tw-mem{position:relative;display:flex;gap:11px;padding:7px 0 7px 4px;}
.tw-mem::before{content:'';position:absolute;left:8px;top:0;bottom:0;width:2px;background:var(--hair);}
.tw-mem-dot{position:relative;z-index:1;flex:0 0 auto;width:9px;height:9px;border-radius:50%;margin-top:4px;background:var(--accent);box-shadow:0 0 9px rgba(76,141,255,.6);}
.tw-mem-body{flex:1 1 auto;min-width:0;}
.tw-mem-ts{font:600 10px/1 var(--mono);color:var(--ink-2);letter-spacing:.04em;display:flex;align-items:center;gap:7px;flex-wrap:wrap;}
.tw-mem-nt{font:500 12.5px/1.45 var(--body);color:var(--ink);margin-top:4px;word-break:break-word;}
/* ---- pantry ---- */
@keyframes tw-pulsered{0%{box-shadow:0 0 0 0 rgba(240,85,107,.5);}70%{box-shadow:0 0 0 7px rgba(240,85,107,0);}100%{box-shadow:0 0 0 0 rgba(240,85,107,0);}}
.tw-pantry{position:relative;border:1px solid var(--hair);border-radius:13px;padding:12px 15px;margin-bottom:9px;background:linear-gradient(180deg,var(--panel),var(--panel-2));overflow:hidden;transition:transform .18s,border-color .18s,box-shadow .18s;animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;}
.tw-pantry::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,var(--accent),rgba(76,141,255,.15));}
.tw-pantry:hover{transform:translateY(-2px);border-color:var(--hair-2);box-shadow:0 12px 28px -16px rgba(0,0,0,.85);}
.tw-pantry-top{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:9px;}
.tw-pantry-name{font:700 14px/1.2 var(--disp);color:var(--ink);}
.tw-pantry-chips{display:inline-flex;gap:6px;flex-wrap:wrap;}
.tw-cat{font:700 9px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border-radius:999px;}
.tw-opt{font:700 9px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border-radius:999px;color:var(--mute);background:rgba(255,255,255,.04);border:1px solid var(--hair);}
.tw-pantry-mid{display:flex;align-items:center;gap:14px;}
.tw-pantry-days{font:700 30px/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.02em;min-width:74px;}
.tw-pantry-days-u{font:600 11px/1 var(--mono);color:var(--mute);margin-left:5px;letter-spacing:.08em;text-transform:uppercase;}
.tw-pantry-days.tw-low{animation:tw-pulsered 1.8s infinite;}
.tw-shelf{flex:1 1 auto;height:9px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;}
.tw-shelf-fill{height:100%;border-radius:5px;transform-origin:left;animation:tw-grow .9s ease both;}
.tw-pantry-meta{display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font:600 11px/1.3 var(--mono);color:var(--ink-2);}
.tw-pantry-note{margin-top:5px;font:600 10.5px/1.3 var(--mono);color:var(--mute);}
.tw-aged{color:var(--mute);}
/* ---- spirit ---- */
.tw-depth{font:700 12px/1 var(--mono);color:var(--win);letter-spacing:1px;}
.tw-depth-off{color:var(--hair-2);}
.tw-energy{font:700 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;}
.tw-spirit-mins{font:600 12px/1.3 var(--mono);color:var(--ink-2);margin:2px 0 8px;}
.tw-word{font:500 13px/1.5 var(--body);color:var(--ink);font-style:italic;margin:6px 0;border-left:2px solid var(--card-accent,var(--accent));padding-left:10px;}
.tw-felt{font:500 12.5px/1.5 var(--body);color:var(--ink-2);margin:6px 0;}
.tw-grat{font:600 11px/1.4 var(--mono);color:var(--win);margin-top:6px;}
.tw-acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;}
.tw-act{font:700 9px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:3px 8px;border-radius:999px;color:var(--jewel);background:rgba(217,70,239,.12);border:1px solid rgba(217,70,239,.35);}
"""
