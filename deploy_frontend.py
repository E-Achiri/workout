#!/usr/bin/env python3
"""
Deployment script for the Workout frontend application.
Builds the Next.js app and uploads it to S3, then invalidates CloudFront cache.
"""

import subprocess
import os
import json
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")
OUT_DIR = os.path.join(FRONTEND_DIR, "out")


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


def create_env_file(outputs):
    """Create .env.production file with the correct values."""
    env_file = os.path.join(FRONTEND_DIR, ".env.production")

    api_url = f"http://{outputs.get('Ec2PublicIp')}:8000"

    content = f"""# Production environment variables
NEXT_PUBLIC_COGNITO_USER_POOL_ID={outputs.get('CognitoUserPoolId')}
NEXT_PUBLIC_COGNITO_CLIENT_ID={outputs.get('CognitoUserPoolClientId')}
NEXT_PUBLIC_API_URL={api_url}
"""

    with open(env_file, "w") as f:
        f.write(content)

    print(f"Created {env_file}")
    print(f"  API URL: {api_url}")


def build_frontend():
    """Build the Next.js application."""
    print("\nBuilding frontend...")

    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        sys.exit(1)

    print("Build complete!")


def upload_to_s3(bucket_name):
    """Upload the built files to S3."""
    print(f"\nUploading to S3 bucket: {bucket_name}")

    result = subprocess.run(
        ["aws", "s3", "sync", OUT_DIR, f"s3://{bucket_name}", "--delete"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Upload failed:\n{result.stderr}")
        sys.exit(1)

    print("Upload complete!")


def invalidate_cloudfront(distribution_id):
    """Invalidate CloudFront cache."""
    print(f"\nInvalidating CloudFront cache: {distribution_id}")

    result = subprocess.run(
        [
            "aws", "cloudfront", "create-invalidation",
            "--distribution-id", distribution_id,
            "--paths", "/*"
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Invalidation failed:\n{result.stderr}")
        # Don't exit - invalidation failure is not critical
    else:
        print("Cache invalidation started!")


def main():
    print("=" * 50)
    print("Workout Frontend Deployment")
    print("=" * 50)

    # Get stack outputs
    outputs = get_stack_outputs()

    frontend_bucket = outputs.get("FrontendBucketName")
    distribution_id = outputs.get("CloudFrontDistributionId")
    cloudfront_url = outputs.get("CloudFrontURL")

    if not frontend_bucket:
        print("Error: FrontendBucketName not found in stack outputs.")
        print("Make sure you've deployed the updated CDK stack first.")
        sys.exit(1)

    print(f"\nFrontend Bucket: {frontend_bucket}")
    print(f"CloudFront Distribution: {distribution_id}")
    print(f"CloudFront URL: {cloudfront_url}")

    # Create production environment file
    create_env_file(outputs)

    # Build and upload
    build_frontend()
    upload_to_s3(frontend_bucket)

    # Invalidate CloudFront cache
    if distribution_id:
        invalidate_cloudfront(distribution_id)

    print()
    print("=" * 50)
    print("Frontend deployment complete!")
    print(f"URL: {cloudfront_url}")
    print("=" * 50)


if __name__ == "__main__":
    main()
