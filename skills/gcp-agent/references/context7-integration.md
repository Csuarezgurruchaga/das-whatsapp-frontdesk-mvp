# Context7 MCP Integration Guide

How to use context7 with the GCP CLI skill for up-to-date documentation.

---

## What is Context7?

Context7 is an MCP (Model Context Protocol) server that provides real-time access to official GCP documentation. Use it to verify current syntax, check for new features, and validate commands before execution.

---

## Integration Strategy: Hybrid Approach

### 🟢 Proactive (Check BEFORE generating commands)

Use context7 proactively when:

1. **Beta/Alpha Features**
   - Any command with `gcloud alpha` or `gcloud beta`
   - Services in preview or recently GA'd
   - Example: "Search context7 for gcloud alpha run deploy latest flags"

2. **User Mentions Currency**
   - Keywords: "latest", "current", "new", "2024", "updated"
   - Example: "What's the latest way to deploy Cloud Run?"
   
3. **Recently Changed Commands**
   - `gcloud storage` (replaced many `gsutil` operations)
   - Cloud Run autoscaling (syntax changed in 2023)
   - Secret Manager integration methods
   
4. **Complex IAM Scenarios**
   - New predefined roles
   - Workload Identity configurations
   - Cross-project service account bindings

5. **New Service Features**
   - Features announced in last 6 months
   - New flags or parameters
   - Example: Cloud Run VPC egress options

**How to request proactive check:**
```
"Deploy Cloud Run with latest syntax (verify with context7)"
"Check context7: what's current way to connect Cloud Run to Cloud SQL?"
"Use context7 to confirm gcloud storage bucket creation syntax"
```

---

### 🔴 Reactive (Check AFTER error occurs)

Use context7 reactively when:

1. **Syntax Errors**
   ```
   ERROR: (gcloud.run.deploy) unrecognized arguments: --new-flag
   ```
   → Search: "gcloud run deploy current flags and syntax"

2. **Deprecated Warnings**
   ```
   WARNING: The --allow-unauthenticated flag is deprecated
   ```
   → Search: "gcloud run deploy authentication flags current syntax"

3. **Unknown Command**
   ```
   ERROR: (gcloud) Invalid choice: 'new-command'
   ```
   → Search: "gcloud new-command replacement syntax"

4. **Unexpected API Behavior**
   - Command succeeds but doesn't work as expected
   - Different behavior than documented in references/
   → Search: "gcloud [service] [command] current behavior"

5. **Permission Errors with Standard Roles**
   ```
   ERROR: Permission denied on resource (or it may not exist)
   ```
   If you've already granted what references/ suggest:
   → Search: "Cloud Run IAM roles requirements latest"

**How to request reactive check:**
```
"This command failed: [paste command and error] - check context7 for fix"
"Got deprecated warning - verify current syntax with context7"
"Permission denied even with standard role - check latest requirements"
```

---

### ⚪ Skip Context7

**Don't check when:**

1. **Stable GA Commands**
   - `gcloud config set/get`
   - `gcloud projects list`
   - Basic `gcloud compute instances create` (standard flags)
   
2. **Covered in References**
   - Command is in `references/common-commands.md` with recent date
   - Pattern is in `references/iam-patterns.md`
   - Already verified in last 30 days

3. **Simple Operations**
   - List, describe, delete (basic syntax)
   - Setting config values
   - Reading logs

4. **Speed Critical**
   - User needs quick answer
   - Command is straightforward and from references/
   - Testing/debugging flow where delay matters

---

## Query Patterns for Context7

### Syntax Verification

```
"gcloud run deploy current syntax 2024"
"gcloud storage buckets create latest flags"
"gcloud secrets create command reference"
```

### Feature Discovery

```
"Cloud Run autoscaling options latest"
"gcloud run deploy new features 2024"
"Secret Manager Cloud Run integration methods"
```

### IAM & Permissions

```
"Cloud Run service account permissions requirements"
"IAM roles for Cloud SQL Cloud Run connection"
"Workload Identity GKE configuration latest"
```

### Migration & Replacements

```
"gsutil to gcloud storage migration guide"
"gcloud run services update deprecated flags replacement"
"Cloud Run VPC connector alternatives"
```

### Troubleshooting

```
"Cloud Run [error message] solution"
"gcloud auth login issues troubleshooting"
"Cloud SQL connection refused from Cloud Run"
```

---

## Integration Workflow

### Example 1: Proactive Check (New Feature Request)

**User asks:**
> "Deploy Cloud Run with the latest VPC egress settings"

**Claude's workflow:**
1. Recognize keywords: "latest", "VPC egress" (feature that evolved)
2. Check context7: "Cloud Run VPC egress configuration latest 2024"
3. Get current syntax from docs
4. Generate commands with verified flags
5. Provide implementation

### Example 2: Reactive Check (Command Failed)

