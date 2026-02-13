---
name: remotion-video-producer
description: "Create and iterate Remotion videos (ads/promos/explainers) end-to-end: brief → storyboard → Remotion code → preview → render. Uses Remotion Documentation MCP to avoid guessing APIs."
metadata:
  tags: remotion, video, react, animation, motion-graphics, ads, codex
  triggers:
    - "video publicitario"
    - "video promo"
    - "video para redes"
    - "remotion"
    - "motion graphics"
    - "render mp4"
---

# Remotion Video Producer (Skill)

## Scope
Use this skill when the user wants to create or modify a video using Remotion (React → video render).

This skill assumes the MCP server `remotion-documentation` is installed and available.

## Non-negotiables
- Do not guess Remotion APIs/props. If uncertain, invoke `remotion-documentation`.
- Keep changes minimal and reviewable.
- Prefer deterministic timing: frame-based reasoning (fps, durationInFrames).
- Prefer preview-first: get something working in Remotion Studio before polishing.
- Do not silently assume creative direction. If key inputs are missing, ask; if the user wants you to pick, present 2–3 options and confirm a choice.

## Inputs (ask upfront)
- Repo/project context: where the Remotion project lives (or confirm we should create one).
- Target deliverable: `mp4` / `mov` / `gif` (and any platform constraints).
- Format + duration: `9:16` / `1:1` / `16:9`, seconds (or frames), `fps` if specified.
- Content: script/copy, CTA, on-screen text, language.
- Brand: colors, font(s), logo(s), tone, do/don't examples.
- Assets: images/video, voiceover/music, data sources (or explicitly "none").

If the user says "you decide", offer 2–3 concrete options and wait for a selection before implementing.

## Outputs (what you deliver)
- A storyboard (shot list with timestamps or frame ranges) + on-screen text per scene.
- Remotion implementation aligned to the storyboard (scene components + timing constants).
- Verified run instructions (preview + render commands that match the project).

## Workflow (progressive)
### 1) Project discovery (do first)
- Confirm whether this is an existing Remotion project or a new one.
- If existing: locate how compositions are registered and how Studio/render is invoked (scripts, `npx`, etc.).
- If new: use Remotion's official project creation workflow; confirm the exact command/flags with `remotion-documentation` if unsure.

### 2) Script + storyboard (high signal)
Produce:
- Script (short)
- Shot list with timestamps (or frame ranges)
- On-screen text per scene
- Motion notes (entry/exit, transitions)

### 3) Implementation plan (Remotion)
Before coding:
- Identify the specific Remotion primitives/features required (Composition/Sequence/AbsoluteFill, audio, fonts, etc.).
- If any API/prop/flag is not 100% certain: consult `remotion-documentation` before writing code.

### 4) Code (Remotion project changes)
Implementation guidelines:
- Keep each scene as a component.
- Use a single source of truth for timing (constants).
- Use `useVideoConfig()` when fps/duration/size are needed.
- For animations: prefer `interpolate()` and `spring()` patterns; choose clamp defaults unless the docs say otherwise.

If dealing with:
- subtitles/captions → consult `remotion-documentation` for the recommended approach before implementing
- audio trimming/duration → consult `remotion-documentation`; use FFmpeg only if required
- charts/data-viz → keep data → visuals deterministic; consult `remotion-documentation` for patterns/libs

(If these topics appear and you're unsure, consult `remotion-documentation`.)

### 5) Preview loop
- Provide the exact command to run Remotion Studio for this project (do not hand-wave "project convention").
- Iterate in small steps: one scene (or one effect) per iteration.

### 6) Render
- Provide render command(s) and output path conventions.
- If codec/format is requested, confirm via docs (or MCP) rather than guessing.
- If the render is slow or fails, capture the minimal error output and iterate from a reproducible command.

## When to invoke Remotion Documentation MCP (hard trigger)
Invoke `remotion-documentation` when:
- you are about to use a Remotion API/prop you are not 100% sure about
- you need canonical examples for a feature (transitions, transparency, audio, captions, render flags)
- you suspect version/package alignment issues
- you need to confirm recommended defaults (e.g., interpolate extrapolation)

## Fast routing (cheat sheet)
- "promo/ad video" → brief → storyboard → implement scenes → preview → render
- "bug in Remotion code" → repro → consult MCP for exact API expectations → fix → proof
- "how do I do X in Remotion?" → consult MCP first → answer with minimal example

## Example prompts (copy/paste)
Use this skill:
```text
Quiero un video 9:16 de 15s para Instagram Stories. Tengo logo (PNG), paleta (#0B1B3A / #F5C542), y este copy: "...".
Necesito 3 escenas con CTA final "Pedilo hoy". Entregable MP4 h264.
```

```text
Tengo un dataset (JSON/CSV) de 200 productos y quiero generar 200 videos, 1 por producto, todos con el mismo template.
Cada video: 6s, 1080x1920, 30fps. El nombre + precio aparecen animados y al final un CTA.
```

```text
Tengo un proyecto Remotion existente. `npx remotion studio` abre, pero el timing de una Sequence está corrido 10 frames.
Te paso el componente y el comportamiento esperado: corregilo sin cambiar el look.
```

Do not use this skill:
```text
Necesito cortar y reordenar clips de un video existente, con color grading y keyframes a mano, estilo editor con timeline.
No quiero tocar código.
```

```text
Quiero construir un editor de video web completo para usuarios finales (timeline, UI de edición, presets) desde cero.
Necesito definir producto/alcance antes de tocar código.
```
