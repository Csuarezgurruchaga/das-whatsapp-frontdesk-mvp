# GCP Common Commands Reference

Quick reference for frequently used gcloud commands by service.

---

## Cloud Run

### Deploy

```bash
# Basic deployment
gcloud run deploy SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=gcr.io/$PROJECT_ID/IMAGE:TAG \
  --service-account=$SA_EMAIL \
  --no-allow-unauthenticated

# With environment variables
gcloud run deploy SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=IMAGE \
  --set-env-vars="KEY1=value1,KEY2=value2"

# With secrets
gcloud run deploy SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=IMAGE \
  --set-secrets="DB_PASSWORD=db-password:latest"

# With Cloud SQL
gcloud run deploy SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=IMAGE \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:INSTANCE_NAME

# With VPC connector
gcloud run deploy SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=IMAGE \
  --vpc-connector=CONNECTOR_NAME
```

### Describe & List

```bash
# Describe service
gcloud run services describe SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID

# Get service URL
gcloud run services describe SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)"

# List all services
gcloud run services list \
  --platform=managed \
  --project=$PROJECT_ID

# List services with filters
gcloud run services list \
  --platform=managed \
  --project=$PROJECT_ID \
  --filter="metadata.labels.env=prod"
```

### Update & Delete

```bash
# Update image
gcloud run services update SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --image=NEW_IMAGE

# Update traffic (gradual rollout)
gcloud run services update-traffic SERVICE_NAME \
  --region=$REGION \
  --to-revisions=LATEST=50,PREVIOUS=50

# Delete service
gcloud run services delete SERVICE_NAME \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --quiet
```

### Logs

```bash
# Stream logs
gcloud run services logs read SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --limit=50 \
  --follow

# Filter logs by severity
gcloud run services logs read SERVICE_NAME \
  --region=$REGION \
  --filter="severity>=ERROR"
```

---

## Cloud Storage

### Buckets

```bash
# Create bucket (preferred gcloud storage command)
gcloud storage buckets create gs://BUCKET_NAME \
  --project=$PROJECT_ID \
  --location=$REGION \
  --uniform-bucket-level-access \
  --labels=env=dev,owner=team

# Create with lifecycle policy
gcloud storage buckets create gs://BUCKET_NAME \
  --location=$REGION \
  --lifecycle-file=lifecycle.json

# Describe bucket
gcloud storage buckets describe gs://BUCKET_NAME

# List buckets
gcloud storage buckets list --project=$PROJECT_ID

# Delete bucket
gcloud storage buckets delete gs://BUCKET_NAME \
  --project=$PROJECT_ID
```

### Objects

```bash
# Upload file
gcloud storage cp LOCAL_FILE gs://BUCKET_NAME/

# Upload directory
gcloud storage cp -r LOCAL_DIR gs://BUCKET_NAME/

# Download file
gcloud storage cp gs://BUCKET_NAME/FILE LOCAL_PATH

# List objects
gcloud storage ls gs://BUCKET_NAME/

# Delete object
gcloud storage rm gs://BUCKET_NAME/FILE

# Delete all objects in bucket
gcloud storage rm -r gs://BUCKET_NAME/**
```

### Legacy gsutil (use only when gcloud storage lacks feature)

```bash
# Set CORS
gsutil cors set cors.json gs://BUCKET_NAME

# Set bucket-level permissions
gsutil iam ch serviceAccount:SA@project.iam.gserviceaccount.com:objectViewer gs://BUCKET_NAME
```

---

## Compute Engine

### Instances

```bash
# Create instance
gcloud compute instances create INSTANCE_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --service-account=$SA_EMAIL \
  --scopes=cloud-platform \
  --labels=env=dev,owner=team

# Create with startup script
gcloud compute instances create INSTANCE_NAME \
  --zone=$ZONE \
  --metadata-from-file=startup-script=startup.sh

# List instances
gcloud compute instances list \
  --project=$PROJECT_ID \
  --filter="zone:$ZONE"

# Describe instance
gcloud compute instances describe INSTANCE_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID

# Start/Stop/Delete
gcloud compute instances start INSTANCE_NAME --zone=$ZONE
gcloud compute instances stop INSTANCE_NAME --zone=$ZONE
gcloud compute instances delete INSTANCE_NAME --zone=$ZONE --quiet
```

### SSH

