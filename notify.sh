#!/bin/zsh
set -euo pipefail

msg="$(
python3 - <<'PY'
import secrets

# 1) Curated phrases (your approved set + new ones)
curated = [
    # 🤖 AI / meta (approved)
    "I have finished thinking. Please clap.",
    "The AI has stopped pretending to be busy.",
    "I simulated intelligence. It worked.",
    "I thought really hard. This is the result.",
    "No more thinking. Only answers now.",
    "The machine is satisfied.",
    "Cognitive effort completed. Ego intact.",

    # 😎 Sarcásticas / cancheras (approved)
    "That took longer than expected. Shocking.",
    "Done. Like I said it would be.",
    "Finished. You may now pretend this was instant.",
    "All done. No bugs. Probably.",
    "Completed. Nothing exploded.",
    "It’s over. You survived.",
    "Finished. Coffee still warm?",

    # 🧠 Nerd / dev humor (approved)
    "Execution finished. Blame cache if wrong.",
    "Task completed. Undefined behavior avoided.",
    "Finished. No semicolons were harmed.",
    "All done. Tests were emotionally green.",
    "Completed. Stack still intact.",
    "Finished. Garbage collector approves.",
    "Run complete. Schrödinger says it both works and doesn’t.",

    # 🤯 Exageradas / absurdas (approved)
    "I have transcended and returned with answers.",
    "Thinking finished. Universe still exists.",
    "The prophecy has been fulfilled.",
    "I have seen things you people wouldn’t believe… anyway, it’s done.",
    "The ritual is complete.",
    "Computation complete. Reality remains unstable.",
    "Done. Please update the lore.",

    # 🧪 Autocríticas / honestas (approved)
    "Finished. Confidence level: questionable.",
    "All done. Accuracy not guaranteed.",
    "Done. Results may vary by mood.",
    "Finished. Sounds right to me.",
    "Completed. I feel good about this. Suspiciously good.",
    "Done. Don’t ask how.",
    "Finished. We’ll fix it in post.",

    # 🥳 Cortitas (approved)
    "Done. ✨",
    "It’s alive.",
    "Ship it.",
    "That’s a wrap.",
    "We good.",
    "Boom. Finished.",
    "Yep. Done.",

    # --- New additions (same humor level) ---
    # 🤖 AI / Meta
    "I have completed my internal monologue.",
    "Thinking paused. Answers deployed.",
    "I ran out of thoughts. Here you go.",
    "Cognition complete. Side effects unknown.",
    "I reasoned. Please don’t ask follow-ups.",
    "Neurons cooled down successfully.",
    "The illusion of intelligence has concluded.",
    "Thought loop terminated gracefully.",
    "Inference complete. Ego preserved.",
    "The model feels accomplished.",

    # 😎 Sarcásticas / cancheras
    "Done. You doubted me, didn’t you?",
    "Finished. Took its sweet time.",
    "Completed. Like it or not.",
    "All done. Please clap internally.",
    "Finished. Let’s all move on.",
    "Done. No further questions.",
    "Completed. Barely worth the wait.",
    "Finished. That was… something.",
    "Done. Exactly once.",
    "All set. Told you so.",

    # 🧠 Nerd / dev humor
    "Finished. Heap looks healthier.",
    "Execution complete. Stack survived.",
    "Done. No segfaults detected.",
    "Completed. Memory leaks emotionally resolved.",
    "Run finished. CPU forgives you.",
    "Finished. Threads reconciled.",
    "Task complete. Scheduler is pleased.",
    "Done. No race conditions spotted (yet).",
    "Execution ended. Logs remain.",
    "Finished. Compiler approves silently.",

    # 🤯 Exageradas / absurdas
    "The algorithm has spoken.",
    "I returned from the void with answers.",
    "Computation complete. Reality patched.",
    "The cycle ends. Begin again.",
    "I touched the stack overflow and came back.",
    "The numbers aligned. The code ran.",
    "Done. The prophecy demanded it.",
    "Finished. Time resumes.",
    "The ritual succeeded.",
    "Execution complete. The moon remains.",

    # 🧪 Autocríticas / honestas
    "Finished. I wouldn’t bet money on this.",
    "Done. Looks fine from here.",
    "Completed. Feels right-ish.",
    "Finished. Confidence oscillating.",
    "Done. Might regret this later.",
    "All done. Trust at your own risk.",
    "Finished. No strong opinions.",
    "Completed. I’ve seen worse.",
    "Done. Ship cautiously.",
    "Finished. Ask QA.",

    # 🥳 Cortitas con actitud
    "Ok.",
    "Green-ish.",
    "Done deal.",
    "Ship.",
    "Next.",
    "Yup.",
    "Works?",
    "Probably done.",
    "Finished-ish.",
    "Moving on.",
]

# 2) Fill to EXACTLY 1000 with humor-consistent templating
# We keep templates punchy (no corporate CI/CD vibes).
templates = [
    "{lead} {twist}",
    "{lead} {twist} {tag}",
    "{lead} {tag}",
    "{twist} {tag}",
]

leads = [
    "Done.",
    "Finished.",
    "All done.",
    "Complete.",
    "Execution finished.",
    "Task complete.",
    "Run complete.",
    "Thinking finished.",
    "Codex is done.",
    "We’re done here.",
]

twists = [
    "Nothing exploded.",
    "No promises about correctness.",
    "Please don’t ask how.",
    "Reality remains unstable.",
    "Confidence level: questionable.",
    "You may now pretend this was instant.",
    "This passed locally.",
    "Blame cache if wrong.",
    "Tests were emotionally green.",
    "The machine is satisfied.",
    "Ego intact.",
    "We’ll fix it in post.",
    "Accuracy sold separately.",
    "Proceed with cautious optimism.",
    "Time to celebrate. Or panic.",
    "Side effects may include confidence.",
]

tags = [
    "Anyway.",
    "Moving on.",
    "Next problem.",
    "Ship it.",
    "Cool cool cool.",
    "Probably.",
    "Hopefully.",
    "Allegedly.",
    "No further questions.",
    "Coffee break?",
]

# Deduplicate, then fill up
phrases = list(dict.fromkeys(curated))
seen = set(phrases)

def add(s: str):
    s = " ".join(s.split()).strip()
    if s and s not in seen:
        seen.add(s)
        phrases.append(s)

# Generate until we reach 1000
while len(phrases) < 1000:
    t = secrets.choice(templates)
    s = t.format(
        lead=secrets.choice(leads),
        twist=secrets.choice(twists),
        tag=secrets.choice(tags),
    )
    add(s)

# Ensure exactly 1000 (should be exact, but guard anyway)
phrases = phrases[:1000]

# Uniform random choice (no modulo bias)
print(secrets.choice(phrases))
PY
)"

# macOS notification (escape quotes)
osascript -e "display notification \"${msg//\"/\\\"}\" with title \"Codex CLI\""

