#!/usr/bin/env python3
"""Hand-built UML sequence diagram for one scheduled run of the DSP v1 pipeline POC
(DTE-151 / DTE-152). Same look as build_sequence_diagram.py (the rh_dsp.js one):
stacked panels so it fits a page width.

The diagram is built once as primitives (lines, rects, text, frames, notes) and rendered two ways:
- SVG (running this script) -> dsp-poc-sequence-diagram-2026-10-28.svg / .png
- draw.io cells (drawio_cells(), used by build_dsp_poc_hld.py to put it under the HLD in the same .drawio)

Sources: from-3po/dsp-poc-decisions-paul_2026-10-27_2220.md (Paul's calls #1, #2, #4),
from-3po/dsp-poc-what-monday-delivers_2026-10-27_2220.md (copy of the Claude Doc, master),
from-3po/dsp-iceberg-pipeline-poc-spec-for-R3_2026-10-24_1645.md (Phase 3 states),
dsp-key-spec-2026-10-27.md (D1-D12).

Step badges (blue circles) use the same numbers as the HLD's arrows, so the two can be read side by side.

Render: rsvg-convert -z 1.5 -o dsp-poc-sequence-diagram-2026-10-28.png dsp-poc-sequence-diagram-2026-10-28.svg
"""
from html import escape
from pathlib import Path

OUT_SVG = str(Path(__file__).resolve().parent / 'dsp-poc-sequence-diagram-2026-10-28.svg')
TITLE = "DSP v1 Pipeline POC — one scheduled run (DTE-151), draft 2026-10-28 · numbers match the HLD"

HEADER_Y, HEADER_H, HEADER_W = 30, 60, 180
ROW_H = 44
ROW1_Y = 120
LIFELINE_TOP = HEADER_Y + HEADER_H
PANEL_BOTTOM_PAD = 30
FRAME_TAB_CLEARANCE = 34
TITLE_H = 26
PANEL_GAP = 50

GREY = ("#E8E8E8", "#333333")
BLUE = ("#CFE8FF", "#2A6FB0")
YELLOW = ("#FFF3C4", "#B8960C")
GREEN = ("#DFF2DF", "#3C8D3C")
RED = ("#FBE0E0", "#B03A3A")

BADGE_FILL = "#1A73E8"  # step badges, same colour as the HLD's
BADGE_R = 11


# ---------------- primitives ----------------
# Each is a dict with a "kind"; coordinates are panel-local until Panel.primitives() offsets them.

def P_line(x1, y1, x2, y2, dashed=False, arrow=None, stroke="#333", width=1.4):
    return dict(kind="line", x1=x1, y1=y1, x2=x2, y2=y2, dashed=dashed, arrow=arrow, stroke=stroke, width=width)


def P_path(points, arrow="solid"):
    return dict(kind="path", points=points, arrow=arrow)


def P_rect(x, y, w, h, fill, stroke, dashed=False, rounded=False, width=1.5, dash_style="6,4"):
    return dict(kind="rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, dashed=dashed, rounded=rounded,
                width=width, dash_style=dash_style)


def P_text(x, y, s, size=13, anchor="start", bold=False, italic=False):
    return dict(kind="text", x=x, y=y, s=s, size=size, anchor=anchor, bold=bold, italic=italic)


def P_tab(x, y, w, tag):
    return dict(kind="tab", x=x, y=y, w=w, tag=tag)


def P_note(x1, y, x2, h, lines, fill, stroke):
    return dict(kind="note", x1=x1, y=y, x2=x2, h=h, lines=lines, fill=fill, stroke=stroke)


def P_badge(cx, cy, n):
    return dict(kind="badge", x=cx, y=cy, n=n)


def P_actor(x, label, fill, stroke, dashed):
    return dict(kind="actor", x=x, y=0, label=label, fill=fill, stroke=stroke, dashed=dashed)


def offset(p, dx, dy):
    q = dict(p)
    for k in ("x", "x1", "x2"):
        if k in q:
            q[k] += dx
    for k in ("y", "y1", "y2"):
        if k in q:
            q[k] += dy
    if "points" in q:
        q["points"] = [(px + dx, py + dy) for px, py in q["points"]]
    return q