```bash
# SSH into instance
gcloud compute ssh INSTANCE_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID

# SSH with IAP tunnel
gcloud compute ssh INSTANCE_NAME \
  --zone=$ZONE \
  --tunnel-through-iap
```

---

## Cloud SQL

### Instances

```bash
# Create Postgres instance
gcloud sql instances create INSTANCE_NAME \
  --project=$PROJECT_ID \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=$REGION \
  --labels=env=dev

# Create MySQL instance
gcloud sql instances create INSTANCE_NAME \
  --project=$PROJECT_ID \
  --database-version=MYSQL_8_0 \
  --tier=db-n1-standard-1 \
  --region=$REGION

# List instances
gcloud sql instances list --project=$PROJECT_ID

# Describe instance
gcloud sql instances describe INSTANCE_NAME \
  --project=$PROJECT_ID

# Delete instance
gcloud sql instances delete INSTANCE_NAME \
  --project=$PROJECT_ID \
  --quiet
```

### Databases & Users

```bash
# Create database
gcloud sql databases create DATABASE_NAME \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID

# Create user
gcloud sql users create USERNAME \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID \
  --password=PASSWORD

# List databases
gcloud sql databases list \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID
```

### Connect

```bash
# Connect via Cloud SQL Proxy
cloud_sql_proxy -instances=$PROJECT_ID:$REGION:INSTANCE_NAME=tcp:5432

# Connect directly
gcloud sql connect INSTANCE_NAME \
  --user=USERNAME \
  --quiet
```

---

## Secret Manager

### Secrets

```bash
# Create secret
echo -n "secret-value" | gcloud secrets create SECRET_NAME \
  --project=$PROJECT_ID \
  --data-file=- \
  --labels=env=dev

# Create from file
gcloud secrets create SECRET_NAME \
  --project=$PROJECT_ID \
  --data-file=secret.txt

# List secrets
gcloud secrets list --project=$PROJECT_ID

# Describe secret
gcloud secrets describe SECRET_NAME \
  --project=$PROJECT_ID

# Delete secret
gcloud secrets delete SECRET_NAME \
  --project=$PROJECT_ID \
  --quiet
```

### Versions

```bash
# Add new version
echo -n "new-value" | gcloud secrets versions add SECRET_NAME \
  --project=$PROJECT_ID \
  --data-file=-

# Access version
gcloud secrets versions access latest \
  --secret=SECRET_NAME \
  --project=$PROJECT_ID

# List versions
gcloud secrets versions list SECRET_NAME \
  --project=$PROJECT_ID

# Delete version
gcloud secrets versions destroy VERSION \
  --secret=SECRET_NAME \
  --project=$PROJECT_ID
```

---

## Pub/Sub

### Topics

```bash
# Create topic
gcloud pubsub topics create TOPIC_NAME \
  --project=$PROJECT_ID \
  --labels=env=dev

# List topics
gcloud pubsub topics list --project=$PROJECT_ID

# Describe topic
gcloud pubsub topics describe TOPIC_NAME \
  --project=$PROJECT_ID

# Delete topic
gcloud pubsub topics delete TOPIC_NAME \
  --project=$PROJECT_ID
```

### Subscriptions

```bash
# Create subscription
gcloud pubsub subscriptions create SUBSCRIPTION_NAME \
  --topic=TOPIC_NAME \
  --project=$PROJECT_ID \
  --ack-deadline=60 \
  --message-retention-duration=7d

# Create push subscription
gcloud pubsub subscriptions create SUBSCRIPTION_NAME \
  --topic=TOPIC_NAME \
  --push-endpoint=https://example.com/push

# Pull messages
gcloud pubsub subscriptions pull SUBSCRIPTION_NAME \
  --limit=10 \
  --auto-ack

# Delete subscription
gcloud pubsub subscriptions delete SUBSCRIPTION_NAME \
  --project=$PROJECT_ID
```

### Publish

```bash
# Publish message
gcloud pubsub topics publish TOPIC_NAME \
  --project=$PROJECT_ID \
  --message="Hello World"

# Publish with attributes
gcloud pubsub topics publish TOPIC_NAME \
  --message="Event data" \
  --attribute=key1=value1,key2=value2
```

---

## IAM & Service Accounts

### Service Accounts

