# PULSE - Life Command Center

A self-hosted life operating system for one operator in Nairobi - a strong
heart that pumps every part of the day. The routine is the spine, the habit
wall the heartbeat, TrueWave the engine, the Vault the blood. Recording
begins **Friday 1 August 2026**; the app ships with zero fake figures and
every write persists to `data/*.json` instantly.

## Privacy: where the money lives
Your balances, net worth, assets, liabilities and ventures live **only**
inside the **Archive (vault)**, behind a fixed access code (`ARCHIVE_PIN` in
`src/data.py`, default `0444`). It is **not** stored in prefs, **not** shown
in Settings, and **not** changeable from the UI - so the screen can't leak it.
The dashboard, journal and stats show *activity and expected money* (commissions
due / pending, income flow, counts) - **never** a balance.

## Money is live and connected (one writer)
Every shilling moves through `move_money()`. The **Daily Flow** tab is the live
ledger: pick a pocket (Wallet / M-Pesa / Bank / any you add), in or out, the
amount, **the time**, **a transaction id** for online transfers, and a note -
and the pocket balance changes on save, net worth recomputes, and a snapshot is
taken. 'Out' is stored as a negative, so the ledger shows `-KSh 500` in red,
not a positive number in red. The **Cash** tab is a balance dashboard +
**Reconcile** (writes an `ADJ` line so the ledger can explain the jump).
Marking a commission **paid** drops that cash into a chosen pocket (live), and
an income entry can optionally land in a pocket too - so collected money
actually shows up in your wallet. Commissions auto-due at **+20 / +50 days**
and lock after the window.

## Backups that actually restore
Settings has **Download JSON backup** (full round-trip), **Download CSVs**
(clients / flow / sales / income / tasks, for spreadsheets), and a **Restore
from backup** uploader - so your weekly download is what you re-ingest on a
brand-new deploy and everything since 1 Aug 2026 returns. TrueWave also has
**bulk-import clients from CSV** (drop your ad-leads export straight in).
Logs (client memory, money flow, net-worth snapshots) are **append-only and
never auto-deleted**.

## The conversion pipeline is a setting, not code
On the **TrueWave** page, the *Configure my conversion pipeline & plans* panel
lets you rename / recolor / reorder / add stages, mark the linear path, and tag
the five roles the engine needs (won / lost / cash / delivered / returned - one
each). Terminal clients carry an **Outcome** line + column showing where their
journey ended.

## Everything else
Now (dashboard) - Routine (today's timeline now sits under the KPI strip) -
Tasks - Journal (auto Day Pulse) - Habits + weigh-ins - Bots (Deriv/Alpaca
risk-reward, demo->LIVE) - Goals + Issues - Stats (weekly/monthly review).

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

VPS: `docker compose up -d` (the `./data` volume is the memory).
Phone: same URL - everything stacks under 760px. Time: Africa/Nairobi.