class Panel:
    """One stacked panel: actors across the top, rows added top to bottom."""

    def __init__(self, title, actors, xs, width):
        self.title, self.actors, self.xs, self.width = title, actors, xs, width
        self.y = ROW1_Y
        self.items = []      # drawn after lifelines
        self.frames = []     # frame boxes, drawn under lifelines so a filled frame can't hide them
        self.active = set()  # actor indexes with an activation bar

    def x(self, i):
        return self.xs[i]

    def nexty(self, h=ROW_H):
        v = self.y
        self.y += h
        return v

    def message(self, a, b, label, kind="call", step=None):
        y = self.nexty()
        x1, x2 = self.x(a), self.x(b)
        self.items.append(P_line(x1, y, x2, y, dashed=(kind != "call"), arrow="solid" if kind == "call" else "open"))
        if not step:
            self.items.append(P_text((x1 + x2) / 2, y - 6, label, anchor="middle"))
            return
        # badge just left of the label, but never on or left of the leftmost lifeline (+ activation bar);
        # a label too wide for that starts right after the badge instead of centring
        text_left = (x1 + x2) / 2 - 0.55 * 13 * len(label) / 2
        min_badge = min(x1, x2) + 9 + BADGE_R + 4
        if text_left - 6 - BADGE_R >= min_badge:
            self.items.append(P_text((x1 + x2) / 2, y - 6, label, anchor="middle"))
            self.items.append(P_badge(text_left - 6 - BADGE_R, y - 11, step))
        else:
            self.items.append(P_badge(min_badge, y - 11, step))
            self.items.append(P_text(min_badge + BADGE_R + 6, y - 6, label))

    def self_message(self, a, label, step=None):
        y = self.nexty()
        x = self.x(a)
        self.items.append(P_path([(x + 8, y), (x + 50, y), (x + 50, y + 18), (x + 8, y + 18)]))
        if step:
            self.items.append(P_badge(x + 57 + BADGE_R, y + 9, step))
            self.items.append(P_text(x + 57 + 2 * BADGE_R + 6, y + 13, label))
        else:
            self.items.append(P_text(x + 57, y + 13, label))

    def note(self, a, b, lines, fill="#FFFBE6", stroke="#C9A227"):
        """UML note spanning actors a..b."""
        h = 10 + 16 * len(lines)
        y = self.nexty(h + 14) - 14
        self.items.append(P_note(self.x(a) - 70, y, self.x(b) + 70, h, lines, fill, stroke))

    def open_frame(self, a, b, tag, label, pad=90):
        top = self.y - 20
        self.y += FRAME_TAB_CLEARANCE
        return (a, b, tag, label, pad, top)

    def close_frame(self, handle, dashed_fill=None):
        a, b, tag, label, pad, top = handle
        bottom = self.y - ROW_H + 26
        x1, x2 = self.x(a) - pad, self.x(b) + pad
        self.frames.append(P_rect(x1, top, x2 - x1, bottom - top, dashed_fill or "none", "#666",
                                  dashed=True, width=1.2, dash_style="3,3"))
        # tab + label go over lifelines/bars; label gets a backing so lifelines don't cut it
        tab_w = 30 + 7 * len(tag)
        self.items.append(P_tab(x1, top, tab_w, tag))
        self.items.append(P_rect(x1 + tab_w + 6, top + 6, 6.2 * len(label) + 8, 16, dashed_fill or "white", "none", width=0))
        self.items.append(P_text(x1 + tab_w + 10, top + 18, label, size=11, italic=True))
        self.y += 16  # clear the frame's bottom border

    def bottom(self):
        return self.y - ROW_H + 26 + PANEL_BOTTOM_PAD

    def height(self):
        return TITLE_H + (self.bottom() - HEADER_Y)

    def primitives(self, dy):
        """All primitives in draw order, offset to canvas coordinates (panel top at dy)."""
        bottom = self.bottom()
        out = [P_text(20, TITLE_H, self.title, size=14, bold=True)]
        body = [P_actor(x, label, fill, stroke, dashed) for (label, (fill, stroke), dashed), x in zip(self.actors, self.xs)]
        body += self.frames
        body += [P_line(x, LIFELINE_TOP, x, bottom, dashed=True, stroke="#999", width=1.3) for x in self.xs]
        body += [P_rect(self.x(i) - 7, LIFELINE_TOP, 14, bottom - LIFELINE_TOP - 10, "#CFE8FF", "#2A6FB0", width=1)
                 for i in sorted(self.active)]
        body += self.items
        out += [offset(p, 0, TITLE_H) for p in body]
        return [offset(p, 0, dy) for p in out]