```bash
# Create SA
gcloud iam service-accounts create SA_NAME \
  --project=$PROJECT_ID \
  --display-name="Display Name"

# List SAs
gcloud iam service-accounts list \
  --project=$PROJECT_ID

# Describe SA
gcloud iam service-accounts describe SA_EMAIL \
  --project=$PROJECT_ID

# Delete SA
gcloud iam service-accounts delete SA_EMAIL \
  --project=$PROJECT_ID \
  --quiet
```

### IAM Bindings

```bash
# Add IAM binding (project level)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/ROLE_NAME"

# Remove IAM binding
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/ROLE_NAME"

# Get IAM policy
gcloud projects get-iam-policy $PROJECT_ID

# Get IAM policy for specific member
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL" \
  --format="table(bindings.role)"
```

### Service Account Keys (avoid in production)

```bash
# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=SA_EMAIL \
  --project=$PROJECT_ID

# List keys
gcloud iam service-accounts keys list \
  --iam-account=SA_EMAIL \
  --project=$PROJECT_ID

# Delete key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=SA_EMAIL \
  --project=$PROJECT_ID
```

---

## Projects & Configuration

### Projects

```bash
# List projects
gcloud projects list

# Describe project
gcloud projects describe $PROJECT_ID

# Set active project
gcloud config set project $PROJECT_ID
```

### Configuration

```bash
# Show all config
gcloud config list

# Set region
gcloud config set compute/region us-central1

# Set zone
gcloud config set compute/zone us-central1-a

# Create named configuration
gcloud config configurations create dev
gcloud config configurations activate dev
```

### APIs

```bash
# Enable API
gcloud services enable SERVICE_NAME.googleapis.com \
  --project=$PROJECT_ID

# List enabled APIs
gcloud services list --enabled \
  --project=$PROJECT_ID

# Disable API
gcloud services disable SERVICE_NAME.googleapis.com \
  --project=$PROJECT_ID
```

---

## Logging & Monitoring

### Logs

```bash
# Read recent logs
gcloud logging read \
  --project=$PROJECT_ID \
  --limit=50 \
  --format=json

# Filter logs
gcloud logging read \
  'resource.type="cloud_run_revision" AND severity>=ERROR' \
  --limit=100 \
  --format=json

# Stream logs
gcloud logging tail \
  'resource.type="cloud_run_revision"' \
  --project=$PROJECT_ID
```

### Metrics

```bash
# List metrics
gcloud monitoring metrics-descriptors list \
  --project=$PROJECT_ID

# Read time series
gcloud monitoring time-series list \
  --filter='metric.type="compute.googleapis.com/instance/cpu/utilization"' \
  --project=$PROJECT_ID
```

---

## Networking

### VPC

```bash
# Create VPC
gcloud compute networks create NETWORK_NAME \
  --project=$PROJECT_ID \
  --subnet-mode=custom

# Create subnet
gcloud compute networks subnets create SUBNET_NAME \
  --project=$PROJECT_ID \
  --network=NETWORK_NAME \
  --region=$REGION \
  --range=10.0.0.0/24

# List networks
gcloud compute networks list --project=$PROJECT_ID
```

### Firewall Rules

```bash
# Create firewall rule
gcloud compute firewall-rules create RULE_NAME \
  --project=$PROJECT_ID \
  --network=NETWORK_NAME \
  --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0

# List firewall rules
gcloud compute firewall-rules list \
  --project=$PROJECT_ID

# Delete firewall rule
gcloud compute firewall-rules delete RULE_NAME \
  --project=$PROJECT_ID \
  --quiet
```

---

## Asset Inventory

### Search Resources

```bash
# Search all resources
gcloud asset search-all-resources \
  --scope=projects/$PROJECT_ID \
  --query="labels.env=dev"

# Export assets
gcloud asset export \
  --output-path=gs://BUCKET/assets.json \
  --content-type=resource \
  --project=$PROJECT_ID
```

---

## Billing

```bash
# Describe billing
gcloud billing projects describe $PROJECT_ID

# List billing accounts
gcloud billing accounts list

# Link billing account
gcloud billing projects link $PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID
```

---

## Common Flags Reference

```bash
--project=$PROJECT_ID          # Specify project
--region=$REGION               # Specify region
--zone=$ZONE                   # Specify zone
--format=json                  # Output as JSON
--format=value(FIELD)          # Extract specific field
--filter="EXPRESSION"          # Filter results
--limit=N                      # Limit results
--quiet                        # Skip confirmations
--labels=key1=val1,key2=val2   # Add labels
--verbosity=debug              # Debug output
```
