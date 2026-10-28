"""Unit tests for dsp_check_lock, using moto's fake Step Functions.

moto keeps started executions in RUNNING, which is what we need to
simulate "another run is in flight".
"""
import json
import os

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import dsp_check_lock  # noqa: E402

FAKE_ROLE = "arn:aws:iam::123456789012:role/dsp-poc-sfn-role"
HERE = os.path.dirname(__file__)


@pytest.fixture
def sfn():
    with mock_aws():
        client = boto3.client("stepfunctions")
        dsp_check_lock.sfn = client  # point the Lambda at the fake service
        yield client


@pytest.fixture
def state_machine_arn(sfn):
    with open(os.path.join(HERE, "state-machine.asl.json")) as f:
        definition = f.read()
    response = sfn.create_state_machine(
        name="dsp-pipeline-poc", definition=definition, roleArn=FAKE_ROLE
    )
    return response["stateMachineArn"]


def start(sfn, state_machine_arn, name):
    return sfn.start_execution(
        stateMachineArn=state_machine_arn, name=name, input=json.dumps({})
    )["executionArn"]


def test_only_me_running_is_not_locked(sfn, state_machine_arn):
    me = start(sfn, state_machine_arn, "run-1035")

    result = dsp_check_lock.handler(
        {"state_machine_arn": state_machine_arn, "execution_arn": me}, None
    )

    assert result == {"locked": False, "running": []}


def test_another_run_in_flight_is_locked(sfn, state_machine_arn):
    earlier = start(sfn, state_machine_arn, "run-1005")
    me = start(sfn, state_machine_arn, "run-1035")

    result = dsp_check_lock.handler(
        {"state_machine_arn": state_machine_arn, "execution_arn": me}, None
    )

    assert result["locked"] is True
    assert [r["arn"] for r in result["running"]] == [earlier]


def test_stopped_run_does_not_hold_the_lock(sfn, state_machine_arn):
    # Stands in for the 25-minute timeout: a run that ended no longer counts.
    stuck = start(sfn, state_machine_arn, "run-1005")
    sfn.stop_execution(executionArn=stuck)
    me = start(sfn, state_machine_arn, "run-1035")

    result = dsp_check_lock.handler(
        {"state_machine_arn": state_machine_arn, "execution_arn": me}, None
    )

    assert result["locked"] is False
