# CheckLock: how the DSP pipeline stops two runs overlapping

Sample code and explanation for the `CheckLock` step of the DSP v1 pipeline POC (DTE-151). It shows how the
lock works. It is not the production Lambda yet; that will live under `src/` when the POC is built.

Design source: `docs/from-3po/dsp-iceberg-pipeline-poc-spec-for-R3_2026-10-24_1645.md`, section "Lock".
Jesse asked how the pipeline locks; the spec reuses the pattern Cillian used in his Glue jobs: if a run is
in flight, the new one discards itself.

## Files

| File | What |
|---|---|
| `dsp_check_lock.py` | The Lambda (Python, boto3 only) |
| `state-machine.asl.json` | Step Functions definition showing how CheckLock is called and how the skip decision is made |
| `iam-policy.json` | The one permission the Lambda needs |
| `test_dsp_check_lock.py` | Unit tests against moto's fake Step Functions (3 tests, all passing 2026-10-28) |

## Where it sits in the pipeline

CheckLock is **step 2** in the HLD and the sequence diagram (`diagrams/dsp-poc-hld-2026-10-28.png`; the
blue numbered circles match between the two). It is the first task the state machine runs:

1. **The heartbeat fires** (step 1). EventBridge only starts the state machine; it never calls this Lambda.
2. **The `CheckLock` state runs first** (`"StartAt": "CheckLock"`). It is a Task state whose only job is to
   invoke the `dsp-check-lock` Lambda, passing the two ARNs.
3. **The Lambda answers** `locked: true` or `false`.
4. **`IsLocked` (a Choice state, no code)** routes the run to `SkippedAlreadyRunning` or on to `FindWork`
   (step 3).

The state and the Lambda are two halves of one step: the `CheckLock` state is the box in the Step Functions
graph; the `dsp-check-lock` Lambda is the Python code that box runs. Nothing else calls this Lambda, and every
run calls it exactly once, before any S3 work begins. That ordering is the point: if another run is in
progress, this run stops before it touches any data.

## Scope: what this Lambda touches

Very little. One read-only call to Step Functions, and a yes/no answer back.

- **No S3.** It doesn't read or write any bucket, file, table or database. Its only permission is
  `states:ListExecutions` on the pipeline's own state machine, so it couldn't touch S3 even if the code tried.
- **It doesn't decide whether to skip.** The `IsLocked` Choice state makes that call based on `locked`.
- **It doesn't stop, cancel or wait for the other run.** It only reports that it exists.
- **It doesn't create or hold a lock.** Nothing is written, so there's nothing to release. The lock is
  Step Functions' own record of what's running.
- **It doesn't set the 25-minute timeout.** That's a setting on the state machine itself.
- **It doesn't look for work.** That's the next step, `FindWork`, a separate Lambda.

Where the S3 work happens instead:

| Step (HLD number) | Touches S3? |
|---|---|
| **2 CheckLock** (this one) | No. Step Functions only |
| **3 FindWork** | Reads only: lists input files, checks which output Parquet files exist |
| **4-9 ProcessHours → Transform** | Reads the input CSV; writes the id ledger, quarantine, Parquet (Writer A) and S3 Tables (Writer B) |
| **10 RecordManifest** | Writes manifest entries |

## What the step does

`CheckLock` is the first state in the state machine. It makes sure only one run happens at a time, like
checking whether someone is already in the room.

1. **The trigger fires.** The Node heartbeat (:05 and :35) sends an event through EventBridge, which starts
   a new execution of the state machine.
2. **The run asks Step Functions what's already running.** It calls `ListExecutions` on this same state
   machine with `statusFilter = RUNNING`. In plain English: "Are any other copies of me running right now?"
3. **It drops itself out of the list.** The new run always shows up as RUNNING too, so it compares each
   result against its own execution ARN (`$$.Execution.Id`) and counts only the others.
4. **It decides:**
   - **No other run:** go on to `FindWork` and do the real work.
   - **Another run is in flight:** go to a `Succeed` state called `SkippedAlreadyRunning` and stop. It ends
     as a success, not a failure, so a skip doesn't set off alarms. Whatever work is still pending gets
     picked up at the next heartbeat.

**Why there's a 25-minute timeout too.** The check only works if a running execution eventually stops. If
one hangs, it would count as "running" forever and every later heartbeat would skip. The state machine's
25-minute timeout (`TimeoutSeconds: 1500`) kills a stuck run before the next heartbeat 30 minutes later, so
the lock frees itself.

**Why it's built this way.** No lock table or DynamoDB item, and nothing has to be cleaned up afterward.
Step Functions' own record of what's running is the lock.

## The Lambda

The Lambda only reports what it finds. It doesn't make the decision. Step Functions reads `locked` and picks
the next step, so the flow stays visible in the console graph instead of being hidden in code.

```python
import boto3

sfn = boto3.client("stepfunctions")


def handler(event, context):
    state_machine_arn = event["state_machine_arn"]  # which state machine to check
    my_execution_arn = event["execution_arn"]       # this run, so we can exclude it

    others = []
    paginator = sfn.get_paginator("list_executions")
    for page in paginator.paginate(
        stateMachineArn=state_machine_arn,
        statusFilter="RUNNING",
    ):
        for execution in page["executions"]:
            if execution["executionArn"] != my_execution_arn:
                others.append(
                    {
                        "arn": execution["executionArn"],
                        "started": execution["startDate"].isoformat(),
                    }
                )

    return {
        "locked": len(others) > 0,  # True = someone else is running, so skip
        "running": others,          # kept for logging and debugging
    }
```

## How Step Functions calls it

Full definition in `state-machine.asl.json`. The parts that matter:

| Part | What it does |
|---|---|
| `"TimeoutSeconds": 1500` | The 25-minute timeout. A stuck run is killed before the next heartbeat, so it can't hold the lock forever. |
| `$$.StateMachine.Id` / `$$.Execution.Id` | `$$` is the Step Functions context object: facts about the current run. These two hand the Lambda the state machine's ARN and this run's ARN. Nothing is hard-coded. |
| `ResultSelector` | `lambda:invoke` wraps the function's return value inside `Payload`. This pulls out only `locked` and `running`. |
| `"ResultPath": "$.lock"` | Puts the result under `lock` and keeps the original EventBridge event, so `FindWork` still sees the heartbeat input. |
| `IsLocked` (Choice) | The actual decision: `locked = true` goes to skip, otherwise it continues. |
| `SkippedAlreadyRunning` (Succeed) | Ends as a success, so a normal skip doesn't trigger failure alarms. |

## Walkthrough: the 10:35 heartbeat

- **Normal case:** the 10:05 run finished at 10:12. At 10:35 a new execution starts. `CheckLock` finds only
  itself running, so `others = []` and `locked = false`. The run goes on to `FindWork`.
- **Busy case:** the 10:05 run is still working on a backlog. The 10:35 run finds the 10:05 run, so
  `locked = true`. It ends at `SkippedAlreadyRunning`, and any hours it would have handled get picked up at
  11:05.
- **Stuck case:** the 10:05 run hangs. At 10:30 the 25-minute timeout marks it `TIMED_OUT`, so it no longer
  counts as RUNNING. The 10:35 run continues normally.

The three tests in `test_dsp_check_lock.py` cover these three cases (the stuck case uses `stop_execution`
as a stand-in for the timeout).

## IAM

The Lambda's role needs one permission (`iam-policy.json`):

```json
{
  "Effect": "Allow",
  "Action": "states:ListExecutions",
  "Resource": "arn:aws:states:<region>:<account>:stateMachine:dsp-pipeline-poc"
}
```

Build this ARN from the state machine's name rather than referencing the state machine resource. The state
machine already references the Lambda, so referencing it back creates a dependency cycle in Terraform or CDK.

## Running the tests

Needs `boto3`, `moto[stepfunctions]` and `pytest` in a venv (not the system Python):

```bash
python -m venv .venv
.venv/bin/pip install boto3 "moto[stepfunctions]" pytest
.venv/bin/python -m pytest -q
```

## What comes next: FindWork (step 3)

If the run isn't locked, the next real task is `FindWork`, a small Python Lambda that answers "which hours
still need processing?":

1. Lists the input files for the last 21 days (Jesse's lookback window).
2. Works out the file-hour each input file belongs to.
3. Checks the **Parquet bucket** for each hour: do all 6 output files (one per publisher) exist?
4. Keeps only the unfinished hours, oldest first, capped at 6 per run so a backlog drains over several
   heartbeats.
5. Returns the list; `ProcessHours` (a Map state, max 2 in parallel) runs the transform once per hour.

| | CheckLock | FindWork |
|---|---|---|
| Touches S3? | No | Yes, read-only. It writes nothing. |
| IAM | `states:ListExecutions` | `s3:ListBucket` on the input and Parquet buckets (maybe `s3:GetObject`/HeadObject, depending on the check) |
| Returns | `locked` true/false | A list of hours to process |

Notes carried from the 10/27-10/28 decisions:

- **6 files per hour, not 3.** Paul's 10/27 decision: one file per publisher, written even when a publisher
  has no rows. Without the empty file, that hour would look unfinished forever and be reprocessed on every
  heartbeat.
- **The POC owns two output buckets** (Paul, 10/28): `rhde-pg-dsp-poc-parquet`, a general-purpose S3 bucket
  for Path A (the contract), and `rhde-pg-dsp-poc-iceberg`, an S3 Tables **table bucket** for Path B (the
  Iceberg trial). Two buckets are required, not just preferred: Iceberg tables in S3 Tables can only live in a
  table bucket, which has its own `s3tables` APIs and policies.
- **FindWork checks only the Parquet bucket.** Path A is the contract, so an hour counts as done when its 6
  Parquet files exist; Path B never blocks Path A. Known gap: if Writer B fails for an hour, FindWork won't
  retry it. Catching up Path B would need its own check later.
- **FindWork and the transform must agree on the output layout**, for example
  `<prefix>/date=YYYY-MM-DD/hour=HH/<publisher>.parquet`. If they disagree, FindWork never finds the files
  the transform wrote and reprocesses the same hours every heartbeat. Bucket and prefix should come from
  environment variables, not be hard-coded.
- FindWork is where the pipeline's idempotency really comes from, which is why CheckLock's best-effort lock
  is good enough.

## R3's take

- **Deploy this as a plain zip Lambda, not the DuckDB container image.** It only needs `boto3`, which the
  Lambda Python runtime already includes, so it starts fast and deploys in seconds. Save the container image
  for the transform.
- **The tradeoff.** Step Functions can call `ListExecutions` directly through an SDK integration
  (`arn:aws:states:::aws-sdk:sfn:listExecutions`), with no Lambda at all. That means one fewer function to
  deploy and no cold start. The Python version costs a few hundred milliseconds per run. In exchange, it can
  be unit-tested and read like the rest of the pipeline's Python Lambdas, and the "exclude myself" logic is a
  simple `if` instead of a JSONata expression or a Pass + Choice pair. R3 recommends the Python version for
  this POC.
- **It's a best-effort lock, not a guaranteed one.** If two executions start within a moment of each other,
  the list results may not show both. Both could then run, or both could skip. With heartbeats 30 minutes
  apart this is unlikely. A manual start during testing could cause it, though.
- **The real protection is the spec's idempotency per file-hour.** `FindWork` only picks hours whose output
  files are missing, and the writers replace whole files. If two runs ever overlap, the cost is duplicate
  work, not bad data. The lock just keeps that from happening.
