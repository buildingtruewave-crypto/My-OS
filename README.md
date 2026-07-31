# PULSE - Life Command Center

A self-hosted life operating system for one operator in Nairobi - a strong
heart that pumps every part of the day. The routine is the spine, the habit
wall the heartbeat, TrueWave the engine, the Vault the blood. Recording
begins **Friday 1 August 2026**; the app ships with zero fake figures and
every write persists to `data/*.json` instantly.

## Privacy: where the money lives
Your balances, net worth, assets, liabilities and ventures live **only**
inside the **Archive (vault)**, behind a fixed access code. The dashboard,
the journal and the stats page show *activity and expected money* -
commissions due, commissions pending, income that flowed in, phones sold -
**never** a balance. So a glance at the screen tells someone how the week is
going, not how much you have.

The vault access code is the constant `ARCHIVE_PIN` in `src/data.py`
(default `0444`). It is **not** stored in prefs, **not** shown in Settings,
and **not** changeable from the UI - so nobody at the screen can read it.
To change it, edit that one line in the source.

## Net worth - no cataloguing required
You never type a net-worth number, and you don't list every possession.
Inside the vault, net worth is *computed* as the sum of the money you
actually move: cash pockets (wallet / M-Pesa / bank) + saved-against-bills
+ remaining fun budget + wishlist savings + venture balances. It re-totals
on every entry and draws "The Climb". Add a real-world asset only if you
want it counted, as an optional pocket or venture.

## The conversion pipeline is a setting, not code
On the **TrueWave** page, the *Configure my conversion pipeline & plans*
panel lets you rename / recolor / reorder / add stages, mark the linear
path, and tag the five roles the engine needs (won / lost / cash /
delivered / returned - one each). Change business, keep the machine.

## The Vault tabs
Cash (pockets) - Daily Flow (every shilling) - Bills (saved vs needed +
due) - Fun (budget without guilt) - Wishlist (save in / pull out) -
Ventures (HHO + any other, growing in the background).

## Money rules
Commissions auto-due at **+20 / +50 days**, editable inside the window and
locked after. Income ledger covers Commission, Bonus, DRV Streamlit, Stock
Streamlit, Gift, Other.

## Everything else
Routine (weekday/Sat/Sun) - Tasks - Journal (auto Day Pulse) - Habits +
weigh-ins - Bots (Deriv/Alpaca risk-reward, demo->LIVE) - Goals + Issues -
Stats (weekly/monthly review).

## Quick start
    pip install -r requirements.txt
    streamlit run app.py

VPS: `docker compose up -d` (the `./data` volume is the memory).
Phone: same URL - everything stacks under 760px. Time: Africa/Nairobi.
