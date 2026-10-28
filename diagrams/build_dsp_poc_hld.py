#!/usr/bin/env python3
"""Generates dsp-poc-hld-2026-10-28.drawio: AWS high level diagram for the DSP v1 pipeline POC
(DTE-151 / DTE-152). Same look as ~/dsp-analysis-sandbox/docs/aws-hld.drawio (approved 10/22):
official mxgraph.aws4 icons and groups, numbered flow edges, dashed = not built / trial / pending.

This script is the master (Paul, 10/28): change the script and rerun; don't hand-edit the .drawio.

Sources: from-3po/dsp-poc-decisions-paul_2026-10-27_2220.md, from-3po/dsp-poc-what-monday-delivers_2026-10-27_2220.md,
from-3po/dsp-iceberg-pipeline-poc-spec-for-R3_2026-10-24_1645.md, dsp-key-spec-2026-10-27.md.

v2 (Paul, 10/28): Step Functions drawn as the AWS "Step Functions workflow" group with its states inside;
step badges are blue circles whose numbers match the badges in the sequence diagram below.

Export: flatpak run com.jgraph.drawio.desktop --export --format png --embed-diagram --scale 1.5 --border 10 \
        --output dsp-poc-hld-2026-10-28.png dsp-poc-hld-2026-10-28.drawio
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dsp_poc_sequence_diagram as seq  # noqa: E402

OUT = str(Path(__file__).resolve().parent / 'dsp-poc-hld-2026-10-28.drawio')

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


def badge(n):
    """Blue step circle, same colour and numbers as the sequence diagram's badges."""
    return (f'<span style="display:inline-block;width:22px;height:22px;line-height:22px;border-radius:11px;'
            f'background-color:{seq.BADGE_FILL};color:#FFFFFF;font-weight:bold;font-size:14px;text-align:center;">{n}</span>')


def edge(cid, src, tgt, value="", color="#232F3E", dashed=False, exit=None, entry=None, points=(),
         both=False, arrow=True, label_bg="#ffffff", pos=None, step=None, offset=None):
    if step:
        value = badge(step) + (" " + value if value else "")
    style = (f"edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;fontSize=11;labelBackgroundColor={label_bg};"
             f"strokeColor={color};strokeWidth=2;jumpStyle=arc;jumpSize=8;")
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
    if offset:
        pts += f'<mxPoint x="{offset[0]}" y="{offset[1]}" as="offset" />'
    cells.append(f'<mxCell id="{cid}" value="{attr(value)}" style="{style}" parent="1" source="{src}" target="{tgt}" edge="1">'
                 f'<mxGeometry{geo_x} relative="1" as="geometry">{pts}</mxGeometry></mxCell>')


# ---------------- frame ----------------
vertex("title", "<b>DSP v1 pipeline POC: high level diagram</b> · PROPOSED, not built · v2 2026-10-28 · "
       "DTE-151 / DTE-152 · names dsp-poc-* · step numbers match the workflow below",
       "text;html=1;align=left;verticalAlign=middle;fontSize=16;fontColor=#232F3E;", 40, 2, 1500, 30)

group("cloud", "AWS Cloud", "group_aws_cloud_alt", "#232F3E", "#232F3E", 40, 40, 1840, 1230)
group("region", "us-east-1 · relevate-sandbox account (474961012168) · serverless, no VPC needed for the POC",
      "group_region", "#00A4A6", "#147EBA", 60, 80, 1480, 1170, dashed=1)


def store(cid, value, res_icon, fill, x, y, font="#232F3E"):
    """Icon with its label to the right, so arrows can reach it from above and below."""
    style = (f"sketch=0;outlineConnect=0;fontColor={font};gradientColor=none;fillColor={fill};strokeColor=#ffffff;"
             "dashed=0;labelPosition=right;verticalLabelPosition=middle;verticalAlign=middle;align=left;spacingLeft=6;"
             f"html=1;fontSize=12;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res_icon};")
    vertex(cid, value, style, x, y, 78, 78)


