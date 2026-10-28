# DSP pipeline + Iceberg POC

Proof of concept for the DSP v1 pipeline (Jira DTE-151; HLD DTE-152). Hourly DSP file in, one transform
(Python + DuckDB in a container Lambda), two outputs:

- **Path A:** Parquet files, 6 per hour (one per publisher), whole-file replacement. The deliverable.
- **Path B:** the same rows in an S3 Tables (Iceberg) `events` table. Time-boxed trial; never blocks Path A.

Orchestration: EventBridge Scheduler (stand-in for the Node heartbeat) -> Step Functions (lock check,
find work, Map over hours, record manifest). Quarantine uses the team's rhde-quarantine format.

## Layout

| Path | What |
|---|---|
| `docs/` | POC plan (draft), evidence notes, queued edits |
| `docs/from-3po/` | Design baseline specs (3PO 10/24, Paul's decisions 10/27, what Monday delivers) |
| `docs/lambda/` | Explained sample Lambdas (Python). `dsp-check-lock/`: the CheckLock step, with tests |
| `diagrams/` | HLD + workflow (.drawio), two-path overview, and the scripts that generate them |
| `src/transform/` | Transform Lambda (not started) |
| `infra/` | Terraform for Step Functions, Lambda, S3 Tables (not started) |
| `sql/`, `tests/` | Queries and tests (not started) |

Related: `pgnorthrim/dsp-analysis-sandbox` (EC2 + DuckDB + Aurora sandbox the POC measures against).

## Diagrams

Regenerate with `python -I diagrams/build_dsp_poc_hld.py` (also builds the sequence diagram) and
`python -I diagrams/build_dsp_poc_two_paths.py`. The scripts are the master: change the script and
rerun, don't hand-edit the `.drawio`. HLD PNG: draw.io CLI (command in the script's docstring); sequence PNG:
`rsvg-convert -z 1.5`. Step badges in the HLD and the sequence diagram use the same numbers.