# ---------------- content ----------------

def build_panels():
    # Panel 1: trigger, lock, find work
    p1 = Panel(
        "Part 1 — Trigger, lock, find work",
        [("EventBridge Scheduler\n(hourly stand-in for\nNode heartbeat)", GREY, False),
         ("Step Functions\ndsp-poc (Standard)", BLUE, False),
         ("CheckLock Lambda\ndsp-check-lock (zip)\nno S3 access", BLUE, False),
         ("FindWork Lambda", BLUE, False),
         ("S3: Input\n(curated DSP copy, sandbox)", YELLOW, False),
         ("S3: Parquet bucket\nrhde-pg-dsp-poc-parquet\n(Output A, the contract)", GREEN, False)],
        [110, 330, 550, 770, 990, 1210], 1320)
    SCHED, SFN, LOCK, FIND, INPUT, OUTA = range(6)
    p1.active = {SFN}

    p1.message(SCHED, SFN, "StartExecution (hourly)", step=1)
    p1.message(SFN, LOCK, "invoke CheckLock", step=2)
    p1.self_message(LOCK, "ListExecutions(status = RUNNING), minus itself")
    p1.message(LOCK, SFN, "locked: true / false", "return")
    f = p1.open_frame(SFN, OUTA, "alt", "locked = true (another execution is running)")
    p1.self_message(SFN, "Succeed: SkippedAlreadyRunning (overlapping trigger discarded)")
    p1.close_frame(f)
    p1.message(SFN, FIND, "invoke FindWork", step=3)
    p1.message(FIND, INPUT, "list input files, last 21 days", step=3)
    p1.message(INPUT, FIND, "file-hours (pld_*.csv.gz)", "return")
    p1.message(FIND, OUTA, "list output keys for those hours", step=3)
    p1.message(OUTA, FIND, "files that exist", "return")
    p1.self_message(FIND, "keep hours missing any of the 6 publisher files; cap 6")
    p1.message(FIND, SFN, "hours[] (oldest first, max 6)", "return")
    p1.note(SFN, OUTA, ["No separate job state: \"done\" = all configured publisher files exist + manifest entry.",
                        "Empty publisher-hour still gets a zero-row file, or FindWork would pick that hour up forever.",
                        "State-machine timeout 25 min, so a stuck run can't hold the lock past the next trigger.",
                        "FindWork checks only the Parquet bucket, so a failed Writer B hour is not retried (known gap)."])

    # Panel 2: per-hour transform
    p2 = Panel(
        "Part 2 — Transform each hour (Map, MaxConcurrency 2)",
        [("Step Functions\n(Map state)", BLUE, False),
         ("Transform Lambda\n(container: Python + DuckDB)", BLUE, False),
         ("S3: Input\n(hourly CSV, gz)", YELLOW, False),
         ("S3: Id ledger\n(Parquet, 1 file/hour,\nevery row's id)", YELLOW, False),
         ("S3: Quarantine\nrhde-quarantine (sandbox)\nfailed-keys/", RED, False)],
        [120, 380, 640, 900, 1160], 1280)
    MAP, XF, IN2, LEDGER, QUAR = range(5)
    p2.active = {XF}

    outer = p2.open_frame(MAP, QUAR, "loop", "for each hour in hours[] (2 in parallel) → continued in Part 3", pad=110)
    p2.message(MAP, XF, "invoke(file-hour)", step=4)
    p2.message(XF, IN2, "read pld_<hour>.csv.gz (stream)", step=5)
    p2.message(IN2, XF, "rows", "return")
    p2.self_message(XF, "1  validate header")
    alt = p2.open_frame(XF, QUAR, "alt", "header invalid")
    p2.message(XF, QUAR, "whole file → quarantine, reason code", step=7)
    p2.message(XF, MAP, "failed (bad header)", "return")
    p2.close_frame(alt)
    p2.message(XF, LEDGER, "write ledger file: ALL rows, before filtering", step=6)
    p2.note(XF, LEDGER, ["ledger row = transaction_id, raw publisher label, row hash, source_file, event_ts",
                         "Seeded once with ~40M historical ids (monthly files, sorted by transaction_id)."])
    p2.self_message(XF, "2  clean up; collapse exact duplicates (D3)")
    p2.self_message(XF, "    same id, different data → conflict (D4)")
    p2.message(XF, LEDGER, "3  semi-join this hour's ids (window: config, default full history)", step=6)
    p2.message(LEDGER, XF, "ids seen on other rows, any publisher (excl. same source_file)", "return")
    p2.message(XF, QUAR, "conflicts + reused ids → failed-keys/, reason code (D4, D5)", step=7)
    p2.self_message(XF, "4  drop Test Account + blank publisher; map 9 labels → 6 (D6)")
    p2.self_message(XF, "    key = <publisher>-<transaction_id>; drop os_code, make_id (D1, D2, D10)")
    p2.close_frame(outer)
    p2.note(XF, QUAR, ["OPEN: parallel hours can each miss an id that appears in the other.",
                       "Fix (Paul, #4): run step 3 once over the batch of hours, or concurrency 1 for that step.",
                       "Fargate: if Phase 0 says an hour is too big for Lambda, the same image runs as an ECS task."],
            fill="#FDECEC", stroke="#B03A3A")

    # Panel 3: writers + manifest
    p3 = Panel(
        "Part 3 — Writers (A first, B second) and manifest",
        [("Transform Lambda\n(continued)", BLUE, False),
         ("S3: Parquet bucket\nrhde-pg-dsp-poc-parquet\n1 file/publisher/hour", GREEN, False),
         ("S3 Tables bucket\nrhde-pg-dsp-poc-iceberg\nevents (time-boxed trial)", GREY, True),
         ("Step Functions\n(continued)", BLUE, False),
         ("S3: Quarantine\nmanifests/ (sandbox)", RED, False)],
        [120, 380, 640, 900, 1160], 1280)
    XF3, OUT_A, OUT_B, SFN3, MAN = range(5)
    p3.active = {XF3, SFN3}

    outer3 = p3.open_frame(XF3, SFN3, "loop", "(continued from Part 2) same hour", pad=110)
    la = p3.open_frame(XF3, OUT_A, "loop", "for each of the 6 configured publishers (config file)")
    p3.message(XF3, OUT_A, "COPY TO tmp key (zero rows if none)", step=8)
    p3.message(XF3, OUT_A, "copy tmp → final key (replaces whole file, D12)")
    p3.close_frame(la)
    ob = p3.open_frame(XF3, OUT_B, "opt", "Writer B: may fail, never fails the hour")
    p3.message(XF3, OUT_B, "overwrite rows for this source_file (same rows as A)", step=9)
    p3.message(OUT_B, XF3, "ok / error (logged, A unaffected)", "return")
    p3.close_frame(ob, dashed_fill="#F7F7F7")
    p3.message(XF3, SFN3, "counts: kept, quarantined by reason; B status", "return")
    p3.close_frame(outer3)
    p3.message(SFN3, MAN, "RecordManifest: 1 entry per hour (file, job id, status, rows quarantined)", step=10)
    p3.self_message(SFN3, "Succeed")
    p3.note(OUT_A, SFN3, ["One-way arrows: nothing on A's path reads from S3 Tables.",
                          "Drop the trial and A ships unchanged. Readers: warehouse, Athena, DuckDB read A."])
    return [p1, p2, p3]


