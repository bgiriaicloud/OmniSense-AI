#!/bin/bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables if .env exists
if [ -f "$ROOT_DIR/.env" ]; then
    echo "💡 Loading environment variables from .env..."
    export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
fi

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="omnisense-agent"
REGION="us-central1"
IMAGE_PATH="$REGION-docker.pkg.dev/$PROJECT_ID/visionguide-repo/$SERVICE_NAME"

echo "🚀 Deploying $SERVICE_NAME to Google Cloud Run in $REGION..."

# Build and Push Image
echo "📦 Building and pushing image to $IMAGE_PATH..."
gcloud builds submit --tag $IMAGE_PATH .

# Ensure Secret exists and is updated
if gcloud secrets list --filter="name ~ GEMINI_API_KEY" | grep -q "GEMINI_API_KEY"; then
    echo "🔐 Updating existing secret GEMINI_API_KEY..."
else
    echo "🔐 Creating new secret GEMINI_API_KEY..."
    gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
fi

echo -n "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# Deploy to Cloud Run using Secret Manager
echo "🚀 Deploying to Cloud Run with Secret Manager..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_PATH \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars GEMINI_MODEL_ID=$GEMINI_MODEL_ID \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest

echo "✅ Deployment complete!"
