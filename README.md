# PULSE - Life Command Center (TrueWave edition)

A self-hosted life operating system for one operator in Nairobi. The routine
is the spine, the habit wall is the heartbeat, TrueWave is the engine, and
everything broadcasts onto one dashboard. Recording begins **Friday 1 August
2026** - the app ships with zero fake figures; every number is hand-entered
from day one, and every write lands in `data/*.json` instantly, so the system
never forgets (and on a VPS it survives reboots too).

## The TrueWave journey (full memory, per client)
New Lead -> Called (no pickup / picked / declined) -> Application Started ->
M-Pesa Review (qualified phones) -> Plan Selection (**Standard 12mo**,
**Lite 12mo** - lower weekly, slightly higher total, **Saver 6mo** - higher
deposit + higher weekly) -> Docs (ID card / clear selfie / next of kin, each
marked passed or **which one failed**) -> strict **Credit Team Call**
(outcomes: APPROVED, **CASH OFFER - CREDIT**, PLAN CHANGE, DECLINED) ->
Deposit & Delivery (accept / decline) -> Delivered with a **7-day return
window** (auto-counted; mark Returned or Paid; window closes itself after a
week) -> Paid & Closed.
Every touch is timestamped in the client's memory log, every client is
searchable by name / number / model / remark / next action and filterable by
stage, and follow-ups surface on the dashboard on their exact day.

## Money rules
- Commissions: 1st due automatically at **+20 days**, 2nd at **+50 days**
  from delivery - editable inside the window, **locked after**, so slipping
  money is visible as red LOCKED rows.
- Income ledger: Commission, Bonus, **DRV Streamlit**, **Stock Streamlit**,
  Gift, Other - everything logged with a note.
- Archive (hidden behind PIN, default **2580**): HHO Carbon Cleaning fund
  (KSh 150k-200k by Jan 2027), savings buckets, wishlist, and the **daily
  flow book** (money in / out, from where, what you got).

## Pages
Now (dashboard) - Routine (weekday/Sat/Sun) - TrueWave (CRM) - Sales
(tally + commissions + income) - Tasks - Journal (auto Day Pulse from every
module) - Habits (+ weigh-ins) - Bots (Deriv/Alpaca risk-reward, demo->LIVE)
- Goals (+ Issues & Fixes) - Stats (weekly/monthly review) - Archive
(hidden vault) - Settings.

## Performance
Built for years of daily use: the board renders the 60 most urgent clients,
memory timelines the last 15 touches, ledgers the last 20 rows; search and
the stage filter narrow everything else. All stats are light passes over
JSON.

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

VPS: `docker compose up -d` (the `./data` volume is the memory).
Phone: open the same URL - everything stacks cleanly under 760px.
Time: Africa/Nairobi everywhere. Change the Archive PIN in Settings.
