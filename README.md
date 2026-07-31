# PULSE - Life Command Center

A self-hosted life operating system for one operator in Nairobi - a strong
heart that pumps every part of the day: the routine is the spine, the habit
wall the heartbeat, TrueWave the engine, and the Vault the blood. Recording
begins **Friday 1 August 2026**; the app ships with zero fake figures, every
number hand-entered, every write persisted to `data/*.json` instantly.

## The TrueWave journey (total memory, per client)
New Lead -> Called (no pickup / picked / declined) -> Application ->
M-Pesa Review (qualified phones) -> Plan (**Standard 12mo**, **Lite 12mo**
lower weekly, **Saver 6mo** higher deposit) -> Docs (ID / selfie / next of
kin, each passed or failed) -> strict Credit Call (APPROVED /
**CASH OFFER - CREDIT** / PLAN CHANGE / DECLINED) -> Deposit & Delivery ->
7-day return window -> Paid & Closed. The page opens with a live Call Sheet
(hottest first), every touch is timestamped, every client searchable.

## The Vault (hidden, PIN default 2580)
Not one business - your whole money life. Cash positions (wallet / M-Pesa /
bank), every shilling of daily flow, bills with saved-vs-needed and due
dates, a fun budget, a wishlist you can save into and pull back out of, and
ventures (HHO is one of many). Net worth is snapshotted on every move, so
the climb is visible day by day.

## Money rules
Commissions auto-due at **+20 / +50 days**, editable inside the window and
**locked after**. Income ledger covers Commission, Bonus, DRV Streamlit,
Stock Streamlit, Gift, Other.

## Everything else
Routine (weekday/Sat/Sun) - Tasks - Journal (auto Day Pulse from every
module, including net worth) - Habits + weigh-ins - Bots (Deriv/Alpaca
risk-reward, demo->LIVE) - Goals + Issues - Stats (weekly/monthly review).

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

VPS: `docker compose up -d` (the `./data` volume is the memory).
Phone: same URL - everything stacks under 760px. Time: Africa/Nairobi.
