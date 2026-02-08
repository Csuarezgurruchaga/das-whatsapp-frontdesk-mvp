# GCP Production Readiness Checklist

Use this checklist before deploying to production or promoting staging to production.

---

## Security

### Identity & Access Management

- [ ] **Service accounts created** with descriptive names and descriptions
- [ ] **Least privilege IAM** - minimum roles granted, no Owner/Editor roles
- [ ] **No personal accounts** used for service identities
- [ ] **Service account keys avoided** - use Workload Identity or metadata service
- [ ] **Resource-level permissions** preferred over project-level where possible
- [ ] **Conditional IAM bindings** used for time/resource constraints
- [ ] **Regular IAM audits** scheduled (quarterly minimum)

```bash
# Audit current IAM bindings
gcloud projects get-iam-policy $PROJECT_ID > iam-audit.txt

# Find overly permissive bindings
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:(roles/owner OR roles/editor)"
```

### Secrets & Credentials

- [ ] **Secret Manager** used for all secrets (no hardcoded credentials)
- [ ] **Secrets rotated** regularly
- [ ] **Secret access auditing** enabled
- [ ] **Different secrets per environment** (dev/staging/prod)

```bash
# Verify secret access logging
gcloud secrets describe SECRET_NAME \
  --format="value(name,createTime,labels)"
```

### Network Security

- [ ] **Custom VPC** created (not using default VPC)
- [ ] **Firewall rules** reviewed and minimal
- [ ] **VPC Service Controls** configured for sensitive data
- [ ] **Cloud Armor** enabled for internet-facing services (WAF/DDoS)
- [ ] **Private Google Access** enabled where needed
- [ ] **VPC Flow Logs** enabled for network monitoring

```bash
# List firewall rules
gcloud compute firewall-rules list --project=$PROJECT_ID

# Check for overly permissive rules
gcloud compute firewall-rules list \
  --filter="allowed[].IPProtocol:all OR sourceRanges:0.0.0.0/0" \
  --format="table(name,allowed[].ports,sourceRanges)"
```

### Encryption

- [ ] **CMEK** (Customer-Managed Encryption Keys) for sensitive data
- [ ] **Encryption at rest** verified for all storage
- [ ] **TLS/HTTPS enforced** for all external endpoints
- [ ] **Certificate management** automated

---

## Reliability & Availability

### High Availability

- [ ] **Multi-zone deployment** for critical services
- [ ] **Multi-region deployment** for global services
- [ ] **Load balancing** configured
- [ ] **Health checks** implemented and tested
- [ ] **Autoscaling** configured with appropriate min/max
- [ ] **Circuit breakers** and retry logic in code

```bash
# Cloud Run HA configuration
gcloud run deploy SERVICE \
  --min-instances=2 \
  --max-instances=100 \
  --concurrency=80

# Check current scaling
gcloud run services describe SERVICE \
  --region=$REGION \
  --format="value(spec.template.metadata.annotations)"
```

### Backup & Recovery

- [ ] **Automated backups** configured
- [ ] **Backup retention policy** defined
- [ ] **Recovery procedures** documented and tested
- [ ] **RTO/RPO** defined and achievable
- [ ] **Cross-region backup** for critical data
- [ ] **Disaster recovery plan** documented

```bash
# Cloud SQL automated backups
gcloud sql instances patch INSTANCE_NAME \
  --backup-start-time=02:00 \
  --enable-bin-log

# GCS lifecycle policy for backups
cat > lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF
```

### Monitoring & Alerting

- [ ] **Uptime checks** configured
- [ ] **Alerting policies** created for critical metrics
- [ ] **Error rate monitoring** enabled
- [ ] **Latency monitoring** configured
- [ ] **Resource utilization alerts** set
- [ ] **Log-based metrics** for business KPIs
- [ ] **On-call rotation** defined
- [ ] **Runbooks** created for common incidents

```bash
# Create uptime check
gcloud monitoring uptime create SERVICE-uptime \
  --resource-type=uptime-url \
  --display-name="Service Health Check" \
  --host=SERVICE-URL \
  --path=/health

# Create alert policy (via console or Cloud Monitoring API)
# https://console.cloud.google.com/monitoring/alerting
```

---

## Performance & Cost

### Performance

- [ ] **Load testing** completed
- [ ] **Performance benchmarks** established
- [ ] **CDN** enabled for static content
- [ ] **Database indexes** optimized
- [ ] **Connection pooling** configured
- [ ] **Caching strategy** implemented
- [ ] **Image optimization** for Cloud Run containers

