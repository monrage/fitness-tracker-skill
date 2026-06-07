"""Resolve natural-language dates (RU + EN) to ISO YYYY-MM-DD.

Logging is retrospective, so a bare weekday ("в понедельник") resolves to the
most recent PAST occurrence (today counts). The assistant passes `today` from
conversation context; timezone is handled by the caller (it supplies the correct
"today"), keeping this module free of the fragile Windows zoneinfo dependency.

Also provides period bounds (week / month / year) for summaries.
"""
from __future__ import annotations
import datetime as _dt
import re

_WEEKDAYS = {
    "monday": 0, "mon": 0, "понедельник": 0, "пн": 0,
    "tuesday": 1, "tue": 1, "вторник": 1, "вт": 1,
    "wednesday": 2, "wed": 2, "среда": 2, "среду": 2, "ср": 2,
    "thursday": 3, "thu": 3, "четверг": 3, "чт": 3,
    "friday": 4, "fri": 4, "пятница": 4, "пятницу": 4, "пт": 4,
    "saturday": 5, "sat": 5, "суббота": 5, "субботу": 5, "сб": 5,
    "sunday": 6, "sun": 6, "воскресенье": 6, "вс": 6,
}
_MONTHS = {
    "january": 1, "jan": 1, "январь": 1, "января": 1,
    "february": 2, "feb": 2, "февраль": 2, "февраля": 2,
    "march": 3, "mar": 3, "март": 3, "марта": 3,
    "april": 4, "apr": 4, "апрель": 4, "апреля": 4,
    "may": 5, "май": 5, "мая": 5,
    "june": 6, "jun": 6, "июнь": 6, "июня": 6,
    "july": 7, "jul": 7, "июль": 7, "июля": 7,
    "august": 8, "aug": 8, "август": 8, "августа": 8,
    "september": 9, "sep": 9, "sept": 9, "сентябрь": 9, "сентября": 9,
    "october": 10, "oct": 10, "октябрь": 10, "октября": 10,
    "november": 11, "nov": 11, "ноябрь": 11, "ноября": 11,
    "december": 12, "dec": 12, "декабрь": 12, "декабря": 12,
}
# offset-from-today keywords, checked longest-first so "позавчера" beats "вчера"
_REL = {
    "today": 0, "сегодня": 0, "сейчас": 0,
    "yesterday": -1, "вчера": -1,
    "day before yesterday": -2, "позавчера": -2,
    "tomorrow": 1, "завтра": 1,
    "послезавтра": 2,
}


def _as_date(today):
    if today is None:
        return _dt.date.today()
    if isinstance(today, _dt.date):
        return today
    return _dt.date.fromisoformat(str(today))


def _safe_date(y, mo, d, ref, past=False):
    if y < 100:
        y += 2000
    try:
        cand = _dt.date(y, mo, d)
    except ValueError:
        return None
    if past and cand > ref:  # "5 июня" said in a month before June -> previous year
        try:
            cand = _dt.date(y - 1, mo, d)
        except ValueError:
            pass
    return cand.isoformat()


def resolve(text, today=None):
    """Return ISO date for a single-day expression, or None if unrecognized.

    Empty / whitespace input defaults to today (the common "no date mentioned" case).
    """
    ref = _as_date(today)
    s = (text or "").strip().lower()
    if not s:
        return ref.isoformat()

    # explicit ISO
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return _safe_date(int(m[1]), int(m[2]), int(m[3]), ref)

    # relative keywords (longest match first)
    for k in sorted(_REL, key=len, reverse=True):
        if k in s:
            return (ref + _dt.timedelta(days=_REL[k])).isoformat()

    # "N дней назад" / "N days ago"
    m = re.search(r"(\d+)\s*(?:дн|day)", s)
    if m and ("назад" in s or "ago" in s):
        return (ref - _dt.timedelta(days=int(m[1]))).isoformat()
    # "неделю назад" / "a week ago"
    if ("недел" in s and "назад" in s) or ("week" in s and "ago" in s):
        return (ref - _dt.timedelta(days=7)).isoformat()

    # DD.MM(.YYYY) or DD/MM(/YYYY)
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b", s)
    if m:
        y = int(m[3]) if m[3] else ref.year
        return _safe_date(y, int(m[2]), int(m[1]), ref, past=(m[3] is None))

    # "D <month>"  (e.g. "5 июня", "5 jun")
    m = re.search(r"\b(\d{1,2})\s+([а-яёa-z]+)", s)
    if m and m[2] in _MONTHS:
        return _safe_date(ref.year, _MONTHS[m[2]], int(m[1]), ref, past=True)
    # "<month> D"  (e.g. "june 5")
    m = re.search(r"\b([а-яёa-z]+)\s+(\d{1,2})\b", s)
    if m and m[1] in _MONTHS:
        return _safe_date(ref.year, _MONTHS[m[1]], int(m[2]), ref, past=True)

    # weekday -> most recent past occurrence (today counts)
    for name, wd in _WEEKDAYS.items():
        if re.search(r"\b" + re.escape(name) + r"\b", s):
            delta = (ref.weekday() - wd) % 7
            return (ref - _dt.timedelta(days=delta)).isoformat()

    return None


def week_bounds(today=None, week_start="mon"):
    d = _as_date(today)
    start_wd = 6 if str(week_start).lower().startswith("sun") else 0
    delta = (d.weekday() - start_wd) % 7
    start = d - _dt.timedelta(days=delta)
    return start.isoformat(), (start + _dt.timedelta(days=6)).isoformat()


def month_bounds(today=None):
    d = _as_date(today)
    start = d.replace(day=1)
    nxt = start.replace(year=start.year + 1, month=1) if start.month == 12 \
        else start.replace(month=start.month + 1)
    return start.isoformat(), (nxt - _dt.timedelta(days=1)).isoformat()


def year_bounds(today=None):
    d = _as_date(today)
    return _dt.date(d.year, 1, 1).isoformat(), _dt.date(d.year, 12, 31).isoformat()


def days_in(date_from, date_to):
    """Inclusive day count between two ISO dates."""
    a = _dt.date.fromisoformat(date_from)
    b = _dt.date.fromisoformat(date_to)
    return (b - a).days + 1
