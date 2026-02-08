#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------
# Spec Interview TUI (gum) for Codex skills
# - Shows a Codex-like selector (gum choose)
# - Outputs EXACT "Qn=X" pairs for paste into Codex
# - Supports meta-options G/H/I/J (Explain/Compare/Recommend/Examples)
# - Persists progress so you can resume
# -----------------------------------------

# Requirements: gum
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1"; exit 1; }; }
need gum

STATE_FILE="${HOME}/.codex/dev-tools/spec-interview-ui-wrapper/scripts/.interview_state.sh"

usage() {
  cat <<'USAGE'
Usage:
  interview_ui.sh            # run / resume interview
  interview_ui.sh --reset    # reset saved progress
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--reset" ]]; then
  rm -f "$STATE_FILE"
  echo "Reset OK."
  exit 0
fi

# -------- Clipboard best-effort --------
copy_to_clipboard() {
  local text="$1"
  if command -v pbcopy >/dev/null 2>&1; then
    printf "%s" "$text" | pbcopy
  elif command -v xclip >/dev/null 2>&1; then
    printf "%s" "$text" | xclip -selection clipboard
  fi
}

# -------- State (resume) --------
# Stored as a bash script with:
#   IDX=0
#   declare -a ANSWERS=( "Q1=A" "Q2=E: foo" )
IDX=0
declare -a ANSWERS=()

load_state() {
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE" || true
  fi
}

save_state() {
  mkdir -p "$(dirname "$STATE_FILE")"
  {
    echo "IDX=${IDX}"
    echo -n "declare -a ANSWERS=("
    local a
    for a in "${ANSWERS[@]}"; do
      printf " %q" "$a"
    done
    echo " )"
  } > "$STATE_FILE"
}

clear_state() {
  rm -f "$STATE_FILE"
}

# -------- Helpers --------
join_answers() {
  local IFS=", "
  echo "${ANSWERS[*]}"
}

# Replace/insert answer for a question index (0-based)
set_answer_at() {
  local idx="$1"
  local value="$2"
  # Ensure array length
  if (( idx < ${#ANSWERS[@]} )); then
    ANSWERS[idx]="$value"
  else
    # Fill any gaps (shouldn't happen normally)
    while (( ${#ANSWERS[@]} < idx )); do
      ANSWERS+=( "" )
    done
    ANSWERS+=( "$value" )
  fi
}

# -------- Question definitions --------
# Define your interview questions here.
# IMPORTANT: The "letter" is the first char before ")"
# Example option strings must look like: "A) something", "G) Explain options (A–D)", etc.
get_title() {
  local i="$1"
  case "$i" in
    0) echo "Spec slug (nombre de la spec)" ;;
    # 1) echo "..." ;;
    # 2) echo "..." ;;
    *) echo "" ;;
  esac
}

get_options() {
  local i="$1"
  case "$i" in
    0)
      cat <<'OPTS'
A) argenfuego-static-contact
B) argenfuego-contact-static-response
C) argenfuego-contact-no-llm
D) argenfuego-estabilidad-contacto
E) Other: <slug>
F) Not sure / later
G) Explain options (A–D)
H) Compare options
I) Recommend
J) Show examples
OPTS
      ;;
    # 1)
    #   cat <<'OPTS'
    #   A) ...
    #   ...
    # OPTS
    #   ;;
    *)
      ;;
  esac
}

num_questions() {
  # Update this when you add more questions
  echo 1
}

# -------- Core: ask one question --------
ask_question() {
  local qidx="$1"
  local qn=$((qidx + 1))
  local qid="Q${qn}"
  local title
  title="$(get_title "$qidx")"

  if [[ -z "$title" ]]; then
    echo "No title for question index $qidx. Did you forget to define it?"
    exit 1
  fi

  local opts
  opts="$(get_options "$qidx")"
  if [[ -z "$opts" ]]; then
    echo "No options for $qid. Did you forget to define them?"
    exit 1
  fi

  local picked
  picked="$(printf "%s\n" "$opts" | gum choose --header "${qid} — ${title}")"

  local letter="${picked:0:1}"

  case "$letter" in
    A|B|C|D|F)
      echo "${qid}=${letter}"
      return 0
      ;;
    E)
      local free
      free="$(gum input --prompt "${qid} Other: " --placeholder "texto...")"
      echo "${qid}=E: ${free}"
      return 0
      ;;
    G|I|J)
      # Meta request: output just the meta pair so Codex can respond (skill will re-ask)
      echo "${qid}=${letter}"
      return 2
      ;;
    H)
      local cmp
      cmp="$(gum input --prompt "${qid} Compare (ej: A vs C): " --placeholder "A vs C")"
      echo "${qid}=H: ${cmp}"
      return 2
      ;;
    *)
      echo "Invalid selection: $picked"
      exit 1
      ;;
  esac
}

# -------- Run / Resume --------
load_state

TOTAL="$(num_questions)"

# If already completed, reset automatically (safety)
if (( IDX >= TOTAL )); then
  clear_state
  IDX=0
  ANSWERS=()
fi

# Loop from current IDX forward until:
# - user requests meta help (G/H/I/J) => print line for Codex and stop WITHOUT advancing IDX
# - finish all questions => print full line, copy, clear state
while (( IDX < TOTAL )); do
  pair="$(ask_question "$IDX")"
  rc=$?

  if [[ $rc -eq 2 ]]; then
    # Meta request: do NOT advance IDX and do NOT overwrite the final answer slot.
    # But you *can* include already-finalized previous answers in the output line, plus this meta pair.
    local_out=""
    if (( ${#ANSWERS[@]} > 0 )); then
      # print previous finalized answers + current meta request
      local_out="$(join_answers)"
      if [[ -n "$local_out" ]]; then
        local_out="${local_out}, ${pair}"
      else
        local_out="${pair}"
      fi
    else
      local_out="${pair}"
    fi

    echo "$local_out"
    copy_to_clipboard "$local_out"
    # Keep state as-is (IDX unchanged) so next run re-asks same Q after Codex responds.
    save_state
    exit 0
  fi

  # Normal answer (A–F / E text): save it at this index and advance
  set_answer_at "$IDX" "$pair"
  IDX=$((IDX + 1))
  save_state
done

# Completed all questions
out="$(join_answers)"
echo "$out"
copy_to_clipboard "$out"
clear_state
