# GCP CLI Troubleshooting Guide

Common errors and solutions when working with GCP CLI tools.

---

## 🔍 First Step: Verify Command Syntax (Context7 MCP)

**Before diving into troubleshooting, check if the command syntax has changed:**

When you encounter an error, first use context7 to verify current syntax:

```
Search GCP documentation for: "gcloud [command] current syntax"
Search GCP documentation for: "[service] CLI commands 2024"
```

**Common scenarios where syntax may have changed:**
- `gcloud storage` commands (replaced `gsutil` for many operations)
- Beta/alpha commands graduating to GA
- Deprecated flags or options
- New required parameters

**Example workflow:**
1. Command fails → Copy exact error message
2. Search context7: "gcloud run deploy error [error message]"
3. Check official docs for current syntax
4. If syntax correct → Continue to specific troubleshooting below

---

## Authentication & Configuration

### Error: "gcloud auth list shows no credentialed accounts"

**Solution:**
```bash
# Login with your user account
gcloud auth login

# Or use service account
gcloud auth activate-service-account --key-file=key.json
```

### Error: "You do not currently have an active account selected"

**Solution:**
```bash
# List available accounts
gcloud auth list

# Set active account
gcloud config set account EMAIL@example.com
```

### Error: "The project property is set to the empty string"

**Solution:**
```bash
# Set project
gcloud config set project PROJECT_ID

# Verify
gcloud config get-value project
```

### Error: "Application Default Credentials (ADC) not found"

**Solution:**
```bash
# For local development
gcloud auth application-default login

# For service accounts
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

---

## API & Permissions

### Error: "API [SERVICE.googleapis.com] not enabled"

**Solution:**
```bash
# Enable the API
gcloud services enable SERVICE.googleapis.com --project=$PROJECT_ID

# Common APIs:
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### Error: "Permission denied" or "PERMISSION_DENIED"

**Diagnosis:**
```bash
# Check current account
gcloud config get-value account

# Check IAM permissions for a project
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)"
```

**Solution:**
```bash
# Grant necessary role (requires project Owner/IAM Admin)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:EMAIL@example.com" \
  --role="roles/ROLE_NAME"

# Wait 60-120 seconds for IAM propagation
```

### Error: "The caller does not have permission" (Service Account)

**Solution:**
```bash
# Verify SA has the role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL"

# Grant the role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/ROLE_NAME"
```

---

## Cloud Run

### Error: "The user-provided container failed to start and listen on the port"

**Common Causes:**
1. App not listening on `$PORT` environment variable
2. App crashes on startup
3. Health check failing

**Solution:**
```bash
# Check logs
gcloud run services logs read SERVICE_NAME \
  --region=$REGION \
  --limit=100

# Verify PORT environment variable is used
# Your app must listen on: PORT=${PORT:-8080}

# Test locally
docker run -p 8080:8080 -e PORT=8080 IMAGE
curl http://localhost:8080
```

### Error: "Cloud Run service not accessible" (403 Forbidden)

**Cause:** Missing invoker permission

**Solution:**
```bash
# For public access
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker"

# For authenticated access
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://SERVICE-URL
```

### Error: "Revision failed with unhandled exception"

**Solution:**
```bash
# Stream logs to see the error
gcloud run services logs read SERVICE_NAME \
  --region=$REGION \
  --follow

# Common fixes:
# 1. Check environment variables are set
# 2. Verify secrets are accessible
# 3. Check Cloud SQL connection string
# 4. Ensure dependencies are in container
```

### Error: "The request was aborted because there was no available instance"

**Cause:** Cold start timeout or insufficient resources

**Solution:**
```bash
# Increase timeout
gcloud run services update SERVICE_NAME \
  --region=$REGION \
  --timeout=300

# Set minimum instances (avoid cold starts)
gcloud run services update SERVICE_NAME \
  --region=$REGION \
  --min-instances=1

# Increase memory
gcloud run services update SERVICE_NAME \
  --region=$REGION \
  --memory=1Gi
```

