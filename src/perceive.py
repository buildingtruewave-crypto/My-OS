"""Page-aware, LIVE perception for the PULSE companion.

Pure functions (no Streamlit, no session, no network). They turn the current
packet plus a per-page live-stats dict into a perception that is anchored to
the clock and distinct per page:

  * moment  - a LIVE eyebrow that ALWAYS carries HH:MM plus a page-flavoured
              clause and the routine block % through, so liveness is verifiable
              against the phone clock to the minute.
  * line    - a STATE fact unique to the page (different angle from the spoken
              voice line, so the two never read the same).
  * alt     - a secondary state fact (for anti-repetition).
  * pulse   - a 7-day relationship line; on Now it leads with blocks behind /
              ahead so it tracks the day's progress.
  * nudge   - the single smallest next physical action, page-tuned.
  * breath / sat - per-page breathing rhythm + mood saturation.

Every layer reads a different angle of the same live state, so no two pages
read the same and no layer repeats another. Everything is guarded so a fault
returns empty strings, never an exception.
"""
from __future__ import annotations


def perceive(pkt, voice, page_stats, allow_money):
    try:
        pkt = pkt or {}
        ps = pkt.get("_ps") or page_stats or {}
        live = pkt.get("_live") or ps.get("live") or {}
        mb = pkt.get("mood_band", "none")
        try:
            hour = int(pkt.get("hour", 12))
        except Exception:
            hour = 12
        breath = {"spirit": 7.0, "vault": 5.0, "sales": 3.4, "now": 5.0,
                  "morning": 5.0, "journal": 5.6, "body": 4.2,
                  "focus": 4.0, "review": 5.2,
                  "quiet": 6.5}.get(voice, 5.0)
        if mb == "low":
            sat = 0.7
        elif mb == "high":
            sat = 1.15
        else:
            sat = 1.0
        line, alt = _perceive_lines(voice, pkt, ps)
        moment = _moment_for(voice, hour, live, ps, pkt)
        pulse = _page_pulse(voice, ps, pkt)
        nudge = _nudge_for(voice, pkt, ps, live)
        return {
            "moment": moment, "line": line, "alt": alt,
            "pulse": pulse, "nudge": nudge,
            "breath": breath, "sat": sat,
        }
    except Exception:
        return {"moment": "", "line": "", "alt": "", "pulse": "",
                "nudge": "", "breath": 5.0, "sat": 1.0}


# ---------------------------------------------------------------------------
# moment (LIVE eyebrow - always carries HH:MM)
# ---------------------------------------------------------------------------

def _moment_for(voice, hour, live, ps, pkt):
    try:
        hour = int(hour)
    except Exception:
        hour = 12
    hm = live.get("now_hm", "--:--")
    cur = live.get("cur_label", "")
    nxt = live.get("nxt_label", "")
    nt = live.get("nxt_time", "")
    prog = int((live.get("prog") or 0) * 100)

    def _with(rest):
        return "LIVE · " + str(hm) + " · " + rest

    if voice in ("now", "morning"):
        if cur:
            return _with("in " + cur + " now · " + str(prog)
                         + "% through · next " + (nxt or "wind-down")
                         + (" at " + nt if nt else ""))
        if nxt:
            return _with("before your first block · next " + nxt
                         + (" at " + nt if nt else ""))
        if live.get("has_blocks") is False:
            return _with("the clock is yours right now")
        return _with("the page is open · one true move")
    if voice in ("sales", "TrueWave"):
        due = ps.get("due", 0) or pkt.get("clients_due_n", 0)
        clause = "the pipe holds " + str(due) + " thread(s)"
        if cur:
            clause = "in " + cur + " · " + clause
        return _with(clause)
    if voice == "spirit":
        if hour < 9:
            return _with("first light · silence lands deepest here")
        if hour >= 20:
            return _with("evening stillness · a short sit closes it")
        return _with("the quiet is open")
    if voice == "journal":
        if hour >= 21:
            return _with("end of day · one honest line before sleep")
        if hour < 8:
            return _with("morning pages · the mind is quietest now")
        return _with("the page is open")
    if voice == "body":
        curl = (cur or "").lower()
        nxtl = (nxt or "").lower()
        if "workout" in curl:
            return _with("in the workout block now · "
                         + str(prog) + "% through")
        if "workout" in nxtl:
            return _with("workout block at " + (nt or "--:--"))
        if 20 <= hour < 21:
            return _with("8-8:45pm · movement, then the shower")
        if 5 <= hour < 7:
            return _with("morning mobility · small beats heroic")
        return _with("the body is yours right now")
    if voice == "focus":
        if 13 <= hour < 15:
            return _with("deep-work window · one tab, 25 minutes")
        return _with("the quiet is for building")
    if voice == "review":
        return _with("the week in one look")
    if voice == "money":
        days = ps.get("days")
        try:
            days = int(days)
        except Exception:
            days = 99
        bo = ps.get("bo", 0)
        if days <= 7 or bo:
            return _with("the books are open · mind the basics")
        return _with("the books are open · calm to plan")
    return _with("the companion is listening")


