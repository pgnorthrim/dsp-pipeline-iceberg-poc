"""Simple two-path overview for the DSP POC plan doc (not the HLD).

Writes dsp-poc-two-paths-2026-10-28.svg; PNG via rsvg-convert.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent / "dsp-poc-two-paths-2026-10-28.svg"
W, H = 1180, 560
FONT = "Liberation Sans, Arial, sans-serif"

A_STROKE, A_FILL = "#1f6f43", "#e6f4ec"
B_STROKE, B_FILL = "#8a5a00", "#fdf3e1"
N_STROKE, N_FILL = "#33475b", "#eef2f6"
Q_STROKE, Q_FILL = "#9b2c2c", "#fbeaea"

parts = []


def box(x, y, w, h, title, lines, stroke, fill, dashed=False):
    dash = ' stroke-dasharray="8 5"' if dashed else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"{dash}/>')
    parts.append(f'<text x="{x + w / 2}" y="{y + 28}" text-anchor="middle" font-size="17" '
                 f'font-weight="bold" fill="{stroke}">{escape(title)}</text>')
    for i, s in enumerate(lines):
        parts.append(f'<text x="{x + w / 2}" y="{y + 54 + i * 21}" text-anchor="middle" '
                     f'font-size="14" fill="#222">{escape(s)}</text>')


def arrow(x1, y1, x2, y2, stroke, dashed=False, label=None, lx=0, ly=0):
    dash = ' stroke-dasharray="8 5"' if dashed else ""
    marker = "arrB" if dashed else ("arrA" if stroke == A_STROKE else "arrN")
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{stroke}" '
                 f'stroke-width="2.5"{dash} marker-end="url(#{marker})"/>')
    if label:
        parts.append(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="bold" '
                     f'fill="{stroke}">{escape(label)}</text>')


def marker(mid, color):
    return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{color}"/></marker>')


parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
parts.append(f'<text x="{W / 2}" y="38" text-anchor="middle" font-size="22" font-weight="bold" '
             f'fill="#222">DSP POC: one transform, two outputs</text>')

# Input and shared transform
box(30, 180, 200, 120, "Hourly DSP file", ["gzipped CSV", "from the source", "account"], N_STROKE, N_FILL)
box(300, 160, 260, 160, "One transform", ["Python + DuckDB, per hour", "clean, map publisher,",
                                          "build key, id check", "(same rows to both paths)"],
    N_STROKE, N_FILL)
arrow(230, 240, 296, 240, N_STROKE)

# Path A
box(660, 80, 230, 120, "Path A: Parquet files", ["6 per hour,", "one per publisher",
                                                  "(whole-file replace)"], A_STROKE, A_FILL)
box(950, 80, 200, 120, "Warehouse load", ["picks up the files", "as it does today"],
    A_STROKE, A_FILL)
arrow(560, 200, 656, 150, A_STROKE, label="Path A", lx=572, ly=160)
arrow(890, 140, 946, 140, A_STROKE)
parts.append(f'<text x="905" y="230" text-anchor="middle" font-size="14" font-style="italic" '
             f'fill="{A_STROKE}">The deliverable: file in, file out</text>')

# Path B
box(660, 280, 230, 120, "Path B: S3 Tables", ["Iceberg 'events' table", "same rows as A"],
    B_STROKE, B_FILL, dashed=True)
box(950, 280, 200, 120, "Compare with A", ["query with Athena", "or DuckDB:", "counts, cost, effort"],
    B_STROKE, B_FILL, dashed=True)
arrow(560, 280, 656, 330, B_STROKE, dashed=True, label="Path B", lx=572, ly=330)
arrow(890, 340, 946, 340, B_STROKE, dashed=True)
parts.append(f'<text x="905" y="430" text-anchor="middle" font-size="14" font-style="italic" '
             f'fill="{B_STROKE}">Time-boxed trial: can never block Path A</text>')

# Shared quarantine + manifest
box(300, 400, 260, 110, "Quarantine + manifest", ["bad rows/files with a reason;", "a record of every run"],
    Q_STROKE, Q_FILL)
arrow(430, 320, 430, 396, Q_STROKE)

parts.append(f'<text x="{W / 2}" y="{H - 18}" text-anchor="middle" font-size="14" fill="#555">'
             f'Nothing on Path A reads from Path B. If Path B is dropped, Path A is unchanged.</text>')

defs = "<defs>" + marker("arrN", N_STROKE) + marker("arrA", A_STROKE) + marker("arrB", B_STROKE) \
       + marker("arrQ", Q_STROKE) + "</defs>"
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="{FONT}">{defs}' + "".join(parts) + "</svg>")
svg = svg.replace(f'stroke="{Q_STROKE}" stroke-width="2.5" marker-end="url(#arrN)"',
                  f'stroke="{Q_STROKE}" stroke-width="2.5" marker-end="url(#arrQ)"')
OUT.write_text(svg)
print(OUT)
