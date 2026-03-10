#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="omnisense-agent"
REGION="us-central1"
IMAGE_PATH="$REGION-docker.pkg.dev/$PROJECT_ID/visionguide-repo/$SERVICE_NAME"

echo "🚀 Deploying $SERVICE_NAME to Google Cloud Run in $REGION..."

# Build and Push Image
echo "📦 Building and pushing image to $IMAGE_PATH..."
gcloud builds submit --tag $IMAGE_PATH .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_PATH \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

echo "✅ Deployment complete!"
