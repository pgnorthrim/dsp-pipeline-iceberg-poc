# DSP Iceberg Pipeline POC: Spec for R3

Oct 24, 2026 · @paul

## Purpose and context

Build a proof of concept of the v1 DSP pipeline: every hour, turn one gzipped DSP CSV into three clean Parquet files, and in parallel test Amazon S3 Tables (managed Iceberg) as the storage layer. Paul demos it to Jesse before anything scales.

The ask comes from the Relevate status meeting on Fri 2026-10-23 (transcript: `transcribed_2026-10-23_12-00-54_relevate.docx`, Drive folder meeting-transcripts-videos, roughly 0:36 to 0:52). After Paul showed the sandbox DuckDB + Postgres query engine, Jesse said:

- **Play with S3 Tables.** Paul has the most Iceberg experience on the team, so he is the one to try it and see whether the team likes it.
- **The pipeline is file in, file out.** Every hour, pick up a generic DSP gzipped CSV and output three Parquet files: one each for Veradigm, CareCloud and DoseSpot (Jesse was unsure of the third name; confirm).
- **In the transform:** check for duplicate IDs and do light syntactic cleanup, for example casting dash-only zip codes to null. No business interpretation of the data; the data warehouse team does that downstream.
- **It must fit the existing heartbeat**, a Node cron runner that wakes every 30 minutes at :05 and :35.
- **Orchestration is open,** except avoid MWAA. Step Functions is acceptable.
- **Paul is responsible for enrichment.**

The sandbox EC2 + DuckDB + Postgres work (see `sandbox-aws-ec2-phased-plan-for-R3_2026-10-23_0745.md`) stays as the analysis environment. This POC is separate: it is the pipeline.

## Decisions and design principles

The design is serverless: Step Functions orchestrating a containerized Python + DuckDB Lambda, with two writers fed from one transform. These are decided unless Phase 0 fails.

| Layer | Choice | Why | Rejected for v1 |
| --- | --- | --- | --- |
| Trigger | Existing Node heartbeat puts an event on EventBridge | Stays inside Jesse's harness; minimal Node code | A new scheduler |
| Orchestration | AWS Step Functions (Standard) | Lock, retries, visible run history; Jesse accepted it | MWAA (Jesse said avoid) |
| Compute | Container-image Lambda: Python + DuckDB | One file-hour per invocation; no box to run; cheap at 24 runs/day | Glue/Spark (parallelism not needed), EC2 shell-out (ties pipeline to a box) |
| Transforms | Plain SQL in DuckDB, called from Python | Job is split + dedupe + cleanup, not a model graph | dbt |
| Output A | Hourly Parquet files in S3 | The contract Jesse described |  |
| Output B | S3 Tables (Iceberg) in a sandbox table bucket | The experiment Jesse asked for |  |
| Fallback compute | Same image on Fargate | Only if an hour exceeds Lambda limits |  |

Principles R3 should hold to:

1. **One transform, two writers.** Everything up to the write is shared; the writer is pluggable. If S3 Tables fails, the Parquet contract still ships.
2. **No separate job-run state.** Jesse is nervous about it. "Already processed?" comes from the output bucket plus the existing manifest format.
3. **Idempotent per file-hour.** Rerunning an hour gives the same output and never duplicates rows.
4. **Syntactic cleanup only.** No interpretation, imputation or business rules.
5. **Measure before committing.** Phase 0 decides Lambda vs Fargate.

## Why this approach: the case for Monday

The work is a bounded, idempotent unit (one file-hour) triggered on a schedule with no state between runs. That is the shape serverless handles best, and every alternative either adds machinery the data doesn't need or leaves the lock and run history to be hand-built.

**What this design gives Jesse, mapped to what he asked on Friday:**

- **"How does it lock?"** The Step Function checks for a running execution and discards itself; a 25-minute timeout means a stuck run can't hold the lock past the next heartbeat. It's the pattern Cillian already uses in his Glue jobs.
- **"Fit the heartbeat."** The Node change is one EventBridge put. Everything else lives outside the monolith.
- **"Nervous about separate state."** None added. Done-ness is the output files plus the existing manifests.
- **"Play with S3 Tables."** Dual writers give a clean comparison: same input, same logic, only the storage differs. And the experiment can't break the contract.
- **"Get off the single-node runtime"** (Jesse, after this pipeline). This is a step in that direction, not another thing on the box.
- **Historical load on a tag.** A Distributed Map fans out the backfill one hour per invocation, so no Spark cluster is needed for it.

