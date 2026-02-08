# GCP IAM Patterns Reference

## Three Types of Identities

Always clarify which identity you're configuring:

1. **Runtime SA** - Used BY the service (Cloud Run, GCE, Cloud Functions run AS this)
2. **Invoker** - CALLS the service (users, other services that trigger/call)
3. **Deployer** - DEPLOYS the service (CI/CD service account or human)

---

## Pattern 1: Cloud Run with Dependencies

### Runtime Service Account (runs AS)

```bash
# Create runtime SA
gcloud iam service-accounts create my-service-runtime \
  --project=$PROJECT_ID \
  --display-name="Cloud Run Runtime SA"

SA_EMAIL="my-service-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant access to Secret Manager
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Grant access to Cloud SQL
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudsql.client"

# Grant access to Pub/Sub (publish)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/pubsub.publisher"

# Deploy with this SA
gcloud run deploy my-service \
  --service-account=$SA_EMAIL \
  ...
```

### Invoker Identity (calls the service)

```bash
# Public access (use with caution)
gcloud run services add-iam-policy-binding my-service \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker"

# Authenticated users only
gcloud run services add-iam-policy-binding my-service \
  --region=$REGION \
  --member="user:alice@example.com" \
  --role="roles/run.invoker"

# Another service account (service-to-service)
gcloud run services add-iam-policy-binding my-service \
  --region=$REGION \
  --member="serviceAccount:caller@project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Deployer Identity (CI/CD)

```bash
# Create CI/CD SA
gcloud iam service-accounts create cicd-deployer \
  --project=$PROJECT_ID

CICD_SA="cicd-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant deployment permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CICD_SA" \
  --role="roles/run.admin"

# Allow impersonation of runtime SA
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --member="serviceAccount:$CICD_SA" \
  --role="roles/iam.serviceAccountUser"
```

---

## Pattern 2: Cloud Functions with Triggers

### Runtime SA

```bash
# Create function SA
gcloud iam service-accounts create my-function-runtime \
  --project=$PROJECT_ID

SA_EMAIL="my-function-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant access to dependencies
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/datastore.user"

# Deploy with SA
gcloud functions deploy my-function \
  --service-account=$SA_EMAIL \
  ...
```

### Invoker (for HTTP functions)

```bash
# Allow public invocation
gcloud functions add-iam-policy-binding my-function \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker"
```

### Event Trigger (Pub/Sub)

```bash
# The Pub/Sub service agent needs permission to invoke
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud functions add-iam-policy-binding my-function \
  --region=$REGION \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/cloudfunctions.invoker"
```

---

## Pattern 3: GCE Instance with Service Account

### Runtime SA

```bash
# Create instance SA
gcloud iam service-accounts create my-instance-sa \
  --project=$PROJECT_ID

SA_EMAIL="my-instance-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/monitoring.metricWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"

# Create instance with SA
gcloud compute instances create my-instance \
  --service-account=$SA_EMAIL \
  --scopes=cloud-platform \
  ...
```

---

## Pattern 4: Cloud Storage Access

### Read-only access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"
```

### Read-write access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"
```

### Bucket-level permissions (preferred over project-level)

```bash
gcloud storage buckets add-iam-policy-binding gs://my-bucket \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"
```

---

## Pattern 5: Cross-Project Access

### Service in Project A accessing resources in Project B

```bash
# In Project A: Create SA
gcloud iam service-accounts create cross-project-sa \
  --project=$PROJECT_A

SA_EMAIL="cross-project-sa@${PROJECT_A}.iam.gserviceaccount.com"

# In Project B: Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_B \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"
```

---

## Pattern 6: Workload Identity (GKE)

### Link Kubernetes SA to Google SA

```bash
# Create Google SA
gcloud iam service-accounts create my-app-sa \
  --project=$PROJECT_ID

# Allow Kubernetes SA to impersonate Google SA
gcloud iam service-accounts add-iam-policy-binding \
  my-app-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[NAMESPACE/KSA_NAME]"

# Annotate Kubernetes SA
kubectl annotate serviceaccount KSA_NAME \
  -n NAMESPACE \
  iam.gke.io/gcp-service-account=my-app-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

---

## Pattern 7: Secret Manager Access

### Grant specific secret access

```bash
# Secret-level permission (preferred)
gcloud secrets add-iam-policy-binding my-secret \
  --project=$PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Project-level (use sparingly)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Pattern 8: Conditional IAM Bindings

### Time-based access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/compute.viewer" \
  --condition='expression=request.time < timestamp("2024-12-31T23:59:59Z"),
               title=temporary-access,
               description=Access expires end of 2024'
```

### Resource-based conditions

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer" \
  --condition='expression=resource.name.startsWith("projects/_/buckets/dev-"),
               title=dev-buckets-only,
               description=Only access dev buckets'
```

---

## Common Roles by Use Case

### Cloud Run

- **Runtime**: `roles/secretmanager.secretAccessor`, `roles/cloudsql.client`
- **Invoker**: `roles/run.invoker`
- **Deployer**: `roles/run.admin`, `roles/iam.serviceAccountUser`

### Cloud Functions

- **Runtime**: `roles/datastore.user`, `roles/pubsub.publisher`
- **Invoker**: `roles/cloudfunctions.invoker`
- **Deployer**: `roles/cloudfunctions.developer`

### GCE

- **Instance**: `roles/logging.logWriter`, `roles/monitoring.metricWriter`
- **SSH Access**: `roles/compute.instanceAdmin.v1`, `roles/iap.tunnelResourceAccessor`

### Cloud Storage

- **Read**: `roles/storage.objectViewer`
- **Write**: `roles/storage.objectCreator`
- **Admin**: `roles/storage.objectAdmin`

### Secret Manager

- **Read**: `roles/secretmanager.secretAccessor`
- **Manage**: `roles/secretmanager.admin`

### Cloud SQL

- **Connect**: `roles/cloudsql.client`
- **Admin**: `roles/cloudsql.admin`

---

## Best Practices

1. **Principle of Least Privilege**: Grant minimum necessary roles
2. **Use Service Accounts**: Never use personal accounts for services
3. **Resource-level Bindings**: Prefer bucket/secret-level over project-level
4. **Avoid Primitive Roles**: Don't use Owner/Editor/Viewer except for humans
5. **Audit Regularly**: Use `gcloud projects get-iam-policy` to review
6. **Use Conditions**: Add time/resource constraints when possible
7. **Separate Environments**: Different SAs for dev/staging/prod
8. **Document Justification**: Comment why each role is needed

---

## Quick Reference Commands

### List all IAM bindings for a service account

```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL" \
  --format="table(bindings.role)"
```

### Remove an IAM binding

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/ROLE_NAME"
```

### Test if SA has permission

```bash
gcloud projects test-iam-permissions $PROJECT_ID \
  --permissions=PERMISSION_NAME
```

### List all service accounts in project

```bash
gcloud iam service-accounts list --project=$PROJECT_ID
```
