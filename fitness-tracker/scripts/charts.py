"""Pure-stdlib chart rendering for fitness-tracker reports.

Two outputs, zero dependencies (keeps the skill sandbox-portable):
  - sparkline(values): a one-line unicode trend for inline text reports.
  - line_chart_svg(series, x_labels, ...): a standalone SVG line chart the
    assistant can show as an artifact.

An optional matplotlib PNG path lives in fittrack's `report` command; it is never
required — SVG + sparkline always work.
"""
from __future__ import annotations

import math

_SPARK = "▁▂▃▄▅▆▇█"

# Small readable palette: warm accent first, then supporting hues.
PALETTE = ["#d97757", "#3b82f6", "#16a34a", "#a855f7", "#eab308", "#0891b2"]


def sparkline(values):
    """Unicode sparkline. None values render as a gap (space). '' if no data."""
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return ""
    lo, hi = min(nums), max(nums)
    rng = hi - lo
    cells = []
    for v in values:
        if v is None:
            cells.append(" ")
        elif rng == 0:
            cells.append(_SPARK[len(_SPARK) // 2])
        else:
            i = int(round((float(v) - lo) / rng * (len(_SPARK) - 1)))
            cells.append(_SPARK[max(0, min(len(_SPARK) - 1, i))])
    return "".join(cells)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_chart_svg(series, x_labels, *, title="", width=760, height=340,
                   value_fmt="{:.1f}", baseline=None, fill=False):
    """Render a multi-line chart as a complete <svg> string.

    series: list of {"label": str, "values": [float|None, ...]} — every series
            aligned to x_labels (same length). Missing points (None) are skipped;
            the line connects the points that exist. The axis auto-zooms to the
            data range, so even small real changes show a clear slope.
    value_fmt: format for the end-of-line value label (e.g. "{:+.1f}%").
    baseline: if set, included in the range and drawn as a dashed reference
              (e.g. 0 for a "% change from start" chart).
    """
    n = len(x_labels)
    pad_l, pad_r, pad_t, pad_b = 56, 64, 46, 38
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    allv = [v for s in series for v in s["values"] if v is not None]
    if not allv or n == 0:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}"></svg>')
    lo, hi = min(allv), max(allv)
    if baseline is not None:
        lo, hi = min(lo, baseline), max(hi, baseline)
    if hi == lo:
        hi = lo + 1
    span = hi - lo
    lo -= span * 0.1
    hi += span * 0.1

    def X(i):
        return pad_l + (pw / 2 if n == 1 else pw * i / (n - 1))

    def Y(v):
        return pad_t + ph * (1 - (v - lo) / (hi - lo))

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="system-ui,Segoe UI,Arial,sans-serif">']
    p.append(f'<rect width="{width}" height="{height}" rx="14" fill="#fbf9f6"/>')
    if title:
        p.append(f'<text x="{pad_l}" y="26" font-size="16" font-weight="700" '
                 f'fill="#1a1916">{_esc(title)}</text>')
    for frac in (0.0, 0.5, 1.0):
        val = lo + (hi - lo) * frac
        yy = Y(val)
        p.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width - pad_r}" y2="{yy:.1f}" stroke="#e7e2da"/>')
        p.append(f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" font-size="11" '
                 f'text-anchor="end" fill="#8a8378">{val:.1f}</text>')
    if baseline is not None and lo <= baseline <= hi:
        yb = Y(baseline)
        p.append(f'<line x1="{pad_l}" y1="{yb:.1f}" x2="{width - pad_r}" y2="{yb:.1f}" '
                 f'stroke="#b8b2a8" stroke-dasharray="5 4"/>')
    for i in sorted({0, n // 2, n - 1}):
        p.append(f'<text x="{X(i):.1f}" y="{height - 14}" font-size="11" '
                 f'text-anchor="middle" fill="#8a8378">{_esc(x_labels[i])}</text>')
    lx = pad_l
    for k, s in enumerate(series):
        color = PALETTE[k % len(PALETTE)]
        iv = [(i, v) for i, v in enumerate(s["values"]) if v is not None]
        pts = [(X(i), Y(v)) for i, v in iv]
        if fill and len(pts) >= 2:
            fy = Y(baseline) if baseline is not None else (pad_t + ph)
            poly = (" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                    + f" {pts[-1][0]:.1f},{fy:.1f} {pts[0][0]:.1f},{fy:.1f}")
            p.append(f'<polygon points="{poly}" fill="{color}" opacity="0.15"/>')
        if len(pts) >= 2:
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            p.append(f'<polyline points="{d}" fill="none" stroke="{color}" '
                     f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in pts:
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        if iv:
            ei, ev = iv[-1]
            p.append(f'<text x="{X(ei) + 7:.1f}" y="{Y(ev) + 4:.1f}" font-size="11" '
                     f'font-weight="600" fill="{color}">{_esc(value_fmt.format(ev))}</text>')
        p.append(f'<rect x="{lx}" y="{pad_t - 17}" width="10" height="10" rx="2" fill="{color}"/>')
        p.append(f'<text x="{lx + 15}" y="{pad_t - 8}" font-size="12" fill="#52514c">{_esc(s["label"])}</text>')
        lx += 25 + 8 * len(str(s["label"]))
    p.append("</svg>")
    return "".join(p)


def bar_chart_svg(values, x_labels, *, title="", width=760, height=340,
                  pos_color="#d97757", neg_color="#16a34a"):
    """Bars around a zero baseline — ideal for daily energy net (deficit/surplus).
    values aligned to x_labels (None = gap). Bars below zero use neg_color, at/above
    zero use pos_color. The zero line is drawn prominently so sign is obvious."""
    n = len(values)
    pad_l, pad_r, pad_t, pad_b = 56, 18, 46, 40
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    nums = [v for v in values if v is not None]
    if not nums or n == 0:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}"></svg>')
    hi = max(nums + [0.0])
    lo = min(nums + [0.0])
    if hi == lo:
        hi = lo + 1
    span = hi - lo
    lo -= span * 0.12
    hi += span * 0.12

    def Y(v):
        return pad_t + ph * (1 - (v - lo) / (hi - lo))

    zero = Y(0)
    bw = max(3.0, pw / n * 0.6)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="system-ui,Segoe UI,Arial,sans-serif">']
    p.append(f'<rect width="{width}" height="{height}" rx="14" fill="#fbf9f6"/>')
    if title:
        p.append(f'<text x="{pad_l}" y="26" font-size="16" font-weight="700" fill="#1a1916">{_esc(title)}</text>')
    for v in (hi, lo):
        p.append(f'<text x="{pad_l - 8}" y="{Y(v) + 4:.1f}" font-size="11" '
                 f'text-anchor="end" fill="#8a8378">{v:.0f}</text>')
    for i, v in enumerate(values):
        if v is None:
            continue
        cx = pad_l + pw * (i + 0.5) / n
        y = min(Y(v), zero)
        h = max(1.0, abs(Y(v) - zero))
        color = neg_color if v < 0 else pos_color
        p.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" fill="{color}"/>')
    p.append(f'<line x1="{pad_l}" y1="{zero:.1f}" x2="{width - pad_r}" y2="{zero:.1f}" stroke="#52514c"/>')
    for i in sorted({0, n // 2, n - 1}):
        cx = pad_l + pw * (i + 0.5) / n
        p.append(f'<text x="{cx:.1f}" y="{height - 14}" font-size="11" text-anchor="middle" fill="#8a8378">{_esc(x_labels[i])}</text>')
    p.append("</svg>")
    return "".join(p)


def bars_vs_goal_svg(values, x_labels, goal, *, title="", width=760, height=340,
                     under_color="#16a34a", over_color="#d97757"):
    """Daily bars from 0 with a dashed goal line. Bars at/under goal use
    under_color, over goal use over_color. For calories-vs-target."""
    n = len(values)
    pad_l, pad_r, pad_t, pad_b = 56, 52, 46, 40
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    nums = [v for v in values if v is not None]
    if not nums or n == 0:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}"></svg>')
    hi = max(nums + [goal]) * 1.12 or 1.0
    base = pad_t + ph

    def Y(v):
        return pad_t + ph * (1 - v / hi)

    bw = max(3.0, pw / n * 0.6)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="system-ui,Segoe UI,Arial,sans-serif">']
    p.append(f'<rect width="{width}" height="{height}" rx="14" fill="#fbf9f6"/>')
    if title:
        p.append(f'<text x="{pad_l}" y="26" font-size="16" font-weight="700" fill="#1a1916">{_esc(title)}</text>')
    for i, v in enumerate(values):
        if v is None:
            continue
        cx = pad_l + pw * (i + 0.5) / n
        yv = Y(v)
        color = over_color if v > goal else under_color
        p.append(f'<rect x="{cx - bw / 2:.1f}" y="{yv:.1f}" width="{bw:.1f}" height="{base - yv:.1f}" rx="2" fill="{color}"/>')
    gy = Y(goal)
    p.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" stroke="#52514c" stroke-dasharray="5 4"/>')
    p.append(f'<text x="{width - pad_r + 5}" y="{gy + 4:.1f}" font-size="11" fill="#52514c">{goal:.0f}</text>')
    p.append(f'<line x1="{pad_l}" y1="{base:.1f}" x2="{width - pad_r}" y2="{base:.1f}" stroke="#e7e2da"/>')
    for i in sorted({0, n // 2, n - 1}):
        cx = pad_l + pw * (i + 0.5) / n
        p.append(f'<text x="{cx:.1f}" y="{height - 14}" font-size="11" text-anchor="middle" fill="#8a8378">{_esc(x_labels[i])}</text>')
    p.append("</svg>")
    return "".join(p)


def heatmap_calendar_svg(day_status, *, title="", lang="ru"):
    """Calendar grid (weeks × 7) coloured by adherence: on=green, off=amber,
    none=grey. day_status = [(iso_date, 'on'|'off'|'none'), ...] over a range."""
    import datetime as _d
    if not day_status:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40"></svg>'
    status = dict(day_status)
    days = sorted(status)
    first = _d.date.fromisoformat(days[0])
    last = _d.date.fromisoformat(days[-1])
    start = first - _d.timedelta(days=first.weekday())
    end = last + _d.timedelta(days=6 - last.weekday())
    weeks = ((end - start).days + 1) // 7
    pad_l, pad_t, cell, gap = 30, 66, 30, 6
    width = pad_l + 7 * (cell + gap) + 30
    height = pad_t + weeks * (cell + gap) + 34
    colors = {"on": "#16a34a", "off": "#e0a458", "none": "#e7e2da"}
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="system-ui,Segoe UI,Arial,sans-serif">']
    p.append(f'<rect width="{width}" height="{height}" rx="14" fill="#fbf9f6"/>')
    if title:
        p.append(f'<text x="{pad_l}" y="26" font-size="16" font-weight="700" fill="#1a1916">{_esc(title)}</text>')
    wd = (["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"] if lang != "en"
          else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    for c in range(7):
        p.append(f'<text x="{pad_l + c * (cell + gap) + cell / 2:.1f}" y="{pad_t - 10}" '
                 f'font-size="11" text-anchor="middle" fill="#8a8378">{wd[c]}</text>')
    d, idx = start, 0
    while d <= end:
        x = pad_l + d.weekday() * (cell + gap)
        y = pad_t + (idx // 7) * (cell + gap)
        iso = d.isoformat()
        if iso in status:
            fillc = colors.get(status[iso], "#e7e2da")
            numc = "#ffffff" if status[iso] == "on" else "#52514c"
        else:
            fillc, numc = "#f1ede7", "#cbc4b8"
        p.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="6" fill="{fillc}"/>')
        p.append(f'<text x="{x + cell / 2:.1f}" y="{y + cell / 2 + 4:.1f}" font-size="10" '
                 f'text-anchor="middle" fill="{numc}">{d.day}</text>')
        d += _d.timedelta(days=1)
        idx += 1
    lx = pad_l
    ly = pad_t + weeks * (cell + gap) + 14
    leg = ([("on", "в цели"), ("off", "мимо"), ("none", "нет данных")] if lang != "en"
           else [("on", "on goal"), ("off", "off"), ("none", "no data")])
    for st, lbl in leg:
        p.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{colors[st]}"/>')
        p.append(f'<text x="{lx + 15}" y="{ly}" font-size="11" fill="#52514c">{_esc(lbl)}</text>')
        lx += 24 + 8 * len(lbl)
    p.append("</svg>")
    return "".join(p)


def donut_svg(segments, *, title="", center="", width=420, height=300):
    """Donut chart. segments = [(label, value, color), ...]; center = hole text.
    Slices are drawn as pie wedges with a background circle punched out."""
    segs = [(l, float(v), c) for l, v, c in segments if v and float(v) > 0]
    total = sum(v for _, v, _ in segs)
    if not segs or total <= 0:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}"></svg>')
    cx, cy, r, inner = 150, 168, 98, 56
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="system-ui,Segoe UI,Arial,sans-serif">']
    p.append(f'<rect width="{width}" height="{height}" rx="14" fill="#fbf9f6"/>')
    if title:
        p.append(f'<text x="24" y="28" font-size="16" font-weight="700" fill="#1a1916">{_esc(title)}</text>')
    ang = -90.0
    for _label, v, color in segs:
        sweep = v / total * 360
        a0, a1 = math.radians(ang), math.radians(ang + sweep)
        if v / total >= 0.999:
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
        else:
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            large = 1 if sweep > 180 else 0
            p.append(f'<path d="M{cx},{cy} L{x0:.1f},{y0:.1f} A{r},{r} 0 {large},1 '
                     f'{x1:.1f},{y1:.1f} Z" fill="{color}"/>')
        ang += sweep
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="#fbf9f6"/>')
    if center:
        lines = str(center).split("\n")
        if len(lines) >= 2:
            p.append(f'<text x="{cx}" y="{cy - 2}" font-size="17" font-weight="700" '
                     f'text-anchor="middle" fill="#1a1916">{_esc(lines[0])}</text>')
            p.append(f'<text x="{cx}" y="{cy + 16}" font-size="11" '
                     f'text-anchor="middle" fill="#8a8378">{_esc(lines[1])}</text>')
        else:
            p.append(f'<text x="{cx}" y="{cy + 5}" font-size="15" font-weight="700" '
                     f'text-anchor="middle" fill="#1a1916">{_esc(center)}</text>')
    lx, ly = 296, 130
    for label, v, color in segs:
        p.append(f'<rect x="{lx}" y="{ly - 11}" width="11" height="11" rx="2" fill="{color}"/>')
        p.append(f'<text x="{lx + 17}" y="{ly}" font-size="12" fill="#52514c">'
                 f'{_esc(label)} {round(100 * v / total)}%</text>')
        ly += 28
    p.append("</svg>")
    return "".join(p)