**Alternatives considered:**

| Alternative | What it's good at | Why not for v1 |
| --- | --- | --- |
| Node heartbeat shells out to DuckDB on the EC2 | Fastest to stand up; Jesse explicitly OK'd it; nothing new to deploy | Lock, retries and run history all hand-built; ties the pipeline to one oversized box; moves away from "off single-node." The strongest alternative: the fallback if speed of delivery wins Monday. |
| AWS Glue (Spark) | Parallel compute; most mature S3 Tables write path | Hourly files don't need Spark; startup time and DPU minimums cost more than the work. Kept as a fallback writer. |
| dbt (with DuckDB or Athena) | A graph of SQL models with tests and docs; the data warehouse team uses it | The job is split, dedupe, cleanup, not a model graph; dbt doesn't handle trigger, lock, manifest or enrichment. Fits downstream, not here. |
| MWAA (managed Airflow) | Full DAG orchestration | Jesse said avoid: conflicts with the cron runner. Heavy for one job. |
| Fargate as the primary compute | No 15-minute limit | Slower start and more cost for no gain if hours finish in minutes. Same image is the built-in fallback. |
| Write everything in Node inside the monolith | No new deployable | Adds to the monolith Jesse wants to break up; DuckDB and Iceberg tooling are Python-first. |

**The honest weak spots, and the answers:**

- **"Lambda has a 15-minute cap."** Phase 0 measures the largest hour before anything is built. Target is under 5 minutes; if not, the same image runs on Fargate with no redesign.
- **"It's a new deployable for a Node team."** True. It's one container image and one state machine, all in code, with a README. That's the cost of leaving the monolith, which Jesse already wants.
- **"DuckDB's S3 Tables support is experimental."** Only Writer B depends on it, and PyIceberg is a ready fallback in the same image. The Parquet contract doesn't touch it.
- **"Enrichment lives in the Node code."** The design calls Cillian's factory endpoint rather than rebuilding it, which is the direction he's already taking.
- **"Isn't this just your favorite pattern?"** Fair question, and it was asked. The EC2 shell-out is a real competitor for speed. This design wins on lock, run history, backfill and direction. If Monday's priority is shipping the Parquet contract this week, start on the EC2 and move to this after.

## Architecture overview

&#91;embedded content: DSP POC architecture · trigger, transform, two writers\]

The heartbeat only fires an event; the Step Function locks and runs each file-hour through one transform Lambda, which writes the Parquet contract first and the S3 Tables experiment second. If Phase 0 shows an hour is too big for Lambda, the same image runs on Fargate in the transform's place.

Text version, for markdown copies where the diagram doesn't render:

```
Node heartbeat (:05/:35) --> EventBridge (dsp.heartbeat) --> Step Functions
                                                             (CheckLock, FindWork,
                                                              Map over hours, max 2,
                                                              RecordManifest)
                                                                    |
                                                                    v
Input bucket (gzipped DSP CSV) ----------------------> Transform Lambda <--> Enrichment endpoint
                                                     (Python + DuckDB,         (Cillian's factory)
                                                      one file-hour)
                                                       |            |
                                          Writer A (first)      Writer B (second)
                                          Parquet, 3 files/hr   S3 Tables (Iceberg)
                                          THE CONTRACT          THE EXPERIMENT

Fallback: same container image on Fargate if an hour exceeds Lambda limits.
```

## Phase 0: largest-hour go/no-go test

Before building anything else, prove the biggest hourly DSP file finishes comfortably inside a Lambda. This one number decides Lambda vs Fargate.

Steps for R3:

1. From the delivered DSP files already pulled into the sandbox, list every hourly file with its compressed size and row count. Report min, median, p95 and max.
2. Take the largest file. Decompress it and record the uncompressed size and the gzip ratio.
3. On the EC2, run the Phase 1 transform against it with DuckDB `memory_limit` set to 8GB and `threads` set to 6, to mimic a 10 GB Lambda. Record wall time and peak memory.
4. Build the container image and run the same file in a real Lambda at 10,240 MB memory and 10,240 MB ephemeral storage. Record duration, max memory used and cold-start time.

Decision rule:

| Largest-hour Lambda duration | Decision |
| --- | --- |
| Under 5 minutes | Lambda. Proceed. |
| 5 to 12 minutes | Lambda, plus wire the Fargate fallback route now |
| Over 12 minutes, or memory errors | Fargate as primary, same image and design |

