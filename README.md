# PULSE - Life Command Center

A self-hosted life operating system for one operator in Nairobi - a strong
heart that pumps every part of the day. The schedule is the spine, the habit
wall the heartbeat, TrueWave the engine, the Vault the blood, and Spirit the
soul. The whole thing wears one design language: cold canvas, monospaced
tabular figures, monochrome line-icons in tinted chips, mint = done / coral =
missed / orange = money out / blue = the live spine / green = M-Pesa, and a
signed-day grid that turns consistency into something you can see.

Design rule: colour encodes outcome, never decoration. The routine is the
data model - change it and every page re-orients. Nothing is auto-deducted;
every figure is a real, timed, manual entry, and derived numbers (food days,
runway, emergency %, spiritual energy) are computed from what you log.

## What it controls
- Now: dashboard - KPIs, glowing consistency trend, live right-now card,
  pipeline + income mix, consistency calendar, today summary (with Spirit),
  call sheet, streaks (incl. spirit), commissions, vault teaser, habit tick.
- Routine: KPI strip, today timeline, 7-day grid, paste-your-routine editor.
- TrueWave: live call sheet, full client journey, editable pipeline + plans,
  bulk CSV import, master table with Outcome column.
- Sales: end-of-day tally, commissions (auto +20/+50, locked after, paid
  drops cash into a pocket live), income ledger (optional pocket drop).
- Tasks: open/done/overdue, premium "recently cleared" feed, add.
- Journal: auto Day Pulse from every module (incl. spiritual energy), write
  the day, premium mood-accented cards.
- Spirit: minutes with God, the word, what you feel, acts of devotion,
  gratitude, depth 1-5 -> derived Spiritual Energy (deterministic), 30-day
  pulse, streak, recent cards.
- Habits: 35-day wall, today checklist, 30-day bars, weigh-ins + trend.
- Bots: Deriv/Alpaca + any venture, risk/reward, demo->LIVE, weekly bars.
- Goals: on-track/at-risk/done, progress cards, Issues & Fixes.
- Stats: life score, streaks, spiritual pulse, consistency trend + weekday,
  week sales, pipeline, income by source, ventures, truewave+spirit kv.
- Archive (locked, code in source): net worth climb, food security / cash
  runway / emergency tiles, Cash pockets, Daily Flow (exact minute + txid,
  M-Pesa green), Bills, Fun, Wishlist, Ventures, Pantry (manual stock,
  aged days-left, bottleneck), Runway + emergency ring-fence + ratchet.
- Settings: name, accent, clock offset, JSON + CSV export, restore, wipe.

## The routine format
Every block is one line. The Routine page parses this directly:
06:00  Wake up                 #Life   @weekdays
09:30  Arrive - post drafts    #Content @weekdays
12:00  TikTok Live + calls     #Content @weekdays
Tags (#Content #Sales #Body #Mind #Life #Rest #Focus) drive chip colours;
scopes (@weekdays @sat @sun @weekend @all or @mon,wed,fri) pick the days.

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

VPS: `docker compose up -d` (the `./data` volume is the memory).
Phone: same URL - everything stacks under 760px. Time: Africa/Nairobi.
The vault access code is the constant ARCHIVE_PIN in src/data.py.
