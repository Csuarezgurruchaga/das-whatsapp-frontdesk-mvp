#!/bin/bash
# Complete Cloud Run Deployment Example
# Deploys Cloud Run service with:
# - Custom service account
# - Secret Manager access
# - Cloud SQL connection (optional)
# - Pub/Sub trigger (optional)

set -euo pipefail

#==============================================================================
# LOAD ENVIRONMENT
#==============================================================================

if [[ -f .gcp-env ]]; then
  source .gcp-env
else
  echo "Error: .gcp-env not found. Copy from templates/gcp-env.template"
  exit 1
fi

#==============================================================================
# CONTEXT VERIFICATION
#==============================================================================

echo "==================================="
echo "Cloud Run Deployment"
echo "==================================="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo "Image:    $IMAGE"
echo "==================================="
read -p "Proceed? (yes/no): " CONFIRM
[[ "$CONFIRM" != "yes" ]] && exit 0

#==============================================================================
# ENABLE APIS
#==============================================================================

echo ""
echo "Enabling required APIs..."

APIS=(
  "run.googleapis.com"
  "iam.googleapis.com"
  "secretmanager.googleapis.com"
)

for api in "${APIS[@]}"; do
  if gcloud services list --enabled --project=$PROJECT_ID \
    --filter="name:$api" --format="value(name)" | grep -q "$api"; then
    echo "  ✓ $api"
  else
    echo "  Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID
  fi
done

#==============================================================================
# CREATE RUNTIME SERVICE ACCOUNT
#==============================================================================

echo ""
echo "Setting up runtime service account..."

if gcloud iam service-accounts describe $RUNTIME_SA_EMAIL \
  --project=$PROJECT_ID 2>/dev/null; then
  echo "  ✓ Service account exists: $RUNTIME_SA_EMAIL"
else
  echo "  Creating service account: $RUNTIME_SA_EMAIL"
  gcloud iam service-accounts create $RUNTIME_SA_NAME \
    --project=$PROJECT_ID \
    --display-name="Cloud Run Runtime Service Account" \
    --description="Used by Cloud Run service $SERVICE_NAME"
fi

#==============================================================================
# GRANT IAM PERMISSIONS TO RUNTIME SA
#==============================================================================

echo ""
echo "Granting IAM permissions..."

# Secret Manager access
echo "  - roles/secretmanager.secretAccessor (read secrets)"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$RUNTIME_SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  --quiet

# Cloud SQL client (if enabled)
if [[ "$ENABLE_CLOUD_SQL" == "true" ]]; then
  echo "  - roles/cloudsql.client (Cloud SQL access)"
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$RUNTIME_SA_EMAIL" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet
fi

# Pub/Sub publisher (if enabled)
if [[ -n "${PUBSUB_TOPIC:-}" ]]; then
  echo "  - roles/pubsub.publisher (publish messages)"
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$RUNTIME_SA_EMAIL" \
    --role="roles/pubsub.publisher" \
    --condition=None \
    --quiet
fi

#==============================================================================
# CREATE SECRETS (if they don't exist)
#==============================================================================

if [[ -n "${DB_PASSWORD_SECRET:-}" ]]; then
  echo ""
  echo "Checking secrets..."
  
  if gcloud secrets describe $DB_PASSWORD_SECRET \
    --project=$PROJECT_ID 2>/dev/null; then
    echo "  ✓ Secret exists: $DB_PASSWORD_SECRET"
  else
    echo "  Creating secret: $DB_PASSWORD_SECRET"
    echo -n "Enter database password: " && read -s DB_PASSWORD && echo
    echo -n "$DB_PASSWORD" | gcloud secrets create $DB_PASSWORD_SECRET \
      --project=$PROJECT_ID \
      --data-file=- \
      --labels=env=$ENVIRONMENT,service=$SERVICE_NAME
  fi
fi

#==============================================================================
# DEPLOY CLOUD RUN SERVICE
#==============================================================================

