# AI Agent Aliases

# Gemini
alias geminip="gemini --model gemini-3.1-pro-preview"
alias geminif="gemini --model gemini-3-flash-preview"
alias geminil="gemini --model gemini-3.1-flash-light-preview"

# Claude
# Claude Code 실행 시 --dsp 인자를 --dangerously-skip-permissions로 변환해주는 래퍼 함수
claude_dsp() {
    local args=()
    for arg; do
        if [[ "$arg" == "--dsp" ]]; then
            args+=("--dangerously-skip-permissions")
        else
            args+=("$arg")
        fi
    done
    command claude "${args[@]}"
}

alias claudeo="claude_dsp --model opus"
alias claudes="claude_dsp --model sonnet"
alias claudeh="claude_dsp --model haiku"

# OpenCode with Ollama
alias ollamad="ollama launch opencode --model deepseek-v3.2:cloud"
alias ollamag="ollama launch opencode --model glm-5.1:cloud"
alias ollamam="ollama launch opencode --model minimax-m2.7:cloud"
alias ollamaq="ollama launch opencode --model qwen3.5:cloud"
alias ollamas="ollama launch opencode --model devstral-2:123b-cloud"
