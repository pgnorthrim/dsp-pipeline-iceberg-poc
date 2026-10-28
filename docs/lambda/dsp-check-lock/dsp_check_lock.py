"""CheckLock: is another execution of this state machine already running?

Step Functions passes in its own ARNs. We list RUNNING executions of the
same state machine and drop ourselves from the list. Anything left means
another run is in flight, so this run should skip.
"""
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