def task(cid, value, x, y, w, h):
    """Step Functions task state: white box with a Lambda function glyph on the left, like the AWS workflow icons."""
    vertex(cid, value, "rounded=0;html=1;whiteSpace=wrap;fillColor=#FFFFFF;strokeColor=#232F3E;strokeWidth=1.5;"
           "fontSize=11;fontColor=#232F3E;align=left;verticalAlign=middle;spacingLeft=52;spacingRight=6;", x, y, w, h)
    vertex(cid + "_icon", "", "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#ED7100;"
           "strokeColor=none;dashed=0;html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.lambda_function;",
           x + 9, y + (h - 34) / 2, 34, 34)


# ---------------- left column: trigger + supporting services ----------------
icon("sched", label("EventBridge Scheduler", "hourly, weekdays 07:00-21:00 ET", "stand-in for the Node heartbeat"),
     "eventbridge", APPINT, 100, 150)
icon("ecr", label("ECR", "dsp-poc transform image"), "ecr", COMPUTE, 100, 420)
icon("cw", label("CloudWatch Logs", "Lambdas + state machine"), "cloudwatch_2", MGMT, 100, 600)
icon("iam", label("IAM roles", "least privilege per function"), "identity_and_access_management", SECURITY, 100, 780)

# ---------------- Step Functions workflow (states inside, like the AWS reference diagrams) ----------------
group("sfn", "<b>AWS Step Functions workflow</b><br>dsp-poc (Standard) · 25 min timeout",
      "group_aws_step_functions_workflow", "#CD2264", "#CD2264", 280, 130, 500, 860)
vertex("start", "Start", "ellipse;html=1;fillColor=#FFFFFF;strokeColor=#232F3E;strokeWidth=1.5;fontSize=11;", 505, 180, 50, 50)
task("lock", "<b>CheckLock</b> · dsp-check-lock (zip)<br>ListExecutions RUNNING, minus itself · no S3",
     390, 260, 280, 56)
vertex("locked", "locked?", "rhombus;html=1;fillColor=#FFFFFF;strokeColor=#232F3E;strokeWidth=1.5;fontSize=11;",
       480, 345, 100, 60)
vertex("skipped", "<b>SkippedAlreadyRunning</b><br>(Succeed)", "rounded=1;html=1;whiteSpace=wrap;fillColor=#F2F3F3;"
       "strokeColor=#879196;fontSize=10;fontColor=#232F3E;", 610, 350, 150, 50)
task("find", "<b>FindWork</b><br>hours missing a Parquet file,<br>oldest first, cap 6", 390, 440, 280, 60)
vertex("map", "<b>ProcessHours</b> (Map) · 1 file-hour per item · max 2 in parallel",
       "rounded=1;arcSize=4;dashed=1;html=1;fillColor=#FDF2F7;strokeColor=#CD2264;fontSize=11;fontColor=#232F3E;"
       "align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;", 300, 540, 440, 240)
task("xf", "<b>Transform</b> (container image:<br>Python + DuckDB)<br>steps 1-4, key spec D1-D12", 390, 580, 280, 170)
vertex("fargate", "", "sketch=0;outlineConnect=0;gradientColor=none;fillColor=#ED7100;strokeColor=#ffffff;html=1;"
       "aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.fargate;opacity=55;", 318, 596, 50, 50)
vertex("fargate_l", "Fargate<br>fallback", "text;html=1;align=center;verticalAlign=top;fontSize=10;fontColor=#545B64;",
       308, 650, 70, 34)
task("manifest", "<b>RecordManifest</b><br>1 entry per hour", 390, 820, 280, 56)
vertex("end", "End", "ellipse;html=1;fillColor=#FFFFFF;strokeColor=#232F3E;strokeWidth=3;fontSize=11;", 505, 920, 50, 50)

# ---------------- data stores (right column, labels beside the icons) ----------------
store("input", label("S3: input (sandbox)", "curated copy of rh-dsp/pld/", "hourly pld_*.csv.gz"), "s3", STORAGE, 900, 431)
store("outa", label("S3: rhde-pg-dsp-poc-parquet", "Output A, the contract: Parquet zstd,", "1 file per publisher per hour,",
                    "6 publishers; empty file if no rows"), "s3", STORAGE, 900, 570)