The 5-minute target leaves headroom under both Lambda's 15-minute cap and the 30-minute heartbeat. Jesse said an hour taking over 30 minutes would be a different conversation.

Write the results to `dsp-poc-phase0-results_<date>_<time>.md` in claude-sync/C-3P0-SYNC so Paul and 3PO can see them.

## Phase 1: shared transform core

One Python module, `dsp_transform`, takes one hourly input file and returns three clean, vendor-split batches. Both writers consume its output; it never writes to S3 itself.

Input: `s3://<input bucket>/<prefix>/<file>.csv.gz` plus the target hour (from the file name or the event).

Steps, all in one DuckDB connection:

1. **Read** the gzipped CSV straight from S3 with `read_csv` and an explicit column list and types. Never rely on type sniffing; the schema is the contract.
2. **Validate the header.** If columns are missing, extra or renamed, fail the run with a clear error. Do not guess.
3. **Syntactic cleanup:** trim whitespace; cast placeholder values (`-`, empty string, `NULL`, `N/A`) to null; cast zip codes made of only a dash to null; normalize timestamps to UTC.
4. **Flag known test values:** MPIs and IDs starting with five or ten 9s or 8s are test data that leaked into production (Jesse, 2026-10-02, about the vendor event feeds). If the DSP file carries these fields, route them to quarantine, not output.
5. **Deduplicate** on the record's natural ID within the file. Keep one row, count the rest. Paul to confirm which column is the ID.
6. **Split by vendor** into Veradigm, CareCloud and DoseSpot batches. Rows with an unknown vendor go to quarantine.
7. **Enrich** (Phase 4). Rows that fail enrichment go to quarantine with a reason.
8. **Return** three batches plus counts: rows in, rows out per vendor, duplicates dropped, quarantined by reason.

The output schema is not agreed yet. Jesse wants to see it. Paul drafts it from his column-population and format analysis, and R3 implements it as a typed DuckDB `CREATE TABLE` or explicit `SELECT` with casts, kept in one file (`schema/dsp_output_v1.sql`) so a schema change is one diff.

Unit tests: a small fixture CSV with one of each case (duplicate, dash zip, test MPI, unknown vendor, bad header) and expected counts.

## Phase 2: dual writers

Two writers take the same three batches. Writer A is the deliverable; Writer B is the experiment and must never block A.

**Writer A: Parquet (the contract)**