echo ""
echo "Deploying Cloud Run service..."

# Build deployment command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=$IMAGE \
  --service-account=$RUNTIME_SA_EMAIL \
  --memory=$MEMORY \
  --cpu=$CPU \
  --timeout=${TIMEOUT}s \
  --concurrency=$CONCURRENCY \
  --min-instances=$MIN_INSTANCES \
  --max-instances=$MAX_INSTANCES \
  --labels=$LABELS"

# Add authentication flag
if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
  DEPLOY_CMD="$DEPLOY_CMD --allow-unauthenticated"
else
  DEPLOY_CMD="$DEPLOY_CMD --no-allow-unauthenticated"
fi

# Add Cloud SQL connection if enabled
if [[ "$ENABLE_CLOUD_SQL" == "true" ]]; then
  DEPLOY_CMD="$DEPLOY_CMD --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${SQL_INSTANCE_NAME}"
fi

# Add VPC connector if enabled
if [[ "$ENABLE_VPC" == "true" ]]; then
  DEPLOY_CMD="$DEPLOY_CMD --vpc-connector=$VPC_CONNECTOR"
fi

# Add environment variables
DEPLOY_CMD="$DEPLOY_CMD \
  --set-env-vars=\"PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT\""

# Add secrets as environment variables
if [[ -n "${DB_PASSWORD_SECRET:-}" ]]; then
  DEPLOY_CMD="$DEPLOY_CMD \
    --set-secrets=\"DB_PASSWORD=${DB_PASSWORD_SECRET}:latest\""
fi

# Execute deployment
echo "Executing: $DEPLOY_CMD"
eval $DEPLOY_CMD

echo "✓ Service deployed"

#==============================================================================
# CONFIGURE INVOKER ACCESS
#==============================================================================

echo ""
echo "Configuring access..."

if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
  echo "  Public access enabled (allUsers)"
else
  echo "  Authenticated access only"
  echo "  Grant access with:"
  echo "    gcloud run services add-iam-policy-binding $SERVICE_NAME \\"
  echo "      --region=$REGION --project=$PROJECT_ID \\"
  echo "      --member='user:email@example.com' \\"
  echo "      --role='roles/run.invoker'"
fi

#==============================================================================
# VALIDATION
#==============================================================================

echo ""
echo "==================================="
echo "Validation"
echo "==================================="

# 1. Check service status
echo "1. Service status:"
gcloud run services describe $SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url,status.conditions[0].type,status.conditions[0].status)"

# 2. Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)")

echo ""
echo "2. Service URL: $SERVICE_URL"

# 3. Test endpoint (if public)
if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
  echo ""
  echo "3. Testing endpoint..."
  if curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" | grep -q "200"; then
    echo "   ✓ Service responding (HTTP 200)"
  else
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL")
    echo "   ⚠ Service returned HTTP $HTTP_CODE"
  fi
else
  echo ""
  echo "3. Test with authenticated request:"
  echo "   curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $SERVICE_URL"
fi

# 4. Verify IAM
echo ""
echo "4. Runtime SA permissions:"
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$RUNTIME_SA_EMAIL" \
  --format="table(bindings.role)"

#==============================================================================
# DEPLOYMENT SUMMARY
#==============================================================================

echo ""
echo "==================================="
echo "Deployment Complete"
echo "==================================="
echo "Service Name:    $SERVICE_NAME"
echo "Service URL:     $SERVICE_URL"
echo "Runtime SA:      $RUNTIME_SA_EMAIL"
echo "Region:          $REGION"
echo "Environment:     $ENVIRONMENT"
echo ""
echo "Next Steps:"
echo "  1. Test the service: curl $SERVICE_URL"
echo "  2. View logs: gcloud run services logs read $SERVICE_NAME --region=$REGION"
echo "  3. Monitor: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo ""
echo "To update: Re-run this script with new IMAGE in .gcp-env"
echo "To rollback: ./scripts/cleanup-helper.sh"
echo "==================================="
