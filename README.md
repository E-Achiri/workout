# Workout App

A full-stack web application for tracking workout messages, built with Next.js, FastAPI, and AWS.

## Architecture

- **Frontend:** Next.js (React) hosted on S3 + CloudFront
- **Backend:** FastAPI (Python) running on EC2
- **Database:** PostgreSQL on RDS
- **Authentication:** AWS Cognito
- **API Gateway:** AWS API Gateway (HTTPS proxy to EC2)
- **Infrastructure:** AWS CDK (Python)

## Live URLs

- **Frontend:** https://d1fbasitrdm7um.cloudfront.net
- **API:** https://etqk3b4rpi.execute-api.us-east-1.amazonaws.com

## Project Structure

```
workout/
├── frontend/          # Next.js frontend application
│   ├── src/
│   │   ├── app/       # Pages (login, home)
│   │   └── lib/       # API client & auth utilities
│   └── package.json
├── fastapi/
│   └── api/           # FastAPI backend
│       ├── main.py    # API endpoints
│       ├── auth.py    # Cognito JWT authentication
│       └── database.py # PostgreSQL connection
├── infra/             # AWS CDK infrastructure
│   └── stacks/
│       └── workout_stack.py
├── deploy.py          # Backend deployment script
└── deploy_frontend.py # Frontend deployment script
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS CLI configured with credentials
- AWS CDK CLI (`npm install -g aws-cdk`)

## Local Development

### Backend

```bash
cd fastapi/api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file with required variables
cp .env.example .env

# Run the server
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local with API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

## Deployment

### Deploy Infrastructure (first time)

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap  # Only needed once per AWS account/region
cdk deploy
```

### Deploy Backend

```bash
python deploy.py
```

### Deploy Frontend

```bash
cd frontend
npm run build
aws s3 sync out s3://workoutstack-frontendbucketefe2e19c-j4bgusb7bn79 --delete
aws cloudfront create-invalidation --distribution-id E24CRBJNT9H3JU --paths "/*"
```

## Environment Variables

### Backend (.env)

```
DATABASE_HOST=<RDS endpoint>
DATABASE_PORT=5432
DATABASE_NAME=workout
DATABASE_USER=workoutadmin
DATABASE_PASSWORD=<from Secrets Manager>
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=<from CDK output>
COGNITO_CLIENT_ID=<from CDK output>
ALLOWED_ORIGINS=https://your-cloudfront-url.cloudfront.net
```

### Frontend (.env.production)

```
NEXT_PUBLIC_COGNITO_USER_POOL_ID=<from CDK output>
NEXT_PUBLIC_COGNITO_CLIENT_ID=<from CDK output>
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com
```

## API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Health check | No |
| GET | `/auth/me` | Get current user info | Yes |
| GET | `/messages` | Get user's messages | Yes |
| POST | `/messages` | Create a new message | Yes |

## License

MIT
