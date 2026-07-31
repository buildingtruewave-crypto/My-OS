# PULSE - Life Command Center (TrueWave edition)

A self-hosted life operating system built with Streamlit for one operator in
Nairobi. The routine is the spine, the habit wall is the heartbeat, TrueWave
(the phone business) is the engine, and everything broadcasts onto one
dashboard. Recording begins **Friday 1 August 2026** - the app ships with zero
fake figures; every number is entered by hand from day one.

## Time
Africa/Nairobi (EAT, UTC+3) everywhere - the live clock, the Right Now card,
streaks and due dates all run on Nairobi time.

## The days
- **Weekdays**: 6am wake - coffee - teeth - clothes - mop - shower - commute.
  9:30 arrive: post TikTok drafts, schedule FB + IG till 12, stories + DMs
  through the 10:30 tea. 12-1 TikTok Live with lunch calls. Afternoon: urgent
  buyer calls first, every postponed client logged with a date + remark +
  reason. Schedule tomorrow's TikToks, bus 4:30-5, home ~6:30, blunt + music,
  workout 8:00-8:45, shower, free till 9, sleep at 10.
- **Saturday**: breakfast, music, beddings, house, then work from anywhere -
  same content + calls routine, no TikTok Live, home 5-6pm.
- **Sunday**: free.
Edit any of it on the Routine page (`HH:MM  Label  #Tag  @weekdays|@sat|@sun`).

## Pages
- **Now** - KPIs, glowing consistency spine, live Right Now card, follow-ups
  promised yesterday + today, commissions due this week, weight, fixes, vault
  progress, habit checklist, today's rhythm.
- **Routine** - week grid, today timeline, paste-to-edit routine.
- **TrueWave** - client pipeline: name, number, what they want, promised date,
  remark, why-not-today; mark Sold / Reschedule / Rejected-system /
  Rejected-cash-only. Nothing falls through.
- **Sales** - end-of-day tally (sold, system rejects, cash-only rejects) and
  per-phone commission instalments with due dates, paid / reason-unpaid.
- **Journal** - the Day Pulse is picked up automatically (new clients,
  follow-ups, tally, commissions, bot runs, weigh-in) - you just write the day.
- **Habits** - consistency wall + weigh-ins with a trend line.
- **Bots** - Deriv + Alpaca (and any venture): daily risk + result, win rate,
  reward:risk, demo → LIVE transition, weekly bars.
- **Goals** - targets + Issues & Fixes with due dates.
- **Stats** - the weekly / monthly review across everything.
- **Archive** - the hidden money manager (PIN, default **2580**): HHO Carbon
  Cleaning fund (KSh 150k-200k by Jan 2027) with daily in/out + source,
  savings buckets (Household / Enjoyment / Emergency), items you're saving to
  buy. Amounts never appear on public pages.
- **Settings** - name, accent, PIN, clock offset, export, wipe.

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

## Persistence
Everything writes to `data/*.json`. On a VPS that folder is real - mount it
(`docker compose up -d`) and a reboot loses nothing. On Streamlit Cloud the
disk is ephemeral, so use Settings → Export all (.zip) to carry your life.

## Phone
Open the same URL on your phone - every row stacks to a single column under
760px and the grids tighten automatically.

## Design language
Space Grotesk / Manrope / JetBrains Mono. Colour encodes outcome, never
decoration: mint = done, coral = missed, blue = the live spine.