store("ledger", label("S3: id ledger", "Parquet, 1 small file per hour,", "every row's id before filtering,",
                      "seeded with ~40M historical ids"), "s3", STORAGE, 900, 665)
store("quar", label("S3: quarantine (sandbox copy)", "rhde-quarantine format: manifests/", "+ failed-keys/, reason code per row"),
      "s3", STORAGE, 900, 809)

box("trial", "<b>Time-boxed trial (Writer B)</b> · never blocks A", 1240, 715, 280, 250,
    fill="#FAFAFA", font="#545B64", size=12)
store("outb", label("S3 Tables bucket", "rhde-pg-dsp-poc-iceberg", "events table, same rows as A"),
      "s3", GREY, 1260, 746, font="#545B64")
box("trialnote", "Partitioned by publisher + day (proposed).<br><b>Next, only if Iceberg is kept:</b> "
    "raw_events (from the ledger, one way A → B) · lake quarantine view",
    1255, 850, 250, 100, fill="#FFFFFF", size=10)

store("athena", label("Athena · DuckDB", "query A and B", "(comparison table)"), "athena", ANALYTICS, 1260, 450)

# ---------------- outside the sandbox ----------------
box("srcacct", "relevate-data account (362403299880)", 1580, 110, 270, 200, fill="none", stroke=STORAGE, font="#3F8624", align="center")
icon("src", label("Source bucket (existing)", "relevatehealth-data", "rh-dsp/pld/ raw .csv.gz"), "s3", STORAGE, 1676, 160)
box("team", "<b>Existing team systems</b> (not touched by the POC)", 1580, 360, 270, 470, fill="none", stroke=GREY, align="center")
box("node", "<b>Node service heartbeat</b><br>becomes the trigger after Jesse reviews the one-line change", 1600, 400, 230, 70)
icon("rs", label("Redshift (warehouse)", "keeps reading Output A", "Parquet, unchanged"), "redshift", ANALYTICS, 1676, 500)
box("enrich", "<b>Enrichment factory endpoint</b> (Cillian)<br>POC: pass-through stub", 1600, 650, 230, 60)
box("prodnote", "No production buckets, l-prod or the real manifest location are written.", 1600, 730, 230, 60)

# ---------------- bottom panels ----------------
box("decided", "<b>Decided (Paul, 10/27-10/28)</b><br>"
    "• One transform, two writers: A first, B second; nothing on A's path reads B<br>"
    "• POC owns two output buckets: Parquet (S3) + Iceberg (S3 Tables table bucket)<br>"
    "• CheckLock = small zip Lambda, Step Functions API only, no S3<br>"
    "• Id history = ledger on the A side; window is config, default full history<br>"
    "• 6 output files per hour, one per publisher (6 vs 3: confirm with Jesse)<br>"
    "• Lake holds events only; quarantine stays in the team format<br>"
    "• Done = all output files exist + manifest; no separate job state",
    260, 1030, 440, 200, dashed=False, fill="#EEF7EE", stroke=STORAGE, font="#232F3E")
box("open", "<b>Open / proposed</b><br>"
    "• Parallel hours: id check once per batch, or concurrency 1 for that step<br>"
    "• Lambda vs Fargate (Phase 0 measures the largest hour, target &lt; 5 min)<br>"
    "• Iceberg layout: one table, publisher + day partitions<br>"
    "• Known gap: FindWork checks only the Parquet bucket, so a failed Writer B hour is not retried<br>"
    "• Jesse: archive window (Q-A), Redshift key retention (Q-B), O1, O2, reject threshold, Python Lambda OK, DTE-147",
    720, 1030, 440, 200, dashed=False, fill="#FDF3E7", stroke=COMPUTE, font="#232F3E")