# ---------------------------------------------------------------------------
# notice (STATE fact, distinct from the spoken voice line)
# ---------------------------------------------------------------------------

def _perceive_lines(voice, pkt, ps):
    if voice in ("now", "morning"):
        done = pkt.get("habits_done", 0)
        total = pkt.get("habits_total", 0)
        due = ps.get("due", 0) or pkt.get("clients_due_n", 0)
        passed = (ps.get("live") or {}).get("passed_habit", "")
        if total:
            line = ("Wall today: " + str(done) + "/" + str(total)
                    + " habits ticked.")
        elif due > 0:
            line = str(due) + " client(s) waiting in the pipe."
        else:
            line = "The page is clean - the next block is yours."
        if passed:
            alt = ("You let " + passed
                   + " slip earlier - log it or release it, no guilt.")
        elif due > 0:
            alt = str(due) + " follow-up(s) due - revenue in your phone."
        else:
            alt = "One true move and the day takes shape."
        return line, alt
    if voice in ("sales", "TrueWave"):
        yest = ps.get("yest", 0)
        over = ps.get("over", 0) or pkt.get("clients_overdue_n", 0)
        due = ps.get("due", 0) or pkt.get("clients_due_n", 0)
        line = ("Yesterday " + str(yest) + " closed · " + str(due)
                + " waiting · " + str(over) + " gone quiet.")
        alt = ("Pipe health: " + str(due + over) + " open thread(s) "
               "to work.")
        return line, alt
    if voice == "spirit":
        sst = ps.get("sat_streak", 0) or pkt.get("spirit_streak", 0)
        sat = ps.get("sat_today", False)
        lw = ps.get("last_word", "") or pkt.get("spirit_today_word", "")
        if sst > 1 and sat:
            line = "Sitting " + str(sst) + " day(s) in a row."
        elif not sat:
            line = "Not sat yet today."
        else:
            line = "You're in the quiet now."
        if lw:
            alt = "Last word held: '" + lw + "'."
        else:
            alt = "The quiet is open - five minutes is the whole ask."
        return line, alt
    if voice == "journal":
        jst = pkt.get("journal_streak", 0)
        jt = ps.get("j_today", False)
        ll = ps.get("last_lesson", "")
        if jst > 0:
            line = "Journal streak " + str(jst) + " day(s)."
        else:
            line = "No streak yet - today starts it."
        if ll:
            alt = "Yesterday's lesson: '" + ll + "'."
        else:
            alt = "The page is where the days stop slipping."
        return line, alt
    if voice == "body":
        ws = pkt.get("workout_streak", 0)
        delta = ps.get("delta", "")
        if ws > 0:
            line = "Movement streak " + str(ws) + " day(s)."
        else:
            line = "No movement streak running."
        if delta:
            alt = "Scale " + delta + " - a trend, not a verdict."
        else:
            alt = "Treat the body like the asset it is."
        return line, alt
    if voice == "focus":
        over = ps.get("overdue", 0)
        due = ps.get("due_t", 0)
        cleared = ps.get("cleared_days_7", 0)
        if over or due:
            line = (str(over) + " overdue · " + str(due)
                    + " due today.")
        else:
            line = ("Cleared tasks on " + str(cleared)
                    + " of the last 7 days.")
        alt = ("Protect one deep block; compounding is invisible "
               "until it isn't.")
        return line, alt
    if voice == "review":
        c = pkt.get("consistency7", 0)
        sw = pkt.get("sales_week", 0)
        sh = pkt.get("spirit_health", 0)
        line = ("Consistency " + str(c) + "% · " + str(sw)
                + " closed · spirit " + str(sh) + "%.")
        alt = "Feed the lowest one this week."
        return line, alt
    if voice == "money":
        days = ps.get("days")
        try:
            days = int(days)
        except Exception:
            days = 99
        bo = ps.get("bo", 0)
        name = ps.get("name", "") or "the staple"
        rm = pkt.get("runway_months")
        if days <= 7 or bo:
            line = (name + " " + str(days) + "d on the shelf · "
                    + str(bo) + " bill(s) overdue.")
        elif rm is not None:
            line = ("Shelves covered · runway "
                    + format(float(rm), ".1f") + " months.")
        else:
            line = "Shelves covered."
        alt = "Move a little into the ring-fence while it's calm."
        return line, alt
    line = "The companion is listening."
    alt = "Tune me below; I learn from what you do after I speak."
    return line, alt


# ---------------------------------------------------------------------------
# pulse (7-day relationship; Now leads with live day progress)
# ---------------------------------------------------------------------------

