# Cube 🧊 - Project Context

This directory contains **Cube**, a unified configuration and instruction system designed to synchronize and manage AI agent behavior (Gemini CLI, Claude Code, OpenCode, Pi) across different environments.

## 🎯 Project Overview

Cube centralizes fragmented instructions (Skills) and environment settings into a single repository. It ensures that whether you are using a CLI tool or a Web UI, the AI agent adheres to the same set of high-quality instructions, architecture-first principles, and development conventions.

## 🚀 Onboarding Mission for AI Agents

If you are an AI agent accessing this repository for the first time, perform the following steps immediately to synchronize your context:

1. **Diagnose Environment:** Run `bash ./scripts/install.sh --check` to verify the current setup and identify missing dependencies or broken links.
2. **Explore Skills:** Scan the `skills/` directory to understand the available `cube-` commands and their specific instructions in `SKILL.md`.
3. **Check Active Plans:** Review `.cube/plans/index.md` to see if there are any ongoing tasks or handovers you should be aware of.
4. **Acknowledge Strategy:** Inform the user of your current diagnostic status and propose the next logical step based on your findings.

## 🎨 Style & Linting

To maintain documentation quality and consistency, this project uses **`markdownlint-cli2`** (maintained by David Anson).

- **Verification:** Always run `npx markdownlint-cli2 "**/*.md" "#node_modules" "#.git"` before finalizing any documentation changes.
- **Rules:** Follow the rules defined in `.markdownlint.json`.
- **VS Code:** It is highly recommended to use the [markdownlint extension](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) for real-time feedback.

## 📂 Directory Overview

- **Main Technologies:** Bash/Zsh scripting, Markdown-based AI Instructions (Skills).
- **Architecture:** Modular "Skills" (`skills/`) symlinked to `~/.claude/skills/` for Claude Code and shared `~/.agents/skills/` for Gemini CLI, OpenCode, and Pi, automated via `scripts/install.sh` with repeatable skill links and explicit latest-package reconciliation for Pi. Pi discovers the shared path directly; do not create `~/.pi/.agents/skills/` or duplicate skills.

- **`skills/`**: The core of the system. Contains modular AI instructions.
  - Each skill (e.g., `cube-summary`, `cube-commit`) is a standalone directory with a `SKILL.md` file.
  - **Convention:** Skills must use the `cube-` prefix to avoid namespace collisions.
- **`scripts/`**: Automation and utility scripts.
  - `install.sh`: The main setup script. Handles shell alias registration, skill symlinking, Pi package setup, and environment diagnosis (`--check`).
  - `pi_packages.py`: Standard-library Python 3 helper for Pi package preflight, scoped CLI operations, and read-only local diagnosis.
- **`agents/`**: Agent-specific configurations and resources, organized by agent name.
  - `claude/`: Claude Code specific resources (e.g., `claude-status-line.sh`).
  - `opencode/`: OpenCode specific resources (e.g., `plugins/cmux-notify.js`).
  - `pi/packages.txt`: Cube-managed, unversioned npm package sources (`pi-web-access`, `pi-subagents`).
- **`templates/`**: Templates for project-specific instructions (e.g., `AGENTS.md`) to be used in local repositories.
- **`cube.sh`**: Shell alias collection for various AI models and agents (Gemini, Claude, Ollama/OpenCode).
- **`.cube/`**: Runtime output directory created by skills in target projects. Managed by `.cube/.gitignore` internally (`plans/` tracked, `review.md` ignored).

## 🛠 Usage & Development

### Key Commands

> **CRITICAL:** Always run the diagnostic check **before** performing a new installation or update.

1. **Diagnose Environment (Mandatory):** `bash ./scripts/install.sh --check`
2. **Install/Update:** `bash ./scripts/install.sh [agents...]` (e.g., `bash ./scripts/install.sh claude gemini` or `bash ./scripts/install.sh pi`). Without agent arguments, defaults to Claude, Gemini, OpenCode, and Pi. Pi-only installation registers the shared shell aliases and skills and installs/updates only Cube-managed Pi packages, without installing other agents' resources. Pi CLI and Python 3 are prerequisites; Cube does not install/update Pi itself. Package commands run outside the project to avoid project-scoped updates. Preserve personal settings and resource filters; skip/report version constraints and duplicate package declarations rather than overwriting them. Legacy Gemini/OpenCode skill links are cleaned up only when the respective agent is selected. The `--check` command always diagnoses the full environment, including unselected agents.
   - **Pi diagnosis boundary:** `--check` checks CLI presence, personal package declarations, and managed local package metadata under `<agent-dir>/npm/node_modules/` without network or extension loading. Legacy global npm installs outside that path require managed reinstallation. Do not claim runtime compatibility or latest-version verification. Honor `PI_CODING_AGENT_DIR`; installation fails when `PI_OFFLINE=1` or `true`.
   - **Session safety:** Do not restart/reload active Pi/Paseo sessions or run real package updates merely to test installer changes. Use the isolated HOME and fake Pi CLI regression tests.
3. **Apply Aliases:** `source ~/.bashrc` or `source ~/.zshrc` (after installation).

### Creating a New Skill

1. Create a directory `skills/cube-<name>`.
2. Create a `SKILL.md` with the required YAML frontmatter:

   ```yaml
   ---
   name: cube-name
   description: "Brief description"
   compatibility: opencode, claude, gemini
   ---
   ```

3. Follow the **Topic-based Indexing** convention (`- **Topic:** Instruction`) for better AI indexing.

## 📜 Development Conventions

- **Diagnose First:** Always perform an environment diagnosis (`--check`) before any installation or major configuration change.
- **Architecture First:** Always prioritize architectural design before code implementation.
- **Atomic Commits:** Use `cube-commit` to ensure meaningful, atomic git commits.
- **Cross-Shell Compatibility:** All scripts must remain compatible with both Bash and Zsh.
- **Web UI Optimization:** Use the "Summary-Detail" hybrid layout (compact table + detailed list) for readability in narrow viewports.

---

**Updated At:** 2026. 4. 11.
