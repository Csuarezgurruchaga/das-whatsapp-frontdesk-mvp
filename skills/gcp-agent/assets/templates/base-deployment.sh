#!/bin/bash
# GCP Base Deployment Template
# Use this as starting point for any GCP CLI deployment

set -euo pipefail  # Exit on error, undefined vars, pipe failures

#==============================================================================
# CONFIGURATION - Edit this section
#==============================================================================

# Load environment variables
if [[ -f .gcp-env ]]; then
  source .gcp-env
else
  echo "Error: .gcp-env file not found"
  echo "Create it using: cp templates/gcp-env.template .gcp-env"
  exit 1
fi

# Deployment metadata
DEPLOYMENT_DATE=$(date -Iseconds)
DEPLOYMENT_USER=$(gcloud config get-value account 2>/dev/null || echo "unknown")

#==============================================================================
# CONTEXT VERIFICATION
#==============================================================================

echo "==================================="
echo "GCP Deployment Context Verification"
echo "==================================="
echo "Project:       $(gcloud config get-value project 2>/dev/null)"
echo "Region:        $(gcloud config get-value compute/region 2>/dev/null)"
echo "Zone:          $(gcloud config get-value compute/zone 2>/dev/null)"
echo "Deploying as:  $DEPLOYMENT_USER"
echo "==================================="
echo ""

read -p "Proceed with this context? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Deployment cancelled."
  exit 0
fi

#==============================================================================
# HELPER FUNCTIONS
#==============================================================================

# Check if resource exists
resource_exists() {
  local resource_type=$1
  local resource_name=$2
  local extra_flags=${3:-}
  
  gcloud $resource_type describe $resource_name $extra_flags \
    --project=$PROJECT_ID 2>/dev/null
  return $?
}

# Log deployment action
log_action() {
  local action=$1
  local resource=$2
  echo "[$DEPLOYMENT_DATE] $action: $resource" | tee -a deploy.log
}

# Enable API if not already enabled
enable_api() {
  local api=$1
  echo "Checking API: $api"
  
  if gcloud services list --enabled --project=$PROJECT_ID \
    --filter="name:$api" --format="value(name)" | grep -q "$api"; then
    echo "  ✓ Already enabled"
  else
    echo "  Enabling..."
    gcloud services enable $api --project=$PROJECT_ID
    log_action "API_ENABLED" $api
  fi
}

#==============================================================================
# PRE-FLIGHT CHECKS
#==============================================================================

echo ""
echo "Running pre-flight checks..."

# Check gcloud version
GCLOUD_VERSION=$(gcloud version --format="value(version)")
echo "✓ gcloud version: $GCLOUD_VERSION"

# Verify billing enabled
if gcloud billing projects describe $PROJECT_ID --format="value(billingEnabled)" | grep -q "True"; then
  echo "✓ Billing enabled"
else
  echo "✗ Billing NOT enabled - this may cause issues"
  read -p "Continue anyway? (yes/no): " BILLING_CONFIRM
  [[ "$BILLING_CONFIRM" != "yes" ]] && exit 1
fi

# Enable required APIs
echo ""
echo "Enabling required APIs..."
# Add your APIs here, for example:
# enable_api "run.googleapis.com"
# enable_api "secretmanager.googleapis.com"

#==============================================================================
# RESOURCE CREATION - CUSTOMIZE THIS SECTION
#==============================================================================

echo ""
echo "==================================="
echo "Starting Resource Deployment"
echo "==================================="

# Example: Create Service Account
# SA_NAME="my-service-sa"
# SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
# 
# if resource_exists "iam service-accounts" $SA_EMAIL; then
#   echo "Service account exists: $SA_EMAIL"
# else
#   echo "Creating service account: $SA_EMAIL"
#   gcloud iam service-accounts create $SA_NAME \
#     --project=$PROJECT_ID \
#     --display-name="My Service Account"
#   log_action "CREATED_SA" $SA_EMAIL
# fi

# Example: Grant IAM roles
# echo "Granting IAM roles..."
# gcloud projects add-iam-policy-binding $PROJECT_ID \
#   --member="serviceAccount:$SA_EMAIL" \
#   --role="roles/secretmanager.secretAccessor" \
#   --condition=None
# log_action "GRANTED_ROLE" "secretmanager.secretAccessor to $SA_EMAIL"

# Example: Deploy Cloud Run service
# if resource_exists "run services" $SERVICE_NAME "--region=$REGION --platform=managed"; then
#   echo "Updating Cloud Run service: $SERVICE_NAME"
#   gcloud run services update $SERVICE_NAME \
#     --platform=managed \
#     --region=$REGION \
#     --project=$PROJECT_ID \
#     --image=$IMAGE
#   log_action "UPDATED_SERVICE" $SERVICE_NAME
# else
#   echo "Creating Cloud Run service: $SERVICE_NAME"
#   gcloud run deploy $SERVICE_NAME \
#     --platform=managed \
#     --region=$REGION \
#     --project=$PROJECT_ID \
#     --image=$IMAGE \
#     --service-account=$SA_EMAIL \
#     --no-allow-unauthenticated \
#     --labels=env=$ENVIRONMENT,owner=$OWNER,deployed=$(date +%Y%m%d)
#   log_action "CREATED_SERVICE" $SERVICE_NAME
# fi

#==============================================================================
# VALIDATION
#==============================================================================

echo ""
echo "==================================="
echo "Validation"
echo "==================================="

# Example validations:
# 1. Resource existence check
# echo "Checking service exists..."
# gcloud run services describe $SERVICE_NAME \
#   --platform=managed \
#   --region=$REGION \
#   --project=$PROJECT_ID \
#   --format="value(metadata.name,status.url)"

# 2. Functional smoke test
# SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
#   --platform=managed \
#   --region=$REGION \
#   --project=$PROJECT_ID \
#   --format="value(status.url)")
# 
# echo "Testing service endpoint: $SERVICE_URL"
# if curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
#   "$SERVICE_URL/health" | grep -q "healthy"; then
#   echo "✓ Health check passed"
# else
#   echo "✗ Health check failed"
# fi

# 3. Permission verification
# echo "Verifying IAM permissions..."
# gcloud projects get-iam-policy $PROJECT_ID \
#   --flatten="bindings[].members" \
#   --filter="bindings.members:serviceAccount:$SA_EMAIL" \
#   --format="table(bindings.role)"

#==============================================================================
# DEPLOYMENT SUMMARY
#==============================================================================

echo ""
echo "==================================="
echo "Deployment Complete"
echo "==================================="
echo "Deployment log: deploy.log"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""
echo "Next steps:"
echo "  1. Review deployment log"
echo "  2. Check Cloud Console for resources"
echo "  3. Monitor logs and metrics"
echo ""
echo "To rollback, run: ./scripts/cleanup-helper.sh"
echo "==================================="
