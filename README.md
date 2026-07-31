# ◉ PULSE — Life Command Center

A self‑hosted **life operating system** built with Streamlit. It does not track
one thing — it tracks *your day*. The schedule is the spine, the habit wall is
the heartbeat, and trading is just one of nine panels. The whole thing wears a
single design language borrowed from a trading terminal: cold canvas, monospaced
tabular figures, mint = done / coral = missed / blue = the live spine, and a
signed‑day grid that turns consistency into something you can *see*.

> **Design rule:** colour encodes outcome, never decoration. The routine is the
> data model — change it and every page re‑orients.

---

## What it controls

| Panel | Purpose |
|---|---|
| **Now** | Live "right now" block, today's timeline, today's habits, goals, trading, last reflection |
| **Routine** | Weekday‑aware schedule; paste‑your‑routine parser; per‑day timelines |
| **Habits** | 35‑day consistency wall, today's checklist, 30‑day completion bars |
| **Trading** | KPIs, equity curve, monthly PnL, recent trades, signed‑day calendar |
| **Goals** | Quarterly targets with progress bars |
| **Tasks** | Today's list with priorities, areas, due dates |
| **Journal** | Daily gratitude / win / lesson / mood |
| **Stats** | Life score, streaks, consistency by weekday, habit outcomes |
| **Settings** | Name, accent, clock offset, regenerate, export `.zip`, deploy info |

## The routine format

Every block is one line. The **Routine** page parses this directly, so you can
paste your real day in once:
