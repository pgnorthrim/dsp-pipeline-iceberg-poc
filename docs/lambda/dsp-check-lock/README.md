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
