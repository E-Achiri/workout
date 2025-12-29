from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigatewayv2 as apigwv2,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpUrlIntegration
from constructs import Construct


class WorkoutStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(
            self,
            "WorkoutVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # Security Group for EC2
        ec2_sg = ec2.SecurityGroup(
            self,
            "Ec2SecurityGroup",
            vpc=vpc,
            description="Security group for EC2 instance",
            allow_all_outbound=True,
        )
        ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "Allow SSH access",
        )
        ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP access",
        )
        ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(8000),
            "Allow FastAPI access",
        )

        # Security Group for RDS
        rds_sg = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=vpc,
            description="Security group for RDS instance",
            allow_all_outbound=True,
        )
        rds_sg.add_ingress_rule(
            ec2_sg,
            ec2.Port.tcp(5432),
            "Allow PostgreSQL access from EC2",
        )

        # RDS PostgreSQL
        db_credentials = rds.DatabaseSecret(
            self,
            "DbCredentials",
            username="workoutadmin",
        )

        database = rds.DatabaseInstance(
            self,
            "WorkoutDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            security_groups=[rds_sg],
            database_name="workout",
            credentials=rds.Credentials.from_secret(db_credentials),
            multi_az=False,
            allocated_storage=20,
            max_allocated_storage=100,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
        )

        # Cognito User Pool
        user_pool = cognito.UserPool(
            self,
            "WorkoutUserPool",
            user_pool_name="workout-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Cognito User Pool Client
        user_pool_client = user_pool.add_client(
            "WorkoutWebClient",
            user_pool_client_name="workout-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            generate_secret=False,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
        )

        # S3 Bucket for backend application deployment
        deployment_bucket = s3.Bucket(
            self,
            "DeploymentBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # S3 Bucket for frontend static hosting
        frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # CloudFront Origin Access Identity
        oai = cloudfront.OriginAccessIdentity(
            self,
            "FrontendOAI",
            comment="OAI for Workout Frontend",
        )

        # Grant CloudFront access to the frontend bucket
        frontend_bucket.grant_read(oai)

        # CloudFront Distribution
        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    frontend_bucket,
                    origin_access_identity=oai,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            error_responses=[
                # Handle SPA routing - return index.html for 404s
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # IAM Role for EC2
        ec2_role = iam.Role(
            self,
            "Ec2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # Grant EC2 access to read the database secret and S3 bucket
        db_credentials.grant_read(ec2_role)
        deployment_bucket.grant_read(ec2_role)

        # EC2 Instance
        # Amazon Linux 2023 AMI
        ami = ec2.MachineImage.latest_amazon_linux2023()

        # User data script to set up and run the application
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            # Install dependencies
            "yum update -y",
            "yum install -y python3.11 python3.11-pip unzip jq",

            # Create app directory
            "mkdir -p /opt/workout",

            # Download app from S3
            f"aws s3 cp s3://{deployment_bucket.bucket_name}/app.zip /opt/workout/app.zip || echo 'App not yet uploaded'",
            "cd /opt/workout && unzip -o app.zip || echo 'No app.zip yet'",

            # Install Python dependencies
            "cd /opt/workout && pip3.11 install -r requirements.txt || echo 'No requirements.txt yet'",

            # Get database credentials from Secrets Manager
            f"export DB_SECRET=$(aws secretsmanager get-secret-value --secret-id {db_credentials.secret_arn} --query SecretString --output text --region {self.region})",

            # Create environment file
            f"cat > /opt/workout/.env << 'ENVEOF'\n"
            f"DATABASE_HOST={database.db_instance_endpoint_address}\n"
            f"DATABASE_PORT=5432\n"
            f"DATABASE_NAME=workout\n"
            f"DATABASE_USER=workoutadmin\n"
            f"COGNITO_REGION={self.region}\n"
            f"COGNITO_USER_POOL_ID={user_pool.user_pool_id}\n"
            f"COGNITO_CLIENT_ID={user_pool_client.user_pool_client_id}\n"
            f"ALLOWED_ORIGINS=*\n"
            "ENVEOF",

            # Extract password from secret and append to .env
            f"DB_PASS=$(aws secretsmanager get-secret-value --secret-id {db_credentials.secret_arn} --query SecretString --output text --region {self.region} | jq -r '.password')",
            "echo \"DATABASE_PASSWORD=$DB_PASS\" >> /opt/workout/.env",

            # Create systemd service
            "cat > /etc/systemd/system/workout.service << 'EOF'\n"
            "[Unit]\n"
            "Description=Workout FastAPI Application\n"
            "After=network.target\n"
            "\n"
            "[Service]\n"
            "Type=simple\n"
            "User=root\n"
            "WorkingDirectory=/opt/workout\n"
            "EnvironmentFile=/opt/workout/.env\n"
            "ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000\n"
            "Restart=always\n"
            "RestartSec=3\n"
            "\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
            "EOF",

            # Enable and start the service
            "systemctl daemon-reload",
            "systemctl enable workout",
            "systemctl start workout || echo 'Service start failed - app may not be uploaded yet'",
        )

        instance = ec2.Instance(
            self,
            "WorkoutInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO,
            ),
            machine_image=ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC,
            ),
            security_group=ec2_sg,
            role=ec2_role,
            user_data=user_data,
            associate_public_ip_address=True,
        )

        # API Gateway HTTP API to proxy requests to EC2
        api = apigwv2.HttpApi(
            self,
            "WorkoutApi",
            api_name="workout-api",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["*"],
                allow_credentials=False,
            ),
        )

        # Integration to forward requests to EC2
        ec2_integration = HttpUrlIntegration(
            "Ec2Integration",
            f"http://{instance.instance_public_ip}:8000/{{proxy}}",
        )

        # Add route to proxy all requests
        api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=ec2_integration,
        )

        # Add root path route
        root_integration = HttpUrlIntegration(
            "Ec2RootIntegration",
            f"http://{instance.instance_public_ip}:8000/",
        )
        api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.ANY],
            integration=root_integration,
        )

        # Outputs
        CfnOutput(
            self,
            "VpcId",
            value=vpc.vpc_id,
            description="VPC ID",
        )

        CfnOutput(
            self,
            "Ec2PublicIp",
            value=instance.instance_public_ip,
            description="EC2 Public IP",
        )

        CfnOutput(
            self,
            "Ec2InstanceId",
            value=instance.instance_id,
            description="EC2 Instance ID",
        )

        CfnOutput(
            self,
            "RdsEndpoint",
            value=database.db_instance_endpoint_address,
            description="RDS Endpoint",
        )

        CfnOutput(
            self,
            "DbSecretArn",
            value=db_credentials.secret_arn,
            description="Database Credentials Secret ARN",
        )

        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        CfnOutput(
            self,
            "CognitoUserPoolClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )

        CfnOutput(
            self,
            "CognitoRegion",
            value=self.region,
            description="Cognito Region",
        )

        CfnOutput(
            self,
            "DeploymentBucketName",
            value=deployment_bucket.bucket_name,
            description="S3 Bucket for application deployment",
        )

        CfnOutput(
            self,
            "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="S3 Bucket for frontend static files",
        )

        CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID",
        )

        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront URL for frontend",
        )

        CfnOutput(
            self,
            "ApiGatewayUrl",
            value=api.url or "",
            description="API Gateway URL (HTTPS)",
        )