def layout():
    """(primitives in canvas coordinates, canvas width, canvas height); title at the top."""
    panels = build_panels()
    width = max(p.width for p in panels) + 40
    height = 40 + sum(p.height() for p in panels) + PANEL_GAP * (len(panels) - 1) + 20
    prims = [P_text(width / 2, 20, TITLE, size=16, anchor="middle", bold=True)]
    dy = 40
    for p in panels:
        prims += p.primitives(dy)
        dy += p.height() + PANEL_GAP
    return prims, width, height


# ---------------- SVG renderer ----------------

def esc(s):
    return escape(s, quote=False)


def svg_of(p):
    k = p["kind"]
    if k == "line":
        dash = 'stroke-dasharray="6,4"' if p["dashed"] and p["arrow"] else ('stroke-dasharray="5,4"' if p["dashed"] else "")
        marker = {"solid": 'marker-end="url(#arrowSolid)"', "open": 'marker-end="url(#arrowOpen)"'}.get(p["arrow"], "")
        return (f'<line x1="{p["x1"]}" y1="{p["y1"]}" x2="{p["x2"]}" y2="{p["y2"]}" stroke="{p["stroke"]}" '
                f'stroke-width="{p["width"]}" {dash} {marker}/>')
    if k == "path":
        d = "M " + " L ".join(f"{x} {y}" for x, y in p["points"])
        return f'<path d="{d}" fill="none" stroke="#333" stroke-width="1.4" marker-end="url(#arrowSolid)"/>'
    if k == "rect":
        dash = f'stroke-dasharray="{p["dash_style"]}"' if p["dashed"] else ""
        rx = 'rx="6"' if p["rounded"] else ""
        return (f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" {rx} fill="{p["fill"]}" '
                f'stroke="{p["stroke"]}" stroke-width="{p["width"]}" {dash}/>')
    if k == "text":
        style = (' font-weight="bold"' if p["bold"] else "") + (' font-style="italic"' if p["italic"] else "")
        return f'<text x="{p["x"]}" y="{p["y"]}" font-size="{p["size"]}" text-anchor="{p["anchor"]}"{style}>{esc(p["s"])}</text>'
    if k == "tab":
        x, y, w = p["x"], p["y"], p["w"]
        return (f'<path d="M {x} {y} L {x + w} {y} L {x + w} {y + 18} L {x + w - 8} {y + 26} L {x} {y + 26} Z" fill="#F0F0F0" stroke="#666" stroke-width="1"/>'
                f'<text x="{x + 8}" y="{y + 18}" font-size="11" font-weight="bold">{p["tag"]}</text>')
    if k == "note":
        x1, y, x2, h = p["x1"], p["y"], p["x2"], p["h"]
        out = [f'<path d="M {x1} {y} L {x2 - 10} {y} L {x2} {y + 10} L {x2} {y + h} L {x1} {y + h} Z" fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="1"/>']
        ty = y + 17
        for line in p["lines"]:
            out.append(f'<text x="{x1 + 8}" y="{ty}" font-size="11.5">{esc(line)}</text>')
            ty += 16
        return "\n".join(out)
    if k == "badge":
        return (f'<circle cx="{p["x"]}" cy="{p["y"]}" r="{BADGE_R}" fill="{BADGE_FILL}"/>'
                f'<text x="{p["x"]}" y="{p["y"] + 5}" font-size="14" font-weight="bold" fill="#FFFFFF" '
                f'text-anchor="middle">{p["n"]}</text>')
    if k == "actor":
        x = p["x"]
        dash = 'stroke-dasharray="6,4"' if p["dashed"] else ""
        out = [f'<rect x="{x - HEADER_W / 2}" y="{HEADER_Y + p["y"]}" width="{HEADER_W}" height="{HEADER_H}" rx="6" fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="1.5" {dash}/>']
        lines = p["label"].split("\n")
        ty = HEADER_Y + p["y"] + HEADER_H / 2 - (len(lines) - 1) * 8 + 5
        for line in lines:
            out.append(f'<text x="{x}" y="{ty}" font-size="12.5" text-anchor="middle">{esc(line)}</text>')
            ty += 16
        return "\n".join(out)
    raise ValueError(k)


