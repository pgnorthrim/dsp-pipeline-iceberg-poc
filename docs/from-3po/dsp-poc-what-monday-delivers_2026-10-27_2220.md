# DSP v1 Pipeline POC: What Monday Delivers

2026-10-27 · Paul Guidry

> Markdown copy for R3 of the team-facing Claude Doc (https://claude.ai/artifact/NkYA4RSMWk4QCFtyC4dUr7), as of 2026-10-27 22:20. The Claude Doc is the master; if Paul edits it, it wins. Read with `dsp-poc-decisions-paul_2026-10-27_2220.md`.

## Summary

By Monday 11/02 the DSP v1 pipeline runs end to end in the Relevate Health sandbox. Every hour it turns one gzipped DSP CSV into one Parquet file per publisher, keyed, deduplicated and with bad rows quarantined. The same rows also land in an S3 Tables (Iceberg) table, so the team can judge Iceberg on real data.

| Milestone | Target | What it is |
| --- | --- | --- |
| Internal goal | Fri 10/30 | POC running end to end |
| POC demo | Mon 11/02 | This document's scope |
| Pipe version | Fri 11/07 | Tweaked, production-shaped |
| Final delivery | Mid-November | Ready to hand over |

Jira: DTE-151 (DSP v1 pipeline POC); HLD is DTE-152. Iceberg stays in only as long as it does not threaten 11/07.

## Purpose

This is one pipeline answering two questions. Both are built at once, but they are not equal: the first is the deliverable, the second is a time-boxed trial.

1. **Does the v1 contract work end to end?** File in, file out: an hourly DSP CSV becomes clean Parquet per publisher, with the agreed key, quarantine and replays, on an hourly schedule. This becomes the 11/07 pipe version.
2. **Do we like S3 Tables (Iceberg)?** The same rows go to an Iceberg table. Because input and logic are identical, the only difference is storage, so the comparison is fair.

**The rule that keeps them apart:** one transform, two writers. The Parquet writer runs first and never reads from Iceberg. If the Iceberg writer fails, or the trial is dropped, the Parquet contract ships unchanged.

## Flow

Once an hour, a Step Function takes a lock, finds hours not yet done, and runs each one through a single transform. The Parquet writer runs first; the Iceberg writer second.

Diagram title: "One transform feeds both writers; the contract never reads from Iceberg". Text version:

```
EventBridge Scheduler (hourly, time-based)
        |
        v
Step Functions (check lock · find work · process hours · record manifest)
        |  one file-hour per invocation
        v
Input (hourly DSP CSV, gz) --> Transform Lambda (Python + DuckDB) <--> Id ledger (Parquet, every row's id; history for the id check)
                               1 Read file, validate header        --> Quarantine (manifests + failed-keys)
                               2 Clean up, collapse exact duplicates
                               3 Dataset-wide id check
                               4 Keep 6 publishers, build the key
                                   |                         |
                              1st  v                  2nd, may fail
                   Writer A: Parquet contract        Writer B: S3 Tables (Iceberg)   [dashed]
                   One file per publisher per hour   events table, same rows
                   The warehouse reads these         Time-boxed trial; never blocks A
```

Arrows run one way: nothing on the contract side reads from Iceberg. Quarantined rows carry a reason code, and every processed hour gets a manifest entry.

## Infrastructure

Everything is serverless, defined as code, and lives in the sandbox AWS account. Nothing touches production buckets, the Node service or the enrichment database.

| Layer | Component | Notes |
| --- | --- | --- |
| Trigger | EventBridge Scheduler, hourly | Stand-in for the Node heartbeat. The heartbeat change waits for Jesse's review. |
| Orchestration | AWS Step Functions (Standard) | Lock check, find work, process hours, record manifest. 25-minute timeout so a stuck run can't hold the lock. |
| Compute | Container-image Lambda: Python + DuckDB | One file-hour per invocation. Same image runs on Fargate if the largest hour is too big (Phase 0 decides). |
| Input | Curated copy of the DSP files in the sandbox | Source-bucket access (DTE-147) is pending. |
| Output A: contract | S3, Parquet (zstd), one file per publisher per hour | Written to a temporary key, then copied, so readers never see a half-written file. |
| Id ledger | S3, Parquet, one small file per hour | Every row's id before filtering. History for the dataset-wide id check. |
| Quarantine | Team's existing quarantine manifests and `failed-keys/` (sandbox copy) | Reuses the existing format and Athena tables. |
| Output B: experiment | S3 Tables (Iceberg), one `events` table | Same rows as Output A. |
| Readers | Athena and DuckDB | The warehouse keeps reading the Parquet files, unchanged. |

All resources are prefixed `dsp-poc-` and tagged `project=dsp-poc`, `owner=paul`. The sandbox runs weekdays 07:00 to 21:00 ET, so scheduled runs only happen in that window.

## Key design decisions

The load rules come from the DSP key spec (DTE-132). The design choices below are Paul's; "proposed" means still open.

| Topic | Decision | Status |
| --- | --- | --- |
| Row key | `<canonical publisher>-<transaction_id>`, e.g. `veradigm-10000021350` | Key spec D1, D2 |
| Duplicates | Exact duplicates collapse; same id with different data is quarantined | Key spec D3, D4 |
| Dataset-wide id check | An id seen on any other row, under any publisher, is quarantined | Key spec D5 |
| Id history source | An id ledger on the contract side, written for every row before filtering. Window is configurable; default is full history. | Decided |
| Outputs per hour | One Parquet file per publisher (6), driven by a config list. Every publisher gets a file every hour, empty if no rows. | Decided; 6 vs 3 to confirm with Jesse |
| Kept rows | 9 publisher labels mapped to 6 canonical publishers; Test Account and blank-publisher rows dropped | Key spec D6; Scott 10/27 |
| Columns | Drop `os_code` and `make_id`; `user_agent` passed through | Key spec D10 |
| NPI | No NPI filtering | Key spec D11 |
| Replays | A replay replaces the whole output file | Key spec D12 |
| Iceberg scope | One `events` table mirroring the Parquet outputs. `raw_events` and a lake quarantine view are next steps, only if Iceberg is kept. | Decided |
| Iceberg layout | One table, partitioned by publisher and day | Proposed |
| Compute | Lambda, with Fargate as fallback | Proposed; Phase 0 measures |

## What the POC will tell us

Monday's demo shows a scheduled run live, then answers each question with evidence.

**Question 1: does the contract work?** Each item is a pass or fail.

- [ ] The largest hour finishes in under 5 minutes in Lambda, or the Fargate route works
- [ ] One correct Parquet file per publisher per hour, matching the agreed schema
- [ ] Rerunning an hour gives identical output, with no duplicates
- [ ] An overlapping trigger is discarded, never run twice
- [ ] Duplicates, id conflicts and reused ids are counted and quarantined with reasons
- [ ] The dataset-wide id check runs against the full history within the time target

**Question 2: do we like S3 Tables?** Filled in during the POC, same input on both sides.

| Measure | Parquet files | S3 Tables |
| --- | --- | --- |
| Write time per hour (s) | | |
| Files written per day | | |
| Query time, one day, DuckDB (s) | | |
| Query time, one day, Athena (s) | | |
| Steps to replay one hour | | |
| Maintenance code needed | | |
| Storage cost per month (USD, estimate) | | |
| Readable by the warehouse as-is | | |

The POC also checks that S3 Tables holds exactly the same rows as the Parquet files for every hour loaded.

## Not in Monday's POC

These are deliberately left out of Monday's demo. Each has a place in the 11/07 pipe version or later.

- **Node heartbeat change:** the POC uses a scheduler stand-in; the one-line heartbeat change comes after Jesse reviews it.
- **Enrichment:** a pass-through stub until Cillian's factory endpoint is ready.
- **Full historical backfill:** the POC backfills one week to prove fan-out and replays.
- **Monthly ledger roll-up:** not needed at POC volume; added for the pipe version.
- **Whole-file rejection threshold:** row-level quarantine only, until the threshold is agreed.
- **NPI validation, bot filtering, restatement handling:** out of scope per the key spec (D8, D9, D11).
- **Wider Iceberg lake** (`raw_events`, a lake quarantine view): only if the team keeps Iceberg.

## Open questions

None of these block Monday; each is a labelled assumption in the POC until answered.

- [ ] **Age-based archive:** how long does DSP data stay in the active table before it's archived? The id-check window will match it. (Jesse)
- [ ] **Warehouse key retention:** how long does Redshift keep DSP history, and does it treat the row key as unique? The window can't be shorter than that. (Jesse)
- [ ] **Outputs:** 6 publisher files, or Jesse's 3? If 3, what happens to Relevate Games and Office Ally? (Jesse)
- [ ] **Id check scope (O1):** quarantine only kept-publisher rows, checked against all rows? (Jesse, Cillian)
- [ ] **Id conflicts (O2):** quarantine both rows or only the later one? Both means pulling an already-delivered row, i.e. replaying the earlier hour's file. (Jesse, Cillian)
- [ ] **Reject threshold:** above what share of bad rows is a whole file rejected? Scott floated about 0.5%. (Jesse)
- [ ] **Reused-id report:** who raises reused ids with AdKernel, and what should the pipeline produce? (Jesse, Scott)
- [ ] **Runtime:** is a Python Lambda acceptable next to the Node service? (Jesse)
- [ ] **Source access:** DTE-147 cross-account read for a true end to end. (Jesse)

## Gaps Paul flagged for tomorrow (not in the Claude Doc)

- **Output schema:** Jesse wants to see it; Paul drafts it from his column analysis. Not defined yet; it's the Writer A sign-off checkpoint. Expect the question Monday.
- **Iceberg time-box estimate:** Paul owes Scott a number for how long the Iceberg trial takes.
