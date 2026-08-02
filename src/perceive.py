"""Page-aware, LIVE perception for the PULSE companion.

Pure functions (no Streamlit, no session, no network). They turn the current
packet plus a page_stats dict (built by the companion from session data,
including a LIVE timeline view) into a per-page perception that is anchored
to the clock:

  * moment  - a LIVE eyebrow keyed to the current routine block + real clock,
              so it is correct at every minute and never reads "morning" at
              night.
  * line    - the factual next-step notice, derived from the live timeline
              (current block -> next block -> next block that maps to an
              unticked habit). Chronologically correct, never list-order.
  * alt     - an alternate notice (for anti-repetition) that adapts to how
              the day went (a passed-but-unticked habit surfaces gently).
  * pulse   - a 7-day relationship line; on Now/Morning it leads with the
              live "blocks behind / ahead" so it tracks the day's progress.
  * nudge   - one concrete next move, time-correct.
  * breath / sat - per-page breathing rhythm + mood saturation.

Because every layer reads a different angle of the same live state, no two
pages read the same and no layer repeats another. Everything is guarded so a
fault returns empty strings, never an exception.
"""
from __future__ import annotations


def perceive(pkt, voice, page_stats, allow_money):
    try:
        pkt = pkt or {}
        ps = page_stats or {}
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
        line, alt = _perceive_lines(voice, pkt, ps, allow_money)
        moment = _moment_for(voice, hour, ps)
        pulse = _page_pulse(voice, ps)
        nudge = _nudge_for(voice, pkt, ps, allow_money)
        return {
            "moment": moment, "line": line, "alt": alt,
            "pulse": pulse, "nudge": nudge,
            "breath": breath, "sat": sat,
        }
    except Exception:
        return {"moment": "", "line": "", "alt": "", "pulse": "",
                "nudge": "", "breath": 5.0, "sat": 1.0}


# ---------------------------------------------------------------------------
# moment (LIVE eyebrow)
# ---------------------------------------------------------------------------

def _moment_for(voice, hour, ps):
    try:
        hour = int(hour)
    except Exception:
        hour = 12
    live = (ps or {}).get("live") or {}

    def _live_prefix(rest):
        if live.get("has_blocks"):
            return "LIVE · " + str(live.get("now_hm", "--:--")) + " · " + rest
        return rest

    def _live_moment():
        cur = live.get("cur_label", "")
        ct = live.get("cur_time", "")
        nxt = live.get("nxt_label", "")
        nt = live.get("nxt_time", "")
        prog = int((live.get("prog") or 0) * 100)
        if cur:
            s = "in " + cur + (" at " + ct if ct else "") + " now"
            if nxt:
                s = s + " · next " + nxt + (" at " + nt if nt else "")
            else:
                s = s + " · winding the day down"
            return _live_prefix(s + " · " + str(prog) + "% through")
        if nxt:
            return _live_prefix("before your first block · next " + nxt
                                + (" at " + nt if nt else ""))
        if live.get("has_blocks") is False:
            return ""
        return _live_prefix("the clock is yours right now")

    if voice in ("now", "morning"):
        m = _live_moment()
        if m:
            return m
        if hour < 12:
            return "morning · the page is yours"
        if hour < 17:
            return "afternoon · keep the thread"
        return "evening · land the day clean"
    if voice in ("sales", "TrueWave"):
        if 12 <= hour < 13:
            return _live_prefix("12-1pm · live window, your best hour")
        if 9 <= hour < 11:
            return _live_prefix("posting hour · last night's drafts work")
        if 13 <= hour < 16:
            return _live_prefix("afternoon calls · urgent first, log rest")
        return _live_moment() or ""
    if voice == "spirit":
        if hour < 9:
            return _live_prefix("first light · silence lands deepest here")
        if hour >= 20:
            return _live_prefix("evening stillness · a short sit closes it")
        return _live_moment() or ""
    if voice == "body":
        cur = (live.get("cur_label") or "").lower()
        nxtl = (live.get("nxt_label") or "").lower()
        if "workout" in cur:
            return _live_prefix("in the workout block now · this is the work")
        if "workout" in nxtl:
            return _live_prefix("workout block at "
                                + (live.get("nxt_time") or "--:--"))
        if 20 <= hour < 21:
            return _live_prefix("8-8:45pm · movement, then the shower")
        if 5 <= hour < 7:
            return _live_prefix("morning mobility · small beats heroic")
        return _live_moment() or ""
    if voice == "journal":
        if hour >= 21:
            return _live_prefix("end of day · one honest line before sleep")
        if hour < 8:
            return _live_prefix("morning pages · the mind is quietest now")
        return _live_moment() or ""
    if voice == "focus":
        if 13 <= hour < 15:
            return _live_prefix("deep-work window · one tab, 25 minutes")
        return _live_moment() or ""
    if voice == "review":
        return _live_moment() or "the week in one look"
    if voice == "money":
        return _live_moment() or ""
    return _live_moment() or ""