- One Parquet file per vendor per hour, written with DuckDB `COPY ... TO ... (FORMAT parquet, COMPRESSION zstd)`.
- Path pattern, until Jesse provides the real folder: `s3://<output bucket>/dsp/<vendor>/<yyyy>/<mm>/<dd>/<vendor>_<yyyymmdd>_<hh>.parquet` (Jesse's naming idea: the input name with `dsp` replaced by the vendor).
- Write to a temporary key, then copy to the final key, so a reader never sees a half-written file.
- The existence of all three final files means "this hour is done."

**Writer B: S3 Tables (the experiment)**

- A sandbox table bucket, for example `relevate-sandbox-dsp`, with a namespace `dsp` and three tables: `veradigm`, `carecloud`, `dosespot`.
- Same columns as the Parquet schema, plus `source_file` and `loaded_at` for lineage.
- Partition by hour of the event timestamp (Iceberg hidden partitioning, `hours(event_ts)`).
- Load as one commit per table per hour. Before appending, delete rows where `source_file` matches this run's file, so a rerun replaces the hour instead of duplicating it.
- Primary path: DuckDB `iceberg` extension attached to the table bucket by ARN with `ENDPOINT_TYPE s3_tables`. DuckDB marks S3 Tables support as experimental, so test writes first.
- Fallback path: PyIceberg using the S3 Tables Iceberg REST endpoint, writing an Arrow table exported from DuckDB. Keep both in the image behind a config flag.
- Leave S3 Tables' automatic maintenance (compaction, snapshot expiry, unreferenced file removal) on defaults; part of the demo is showing it working without any code.

**Failure isolation:** Writer A runs first. If Writer B fails, the Step Function records the failure and still marks the hour done for A. Do not retry B forever; log it for the comparison.

## Phase 3: orchestration and locking

The heartbeat fires an event; a Step Function does the rest and refuses to run twice at once.

**Trigger.** The Node heartbeat runs every 30 minutes at :05 and :35. When it reaches the DSP job, it puts one event on EventBridge (detail-type `dsp.heartbeat`). That is the only Node change: a few lines, reviewed by Jesse. An EventBridge rule targets the Step Function. For the POC, before touching the Node code, use an EventBridge Scheduler rule at the same minutes as a stand-in.

**Lock.** Jesse's question was how it locks. Use the pattern Cillian used in his Glue jobs: if a run is in flight, the new one discards itself.

- First state: `ListExecutions` on this state machine with `statusFilter = RUNNING`. If any execution other than this one is running, go to a `Succeed` state named `SkippedAlreadyRunning`.
- Set a state-machine timeout of 25 minutes so a stuck run can never hold the lock past the next heartbeat.

**State machine steps:**

1. `CheckLock` (above).
2. `FindWork`: a small Lambda lists input files for the last 21 days (matching Jesse's lookback) and returns the hours whose three output Parquet files do not all exist. Cap the list per run (start with 6 hours) so a backlog drains over several heartbeats.
3. `ProcessHours`: an inline `Map` over the list, `MaxConcurrency` 2, each item invoking the transform Lambda for one file-hour.
4. `RecordManifest`: write one manifest entry per hour processed (Phase 4).
5. `Summarize`: emit counts to CloudWatch (rows in/out, quarantined, duration per writer).

**Retries.** Retry the transform task twice on `Lambda.ServiceException`, `Lambda.TooManyRequestsException` and timeouts, with backoff. Do not retry on schema-validation errors; those need a human.

**Fargate route.** If Phase 0 says so, add a `Choice` before the transform: files above a size threshold go to an ECS `RunTask` with the same image.

## Phase 4: enrichment, manifests and restatements

Reuse the team's existing pieces rather than building parallel ones: Cillian's enrichment, the existing manifest format, and today's restatement procedure.

**Enrichment.** Jesse said Paul owns enrichment, and running outside the Node code means replicating how Cillian gets enrichment data. Cillian is turning the current `enrich utm media` code into a factory endpoint: pass keys, get back a hash map of values, with its own cache. His PR should be ready for review around Mon 2026-10-26.

- POC approach: wrap enrichment behind one interface in the transform (`enrich(batch) -> batch, failures`). Version 1 can be a stub that passes rows through, so Phases 0 to 3 are not blocked.
- Then implement it against Cillian's endpoint once it lands. Do not read the enrichment database directly, and do not copy his code; Paul said he doesn't want to build a parallel version.
- The Lambda will need VPC access to reach it, plus credentials from Secrets Manager. Get the secret names from Cillian.
- Track his stored-procedure updates. Jesse wants to know the pipeline uses the current one.

**Manifests.** If the pipeline needs a record of what it did, use the existing manifest format from the `l-event-tracking` repo, written to the manifest location in `l-prod` (sandbox equivalent for the POC). Per Jesse, it records the file processed, a job ID, success or failure, and the number of rows quarantined. Add nothing beyond what the format already has without asking Paul.

**Restatements.** DSP vendors have never restated, so keep this simple:

- "Is this hour done?" = do all three output Parquet files exist. Jesse called it a bad pattern but approved it because it matches how restatement works today.
- To force a rerun: archive the hour's output files to an `archive/` prefix, record the forced regeneration, then let the next heartbeat pick the hour up. This mirrors today's tooling.
- The likely real case is a new output schema: archive all old files, regenerate with the new schema.
- On S3 Tables, the same rerun replaces the hour's rows in one commit, and the previous snapshot stays available for time travel. Show this side by side in the demo.

## Phase 5: historical backfill

The backfill is a separate state machine using the same transform Lambda, run until it's right and then retired to a git tag, as Jesse and Eric did for their pipeline.

- **Separate state machine:** `dsp-backfill`, a Step Functions Distributed Map over a list of historical input files (an S3 inventory or a manifest CSV), one child execution per file-hour.
- **Concurrency cap:** start at 10 and raise only after checking load on the enrichment endpoint. Backfill concurrency is the main way to overload Cillian's endpoint or its database.
- **Same code path:** the backfill calls the identical transform and writers. Anything backfill-only (one-off fixes for old file formats, for example) lives on a `historical` branch.
- **Branching, per Jesse:** build the historical code on its own branch, run it until it's correct, tag it (for example `dsp-historical-v1`), and merge only the active pipeline code to main. The tag keeps a runnable version if the historical load is ever needed again, without carrying dead code.
- **Scope for the POC:** backfill one week, not all history. It's enough to prove fan-out, idempotency and S3 Tables behavior at volume.
- **Verification:** for each backfilled hour, compare row counts with Paul's existing DuckDB analysis of the same raw files in the sandbox. Differences go in the Phase 0 results file.

## Demo plan and success criteria

The demo answers Jesse's two questions: does the v1 contract work inside the heartbeat, and do we like S3 Tables.

Demo script (about 15 minutes):

1. Show one heartbeat-triggered run in the Step Functions console: lock check, the hours found, the per-hour Map, the result.
2. Fire a second trigger mid-run and show it discarding itself.
3. Open the three hourly Parquet outputs; query them from DuckDB.
4. Query the same hour in S3 Tables from DuckDB and from Athena.
5. Force a rerun of one hour. Show the Parquet archive-and-regenerate, then the S3 Tables snapshot history and a time-travel query to the old version.
6. Show the comparison table below.

Success criteria:

- [ ] Largest hour finishes under 5 minutes in Lambda (or the Fargate route works)
- [ ] Three correct Parquet files per hour, matching the agreed schema
- [ ] Rerunning an hour produces identical output with no duplicates
- [ ] Overlapping trigger is discarded, never run twice
- [ ] Duplicate, dash-zip and test-value rows are counted and quarantined
- [ ] S3 Tables holds the same rows as the Parquet files for every hour loaded
- [ ] One week of backfill completed and reconciled

Comparison table to fill during the POC:

| Measure | Parquet files | S3 Tables |
| --- | --- | --- |
| Write time per hour (s) |  |  |
| Files written per day |  |  |
| Query time, one day, DuckDB (s) |  |  |
| Query time, one day, Athena (s) |  |  |
| Steps to restate one hour |  |  |
| Code needed for maintenance |  |  |
| Storage cost per month (estimate, USD) |  |  |
| Readable by the data warehouse team as-is |  |  |

## Build instructions and guardrails for R3

Work in the Relevate Health sandbox AWS account only, in small reviewable steps, and stop for Paul at each checkpoint.

**Order of work:**

1. Phase 0 test. **Checkpoint:** post results; Paul decides Lambda vs Fargate.
2. `dsp_transform` with unit tests, run locally on the EC2 against real files.
3. Container image and Writer A, invoked by hand for one hour. **Checkpoint:** Paul reviews the output schema with Jesse.
4. Writer B against a sandbox table bucket.
5. Step Function, lock and EventBridge Scheduler stand-in. **Checkpoint:** before any change to the Node heartbeat, Paul reviews with Jesse.
6. Enrichment against Cillian's endpoint, once available.
7. One-week backfill and the comparison table.

**Repository layout:**

```
dsp-pipeline/
  src/dsp_transform/     # transform core, no S3 writes
  src/writers/           # parquet_writer.py, s3tables_writer.py
  src/handlers/          # lambda entrypoints: find_work, process_hour
  schema/dsp_output_v1.sql
  infra/                 # IaC for Lambda, ECR, Step Functions, EventBridge, table bucket
  statemachines/         # dsp-pipeline.asl.json, dsp-backfill.asl.json
  tests/fixtures/
  Dockerfile
  README.md
```

**Container image:** base it on the AWS Lambda Python image. Install `duckdb`, `pyarrow` and `pyiceberg`. Pre-install the DuckDB `httpfs` and `iceberg` extensions at build time into a directory inside the image, and point DuckDB at it. Give the entrypoint a mode flag so the same image runs on Fargate.

**Guardrails:**

- Never write to production buckets, `l-prod`, or the real manifest location. Use sandbox equivalents and prefix everything with `dsp-poc-`.
- Never modify the Node heartbeat code, the enrichment database or Cillian's code. Propose changes to Paul in writing.
- Do not touch VPCs other than the one Paul took over. Leave the apiary, API gateway and ln-for-dev VPCs alone.
- Tag every resource `project=dsp-poc` and `owner=paul` so it can be found and torn down.
- Keep secrets in Secrets Manager; never in code, environment files or the repo.
- Use infrastructure as code for everything. If something is clicked in the console to test, recreate it in code before the checkpoint.
- When unsure, write the question to the open questions list in the sync folder and continue with the next unblocked step.

## Gotchas

Most of these bite inside Lambda, not on the EC2, so test in a real Lambda early.

| Gotcha | What happens | Fix |
| --- | --- | --- |
| Lambda filesystem is read-only except `/tmp` | DuckDB fails writing its home or temp files | Set `home_directory` and `temp_directory` to paths under `/tmp` |
| No memory cap on DuckDB | The function is killed instead of spilling | Set `memory_limit` to about 80% of the Lambda's memory |
| Extensions downloaded at runtime | Fails in a VPC with no outbound internet; slow cold starts | Pre-install `httpfs` and `iceberg` in the image |
| gzip expands 5 to 10 times | `/tmp` or memory runs out on big hours | Stream from S3; size from Phase 0 numbers |
| DuckDB S3 Tables support is experimental | Writes may fail or behave oddly | Test writes first; keep the PyIceberg fallback |
| Credentials in Lambda | DuckDB does not see the role automatically | Create the S3 secret with the `credential_chain` provider |
| VPC Lambda reaching S3 | Slow or failing S3 calls without a route | Add an S3 gateway endpoint to the VPC |
| Partial Parquet writes | A reader sees a half-written hour | Write to a temp key, then copy to the final key |
| Backfill concurrency | Overloads the enrichment endpoint or database | Cap Distributed Map concurrency; raise slowly |
| Overlapping heartbeats | Two runs process the same hour | `CheckLock` state plus 25-minute timeout |
| S3 Tables and plain S3 are different services | Bucket policies and APIs differ | Use the `s3tables` APIs and table-bucket policies for Writer B |

## Open questions

The biggest is the output contract: Jesse described plain Parquet files in a folder, and S3 Tables changes how consumers read.

| Question | Who answers | Blocks |
| --- | --- | --- |
| Should S3 Tables stay an internal layer with Parquet exported from it, or can consumers (the data warehouse team on Redshift) read Iceberg directly? | Jesse | Long-term design, not the POC |
| What are the real input and output bucket paths? Jesse said he'll give a folder later. | Jesse | Final paths only |
| Is the third vendor DoseSpot? Jesse wasn't sure. | Jesse | Vendor split |
| What column is the record's natural ID for deduplication? | Paul | Phase 1 |
| What is the v1 output schema? Jesse wants to see it. | Paul, then Jesse | Writer A sign-off |
| Which fields need enrichment for DSP, and what does Cillian's endpoint expect? | Cillian | Phase 4 |
| Partition by hour, day, week or month? The data warehouse team prefers day; Jesse suggested sequential buckets by week or month if no restatements. | Jesse | S3 Tables partition spec |
| Where do sandbox manifests live? | Paul | Phase 4 |
| Which infrastructure-as-code tool does the team use? | Paul | Phase 2 onward |

## Background for R3: people, systems, terms

Context from the meetings that R3 wasn't in.

| Name | What it is | Why it matters here |
| --- | --- | --- |
| Jesse (Jessey Reed) | Paul's lead | Approves the design, the schema and any Node change |
| Cillian Kennedy | Engineer on the web pipeline | Owns the enrichment code and factory endpoint; built the Glue-job lock pattern |
| David Powell | Engineer on the email pipeline | Parallel file-in/file-out work; useful to compare notes |
| Scott Clair | Team member | Receives Paul's analysis reports |
| Eric | Engineer on an earlier pipeline | Source of the historical-branch-on-a-tag pattern |
| Data warehouse team (data management team) | Downstream consumer | Classic medallion on Redshift, Dagster, dbt, Great Expectations; runs nightly; the team restatements go to |
| Steve | Consumer of output files | Picks up regenerated files after a schema change |
| Heartbeat | Node cron runner, every 30 min at :05 and :35 | Wakes all enabled jobs; two run at once, others queue, one queued per job; looks back 21 days |
| File in, file out | Team rule | Pipelines turn input files into output files; internal tables are stepping stones, not products |
| Manifests | Record of files processed | Code in `l-event-tracking`, buckets in `l-prod`; job ID, status, rows quarantined |
| Quarantine | Rows that fail validation or enrichment | Counted and kept, not dropped silently |
| DSP feed | Hourly gzipped CSV, one schema across vendors | Split into Veradigm, CareCloud, DoseSpot Parquet files |
| Sandbox | Relevate Health sandbox AWS account | Where all POC resources live |
| S3 Tables | AWS-managed Iceberg tables in table buckets | The experiment; automatic compaction and snapshot cleanup |

Related docs in claude-sync/C-3P0-SYNC: `sandbox-aws-ec2-phased-plan-for-R3_2026-10-23_0745.md` (the analysis environment) and `relevate-2026-10-02-paul-jessey-summary_2026-10-03_2217.md` (Jesse's earlier guidance on vendor data quirks).
