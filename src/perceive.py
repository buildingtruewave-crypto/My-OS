"""Page-aware perception for the PULSE companion.

Pure functions (no Streamlit, no session, no network) that turn the current
packet plus a small page_stats dict (built by the companion from session
data) into a per-page perception: a time/place moment, a factual notice
unique to the page, an alternate notice (for anti-repetition), a 7-day
relationship pulse, a concrete next-move nudge, and a per-page breathing
rhythm plus saturation. Because every layer is computed from a different
angle of the same state, no two pages ever read the same and no layer
repeats another. Everything is guarded so a fault returns empty strings,
never an exception - the companion imports this module under a guard and
degrades gracefully if it ever hiccups.
"""
from __future__ import annotations


def perceive(pkt, voice, page_stats, allow_money):
    try:
        pkt = pkt or {}
        ps = page_stats or {}
        mb = pkt.get("mood_band", "none")
        hour = int(pkt.get("hour", 12))
        breath = {"spirit": 7.0, "vault": 5.0, "sales": 3.4, "now": 5.0,
                  "morning": 5.0, "journal": 5.6, "body": 4.2,
                  "focus": 4.0, "review": 5.2, "quiet": 6.5}.get(voice, 5.0)
        if mb == "low":
            sat = 0.7
        elif mb == "high":
            sat = 1.15
        else:
            sat = 1.0
        line, alt = _perceive_lines(voice, pkt, ps, allow_money)
        return {
            "moment": _moment_for(voice, hour),
            "line": line,
            "alt": alt,
            "pulse": _page_pulse(voice, ps),
            "nudge": _nudge_for(voice, pkt, ps, allow_money),
            "breath": breath,
            "sat": sat,
        }
    except Exception:
        return {"moment": "", "line": "", "alt": "", "pulse": "",
                "nudge": "", "breath": 5.0, "sat": 1.0}


def _moment_for(voice, hour):
    try:
        hour = int(hour)
    except Exception:
        hour = 12
    if voice in ("sales", "TrueWave"):
        if 12 <= hour < 13:
            return ("12-1pm - live window, your highest-conversion "
                    "hour; protect it")
        if 9 <= hour < 11:
            return ("posting hour - last night's queued drafts do "
                    "the work now")
        if 13 <= hour < 16:
            return ("afternoon calls - the urgent ones first, "
                    "log the rest")
        return ""
    if voice == "spirit":
        if hour < 9:
            return "first light - silence lands deepest for you here"
        if hour >= 20:
            return ("evening stillness - a short sit closes the "
                    "day clean")
        return ""
    if voice == "body":
        if 20 <= hour < 21:
            return ("8-8:45pm - movement window, then the shower "
                    "closes the day")
        if 5 <= hour < 7:
            return ("morning mobility - small and consistent beats "
                    "heroic")
        return ""
    if voice in ("now", "morning"):
        if 6 <= hour < 8:
            return ("first hour - it sets the spine; keep it small "
                    "and kind")
        return ""
    if voice == "journal":
        if hour >= 21:
            return "end of day - one honest line before sleep"
        if hour < 8:
            return "morning pages - the mind is quietest now"
        return ""
    if voice == "focus":
        if 13 <= hour < 15:
            return "deep-work window - one tab, twenty-five minutes"
        return ""
    return ""