def _page_pulse(voice, ps, pkt):
    try:
        if voice in ("now", "morning"):
            live = ps.get("live") or pkt.get("_live") or {}
            if live.get("has_blocks"):
                pn = int(live.get("passed_n", 0) or 0)
                ah = int(live.get("ahead", 0) or 0)
                return (str(pn) + " block(s) behind you, " + str(ah)
                        + " ahead - the day is moving.")
            j = int(ps.get("j_days_7", 0) or 0)
            s = int(ps.get("sat_days_7", 0) or 0)
            m = int(ps.get("move_days_7", 0) or 0)
            parts = []
            if j > 0:
                parts.append(str(j) + " wrote")
            if s > 0:
                parts.append(str(s) + " sat")
            if m > 0:
                parts.append(str(m) + " moved")
            if parts:
                return "Last 7 days: " + ", ".join(parts) + "."
            return ""
        if voice in ("sales", "TrueWave"):
            x = int(ps.get("sold_days_7", 0) or 0)
            if x:
                return ("You opened to sell on " + str(x)
                        + " of the last 7 days.")
            return ""
        if voice == "spirit":
            x = int(ps.get("sat_days_7", 0) or 0)
            if x:
                return ("You sat " + str(x) + " of the last 7 days.")
            return ""
        if voice == "body":
            x = int(ps.get("move_days_7", 0) or 0)
            if x:
                return ("You moved " + str(x) + " of the last 7 days.")
            return ""
        if voice == "journal":
            x = int(ps.get("j_days_7", 0) or 0)
            if x:
                return ("You wrote " + str(x) + " of the last 7 days.")
            return ""
        if voice == "review":
            c = int(pkt.get("consistency7", 0) or 0)
            if c:
                return ("Consistency held " + str(c)
                        + "% over 30 days.")
            return ""
        if voice == "focus":
            x = int(ps.get("cleared_days_7", 0) or 0)
            if x:
                return ("You cleared tasks on " + str(x)
                        + " of the last 7 days.")
            return ""
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# nudge (the single smallest next physical action)
# ---------------------------------------------------------------------------

def _nudge_for(voice, pkt, ps, live):
    try:
        cur = (live.get("cur_label", "") or "").lower()
        nxtl = (live.get("nxt_label", "") or "").lower()
        nht = live.get("nxt_time", "")
        if voice in ("now", "morning"):
            fu = ps.get("first_undone", "")
            due = ps.get("due", 0) or pkt.get("clients_due_n", 0)
            hot = ps.get("hottest", "")
            if fu:
                return "Tick " + fu + " now - the wall is watching."
            if due > 0:
                return ("Open with " + (hot or "the hottest")
                        + " - one call.")
            return "Write one line or do one block - the rest follows."
        if voice in ("sales", "TrueWave"):
            over = ps.get("over", 0) or pkt.get("clients_overdue_n", 0)
            due = ps.get("due", 0) or pkt.get("clients_due_n", 0)
            hot = ps.get("hottest", "")
            yest = ps.get("yest", 0)
            if over > 0 and hot:
                return "Dial " + hot + " now - then chase the rest."
            if due > 0:
                return "Pick up the oldest waiting - one call, log it."
            if yest > 0:
                return ("Stack on yesterday's " + str(yest)
                        + " - queue the next draft.")
            return "Log the next call the second it ends."
        if voice == "spirit":
            if not ps.get("sat_today", False):
                return "Sit five silent minutes now."
            return "Write the one word before it fades."
        if voice == "journal":
            if not ps.get("j_today", False):
                return ("One line: what happened, what you learned.")
            return "Close today's page with the lesson."
        if voice == "body":
            if "workout" in cur:
                return "Give the block the full forty-five."
            if "workout" in nxtl:
                return ("Be ready at " + (nht or "--:--")
                        + " - protect it like a meeting.")
            if int(pkt.get("workout_streak", 0) or 0) == 0:
                return "Twenty minutes tonight resets the streak."
            return "Protect the 8pm block; the streak is compounding."
        if voice == "focus":
            over = ps.get("overdue", 0)
            due = ps.get("due_t", 0)
            if over > 0:
                return "Do the smallest overdue task first."
            if due > 0:
                return "One twenty-five-minute deep block."
            return "Build, don't clear - the quiet is yours."
        if voice == "review":
            return "Name the lowest metric; one move for it."
        if voice == "money":
            days = ps.get("days")
            try:
                days = int(days)
            except Exception:
                days = 99
            bo = ps.get("bo", 0)
            name = ps.get("name", "") or "the staple"
            if days <= 3 and bo > 0:
                return ("Shop " + name + " today; hold the fun top-up.")
            if days <= 3:
                return "Add " + name + " to today's shop list."
            if bo > 0:
                return "Clear the oldest overdue bill first."
            return "Move 500 into the ring-fence while it's quiet."
        return "Set an anchor line below; I'll lean on it."
    except Exception:
        return ""
