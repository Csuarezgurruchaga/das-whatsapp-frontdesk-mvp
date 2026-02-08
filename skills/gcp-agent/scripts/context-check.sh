#!/bin/bash
# GCP Context Verification Script
# Run this before any deployment to verify you're in the right project/region

set -euo pipefail

#==============================================================================
# COLORS (optional, for better readability)
#==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#==============================================================================
# GET CURRENT CONTEXT
#==============================================================================

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "NOT SET")
CURRENT_REGION=$(gcloud config get-value compute/region 2>/dev/null || echo "NOT SET")
CURRENT_ZONE=$(gcloud config get-value compute/zone 2>/dev/null || echo "NOT SET")
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "NOT SET")

#==============================================================================
# DISPLAY CONTEXT
#==============================================================================

echo "==================================="
echo "GCP Context Verification"
echo "==================================="
echo ""
echo -e "${GREEN}Current Configuration:${NC}"
echo "  Account:  $CURRENT_ACCOUNT"
echo "  Project:  $CURRENT_PROJECT"
echo "  Region:   $CURRENT_REGION"
echo "  Zone:     $CURRENT_ZONE"
echo ""

#==============================================================================
# CHECK FOR ISSUES
#==============================================================================

ISSUES=0

# Check if project is set
if [[ "$CURRENT_PROJECT" == "NOT SET" ]]; then
  echo -e "${RED}✗ Project not set${NC}"
  echo "  Fix: gcloud config set project YOUR_PROJECT_ID"
  ISSUES=$((ISSUES + 1))
else
  echo -e "${GREEN}✓ Project set${NC}"
fi

# Check if region is set
if [[ "$CURRENT_REGION" == "NOT SET" ]]; then
  echo -e "${YELLOW}⚠ Region not set (will default to us-central1)${NC}"
  echo "  Fix: gcloud config set compute/region YOUR_REGION"
else
  echo -e "${GREEN}✓ Region set${NC}"
fi

# Check if authenticated
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
  echo -e "${GREEN}✓ Authenticated${NC}"
else
  echo -e "${RED}✗ Not authenticated${NC}"
  echo "  Fix: gcloud auth login"
  ISSUES=$((ISSUES + 1))
fi

# Check billing (if project is set)
if [[ "$CURRENT_PROJECT" != "NOT SET" ]]; then
  BILLING_ENABLED=$(gcloud billing projects describe $CURRENT_PROJECT \
    --format="value(billingEnabled)" 2>/dev/null || echo "UNKNOWN")
  
  if [[ "$BILLING_ENABLED" == "True" ]]; then
    echo -e "${GREEN}✓ Billing enabled${NC}"
  elif [[ "$BILLING_ENABLED" == "False" ]]; then
    echo -e "${RED}✗ Billing NOT enabled${NC}"
    echo "  This will prevent resource creation"
    ISSUES=$((ISSUES + 1))
  else
    echo -e "${YELLOW}⚠ Could not verify billing status${NC}"
  fi
fi

echo ""

#==============================================================================
# WARNINGS FOR PRODUCTION
#==============================================================================

# Check if project looks like production
if [[ "$CURRENT_PROJECT" =~ prod|production ]]; then
  echo -e "${RED}==================================="
  echo "⚠  WARNING: PRODUCTION PROJECT  ⚠"
  echo "===================================${NC}"
  echo "You are operating in what appears to be a production project."
  echo "Please ensure you:"
  echo "  1. Have proper authorization"
  echo "  2. Have tested in dev/staging first"
  echo "  3. Have a rollback plan"
  echo ""
fi

#==============================================================================
# SUGGEST CORRECTIONS
#==============================================================================

if [[ $ISSUES -gt 0 ]]; then
  echo -e "${RED}Found $ISSUES issue(s) that need attention${NC}"
  echo ""
  echo "Quick fix commands:"
  echo "  gcloud auth login"
  echo "  gcloud config set project YOUR_PROJECT_ID"
  echo "  gcloud config set compute/region us-central1"
  echo "  gcloud config set compute/zone us-central1-a"
  echo ""
  exit 1
fi

#==============================================================================
# FINAL CONFIRMATION
#==============================================================================

echo "==================================="
echo -e "${GREEN}Context looks good!${NC}"
echo "==================================="
echo ""

# If called with --interactive flag, ask for confirmation
if [[ "${1:-}" == "--interactive" ]]; then
  read -p "Proceed with this context? (yes/no): " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "Cancelled by user"
    exit 0
  fi
fi

echo -e "${GREEN}✓ Ready to proceed${NC}"
exit 0
