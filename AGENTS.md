# Cube 🧊 - Project Context

This directory contains **Cube**, a unified configuration and instruction system designed to synchronize and manage AI agent behavior (Gemini CLI, Claude Code, OpenCode) across different environments.

## 🎯 Project Overview

Cube centralizes fragmented instructions (Skills) and environment settings into a single repository. It ensures that whether you are using a CLI tool or a Web UI, the AI agent adheres to the same set of high-quality instructions, architecture-first principles, and development conventions.

- **Main Technologies:** Bash/Zsh scripting, Markdown-based AI Instructions (Skills).
- **Architecture:** Modular "Skills" (`skills/`) symlinked to specific agent directories, automated via an idempotent installation script (`scripts/install.sh`).

## 📂 Directory Overview

- **`skills/`**: The core of the system. Contains modular AI instructions.
  - Each skill (e.g., `cube-summary`, `cube-commit`) is a standalone directory with a `SKILL.md` file.
  - **Convention:** Skills must use the `cube-` prefix to avoid namespace collisions.
- **`scripts/`**: Automation and utility scripts.
  - `install.sh`: The main setup script. Handles shell alias registration, skill symlinking, and environment diagnosis (`--check`).
  - `claude-status-line.sh`: Custom status line integration for Claude Code.
- **`templates/`**: Templates for project-specific instructions (e.g., `AGENTS.md`) to be used in local repositories.
- **`cube.sh`**: Shell alias collection for various AI models and agents (Gemini, Claude, Ollama/OpenCode).
- **`.cube/`**: Runtime output directory created by skills in target projects. Managed by `.cube/.gitignore` internally (`plans/` tracked, `review.md` ignored).

## 🛠 Usage & Development

### Key Commands

- **Install/Update:** `bash ./scripts/install.sh [agents...]` (e.g., `bash ./scripts/install.sh claude gemini`)
- **Diagnose Environment:** `bash ./scripts/install.sh --check`
- **Apply Aliases:** `source ~/.bashrc` or `source ~/.zshrc` (after installation).

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

- **Architecture First:** Always prioritize architectural design before code implementation.
- **Atomic Commits:** Use `cube-commit` to ensure meaningful, atomic git commits.
- **Cross-Shell Compatibility:** All scripts must remain compatible with both Bash and Zsh.
- **Web UI Optimization:** Use the "Summary-Detail" hybrid layout (compact table + detailed list) for readability in narrow viewports.

---

**Updated At:** 2026. 4. 7.
