#!/bin/bash
# ==============================================================================
# Context Clutch: GCP Cloud Run Deployment Script
# Deploy your secure Context Clutch API Gateway Serverless-ly.
# ==============================================================================

PROJECT_ID="YOUR_GCP_PROJECT_ID" # TODO: Update this to your GCP project ID
REGION="us-central1"
SERVICE_NAME="context-clutch"

echo "Deploying Context Clutch to Google Cloud Run natively..."
echo "This will upload the Dockerfile, build it in Cloud Build, and deploy to Cloud Run."

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --project $PROJECT_ID \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 

echo ""
echo "Deployment Complete."
echo "Your Context Clutch proxy is now live and token-safe for your agents!"
