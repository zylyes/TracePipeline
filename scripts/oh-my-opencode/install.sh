#!/usr/bin/env bash
# Minimal installer wrapper for oh-my-opencode
set -euo pipefail

echo "Oh-My-Opencode: Interactive installer wrapper"

if ! command -v bunx >/dev/null 2>&1; then
  echo "Error: bunx (Bun) is not installed or not in PATH."
  echo "Please install Bun from https://bun.sh and ensure 'bunx' is available in PATH."
  exit 1
fi

echo "Note: This installer collects your subscription preferences and runs the official installer."
echo "It will download and install oh-my-opencode using bunx with the flags you provide."

declare -A FLAGS

prompt_yes_no() {
  local varname=$1
  local prompt=$2
  local default=${3:-y}
  while true; do
    read -rp "$prompt [$default]: " ans
    if [ -z "$ans" ]; then ans="$default"; fi
    case "${ans,,}" in
      y|yes) FLAGS[$varname]="yes"; return 0 ;;
      n|no)  FLAGS[$varname]="no"; return 0 ;;
      *) echo "Please answer yes or no."; ;;
    esac
  done
}

prompt_choice() {
  local varname=$1
  local prompt=$2
  local default=$3
  shift 3
  local choices=($@)
  echo "$prompt"
  local i=1
  for c in "${choices[@]}"; do
    echo "  $i) $c"
    ((i++))
  done
  while true; do
    read -rp "Enter choice (1-${#choices[@]}): " ch
    if [[ -z "$ch" ]]; then ch="$default"; fi
    if [[ "$ch" =~ ^[0-9]+$ ]] && [ "$ch" -ge 1 ] && [ "$ch" -le "${#choices[@]}" ]; then
      FLAGS[$varname]="${choices[$((ch-1))],,}"
      return 0
    else
      echo "Invalid choice."
    fi
  done
}

echo
echo "Step 0: Collect subscription preferences"
prompt_yes_no "claude" "Do you have a Claude Pro/Max subscription? (yes/no)" "no"
CLAUDE_FLAG="--claude=no"
CLAUDE_MAX20_FLAG="--claude=max20"
if [ "${FLAGS[claude]}" = "yes" ]; then
  prompt_choice "claude_variant" "Claude mode:" 1 standard max20
  if [ "${FLAGS[claude_variant]}" = "standard" ]; then
    CLAUDE_FLAG="--claude=yes"
  else
    CLAUDE_FLAG="--claude=max20"
  fi
fi

prompt_yes_no "openai" "Do you have an OpenAI ChatGPT Plus subscription? (yes/no)" "no"
OPENAI_FLAG="--openai=no"
if [ "${FLAGS[openai]}" = "yes" ]; then OPENAI_FLAG="--openai=yes"; fi

prompt_yes_no "gemini" "Would you like to enable Gemini integration? (yes/no)" "no"
GEMINI_FLAG="--gemini=no"; if [ "${FLAGS[gemini]}" = "yes" ]; then GEMINI_FLAG="--gemini=yes"; fi

prompt_yes_no "copilot" "Do you have a GitHub Copilot subscription? (yes/no)" "no"
COPILOT_FLAG="--copilot=no"; if [ "${FLAGS[copilot]}" = "yes" ]; then COPILOT_FLAG="--copilot=yes"; fi

prompt_yes_no "opencode_zen" "Do you have access to OpenCode Zen models? (yes/no)" "no"
OPENCODE_ZEN_FLAG="--opencode-zen=no"; if [ "${FLAGS[opencode_zen]}" = "yes" ]; then OPENCODE_ZEN_FLAG="--opencode-zen=yes"; fi

prompt_yes_no "zai_coding_plan" "Do you have a Z.ai Coding Plan subscription? (yes/no)" "no"
ZAI_CODING_PLAN_FLAG="--zai-coding-plan=no"; if [ "${FLAGS[zai_coding_plan]}" = "yes" ]; then ZAI_CODING_PLAN_FLAG="--zai-coding-plan=yes"; fi

prompt_yes_no "opencode_go" "Do you have OpenCode Go subscription? (yes/no)" "no"
OPENCODE_GO_FLAG="--opencode-go=no"; if [ "${FLAGS[opencode_go]}" = "yes" ]; then OPENCODE_GO_FLAG="--opencode-go=yes"; fi

prompt_yes_no "kimi_for_coding" "Do you have Kimi for Coding subscription? (yes/no)" "no"
KIMI_FOR_CODING_FLAG="--kimi-for-coding=no"; if [ "${FLAGS[kimi_for_coding]}" = "yes" ]; then KIMI_FOR_CODING_FLAG="--kimi-for-coding=yes"; fi

prompt_yes_no "vercel_ai_gateway" "Do you use Vercel AI Gateway? (yes/no)" "no"
VERCEL_AI_GATEWAY_FLAG="--vercel-ai-gateway=no"; if [ "${FLAGS[vercel_ai_gateway]}" = "yes" ]; then VERCEL_AI_GATEWAY_FLAG="--vercel-ai-gateway=yes"; fi

echo
echo "Step 1: Install Oh-My-Opencode (non-interactive flags)"
echo "Command: bunx oh-my-opencode install --no-tui \
  $CLAUDE_FLAG $OPENAI_FLAG $GEMINI_FLAG $COPILOT_FLAG $OPENCODE_ZEN_FLAG $ZAI_CODING_PLAN_FLAG $OPENCODE_GO_FLAG $KIMI_FOR_CODING_FLAG $VERCEL_AI_GATEWAY_FLAG"

INSTALL_CMD="bunx oh-my-opencode install --no-tui $CLAUDE_FLAG $OPENAI_FLAG $GEMINI_FLAG $COPILOT_FLAG $OPENCODE_ZEN_FLAG $ZAI_CODING_PLAN_FLAG $OPENCODE_GO_FLAG $KIMI_FOR_CODING_FLAG $VERCEL_AI_GATEWAY_FLAG"
eval "$INSTALL_CMD"

echo
echo "Step 2: Run doctor to verify installation"
if command -v opencode >/dev/null 2>&1; then
  echo "Verifying..."
  bunx oh-my-opencode doctor || true
else
  echo "Note: The 'opencode' binary does not appear to be in PATH post-install."
fi

echo "Done."
