#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.workout_stack import WorkoutStack

app = cdk.App()

WorkoutStack(
    app,
    "WorkoutStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    ),
)

app.synth()
