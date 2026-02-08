#!/bin/bash
# GCP Cleanup Helper
# Safely delete resources with confirmation and logging

set -euo pipefail

#==============================================================================
# LOAD ENVIRONMENT
#==============================================================================

if [[ -f .gcp-env ]]; then
  source .gcp-env
else
  echo "Warning: .gcp-env not found, will use command line arguments"
fi

#==============================================================================
# COLORS
#==============================================================================

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

#==============================================================================
# CLEANUP LOG
#==============================================================================

CLEANUP_LOG="cleanup-$(date +%Y%m%d-%H%M%S).log"

log_cleanup() {
  local action=$1
  local resource=$2
  echo "[$(date -Iseconds)] $action: $resource" | tee -a $CLEANUP_LOG
}

#==============================================================================
# HELPER FUNCTIONS
#==============================================================================

confirm_delete() {
  local resource_type=$1
  local resource_name=$2
  
  echo -e "${YELLOW}About to delete: $resource_type/$resource_name${NC}"
  read -p "Type 'DELETE' to confirm: " CONFIRM
  [[ "$CONFIRM" == "DELETE" ]]
}

safe_delete() {
  local resource_type=$1
  local resource_name=$2
  local extra_flags=${3:-}
  
  if confirm_delete "$resource_type" "$resource_name"; then
    echo "Deleting $resource_type: $resource_name"
    if gcloud $resource_type delete $resource_name $extra_flags \
      --project=$PROJECT_ID --quiet; then
      log_cleanup "DELETED" "$resource_type/$resource_name"
      echo -e "${GREEN}✓ Deleted${NC}"
    else
      log_cleanup "FAILED_DELETE" "$resource_type/$resource_name"
      echo -e "${RED}✗ Failed to delete${NC}"
    fi
  else
    log_cleanup "SKIPPED" "$resource_type/$resource_name"
    echo "Skipped"
  fi
}

#==============================================================================
# CONTEXT VERIFICATION
#==============================================================================

echo -e "${RED}==================================="
echo "⚠  RESOURCE CLEANUP WARNING  ⚠"
echo "===================================${NC}"
echo "Project: ${PROJECT_ID:-NOT SET}"
echo "Region:  ${REGION:-NOT SET}"
echo ""
echo "This will DELETE resources."
echo "This action CANNOT be undone."
echo ""
read -p "Proceed with cleanup? (yes/no): " PROCEED
[[ "$PROCEED" != "yes" ]] && exit 0

#==============================================================================
# LIST RESOURCES TO DELETE
#==============================================================================

echo ""
echo "Select resources to delete:"
echo ""

# Cloud Run services
if [[ -n "${SERVICE_NAME:-}" ]]; then
  if gcloud run services describe $SERVICE_NAME \
    --platform=managed --region=$REGION --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[1] Cloud Run Service: $SERVICE_NAME${NC}"
    CLEANUP_CLOUD_RUN=1
  else
    echo "[1] Cloud Run Service: Not found"
    CLEANUP_CLOUD_RUN=0
  fi
else
  CLEANUP_CLOUD_RUN=0
fi

# Service Accounts
if [[ -n "${RUNTIME_SA_EMAIL:-}" ]]; then
  if gcloud iam service-accounts describe $RUNTIME_SA_EMAIL \
    --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[2] Service Account: $RUNTIME_SA_EMAIL${NC}"
    CLEANUP_SA=1
  else
    echo "[2] Service Account: Not found"
    CLEANUP_SA=0
  fi
else
  CLEANUP_SA=0
fi

# Cloud SQL instances
if [[ -n "${SQL_INSTANCE_NAME:-}" ]]; then
  if gcloud sql instances describe $SQL_INSTANCE_NAME \
    --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[3] Cloud SQL Instance: $SQL_INSTANCE_NAME${NC}"
    CLEANUP_SQL=1
  else
    echo "[3] Cloud SQL Instance: Not found"
    CLEANUP_SQL=0
  fi
else
  CLEANUP_SQL=0
fi

# GCS Buckets
if [[ -n "${DATA_BUCKET:-}" ]]; then
  if gcloud storage buckets describe gs://$DATA_BUCKET \
    --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[4] Storage Bucket: $DATA_BUCKET${NC}"
    CLEANUP_BUCKET=1
  else
    echo "[4] Storage Bucket: Not found"
    CLEANUP_BUCKET=0
  fi
else
  CLEANUP_BUCKET=0
fi

# Pub/Sub topics
if [[ -n "${PUBSUB_TOPIC:-}" ]]; then
  if gcloud pubsub topics describe $PUBSUB_TOPIC \
    --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[5] Pub/Sub Topic: $PUBSUB_TOPIC${NC}"
    CLEANUP_PUBSUB=1
  else
    echo "[5] Pub/Sub Topic: Not found"
    CLEANUP_PUBSUB=0
  fi