box("notpoc", "<b>Not in Monday's POC</b><br>"
    "Node heartbeat change · real enrichment · full backfill (1 week only) · "
    "monthly ledger roll-up (by 11/07) · whole-file reject threshold · "
    "NPI checks, bot filtering, restatements (D8, D9, D11) · wider Iceberg lake",
    1180, 1030, 340, 125)
box("tags", "<b>Tags</b>: project=dsp-poc, owner=paul, plus the sandbox standard set "
    "(Environment, DataClassification, AutoShutdown, managed_by=terraform)",
    1180, 1170, 340, 60, size=10)

# ---------------- workflow edges (inside the state machine) ----------------
# SkippedAlreadyRunning is a Succeed state: it ends the run itself, so it has no edge to End.
edge("e1", "sched", "start", "hourly", step=1, exit=(1, 0.5), entry=(0, 0.5), points=[(330, 189), (330, 205)])
edge("e2", "start", "lock", "", step=2, exit=(0.5, 1), entry=(0.5, 0))
edge("s1", "lock", "locked", "", exit=(0.5, 1), entry=(0.5, 0))
edge("s2", "locked", "skipped", "yes", exit=(1, 0.5), entry=(0, 0.5))
edge("s3", "locked", "find", "no", exit=(0.5, 1), entry=(0.5, 0))
edge("e4", "find", "xf", "hours[]: 1 file-hour per call", step=4, exit=(0.5, 1), entry=(0.5, 0), pos=-0.3)
edge("s5", "xf", "manifest", "", exit=(0.5, 1), entry=(0.5, 0))
edge("s6", "manifest", "end", "", exit=(0.5, 1), entry=(0.5, 0))
edge("s7", "xf", "fargate", "", color=GREY, dashed=True, arrow=False, exit=(0, 0.3), entry=(1, 0.5))

# ---------------- data edges: each store sits level with the state that uses it ----------------
edge("e3a", "find", "input", "list input (21 days)", step=3, color=STORAGE, exit=(1, 0.5), entry=(0, 0.5), offset=(0, -12))
edge("e3b", "find", "outa", "check outputs exist", step=3, color=STORAGE, exit=(1, 0.85), entry=(0, 0.13),
     points=[(845, 491), (845, 580)], pos=-0.45, offset=(0, 12))
edge("e5", "input", "xf", "read CSV.gz", step=5, color=STORAGE, exit=(0, 0.92), entry=(1, 0.04),
     points=[(815, 503), (815, 587)], pos=0.55, offset=(0, 10))
edge("e8", "xf", "outa", "Writer A first: tmp → final key", step=8, color=STORAGE, exit=(1, 0.17), entry=(0, 0.5),
     offset=(0, 14))
edge("e6", "xf", "ledger", "write all ids / id check (D5)", step=6, color=STORAGE, both=True, exit=(1, 0.73), entry=(0, 0.5),
     offset=(0, -12))
edge("e9", "xf", "outb", "Writer B second (may fail)", step=9, color=GREY, dashed=True, exit=(1, 0.85), entry=(0, 0.5),
     points=[(880, 724.5), (880, 785)], pos=0.4)
edge("e7", "xf", "quar", "failed rows, reason codes", step=7, color="#DD344C", exit=(1, 0.95), entry=(0, 0.25),
     points=[(850, 741.5), (850, 828.5)], pos=0.3, offset=(-40, 0))
edge("e10", "manifest", "quar", "RecordManifest", step=10, color="#DD344C", exit=(1, 0.5), entry=(0, 0.5), offset=(10, 12))
edge("e11", "athena", "outa", "query", step=11, color=ANALYTICS, exit=(0, 0.5), entry=(1, 0.3),
     points=[(1225, 489), (1225, 593)], pos=-0.6)
edge("e13", "src", "input", "DTE-147 cross-account read (pending); POC uses the curated copy", color=GREY, dashed=True,
     exit=(0.5, 0), entry=(0.5, 0), points=[(1715, 118), (939, 118)])

# ---------------- sequence diagram, under the HLD (same content as dsp-poc-sequence-diagram-2026-10-28.png) ----------------
SEQ_Y = 1310
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