```bash
# Cloud CDN (requires Load Balancer)
gcloud compute backend-services update BACKEND \
  --enable-cdn

# Check Cloud Run cold start metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"'
```

### Cost Optimization

- [ ] **Committed use discounts** evaluated
- [ ] **Sustained use discounts** understood
- [ ] **Right-sizing** performed for all resources
- [ ] **Idle resource detection** automated
- [ ] **Budget alerts** configured
- [ ] **Cost allocation labels** applied to all resources
- [ ] **Preemptible instances** used where appropriate
- [ ] **Auto-scaling policies** tuned

```bash
# Apply cost labels to all resources
--labels=env=prod,team=platform,cost-center=engineering,app=myapp

# Set up budget alert
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Production Budget" \
  --budget-amount=1000 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## Compliance & Governance

### Audit Logging

- [ ] **Admin Activity logs** enabled (on by default)
- [ ] **Data Access logs** enabled for sensitive services
- [ ] **System Event logs** reviewed regularly
- [ ] **Log retention** configured (minimum 1 year)
- [ ] **Log exports** to BigQuery or Cloud Storage
- [ ] **Log analysis** automated

```bash
# Enable Data Access logs
gcloud projects get-iam-policy $PROJECT_ID \
  --format=json > iam-policy.json

# Edit to add auditConfigs, then apply:
gcloud projects set-iam-policy $PROJECT_ID iam-policy.json

# Export logs
gcloud logging sinks create prod-logs-export \
  storage.googleapis.com/prod-logs-bucket \
  --log-filter='severity>=WARNING'
```

### Compliance

- [ ] **Data residency** requirements met
- [ ] **Compliance certifications** verified (SOC 2, ISO 27001, etc.)
- [ ] **Security Command Center** enabled
- [ ] **Vulnerability scanning** enabled
- [ ] **DLP** (Data Loss Prevention) configured for PII
- [ ] **Access transparency** enabled (if available)

```bash
# Enable Security Command Center
# https://console.cloud.google.com/security/command-center

# Enable vulnerability scanning for containers
gcloud container images scan IMAGE_URL
```

### Resource Organization

- [ ] **Project naming** follows conventions
- [ ] **Resource naming** follows conventions
- [ ] **Labels** applied consistently to all resources
- [ ] **Resource hierarchy** (Org > Folder > Project) utilized
- [ ] **Organizational policies** enforced
- [ ] **Resource quotas** appropriate

```bash
# Check labels on all resources
gcloud asset search-all-resources \
  --scope=projects/$PROJECT_ID \
  --query="NOT labels.env:*" \
  --format="table(name,assetType)"

# Standard label set
--labels=env=prod,owner=team-name,app=app-name,cost-center=cc123,compliance=pci
```

---

## Operations

### Deployment

- [ ] **CI/CD pipeline** fully automated
- [ ] **Blue-green deployments** or canary releases
- [ ] **Automated testing** in pipeline
- [ ] **Deployment windows** defined
- [ ] **Rollback procedures** automated and tested
- [ ] **Change management** process in place
- [ ] **Deployment notifications** to team

```bash
# Cloud Run gradual rollout
gcloud run services update-traffic SERVICE \
  --to-revisions=NEW_REVISION=10,OLD_REVISION=90

# Monitor for 30 minutes, then:
gcloud run services update-traffic SERVICE \
  --to-revisions=NEW_REVISION=100
```

### Documentation

- [ ] **Architecture diagrams** up to date
- [ ] **Runbooks** for common operations
- [ ] **Incident response procedures** documented
- [ ] **API documentation** current
- [ ] **Onboarding guide** for new team members
- [ ] **Dependency map** maintained
- [ ] **Contact list** for escalations

### Observability

- [ ] **Distributed tracing** enabled (Cloud Trace)
- [ ] **Error tracking** configured (Error Reporting)
- [ ] **Custom metrics** for business KPIs
- [ ] **Dashboard** for key metrics
- [ ] **SLI/SLO** defined and tracked

```bash
# Enable Cloud Trace
# Add OpenTelemetry SDK to your application

# Check Error Reporting
gcloud error-reporting events list --service=SERVICE_NAME
```

---

## Pre-Production Checklist

Before going live:

### Load Testing
```bash
# Example with Apache Bench
ab -n 10000 -c 100 https://SERVICE_URL/