else
  CLEANUP_PUBSUB=0
fi

# Secrets
if [[ -n "${DB_PASSWORD_SECRET:-}" ]]; then
  if gcloud secrets describe $DB_PASSWORD_SECRET \
    --project=$PROJECT_ID 2>/dev/null; then
    echo -e "${YELLOW}[6] Secret: $DB_PASSWORD_SECRET${NC}"
    CLEANUP_SECRET=1
  else
    echo "[6] Secret: Not found"
    CLEANUP_SECRET=0
  fi
else
  CLEANUP_SECRET=0
fi

echo ""
echo "Cleanup will be logged to: $CLEANUP_LOG"
echo ""

#==============================================================================
# EXECUTE CLEANUP (in reverse dependency order)
#==============================================================================

# Delete Cloud Run service first (depends on SA)
if [[ $CLEANUP_CLOUD_RUN -eq 1 ]]; then
  echo ""
  echo "=== Cloud Run Service ==="
  safe_delete "run services" "$SERVICE_NAME" "--platform=managed --region=$REGION"
fi

# Delete Pub/Sub subscriptions and topics
if [[ $CLEANUP_PUBSUB -eq 1 ]]; then
  echo ""
  echo "=== Pub/Sub ==="
  
  # Delete subscriptions first
  if [[ -n "${PUBSUB_SUBSCRIPTION:-}" ]]; then
    if gcloud pubsub subscriptions describe $PUBSUB_SUBSCRIPTION \
      --project=$PROJECT_ID 2>/dev/null; then
      safe_delete "pubsub subscriptions" "$PUBSUB_SUBSCRIPTION" ""
    fi
  fi
  
  # Then delete topic
  safe_delete "pubsub topics" "$PUBSUB_TOPIC" ""
fi

# Delete Cloud SQL instance (WARNING: includes data!)
if [[ $CLEANUP_SQL -eq 1 ]]; then
  echo ""
  echo -e "${RED}=== Cloud SQL Instance ===${NC}"
  echo -e "${RED}WARNING: This will delete ALL data in the database!${NC}"
  safe_delete "sql instances" "$SQL_INSTANCE_NAME" ""
fi

# Delete GCS buckets (WARNING: includes data!)
if [[ $CLEANUP_BUCKET -eq 1 ]]; then
  echo ""
  echo -e "${RED}=== Storage Bucket ===${NC}"
  echo -e "${RED}WARNING: This will delete ALL files in the bucket!${NC}"
  
  # First, list contents
  OBJECT_COUNT=$(gcloud storage ls gs://$DATA_BUCKET/** 2>/dev/null | wc -l || echo "0")
  echo "Bucket contains approximately $OBJECT_COUNT objects"
  
  if confirm_delete "storage bucket" "$DATA_BUCKET"; then
    echo "Deleting bucket contents..."
    gcloud storage rm -r gs://$DATA_BUCKET --project=$PROJECT_ID || true
    log_cleanup "DELETED" "storage bucket/$DATA_BUCKET"
    echo -e "${GREEN}✓ Deleted${NC}"
  else
    log_cleanup "SKIPPED" "storage bucket/$DATA_BUCKET"
    echo "Skipped"
  fi
fi

# Delete secrets
if [[ $CLEANUP_SECRET -eq 1 ]]; then
  echo ""
  echo "=== Secrets ==="
  safe_delete "secrets" "$DB_PASSWORD_SECRET" ""
fi

# Delete service account LAST (other resources may depend on it)
if [[ $CLEANUP_SA -eq 1 ]]; then
  echo ""
  echo "=== Service Account ==="
  
  # First, remove IAM bindings
  echo "Removing IAM policy bindings..."
  gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:$RUNTIME_SA_EMAIL" \
    --format="value(bindings.role)" | while read role; do
    echo "  Removing role: $role"
    gcloud projects remove-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:$RUNTIME_SA_EMAIL" \
      --role="$role" \
      --quiet 2>/dev/null || true
  done
  
  # Then delete SA
  safe_delete "iam service-accounts" "$RUNTIME_SA_EMAIL" ""
fi

#==============================================================================
# CLEANUP SUMMARY
#==============================================================================

echo ""
echo "==================================="
echo "Cleanup Complete"
echo "==================================="
echo "Log file: $CLEANUP_LOG"
echo ""
echo "Summary of deleted resources:"
cat $CLEANUP_LOG
echo ""
echo -e "${GREEN}Cleanup finished${NC}"
