#!/usr/bin/env python3
"""Generates dsp-poc-hld-2026-10-28.drawio: AWS high level diagram for the DSP v1 pipeline POC
(DTE-151 / DTE-152). Same look as ~/dsp-analysis-sandbox/docs/aws-hld.drawio (approved 10/22):
official mxgraph.aws4 icons and groups, numbered flow edges, dashed = not built / trial / pending.

One-shot generator: once Paul edits the .drawio in draw.io, edit the .drawio directly, don't rerun.

Sources: from-3po/dsp-poc-decisions-paul_2026-10-27_2220.md, from-3po/dsp-poc-what-monday-delivers_2026-10-27_2220.md,
from-3po/dsp-iceberg-pipeline-poc-spec-for-R3_2026-10-24_1645.md, dsp-key-spec-2026-10-27.md.

Export: flatpak run com.jgraph.drawio.desktop --export --format png --embed-diagram --scale 1.5 --border 10 \
        --output dsp-poc-hld-2026-10-28.png dsp-poc-hld-2026-10-28.drawio
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dsp_poc_sequence_diagram as seq  # noqa: E402

OUT = '/home/pgadmin/relevate-health/Docs/diagrams/dsp-poc-hld-2026-10-28.drawio'

GROUP_POINTS = ("points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],"
                "[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;gradientColor=none;html=1;"
                "whiteSpace=wrap;fontSize=12;fontStyle=0;container=0;pointerEvents=0;collapsible=0;recursiveResize=0;"
                "shape=mxgraph.aws4.group;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;")

# AWS category colours, as in the sandbox HLD
STORAGE, COMPUTE, APPINT, ANALYTICS, SECURITY, MGMT, GREY = "#7AA116", "#ED7100", "#E7157B", "#8C4FFF", "#DD344C", "#E7157B", "#879196"

cells = []


def attr(s):
    return escape(s, quote=True)


def label(title, *lines):
    return "<b>" + escape(title) + "</b>" + "".join("<br>" + escape(l) for l in lines)


def vertex(cid, value, style, x, y, w, h):
    cells.append(f'<mxCell id="{cid}" value="{attr(value)}" style="{style}" parent="1" vertex="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')


def group(cid, value, gr_icon, stroke, font, x, y, w, h, dashed=0):
    vertex(cid, value, GROUP_POINTS + f"grIcon=mxgraph.aws4.{gr_icon};strokeColor={stroke};fontColor={font};dashed={dashed};", x, y, w, h)


def icon(cid, value, res_icon, fill, x, y, dashed=False, font="#232F3E"):
    style = (f"sketch=0;outlineConnect=0;fontColor={font};gradientColor=none;fillColor={fill};strokeColor=#ffffff;"
             "dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;"
             f"aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res_icon};")
    if dashed:
        style += "opacity=55;"
    vertex(cid, value, style, x, y, 78, 78)


def box(cid, value, x, y, w, h, dashed=True, fill="#F2F3F3", stroke=GREY, font="#545B64", align="left", size=11):
    style = (f"rounded=1;arcSize=6;dashed={1 if dashed else 0};html=1;fillColor={fill};strokeColor={stroke};"
             f"fontColor={font};fontSize={size};align={align};spacingLeft=8;spacingRight=6;verticalAlign=top;whiteSpace=wrap;")
    vertex(cid, value, style, x, y, w, h)


def edge(cid, src, tgt, value="", color="#232F3E", dashed=False, exit=None, entry=None, points=(),
         both=False, arrow=True, label_bg="#ffffff", pos=None):
    style = (f"edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;fontSize=11;labelBackgroundColor={label_bg};"
             f"strokeColor={color};strokeWidth=2;")
    style += "endArrow=block;endFill=1;" if arrow else "endArrow=none;"
    if both:
        style += "startArrow=block;startFill=1;"
    if dashed:
        style += "dashed=1;"
    if exit:
        style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
    if entry:
        style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    geo_x = f' x="{pos}"' if pos is not None else ""
    pts = ""
    if points:
        pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in points) + "</Array>"
    cells.append(f'<mxCell id="{cid}" value="{attr(value)}" style="{style}" parent="1" source="{src}" target="{tgt}" edge="1">'
                 f'<mxGeometry{geo_x} relative="1" as="geometry">{pts}</mxGeometry></mxCell>')


# ---------------- frame ----------------
vertex("title", "<b>DSP v1 pipeline POC: high level diagram</b> · PROPOSED, not built · draft 2026-10-28 · "
       "DTE-151 / DTE-152 · names dsp-poc-* · flow detail in dsp-poc-sequence-diagram-2026-10-28",
       "text;html=1;align=left;verticalAlign=middle;fontSize=16;fontColor=#232F3E;", 40, 2, 1300, 30)

group("cloud", "AWS Cloud", "group_aws_cloud_alt", "#232F3E", "#232F3E", 40, 40, 1820, 1060)
group("region", "us-east-1 · relevate-sandbox account (474961012168) · serverless, no VPC needed for the POC",
      "group_region", "#00A4A6", "#147EBA", 60, 80, 1460, 1000, dashed=1)

# ---------------- orchestration row ----------------
icon("sched", label("EventBridge Scheduler", "hourly, weekdays 07:00-21:00 ET", "stand-in for the Node heartbeat"),
     "eventbridge", APPINT, 100, 170)
icon("sfn", label("Step Functions", "dsp-poc (Standard), 25 min timeout", "CheckLock · FindWork ·", "Map (max 2) · RecordManifest"),
     "step_functions", APPINT, 340, 170)
icon("find", label("FindWork Lambda", "hours missing outputs, cap 6"), "lambda", COMPUTE, 600, 170)
icon("input", label("S3: input (sandbox)", "curated copy of rh-dsp/pld/", "hourly pld_*.csv.gz"), "s3", STORAGE, 880, 170)

# ---------------- transform row ----------------
icon("xf", label("Transform Lambda", "container image: Python + DuckDB", "1 file-hour per invocation", "steps 1-4, key spec D1-D12"),
     "lambda", COMPUTE, 600, 430)
icon("fargate", label("Fargate task (fallback)", "same image, only if Phase 0", "says an hour is too big"),
     "fargate", COMPUTE, 440, 560, dashed=True, font="#545B64")
icon("ledger", label("S3: id ledger", "Parquet, 1 small file per hour", "every row's id, before filtering", "seeded with ~40M historical ids"),
     "s3", STORAGE, 880, 430)
icon("quar", label("S3: quarantine (sandbox copy)", "rhde-quarantine format:", "manifests/ + failed-keys/", "reason code per row"),
     "s3", STORAGE, 880, 680)

# ---------------- outputs ----------------
icon("outa", label("S3: Output A, the contract", "Parquet zstd, 1 file per publisher/hour", "6 publishers from config;", "empty file when no rows"),
     "s3", STORAGE, 1140, 300)
box("trial", "<b>Time-boxed trial (Writer B)</b> · never blocks A", 1060, 560, 440, 260,
    fill="#FAFAFA", font="#545B64", size=12)
icon("outb", label("S3 Tables (Iceberg)", "events table, same rows as A"), "s3", GREY, 1100, 610, font="#545B64")
box("trialnote", "Partitioned by publisher + day (proposed).<br><br><b>Next, only if Iceberg is kept:</b><br>"
    "raw_events (loaded from the ledger, one way A → B) · lake quarantine view",
    1250, 610, 240, 130, fill="#FFFFFF")

icon("athena", label("Athena", "queries A and B", "(comparison table)"), "athena", ANALYTICS, 1380, 170)
box("duckdb", "<b>DuckDB</b><br>queries A and B<br>(comparison table)", 1360, 420, 130, 60, dashed=False,
    fill="#FFFFFF", stroke="#232F3E", font="#232F3E", align="center", size=11)

# ---------------- supporting services ----------------
icon("ecr", label("ECR", "dsp-poc transform image"), "ecr", COMPUTE, 100, 400)
icon("cw", label("CloudWatch Logs", "Lambda + state machine"), "cloudwatch_2", MGMT, 100, 570)
icon("iam", label("IAM roles", "least privilege per function"), "identity_and_access_management", SECURITY, 100, 740)

# ---------------- outside the sandbox ----------------
box("srcacct", "relevate-data account (362403299880)", 1560, 110, 270, 200, fill="none", stroke=STORAGE, font="#3F8624", align="center")
icon("src", label("Source bucket (existing)", "relevatehealth-data", "rh-dsp/pld/ raw .csv.gz"), "s3", STORAGE, 1656, 160)
box("team", "<b>Existing team systems</b> (not touched by the POC)", 1560, 360, 270, 470, fill="none", stroke=GREY, align="center")
box("node", "<b>Node service heartbeat</b><br>becomes the trigger after Jesse reviews the one-line change", 1580, 400, 230, 70)
icon("rs", label("Redshift (warehouse)", "keeps reading Output A", "Parquet, unchanged"), "redshift", ANALYTICS, 1656, 500)
box("enrich", "<b>Enrichment factory endpoint</b> (Cillian)<br>POC: pass-through stub", 1580, 650, 230, 60)
box("prodnote", "No production buckets, l-prod or the real manifest location are written.", 1580, 730, 230, 60)

# ---------------- bottom panels ----------------
box("decided", "<b>Decided (Paul, 10/27)</b><br>"
    "• One transform, two writers: A first, B second; nothing on A's path reads B<br>"
    "• Id history = ledger on the A side; window is config, default full history<br>"
    "• 6 output files per hour, one per publisher (6 vs 3: confirm with Jesse)<br>"
    "• Lake holds events only; quarantine stays in the team format<br>"
    "• Done = all output files exist + manifest; no separate job state",
    260, 880, 420, 180, dashed=False, fill="#EEF7EE", stroke=STORAGE, font="#232F3E")
box("open", "<b>Open / proposed</b><br>"
    "• Parallel hours: id check once per batch, or concurrency 1 for that step<br>"
    "• Lambda vs Fargate (Phase 0 measures the largest hour, target &lt; 5 min)<br>"
    "• Iceberg layout: one table, publisher + day partitions<br>"
    "• Jesse: archive window (Q-A), Redshift key retention (Q-B), O1, O2, reject threshold, Python Lambda OK, DTE-147",
    700, 880, 420, 180, dashed=False, fill="#FDF3E7", stroke=COMPUTE, font="#232F3E")
box("notpoc", "<b>Not in Monday's POC</b><br>"
    "Node heartbeat change · real enrichment · full backfill (1 week only) · "
    "monthly ledger roll-up (by 11/07) · whole-file reject threshold · "
    "NPI checks, bot filtering, restatements (D8, D9, D11) · wider Iceberg lake",
    1140, 880, 360, 120)
box("tags", "<b>Tags</b>: project=dsp-poc, owner=paul, plus the sandbox standard set "
    "(Environment, DataClassification, AutoShutdown, managed_by=terraform)",
    1140, 1010, 360, 55, size=10)

# ---------------- flow edges ----------------
edge("e1", "sched", "sfn", "① hourly", exit=(1, 0.5), entry=(0, 0.5))
edge("e2", "sfn", "find", "② CheckLock,<br>then FindWork", exit=(1, 0.5), entry=(0, 0.5))
edge("e3", "find", "input", "③ list input (21 days),<br>check outputs exist", color=STORAGE, exit=(1, 0.5), entry=(0, 0.5))
edge("e4", "sfn", "xf", "④ Map: 1 file-hour<br>per call, max 2", exit=(0, 0.95), entry=(0, 0.5), points=[(280, 244), (280, 469)], pos=0.5)
edge("e5", "input", "xf", "⑤ read CSV.gz", color=STORAGE, exit=(0, 0.9), entry=(0.8, 0),
     points=[(760, 240), (760, 410), (662, 410)], pos=-0.2)
edge("e6", "xf", "ledger", "⑥ write all ids /<br>id check (D5)", color=STORAGE, both=True, exit=(1, 0.5), entry=(0, 0.5), pos=0.1)
edge("e7", "xf", "quar", "⑦ failed rows,<br>reason codes", color="#DD344C", exit=(1, 0.9), entry=(0, 0.4),
     points=[(810, 500), (810, 711)], pos=0.2)
edge("e8", "xf", "outa", "⑧ Writer A first: tmp key → final key", color=STORAGE, exit=(1, 0.2), entry=(0, 0.5),
     points=[(790, 446), (790, 339)], pos=0.35)
edge("e9", "xf", "outb", "⑨ Writer B second (may fail)", color=GREY, dashed=True, exit=(1, 0.7), entry=(0, 0.5),
     points=[(830, 485), (830, 649)], pos=0.45)
edge("e10", "sfn", "quar", "⑩ RecordManifest: 1 entry per hour", color="#DD344C", exit=(0, 0.75), entry=(0, 0.8),
     points=[(255, 228), (255, 742)], pos=0.5)
edge("e11", "athena", "outa", "⑪ query", color=ANALYTICS, exit=(0.5, 1), entry=(1, 0.3), points=[(1419, 323)])
edge("e12", "duckdb", "outa", "", color=ANALYTICS, exit=(0, 0.5), entry=(1, 0.8), points=[(1300, 450), (1300, 362)])
edge("e13", "src", "input", "DTE-147 cross-account read (pending); POC uses the curated copy", color=GREY, dashed=True,
     exit=(0.5, 0), entry=(0.5, 0), points=[(1695, 130), (919, 130)])
edge("e14", "xf", "fargate", "", color=GREY, dashed=True, arrow=False, exit=(0, 0.9), entry=(0.5, 0), points=[(479, 500)])

# ---------------- sequence diagram, under the HLD (same content as dsp-poc-sequence-diagram-2026-10-28.png) ----------------
SEQ_Y = 1140
vertex("seqhead", "<b>Workflow: one scheduled run</b> (sequence diagram; same content as dsp-poc-sequence-diagram-2026-10-28.png)",
       "text;html=1;align=left;verticalAlign=middle;fontSize=16;fontColor=#232F3E;", 40, SEQ_Y, 1300, 30)
vertex("seqframe", "", "rounded=1;arcSize=1;html=1;fillColor=#FFFFFF;strokeColor=#879196;", 40, SEQ_Y + 36, 1320, 1)  # sized below
seq_cells, seq_w, seq_h = seq.drawio_cells(40, SEQ_Y + 36)
cells[-1] = cells[-1].replace('width="1320" height="1"', f'width="{seq_w}" height="{seq_h}"')
cells.extend(seq_cells)
page_h = SEQ_Y + 36 + seq_h + 40

xml = ('<mxfile host="drawio" type="device">\n  <diagram name="DSP POC HLD" id="dsp-poc-hld">\n'
       '    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
       f'fold="1" page="1" pageScale="1" pageWidth="1900" pageHeight="{page_h}" math="0" shadow="0">\n      <root>\n'
       '        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n        '
       + "\n        ".join(cells) +
       '\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n')

with open(OUT, "w") as f:
    f.write(xml)
print(f"wrote {OUT} ({len(cells)} cells)")