# ---------------------------------------------------------------------------
# notice (factual next-step, live + adaptive)
# ---------------------------------------------------------------------------

def _perceive_lines(voice, pkt, ps, allow_money):
    v = voice
    if v in ("now", "morning"):
        live = (ps or {}).get("live") or {}
        ch = live.get("cur_habit", "")
        nh = live.get("nxt_habit", "")
        nht = live.get("nxt_habit_time", "")
        ph = live.get("passed_habit", "")
        dn = int(ps.get("due_n", 0) or 0)
        hot = ps.get("hottest", "")
        if ch:
            line = ("You're in your " + ch
                    + " block - tick it the moment it's done.")
        elif nh:
            line = ("Next habit on the clock: " + nh
                    + (" at " + nht if nht else "") + ".")
        elif live.get("nxt_label"):
            nt = live.get("nxt_time", "")
            line = ("Next on your day: " + live["nxt_label"]
                    + (" at " + nt if nt else "") + ".")
        else:
            line = "The clock's quiet - one true move is the whole win."
        if ph:
            alt = ("You let " + ph
                   + " slip earlier - log it or release it, no guilt.")
        elif dn > 0:
            alt = (str(dn) + " call(s) waiting"
                   + (" - open with " + hot if hot else "") + ".")
        else:
            alt = "Clean slate; the next block is yours."
        return line, alt
    if v in ("sales", "TrueWave"):
        due = int(ps.get("due", 0) or 0)
        over = int(ps.get("over", 0) or 0)
        yest = int(ps.get("yest", 0) or 0)
        hot = ps.get("hottest", "")
        if due > 0 and yest > 0:
            line = (str(due) + " waiting and you closed " + str(yest)
                    + " yesterday - momentum is real"
                    + (", dial " + hot if hot else "") + ".")
            if over > 0:
                alt = (str(over) + " overdue call(s) - oldest first, "
                       "always.")
            else:
                alt = (str(due) + " follow-up(s) due; that's revenue "
                       "in your phone.")
        elif over > 0:
            line = (str(over) + " overdue call(s) - oldest first, "
                    "always.")
            if due > 0:
                alt = (str(due) + " follow-up(s) due; that's revenue "
                       "in your phone.")
            else:
                alt = "Quiet pipe; log the next call the second it ends."
        elif due > 0:
            line = (str(due) + " follow-up(s) due; that's revenue "
                    "in your phone.")
            alt = "Quiet pipe; log the next call the second it ends."
        else:
            line = "Quiet pipe; log the next call the second it ends."
            if yest > 0:
                alt = ("Stack on yesterday's " + str(yest)
                       + ": queue the next draft.")
            else:
                alt = "Post the next draft; the queue feeds the calls."
        return line, alt
    if v == "spirit":
        sat_today = bool(ps.get("sat_today", False))
        lw = ps.get("last_word", "") or ps.get("word", "")
        depth = int(ps.get("depth", 0) or 0)
        sst = int(ps.get("sat_streak", 0) or 0)
        if not sat_today and lw:
            line = ("Not sat yet; '" + lw + "' is still warm from "
                    "last time.")
            alt = "Five silent minutes counts as showing up."
        elif not sat_today:
            line = "Five silent minutes counts as showing up."
            alt = "Come back to your anchor; it knows the hard days."
        else:
            line = ("Holding the quiet today"
                    + (" at depth " + str(depth) if depth else "")
                    + (" - a " + str(sst) + "-day thread"
                       if sst > 1 else "") + ".")
            alt = "Write the one word before it fades."
        return line, alt
    if v == "journal":
        j_today = bool(ps.get("j_today", False))
        ll = ps.get("last_lesson", "")
        jst = int(ps.get("j_streak", 0) or 0)
        if not j_today and ll:
            line = ("Blank page; the thread you keep writing is '"
                    + ll + "'.")
            alt = "One line is enough: what happened, what you learned."
        elif not j_today:
            line = ("One line is enough: what happened, what you "
                    "learned.")
            alt = "The page is where the days stop slipping."
        else:
            line = ("Today's page is open"
                    + (" - a " + str(jst) + "-day streak"
                       if jst > 1 else "")
                    + "; the streak is the point, not the prose.")
            alt = "Close today's page with the lesson."
        return line, alt
    if v == "body":
        ws = int(ps.get("ws", 0) or 0)
        delta = ps.get("delta", "")
        live = (ps or {}).get("live") or {}
        cur = (live.get("cur_label") or "").lower()
        nxtl = (live.get("nxt_label") or "").lower()
        nht = live.get("nxt_time", "")
        if "workout" in cur:
            line = ("In the workout block now - give it the full "
                    "forty-five.")
            alt = "Tick it the moment it's done; the streak loves that."
        elif "workout" in nxtl:
            line = ("Workout block is next at " + (nht or "--:--")
                    + " - protect it.")
            alt = "Small and consistent beats heroic, every time."
        elif ws > 0:
            line = ("Movement streak " + str(ws)
                    + ("; scale " + delta if delta else "")
                    + " - the body trusts you right now.")
            alt = "Protect the 8pm block; the streak is compounding."
        else:
            line = ("No streak running; twenty minutes tonight "
                    "resets it.")
            if delta:
                alt = "Scale " + delta + " - a trend, not a verdict."
            else:
                alt = "Treat the body like the asset it is."
        return line, alt
    if v == "focus":
        over = int(ps.get("overdue", 0) or 0)
        due = int(ps.get("due_t", 0) or 0)
        if over > 0:
            line = (str(over) + " overdue - smallest first breaks "
                    "the logjam.")
            if due > 0:
                alt = ("Protect one deep block for the " + str(due)
                       + " due today.")
            else:
                alt = "Use the quiet to build, not just clear."
        elif due > 0:
            line = (str(due) + " due today; protect one deep block.")
            alt = "Phones down, one tab, twenty-five minutes."
        else:
            line = ("Nothing overdue; use the quiet to build, not "
                    "just clear.")
            alt = ("Protect one deep block; the compounding is "
                   "invisible until it isn't.")
        return line, alt
    if v == "review":
        line = ("The score follows the showing-up; keep feeding "
                "the floor.")
        alt = "Name the one metric that's slipping; that's the next move."
        return line, alt
    if v == "money":
        if not allow_money:
            return _perceive_lines("review", pkt, ps, allow_money)
        days = ps.get("days")
        days = int(days) if days not in (None, "") else 99
        bo = int(ps.get("bo", 0) or 0)
        name = ps.get("name", "") or "the staple"
        if days <= 3 and bo > 0:
            line = (name + " at " + str(days) + "d and " + str(bo)
                    + " bill(s) overdue - shop today, hold the fun "
                    "top-up.")
            alt = (name + " at " + str(days)
                   + "d - on the shop list today.")
        elif days <= 3:
            line = (name + " at " + str(days)
                    + "d - on the shop list today.")
            alt = ("Money calm; move 500 into the ring-fence while "
                   "it's quiet.")
        elif bo > 0:
            line = (str(bo) + " bill(s) overdue; clear the oldest "
                    "first.")
            alt = ("Money calm; move 500 into the ring-fence while "
                   "it's quiet.")
        else:
            line = ("Money calm; move 500 into the ring-fence while "
                    "it's quiet.")
            alt = "Runway holds; let the basics stay covered."
        return line, alt
    line = "Tune me below; I learn from what you do after I speak."
    alt = "Set an anchor line; I'll lean on it on the hard days."
    return line, alt


