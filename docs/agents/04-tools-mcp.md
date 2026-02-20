# Tools (MCP servers)

This project is configured with MCP servers that extend agent capabilities.

## Context7 MCP (just-in-time docs)
Use when:
- confirming APIs/versions/edge-cases/canonical usage
- validating best practices against official docs
- resolving ambiguous framework/SDK behavior

## Playwright MCP (browser automation)
Use when:
- validating UI changes (routing/layout/CSS/components)
- reproducing/verifying frontend bugs
- smoke-testing critical flows
- capturing evidence (screenshots/logs)

## Google Cloud MCP (gcloud / observability / storage)

### gcloud MCP
Use when:
- listing/describing resources (Cloud Run, IAM, Pub/Sub, secrets, etc.)
- deploying/updating only when explicitly requested

Safety:
- prefer read-only (`list`, `describe`) before mutation
- if destructive or downtime-risky: ask first
- avoid interactive commands
- log non-trivial changes in the LOCAL `<repo_root>/AGENTS.md`

### Observability MCP (logs/metrics/traces)
Use when:
- confirming runtime behavior after deploy/config change
- investigating incidents (errors/latency/5xx/retries)
- producing evidence (scoped excerpts/snapshots)

Safety:
- scope queries (time range/service/severity)
- redact secrets/tokens before pasting into docs/chat

### Storage MCP (GCS)
Use when:
- inspecting/downloading/uploading artifacts for repro/verification

Safety:
- treat delete/move/overwrite as destructive: ask first
- prefer copy over move unless required
- never upload secrets without explicit instruction
- log meaningful storage mutations in local ledger

## Remotion Documentation MCP
Use when:
- building or modifying Remotion videos/compositions
- confirming API usage, component props, rendering/export workflow
- resolving version-specific behavior or breaking changes

Safety:
- prefer minimal examples and link back to the exact API name you used
- do not guess props/types; confirm via this MCP before implementing

## Remotion Documentation MCP (`remotion-documentation`)
What it is:
- Documentation MCP for Remotion. It indexes Remotion docs into a vector database and answers with domain-specific references (not a remote render/control API).

Use when:
- working in a Remotion project and you need exact API/props usage (do not guess)
- you need canonical examples for animations, sequencing, transitions, audio/video handling, captions
- you suspect version/package alignment or behavior differences and want to confirm via docs