def _perceive_lines(voice, pkt, ps, allow_money):
    v = voice
    if v in ("now", "morning"):
        fu = ps.get("first_undone", "")
        dn = int(ps.get("due_n", 0) or 0)
        hot = ps.get("hottest", "")
        if fu and dn > 0:
            line = ("Two things are open: " + fu + ", and " + str(dn)
                    + " call(s) waiting - the wall and the phone "
                    "both want you.")
            alt = (fu + " is the first open habit; do it and the "
                   "wall answers.")
        elif fu:
            line = (fu + " is the first open habit; do it and the "
                    "wall answers.")
            alt = "Clean page; one true move is the whole win."
        elif dn > 0:
            line = (str(dn) + " call(s) waiting"
                    + (" - open with " + hot if hot else "") + ".")
            alt = "Clean page; one true move is the whole win."
        else:
            line = "Clean page; one true move is the whole win."
            alt = ("The first hour sets the spine; keep it small "
                   "and kind.")
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
                alt = (str(over) + " overdue call(s) - the oldest "
                       "first, always.")
            else:
                alt = (str(due) + " follow-up(s) due; that's revenue "
                       "in your phone.")
        elif over > 0:
            line = (str(over) + " overdue call(s) - the oldest "
                    "first, always.")
            if due > 0:
                alt = (str(due) + " follow-up(s) due; that's revenue "
                       "in your phone.")
            else:
                alt = ("Quiet pipe; log the next call the second "
                       "it ends.")
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
                alt = ("Post the next draft; the queue feeds the "
                       "calls.")
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
            line = "One line is enough: what happened, what you learned."
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
        if ws > 0:
            line = ("Movement streak " + str(ws)
                    + ("; scale " + delta if delta else "")
                    + " - the body trusts you right now.")
            alt = "Protect the 8pm block; the streak is compounding."
        else:
            line = "No streak running; twenty minutes tonight resets it."
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
            line = str(due) + " due today; protect one deep block."
            alt = "Phones down, one tab, twenty-five minutes."
        else:
            line = "Nothing overdue; use the quiet to build, not just clear."
            alt = ("Protect one deep block; the compounding is "
                   "invisible until it isn't.")
        return line, alt
    if v == "review":
        line = "The score follows the showing-up; keep feeding the floor."
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
            alt = name + " at " + str(days) + "d - on the shop list today."
        elif days <= 3:
            line = name + " at " + str(days) + "d - on the shop list today."
            alt = "Money calm; move 500 into the ring-fence while it's quiet."
        elif bo > 0:
            line = str(bo) + " bill(s) overdue; clear the oldest first."
            alt = "Money calm; move 500 into the ring-fence while it's quiet."
        else:
            line = "Money calm; move 500 into the ring-fence while it's quiet."
            alt = "Runway holds; let the basics stay covered."
        return line, alt
    line = "Tune me below; I learn from what you do after I speak."
    alt = "Set an anchor line; I'll lean on it on the hard days."
    return line, alt


def _page_pulse(voice, ps):
    try:
        if voice in ("sales", "TrueWave"):
            x = int(ps.get("sold_days_7", 0) or 0)
            if x:
                return ("You opened to sell on " + str(x)
                        + " of the last 7 days.")
            return ""
        if voice == "spirit":
            x = int(ps.get("sat_days_7", 0) or 0)
            if x:
                return "You sat " + str(x) + " of the last 7 days."
            return ""
        if voice == "body":
            x = int(ps.get("move_days_7", 0) or 0)
            if x:
                return "You moved " + str(x) + " of the last 7 days."
            return ""
        if voice == "journal":
            x = int(ps.get("j_days_7", 0) or 0)
            if x:
                return "You wrote " + str(x) + " of the last 7 days."
            return ""
        if voice in ("now", "morning"):
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


def _nudge_for(voice, pkt, ps, allow_money):
    try:
        v = voice
        if v in ("now", "morning"):
            fu = ps.get("first_undone", "")
            dn = int(ps.get("due_n", 0) or 0)
            hot = ps.get("hottest", "")
            if fu:
                return "Do " + fu + " next; the wall is watching."
            if dn > 0:
                return ("Open with " + (hot or "the hottest")
                        + " - one call.")
            return "The page is clean; one true move."
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
            return "Pick the one metric that's slipping; name the next move."
        if v == "money":
            if not allow_money:
                return _nudge_for("review", pkt, ps, allow_money)
            days = ps.get("days")
            days = int(days) if days not in (None, "") else 99
            bo = int(ps.get("bo", 0) or 0)
            name = ps.get("name", "") or "the staple"
            if days <= 3 and bo > 0:
                return "Shop " + name + " today; hold the fun top-up."
            if days <= 3:
                return "Add " + name + " to today's shop list."
            if bo > 0:
                return "Clear the oldest overdue bill first."
            return "Move 500 into the ring-fence while it's quiet."
        return "Tune me below; I learn from what you do after I speak."
    except Exception:
        return ""
