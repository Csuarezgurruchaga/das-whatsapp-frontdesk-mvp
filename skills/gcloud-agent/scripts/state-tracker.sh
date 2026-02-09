#!/bin/bash
# GCP State Tracker
# Track and inventory resources created with consistent labels

set -euo pipefail

#==============================================================================
# CONFIGURATION
#==============================================================================

# Load environment if available
[[ -f .gcp-env ]] && source .gcp-env

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
ENVIRONMENT=${ENVIRONMENT:-"dev"}
OWNER=${OWNER:-"platform-team"}

#==============================================================================
# FUNCTIONS
#==============================================================================

usage() {
  cat << EOF
GCP State Tracker - Inventory resources with labels

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  list                 List all tracked resources
  find LABEL=VALUE     Find resources by label
  export FILE          Export inventory to JSON file
  summary              Show summary by resource type
  check-drift          Compare tracked vs actual resources

Options:
  --project ID         Override project ID
  --env ENV            Filter by environment (dev/staging/prod)
  --owner OWNER        Filter by owner label

Examples:
  $0 list
  $0 find env=dev
  $0 find owner=platform-team
  $0 summary --env prod
  $0 export resources.json

EOF
  exit 0
}

list_resources() {
  local filter=${1:-""}
  
  echo "Searching for resources in project: $PROJECT_ID"
  [[ -n "$filter" ]] && echo "Filter: $filter"
  echo ""
  
  # Use Cloud Asset Inventory for comprehensive search
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="$filter" \
    --format="table(
      name.segment(-1):label=NAME,
      assetType:label=TYPE,
      location:label=LOCATION,
      labels.env:label=ENV,
      labels.owner:label=OWNER,
      createTime.date('%Y-%m-%d'):label=CREATED
    )"
}

find_by_label() {
  local label_query=$1
  
  echo "Finding resources with label: $label_query"
  echo ""
  
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="labels.$label_query" \
    --format="table(
      name:label=RESOURCE_NAME,
      assetType:label=TYPE,
      location:label=LOCATION
    )"
}

export_inventory() {
  local output_file=$1
  
  echo "Exporting inventory to: $output_file"
  
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --format=json > "$output_file"
  
  echo "✓ Exported $(jq length $output_file) resources"
}

show_summary() {
  echo "Resource Summary for project: $PROJECT_ID"
  echo ""
  
  # Count by resource type
  echo "=== By Resource Type ==="
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --format="value(assetType)" | \
    sort | uniq -c | \
    awk '{printf "%-50s %d\n", $2, $1}'
  
  echo ""
  
  # Count by environment
  echo "=== By Environment ==="
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="labels.env:*" \
    --format="value(labels.env)" | \
    sort | uniq -c | \
    awk '{printf "%-20s %d\n", $2, $1}'
  
  echo ""
  
  # Count by owner
  echo "=== By Owner ==="
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="labels.owner:*" \
    --format="value(labels.owner)" | \
    sort | uniq -c | \
    awk '{printf "%-20s %d\n", $2, $1}'
}

check_drift() {
  echo "Checking for resources without required labels..."
  echo ""
  
  # Find resources missing 'env' label
  echo "=== Missing 'env' label ==="
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="NOT labels.env:*" \
    --format="table(name,assetType,location)" | head -20
  
  echo ""
  
  # Find resources missing 'owner' label
  echo "=== Missing 'owner' label ==="
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --query="NOT labels.owner:*" \
    --format="table(name,assetType,location)" | head -20
  
  echo ""
  echo "Note: Showing max 20 resources per category"
}

track_deployment() {
  local resource_type=$1
  local resource_name=$2
  local deploy_log="deploy.log"
  
  # Log deployment
  echo "[$(date -Iseconds)] DEPLOYED $resource_type/$resource_name PROJECT=$PROJECT_ID" >> $deploy_log
  
  # Verify labels
  echo "Verifying labels on $resource_name..."
  
  # This is a placeholder - actual implementation depends on resource type
  # Examples:
  # gcloud run services describe $resource_name --format="value(metadata.labels)"
  # gcloud compute instances describe $resource_name --format="value(labels)"
}

generate_label_report() {
  local report_file="label-report-$(date +%Y%m%d).csv"
  
  echo "Generating label compliance report..."
  
  cat > $report_file << 'EOF'
ResourceName,ResourceType,HasEnv,HasOwner,HasCostCenter,Location
EOF
  
  gcloud asset search-all-resources \
    --scope=projects/$PROJECT_ID \
    --format="csv[no-heading](
      name.segment(-1),
      assetType,
      labels.env.yesno(yes='Yes',no='No'),
      labels.owner.yesno(yes='Yes',no='No'),
      labels.cost-center.yesno(yes='Yes',no='No'),
      location
    )" >> $report_file
  
  echo "✓ Report saved to: $report_file"
  
  # Show summary
  echo ""
  echo "Label Compliance Summary:"
  TOTAL=$(tail -n +2 $report_file | wc -l)
  HAS_ENV=$(tail -n +2 $report_file | grep ",Yes," | wc -l)
  HAS_OWNER=$(tail -n +2 $report_file | cut -d',' -f4 | grep "Yes" | wc -l)
  
  echo "  Total resources: $TOTAL"
  echo "  With 'env' label: $HAS_ENV ($(( HAS_ENV * 100 / TOTAL ))%)"
  echo "  With 'owner' label: $HAS_OWNER ($(( HAS_OWNER * 100 / TOTAL ))%)"
}

#==============================================================================
# MAIN
#==============================================================================

# Parse arguments
COMMAND=${1:-}
shift || true

case "$COMMAND" in
  list)
    list_resources ""
    ;;
  find)
    [[ -z "${1:-}" ]] && echo "Error: Label filter required" && usage
    find_by_label "$1"
    ;;
  export)
    [[ -z "${1:-}" ]] && echo "Error: Output file required" && usage
    export_inventory "$1"
    ;;
  summary)
    show_summary
    ;;
  check-drift|drift)
    check_drift
    ;;
  track)
    [[ -z "${1:-}" ]] && echo "Error: Resource type required" && usage
    [[ -z "${2:-}" ]] && echo "Error: Resource name required" && usage
    track_deployment "$1" "$2"
    ;;
  report)
    generate_label_report
    ;;
  help|--help|-h)
    usage
    ;;
  "")
    echo "Error: Command required"
    usage
    ;;
  *)
    echo "Error: Unknown command: $COMMAND"
    usage
    ;;
esac