# Or use Cloud Load Testing
# https://cloud.google.com/solutions/load-testing
```

### Security Scan
```bash
# Container vulnerability scan
gcloud container images scan gcr.io/$PROJECT_ID/IMAGE:TAG

# Check for misconfigurations
# Use Forseti or Cloud Security Scanner
```

### Failover Test
```bash
# Test multi-region failover
# Simulate region outage and verify traffic shifts
```

### Restore Test
```bash
# Test backup restore process
gcloud sql backups restore BACKUP_ID \
  --backup-instance=SOURCE_INSTANCE \
  --backup-instance-region=REGION \
  --target-instance=RESTORE_INSTANCE
```

---

## Post-Production Checklist

After going live:

### Week 1
- [ ] Monitor error rates and latency
- [ ] Review logs for anomalies
- [ ] Verify backups running
- [ ] Check cost against budget
- [ ] Confirm alerts are working

### Week 2
- [ ] Performance review meeting
- [ ] Update documentation based on incidents
- [ ] Fine-tune auto-scaling
- [ ] Review resource utilization

### Month 1
- [ ] Security audit
- [ ] Cost optimization review
- [ ] SLO/SLA compliance review
- [ ] Disaster recovery drill

### Quarterly
- [ ] IAM audit
- [ ] Dependency updates
- [ ] Architecture review
- [ ] Compliance audit
- [ ] Cost trend analysis

---

## Quick Production Deployment Script

```bash
#!/bin/bash
# Production deployment with safety checks

set -euo pipefail

# Verify production project
CURRENT_PROJECT=$(gcloud config get-value project)
if [[ "$CURRENT_PROJECT" != "my-prod-project" ]]; then
  echo "ERROR: Not in production project"
  exit 1
fi

# Require manual confirmation
echo "DEPLOYING TO PRODUCTION"
read -p "Type 'DEPLOY-TO-PROD' to confirm: " CONFIRM
[[ "$CONFIRM" != "DEPLOY-TO-PROD" ]] && exit 1

# Take snapshot before deploy
echo "Creating backup..."
gcloud sql backups create \
  --instance=prod-db \
  --description="Pre-deployment backup $(date -Iseconds)"

# Deploy with gradual rollout
echo "Deploying new version..."
gcloud run deploy prod-service \
  --image=gcr.io/$PROJECT_ID/app:$VERSION \
  --region=us-central1 \
  --no-traffic  # Deploy but don't route traffic yet

# Get revision name
NEW_REVISION=$(gcloud run services describe prod-service \
  --region=us-central1 \
  --format="value(status.latestReadyRevisionName)")

# Gradual rollout: 10% -> 50% -> 100%
echo "Rolling out 10%..."
gcloud run services update-traffic prod-service \
  --to-revisions=$NEW_REVISION=10 \
  --region=us-central1

sleep 300  # Monitor for 5 minutes

echo "Rolling out 50%..."
gcloud run services update-traffic prod-service \
  --to-revisions=$NEW_REVISION=50 \
  --region=us-central1

sleep 300

echo "Rolling out 100%..."
gcloud run services update-traffic prod-service \
  --to-revisions=$NEW_REVISION=100 \
  --region=us-central1

echo "✓ Deployment complete"
echo "Monitor: https://console.cloud.google.com/run/detail/us-central1/prod-service"
```

---

## Emergency Rollback Script

```bash
#!/bin/bash
# Emergency rollback

set -euo pipefail

echo "EMERGENCY ROLLBACK"
read -p "Type 'ROLLBACK' to confirm: " CONFIRM
[[ "$CONFIRM" != "ROLLBACK" ]] && exit 1

# Get previous stable revision
PREVIOUS_REVISION=$(gcloud run services describe prod-service \
  --region=us-central1 \
  --format="value(status.traffic[1].revisionName)")

# Immediate rollback
gcloud run services update-traffic prod-service \
  --to-revisions=$PREVIOUS_REVISION=100 \
  --region=us-central1

echo "✓ Rolled back to $PREVIOUS_REVISION"
```

---

## Resources

- [Cloud Architecture Framework](https://cloud.google.com/architecture/framework)
- [Production Checklist (Official)](https://cloud.google.com/architecture/framework/operational-excellence/production-readiness)
- [Security Best Practices](https://cloud.google.com/security/best-practices)
- [Cost Optimization](https://cloud.google.com/architecture/framework/cost-optimization)
