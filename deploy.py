#!/usr/bin/env python3
"""
Deployment script for the Workout application.
Packages the FastAPI app and uploads it to S3, then restarts the EC2 service.
"""

import subprocess
import zipfile
import os
import json
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(SCRIPT_DIR, "fastapi", "api")
INFRA_DIR = os.path.join(SCRIPT_DIR, "infra")
ZIP_FILE = os.path.join(SCRIPT_DIR, "app.zip")

# Files to include in the deployment package
FILES_TO_DEPLOY = [
    "main.py",
    "auth.py",
    "database.py",
    "requirements.txt",
]


def get_stack_outputs():
    """Get CloudFormation stack outputs."""
    print("Getting stack outputs...")
    result = subprocess.run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", "WorkoutStack", "--query", "Stacks[0].Outputs"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error getting stack outputs: {result.stderr}")
        sys.exit(1)

    outputs = json.loads(result.stdout)
    return {o["OutputKey"]: o["OutputValue"] for o in outputs}


def create_zip():
    """Create a zip file of the application."""
    print(f"Creating deployment package: {ZIP_FILE}")

    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in FILES_TO_DEPLOY:
            filepath = os.path.join(API_DIR, filename)
            if os.path.exists(filepath):
                zf.write(filepath, filename)
                print(f"  Added: {filename}")
            else:
                print(f"  Warning: {filename} not found")

    print(f"Created: {ZIP_FILE}")


def upload_to_s3(bucket_name):
    """Upload the zip file to S3."""
    print(f"Uploading to S3 bucket: {bucket_name}")

    result = subprocess.run(
        ["aws", "s3", "cp", ZIP_FILE, f"s3://{bucket_name}/app.zip"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error uploading to S3: {result.stderr}")
        sys.exit(1)

    print("Upload complete!")


def restart_service(instance_id):
    """Restart the workout service on EC2 via SSM."""
    print(f"Restarting service on instance: {instance_id}")

    commands = [
        "cd /opt/workout",
        "aws s3 cp s3://$(aws s3 ls | grep workoutstack | awk '{print $3}')/app.zip /opt/workout/app.zip",
        "unzip -o app.zip",
        "pip3.11 install -r requirements.txt",
        "systemctl restart workout",
        "systemctl status workout",
    ]

    result = subprocess.run(
        [
            "aws", "ssm", "send-command",
            "--instance-ids", instance_id,
            "--document-name", "AWS-RunShellScript",
            "--parameters", json.dumps({"commands": commands}),
            "--output", "text",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error sending SSM command: {result.stderr}")
        print("You may need to manually restart the service or reboot the instance.")
    else:
        print("SSM command sent! Service should restart shortly.")
        print("Check the EC2 instance logs or SSM command history for status.")


def main():
    print("=" * 50)
    print("Workout Application Deployment")
    print("=" * 50)

    # Get stack outputs
    outputs = get_stack_outputs()
    bucket_name = outputs.get("DeploymentBucketName")
    instance_id = outputs.get("Ec2InstanceId")
    ec2_ip = outputs.get("Ec2PublicIp")

    if not bucket_name:
        print("Error: DeploymentBucketName not found in stack outputs.")
        print("Make sure you've deployed the updated CDK stack first.")
        sys.exit(1)

    print(f"\nDeployment Bucket: {bucket_name}")
    print(f"EC2 Instance ID: {instance_id}")
    print(f"EC2 Public IP: {ec2_ip}")
    print()

    # Create zip and upload
    create_zip()
    upload_to_s3(bucket_name)

    # Restart the service
    if instance_id:
        restart_service(instance_id)

    print()
    print("=" * 50)
    print("Deployment complete!")
    print(f"API URL: http://{ec2_ip}:8000")
    print("=" * 50)

    # Cleanup
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)


if __name__ == "__main__":
    main()