def render_svg():
    prims, width, height = layout()
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Helvetica,Arial,sans-serif">',
           '''<defs>
    <marker id="arrowSolid" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#333"/></marker>
    <marker id="arrowOpen" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8" fill="none" stroke="#333" stroke-width="1.3"/></marker>
    </defs>''',
           f'<rect width="{width}" height="{height}" fill="white"/>']
    svg += [svg_of(p) for p in prims]
    svg.append('</svg>')
    return "\n".join(svg), width, height


# ---------------- draw.io renderer ----------------

def drawio_cells(ox, oy, id_prefix="seq", parent="1"):
    """mxCell XML strings for the whole diagram, placed with its top-left at (ox, oy)."""
    prims, width, height = layout()
    cells = []
    n = 0

    def nid():
        nonlocal n
        n += 1
        return f"{id_prefix}{n}"

    def vertex(value, style, x, y, w, h):
        cells.append(f'<mxCell id="{nid()}" value="{escape(value, quote=True)}" style="{style}" parent="{parent}" vertex="1">'
                     f'<mxGeometry x="{x + ox:.1f}" y="{y + oy:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry" /></mxCell>')

    def free_edge(points, style):
        (sx, sy), (tx, ty), mids = points[0], points[-1], points[1:-1]
        pts = ""
        if mids:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x + ox:.1f}" y="{y + oy:.1f}" />' for x, y in mids) + "</Array>"
        cells.append(f'<mxCell id="{nid()}" value="" style="{style}" parent="{parent}" edge="1"><mxGeometry relative="1" as="geometry">'
                     f'<mxPoint x="{sx + ox:.1f}" y="{sy + oy:.1f}" as="sourcePoint" /><mxPoint x="{tx + ox:.1f}" y="{ty + oy:.1f}" as="targetPoint" />'
                     f'{pts}</mxGeometry></mxCell>')

    text_base = "text;html=1;strokeColor=none;fillColor=none;whiteSpace=nowrap;verticalAlign=middle;spacing=0;fontColor=#232F3E;"
    for p in prims:
        k = p["kind"]
        if k in ("line", "path"):
            pts = [(p["x1"], p["y1"]), (p["x2"], p["y2"])] if k == "line" else p["points"]
            arrow = p.get("arrow", "solid")
            style = f"html=1;rounded=0;strokeColor={p.get('stroke', '#333')};strokeWidth={p.get('width', 1.4)};"
            style += {"solid": "endArrow=block;endFill=1;", "open": "endArrow=open;endFill=0;"}.get(arrow, "endArrow=none;")
            if p.get("dashed"):
                style += "dashed=1;"
            if k == "path":
                style += "edgeStyle=none;"
            free_edge(pts, style)
        elif k == "rect":
            fill = "none" if p["fill"] == "none" else p["fill"]
            stroke = "none" if p["stroke"] == "none" else p["stroke"]
            style = f"html=1;fillColor={fill};strokeColor={stroke};strokeWidth={p['width']};"
            style += ("rounded=1;arcSize=10;" if p["rounded"] else "rounded=0;") + ("dashed=1;" if p["dashed"] else "")
            if p["dashed"] and p["dash_style"] == "3,3":
                style += "dashPattern=3 3;"
            vertex("", style, p["x"], p["y"], p["w"], p["h"])
        elif k == "text":
            w = 0.6 * p["size"] * len(p["s"]) + 4
            align = {"start": "left", "middle": "center"}[p["anchor"]]
            x = p["x"] - w / 2 if align == "center" else p["x"]
            fs = (1 if p["bold"] else 0) + (2 if p["italic"] else 0)
            vertex(escape(p["s"]), text_base + f"align={align};fontSize={p['size']};fontStyle={fs};", x, p["y"] - p["size"] - 1, w, p["size"] + 6)
        elif k == "tab":
            vertex(p["tag"], "shape=card;flipH=1;flipV=1;size=8;html=1;fillColor=#F0F0F0;strokeColor=#666;fontSize=11;"
                   "fontStyle=1;align=left;spacingLeft=6;verticalAlign=middle;", p["x"], p["y"], p["w"], 26)
        elif k == "note":
            value = "<br>".join(escape(l) for l in p["lines"])
            vertex(value, f"shape=note;size=10;html=1;whiteSpace=nowrap;fillColor={p['fill']};strokeColor={p['stroke']};"
                   "fontSize=11.5;align=left;verticalAlign=top;spacingLeft=6;spacingTop=2;fontColor=#232F3E;",
                   p["x1"], p["y"], p["x2"] - p["x1"], p["h"])
        elif k == "badge":
            vertex(str(p["n"]), f"ellipse;html=1;fillColor={BADGE_FILL};strokeColor=none;fontColor=#FFFFFF;fontSize=14;"
                   "fontStyle=1;align=center;verticalAlign=middle;spacing=0;",
                   p["x"] - BADGE_R, p["y"] - BADGE_R, 2 * BADGE_R, 2 * BADGE_R)
        elif k == "actor":
            value = "<br>".join(escape(l) for l in p["label"].split("\n"))
            vertex(value, f"rounded=1;arcSize=10;html=1;whiteSpace=wrap;fillColor={p['fill']};strokeColor={p['stroke']};"
                   f"strokeWidth=1.5;fontSize=12.5;fontColor=#232F3E;" + ("dashed=1;" if p["dashed"] else ""),
                   p["x"] - HEADER_W / 2, HEADER_Y + p["y"], HEADER_W, HEADER_H)
        else:
            raise ValueError(k)
    return cells, width, height


if __name__ == "__main__":
    svg, width, height = render_svg()
    with open(OUT_SVG, 'w') as f:
        f.write(svg)
    print(f"Canvas: {width}x{height}")