---

## Cloud SQL

### Error: "Cloud SQL instance not found"

**Solution:**
```bash
# List instances to verify name
gcloud sql instances list --project=$PROJECT_ID

# Verify you're in the right project
gcloud config get-value project
```

### Error: "Cannot connect to Cloud SQL from Cloud Run"

**Diagnosis:**
```bash
# Check if Cloud SQL Admin API is enabled
gcloud services list --enabled | grep sqladmin

# Verify connection string format
# Should be: PROJECT_ID:REGION:INSTANCE_NAME

# Check service account has cloudsql.client role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL AND bindings.role:roles/cloudsql.client"
```

**Solution:**
```bash
# Enable API
gcloud services enable sqladmin.googleapis.com

# Grant cloudsql.client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/cloudsql.client"

# Verify Cloud Run deployment includes Cloud SQL instance
gcloud run services describe SERVICE_NAME \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].cloudSqlInstances)"
```

### Error: "Access denied for user"

**Solution:**
```bash
# Reset password
gcloud sql users set-password USERNAME \
  --instance=INSTANCE_NAME \
  --password=NEW_PASSWORD

# Verify user exists
gcloud sql users list --instance=INSTANCE_NAME
```

---

## Secret Manager

### Error: "Secret not found"

**Solution:**
```bash
# List secrets
gcloud secrets list --project=$PROJECT_ID

# Create if missing
echo -n "secret-value" | gcloud secrets create SECRET_NAME \
  --data-file=- \
  --project=$PROJECT_ID
```

### Error: "Permission denied on secret"

**Solution:**
```bash
# Grant secret accessor role (secret-level)
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID

# OR at project level
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### Error: "Secret version not found"

**Solution:**
```bash
# List versions
gcloud secrets versions list SECRET_NAME --project=$PROJECT_ID

# Add new version
echo -n "value" | gcloud secrets versions add SECRET_NAME \
  --data-file=- \
  --project=$PROJECT_ID
```

---

## Storage

### Error: "BucketNotFoundException: 404"

**Solution:**
```bash
# Create bucket
gcloud storage buckets create gs://BUCKET_NAME \
  --project=$PROJECT_ID \
  --location=$REGION

# Verify bucket exists
gcloud storage buckets list --project=$PROJECT_ID
```

### Error: "AccessDeniedException: 403"

**Solution:**
```bash
# Grant storage permissions
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/storage.objectAdmin"

# OR at project level
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/storage.objectAdmin"
```

### Error: "Your previous default credentials are invalid"

**Solution:**
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

---

## Compute Engine

### Error: "Quota exceeded for RESOURCE_NAME"

**Diagnosis:**
```bash
# Check current quotas
gcloud compute project-info describe \
  --project=$PROJECT_ID \
  --format="table(quotas.metric,quotas.limit,quotas.usage)"
```

**Solution:**
- Request quota increase: https://console.cloud.google.com/quotas
- Or use smaller/fewer resources

### Error: "ZONE_RESOURCE_POOL_EXHAUSTED"

**Solution:**
```bash
# Try a different zone
gcloud compute instances create INSTANCE \
  --zone=us-central1-b  # Instead of us-central1-a

# Or different machine type
--machine-type=n1-standard-1
```

### Error: "Cannot SSH into instance"

**Diagnosis:**
```bash
# Check firewall rules allow SSH (port 22)
gcloud compute firewall-rules list \
  --filter="allowed.ports:22"

# Check instance is running
gcloud compute instances describe INSTANCE \
  --zone=$ZONE \
  --format="value(status)"
```

**Solution:**
```bash
# Create firewall rule for SSH
gcloud compute firewall-rules create allow-ssh \
  --network=default \
  --allow=tcp:22 \
  --source-ranges=0.0.0.0/0