# ---------------------------------------------------------------------------
# pulse (7-day relationship; Now/Morning leads with live day progress)
# ---------------------------------------------------------------------------

def _page_pulse(voice, ps):
    try:
        if voice in ("now", "morning"):
            live = (ps or {}).get("live") or {}
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
            c = int(ps.get("c", 0) or 0)
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
# nudge (one concrete, time-correct next move)
# ---------------------------------------------------------------------------

def _nudge_for(voice, pkt, ps, allow_money):
    try:
        v = voice
        if v in ("now", "morning"):
            live = (ps or {}).get("live") or {}
            ch = live.get("cur_habit", "")
            nh = live.get("nxt_habit", "")
            nht = live.get("nxt_habit_time", "")
            if ch:
                return ("Stay in " + ch
                        + " - tick it the moment it's done.")
            if nh:
                return ("Next: " + nh + (" at " + nht if nht else "")
                        + " - be ready for it.")
            if live.get("nxt_label"):
                nt = live.get("nxt_time", "")
                return ("Next block " + live["nxt_label"]
                        + (" at " + nt if nt else "") + ".")
            dn = int(ps.get("due_n", 0) or 0)
            if dn > 0:
                hot = ps.get("hottest", "")
                return ("Open with " + (hot or "the hottest")
                        + " - one call.")
            return "One true move; the rest follows."
        if v in ("sales", "TrueWave"):
            due = int(ps.get("due", 0) or 0)
            yest = int(ps.get("yest", 0) or 0)
            hot = ps.get("hottest", "")
            if due > 0:
                return ("Dial " + (hot or "the oldest overdue")
                        + " now - one call.")
            if yest > 0:
                return ("Stack on yesterday's " + str(yest)
                        + ": queue the next draft.")
            return "Log the next call the second it ends."
        if v == "spirit":
            if not bool(ps.get("sat_today", False)):
                return "Five silent minutes before the phone wakes."
            return "Write the one word before it fades."
        if v == "journal":
            if not bool(ps.get("j_today", False)):
                return "One line: what happened, what you learned."
            return "Close today's page with the lesson."
        if v == "body":
            live = (ps or {}).get("live") or {}
            cur = (live.get("cur_label") or "").lower()
            nxtl = (live.get("nxt_label") or "").lower()
            nht = live.get("nxt_time", "")
            if "workout" in cur:
                return "Give the workout block the full forty-five."
            if "workout" in nxtl:
                return ("Workout's next at " + (nht or "--:--")
                        + " - protect it.")
            if int(ps.get("ws", 0) or 0) == 0:
                return "Twenty minutes tonight resets the streak."
            return "Protect the 8pm block; the streak is compounding."
        if v == "focus":
            over = int(ps.get("overdue", 0) or 0)
            due = int(ps.get("due_t", 0) or 0)
            if over > 0:
                return "Do the smallest overdue task first."
            if due > 0:
                return "Protect one twenty-five-minute deep block."
            return "Use the quiet to build, not just clear."
        if v == "review":
            return ("Pick the one metric that's slipping; name the "
                    "next move.")
        if v == "money":
            if not allow_money:
                return _nudge_for("review", pkt, ps, allow_money)
            days = ps.get("days")
            days = int(days) if days not in (None, "") else 99
            bo = int(ps.get("bo", 0) or 0)
            name = ps.get("name", "") or "the staple"
            if days <= 3 and bo > 0:
                return ("Shop " + name + " today; hold the fun "
                        "top-up.")
            if days <= 3:
                return ("Add " + name + " to today's shop list.")
            if bo > 0:
                return "Clear the oldest overdue bill first."
            return "Move 500 into the ring-fence while it's quiet."
        return "Tune me below; I learn from what you do after I speak."
    except Exception:
        return ""