**User reports:**
> "This failed: `gcloud run deploy --vpc-egress=all`"
> "Error: unknown flag --vpc-egress"

**Claude's workflow:**
1. Recognize error: unknown flag
2. Check context7: "gcloud run deploy VPC egress flag current syntax"
3. Find correct flag: `--vpc-egress-setting=all-traffic`
4. Provide corrected command
5. Explain what changed

### Example 3: Skip Check (Standard Operation)

**User asks:**
> "List all my Cloud Run services"

**Claude's workflow:**
1. Recognize: simple, stable GA command
2. Command in references/common-commands.md
3. No context7 check needed
4. Provide: `gcloud run services list`

---

## Best Practices

### 1. Be Specific in Searches

❌ Bad: "Cloud Run help"  
✅ Good: "gcloud run deploy authentication flags syntax 2024"

❌ Bad: "IAM errors"  
✅ Good: "Cloud Run service account Cloud SQL permission requirements"

### 2. Include Version/Date When Relevant

✅ "gcloud storage commands latest syntax"  
✅ "Cloud Run features announced 2024"  
✅ "Secret Manager integration Cloud Run current method"

### 3. Combine with References

```
1. Check references/common-commands.md first
2. If command looks outdated or fails → context7
3. Update mental model for next time
```

### 4. Document Findings

When context7 reveals changes:
```
"Note: Syntax changed - updating from old pattern to new"
"Deprecated: --old-flag → Replacement: --new-flag"
```

### 5. Batch Related Checks

If deploying complex service:
```
"Check context7 for:
1. Cloud Run deployment flags
2. Secret Manager integration
3. Cloud SQL connection syntax"
```

---

## Common Scenarios

### Scenario: Beta Command Going GA

**Before:**
```bash
gcloud alpha run deploy --feature-flag
```

**Detection:** User mentions feature by name, might be GA now

**Action:** Check context7 → "Cloud Run [feature] GA status 2024"

**After:**
```bash
gcloud run deploy --feature-flag  # Now in GA
```

### Scenario: Deprecated Flag

**Error:**
```
WARNING: Flag --allow-unauthenticated is deprecated
Use --no-allow-unauthenticated instead
```

**Action:** Check context7 → "gcloud run deploy authentication latest syntax"

**Update:**
```bash
# Old
gcloud run deploy --allow-unauthenticated

# Current
gcloud run deploy --no-allow-unauthenticated  # Private
# OR
gcloud run deploy  # Then set IAM policy separately
```

### Scenario: New Service Feature

**User:** "Can Cloud Run connect to VPC now without a connector?"

**Action:** Check context7 → "Cloud Run VPC Direct latest 2024"

**Result:**
```bash
# Direct VPC access (if GA)
gcloud run deploy \
  --network=NETWORK \
  --subnet=SUBNET
  
# vs old connector method
gcloud run deploy \
  --vpc-connector=CONNECTOR
```

---

## Updating the Skill

When context7 reveals significant changes:

1. **Update references/common-commands.md**
   - Add new syntax
   - Mark old syntax as deprecated

2. **Update references/troubleshooting.md**
   - Add new error patterns
   - Update solutions

3. **Update templates/**
   - Modernize script examples
   - Add new flags/options

4. **Document in README.md**
   - Note major changes
   - Update examples

---

## Quick Reference

| Situation | Action | Example Query |
|-----------|--------|---------------|
| Beta command | Proactive | "gcloud alpha run deploy latest flags" |
| User says "latest" | Proactive | "Cloud Run deployment current syntax 2024" |
| Syntax error | Reactive | "gcloud run deploy error [message]" |
| Deprecated warning | Reactive | "gcloud run [flag] replacement" |
| New feature question | Proactive | "Cloud Run [feature] GA status" |
| Simple list/describe | Skip | - |
| Command in references/ | Skip (unless fails) | - |

---

## Example Conversation Flows

### Flow 1: Proactive Success

```
User: "Deploy Cloud Run with latest secret manager integration"

Claude:
[Checks context7: "Cloud Run Secret Manager integration 2024"]
[Finds current best practice: --set-secrets flag]

Here's the current recommended approach...

gcloud run deploy SERVICE \
  --set-secrets="DB_PASSWORD=db-password:latest"
```

### Flow 2: Reactive Recovery

```
User: "This failed: gcloud run deploy --memory=512MB"
      "Error: invalid value for --memory"

Claude:
[Checks context7: "gcloud run deploy memory flag syntax"]
[Finds correct format: no space in unit]

The syntax changed - memory units should be written without space:

gcloud run deploy SERVICE \
  --memory=512Mi
```

### Flow 3: Skip Unnecessary

```
User: "List my Cloud Run services"

Claude:
[Recognizes: simple, stable command]
[No context7 needed]

gcloud run services list --project=$PROJECT_ID
```

---

**Remember:** Context7 is a tool, not a requirement. Use it strategically to ensure accurate, current commands while maintaining response speed.