# Use IAP tunnel if direct SSH blocked
gcloud compute ssh INSTANCE \
  --zone=$ZONE \
  --tunnel-through-iap
```

---

## Billing

### Error: "Billing must be enabled for activation of service"

**Solution:**
```bash
# Check billing status
gcloud billing projects describe $PROJECT_ID

# Link billing account (requires billing admin)
gcloud billing projects link $PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID

# Or enable in console:
# https://console.cloud.google.com/billing/linkedaccount?project=PROJECT_ID
```

---

## Service Account Impersonation

### Error: "Failed to impersonate SERVICE_ACCOUNT"

**Solution:**
```bash
# Grant iam.serviceAccountUser role
gcloud iam service-accounts add-iam-policy-binding SA_EMAIL \
  --member="user:YOUR_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# Then impersonate
gcloud run deploy SERVICE \
  --impersonate-service-account=SA_EMAIL
```

---

## General Debugging

### Enable verbose logging

```bash
# Debug mode
gcloud COMMAND --verbosity=debug

# Example
gcloud run deploy SERVICE --verbosity=debug
```

### Check gcloud version

```bash
# Show version
gcloud version

# Update components
gcloud components update
```

### Verify context

```bash
# Show all config
gcloud config list

# Show specific values
gcloud config get-value project
gcloud config get-value account
gcloud config get-value compute/region
```

### Clear cache

```bash
# Clear cached credentials
rm -rf ~/.config/gcloud/credentials.db

# Re-authenticate
gcloud auth login
```

---

## Common Error Patterns

### "Resource not found" Checklist
1. ✓ Correct project? `gcloud config get-value project`
2. ✓ Correct region/zone? `gcloud config get-value compute/region`
3. ✓ Resource exists? `gcloud RESOURCE list`
4. ✓ Correct spelling/name?

### "Permission denied" Checklist
1. ✓ Authenticated? `gcloud auth list`
2. ✓ Correct account? `gcloud config get-value account`
3. ✓ Has IAM role? Check with `get-iam-policy`
4. ✓ Waited for propagation? (60-120 seconds)
5. ✓ API enabled? `gcloud services list --enabled`

### "Operation timed out" Checklist
1. ✓ Network connectivity? `ping 8.8.8.8`
2. ✓ Firewall rules? `gcloud compute firewall-rules list`
3. ✓ VPC configuration? (if using custom VPC)
4. ✓ Quota limits? `gcloud compute project-info describe`

---

## Getting Help

### Use Context7 MCP for Documentation

**Query patterns for common issues:**

```bash
# Syntax errors
"gcloud run deploy current syntax and flags"
"gcloud storage buckets create latest options"

# Permission errors
"Cloud Run service account permissions requirements"
"IAM roles for Cloud SQL connection from Cloud Run"

# Service-specific issues
"Cloud Run environment variables secret manager syntax"
"Cloud SQL connection string format for Cloud Run"

# Deprecated warnings
"gcloud [command] replacement for deprecated flag"
"migration from gsutil to gcloud storage"

# New features
"Cloud Run latest features 2024"
"gcloud run deploy new flags"
```

**When to use context7:**
1. ✅ Command returns "unknown flag" or "invalid syntax"
2. ✅ Getting deprecated warnings
3. ✅ Service documentation unclear in references/
4. ✅ Need to verify latest IAM roles or permissions
5. ✅ Checking if new features are available

### Check command help
```bash
gcloud COMMAND --help
gcloud run deploy --help
```

### Search documentation
- Official docs: https://cloud.google.com/sdk/gcloud
- Cloud Run: https://cloud.google.com/run/docs
- IAM: https://cloud.google.com/iam/docs

### Check status page
- GCP Status: https://status.cloud.google.com

### Get support
```bash
# Submit feedback
gcloud feedback

# Check known issues
# https://issuetracker.google.com/issues?q=componentid:187143
```
