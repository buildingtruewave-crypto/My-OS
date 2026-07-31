# PULSE - Life Command Center

A self-hosted life operating system built with Streamlit. It does not track one
thing - it tracks your day. The schedule is the spine, the habit wall is the
heartbeat, and trading is just one of nine panels. The whole thing wears a
single design language borrowed from a trading terminal: cold canvas, monospaced
tabular figures, mint = done / coral = missed / blue = the live spine, and a
signed-day grid that turns consistency into something you can see.

Design rule: colour encodes outcome, never decoration. The routine is the data
model - change it and every page re-orients.

## What it controls

- Now: live right-now block, today timeline, today habits, goals, trading, last reflection
- Routine: weekday-aware schedule, paste-your-routine parser, per-day timelines
- Habits: 35-day consistency wall, today checklist, 30-day completion bars
- Trading: KPIs, equity curve, monthly PnL, recent trades, signed-day calendar
- Goals: quarterly targets with progress bars
- Tasks: today list with priorities, areas, due dates
- Journal: daily gratitude / win / lesson / mood
- Stats: life score, streaks, consistency by weekday, habit outcomes
- Settings: name, accent, clock offset, regenerate, export zip, deploy info

## The routine format

Every block is one line. The Routine page parses this directly:

    05:00  Wake - hydrate - light        #Body      @all
    07:45  Pre-market analysis - levels  #Trade     @weekdays
    08:00  London open - execution       #Trade     @weekdays
    12:00  Lunch - no screens            #Rest      @all
    18:30  Dinner - family               #Life      @all

Tags (#Trade #Body #Mind #Life #Rest #Focus) drive chip colours; scopes
(@weekdays @weekend @all or @mon,wed,fri) decide which days a block shows.

## Quick start

    pip install -r requirements.txt
    streamlit run app.py

Data is generated relative to today at first run, so streaks always look
current. Everything you edit is saved to data/*.json and data/trades.csv.

## Project layout

    app.py                 entry point + context + top bar
    src/data.py            seed, parse, persist, export
    src/metrics.py         all derived stats
    src/theme.py           the whole design language (CSS)
    src/ui.py              HTML / SVG components
    src/widgets.py         interactive checkboxes that write back
    src/pages/*.py         the nine panels
    deploy/                systemd unit + nginx config
    Dockerfile / compose   one-command VPS deploy

## Persistence and moving to a VPS

On Streamlit Cloud the data/ writes are ephemeral - fine for a demo; use
Settings -> Export all (.zip) to carry your life between hosts.

On a VPS the data/ folder is real and persistent:

    docker compose up -d --build

or bare metal:

    python -m venv venv && venv/bin/pip install -r requirements.txt
    sudo cp deploy/pulse.service /etc/systemd/system/
    sudo systemctl enable --now pulse
    sudo cp deploy/nginx.conf /etc/nginx/sites-available/pulse

The design lives entirely in client-side CSS, so the migration is a deploy
change, never a rewrite.

## Design language

- Type: Space Grotesk (display), Manrope (body), JetBrains Mono (figures, tabular)
- Motion (pure CSS): equity line draw-in, staggered panel rise, pulsing live
  dot and active timeline node, growing bars, hover lifts
- Ambient field: faint terminal grid plus drifting semantic glows
- Palette: #070B14 canvas, #34D399 done, #F0556B missed, #4C8DFF spine

## License

MIT - see LICENSE.
