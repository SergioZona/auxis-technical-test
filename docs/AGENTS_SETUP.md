# Antigravity Agent Configuration & Tooling

This project uses Google's Antigravity AI assistant with advanced Context, Memory, and Code Analysis capabilities. To keep the AI agent highly effective, we use a strict `.agents/` folder structure containing `rules/` (global configurations) and `skills/` (specific task workflows).

## The Four Pillars (Installed Tools)

Our AI development pipeline relies on four major AI toolsets installed in this environment:

### 1. Caveman Mode (`caveman-*`)
**Purpose**: Extreme token efficiency.  
**Repository**: [juliusbrussee/caveman](https://github.com/juliusbrussee/caveman)  
**What it does**: Forces the LLM to output highly compressed, terse language (omitting articles and pleasantries) while maintaining 100% technical accuracy. This saves up to 75% of context window tokens and speeds up response times.  
**Skills included**: `caveman`, `caveman-commit`, `caveman-review`, `compress`, `caveman-help`.

### 2. Code Review Graph (`crg-*`)
**Purpose**: Context-aware code intelligence via MCP.  
**Repository**: [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)  
**What it does**: A local Tree-sitter-based Incremental Knowledge Graph that maps your entire codebase's structural dependencies. Instead of raw file reading, the AI queries the graph to understand caller paths, blast radius, and missing test coverage.  
**Skills included**: `crg-build-graph`, `crg-review-pr`, `crg-debug-issue`, `crg-explore-codebase`, `crg-refactor-safely`, `crg-review-changes`, `crg-review-delta`.

### 3. Context Mode (`ctx-*`)
**Purpose**: Sandbox processing and I/O parallelization via MCP.  
**Repository**: [mksglu/context-mode](https://github.com/mksglu/context-mode)  
**What it does**: Replaces standard terminal execution with a secure sandbox that forces the AI to "Think in Code." Instead of reading massive JSON/HTML files or logs into the context window to reason about them, the AI writes Node.js/Shell scripts to process the data and only prints the final answer. It also parallelizes network calls (HTTP fetching, GitHub API).

### 4. RTK (Real-Time Knowledge)
**Purpose**: Immediate domain grounding.  
**Repository**: [rtk-ai/rtk](https://github.com/rtk-ai/rtk)  
**What it does**: Provides persistent rules and dynamic retrieval constraints so the AI inherently understands Hexagonal Architecture constraints and domain specifics without needing to be repeatedly prompted.

---

## Folder Structure

To prevent confusion and rule collision, the `.agents/` directory is strictly organized via prefixes:

### `.agents/rules/` (Global Rules)
These files are globally active. The AI will constantly refer to them during generation.
- `caveman-rules.md` (Activates caveman modes and compression behaviors)
- `crg-rules.md` (Mandates using graph tools instead of grep/glob)
- `ctx-rules.md` (Mandates the "Think in Code" Context Mode behavior)
- `rtk-rules.md` (General RTK constraints)
- `proj-*.md` (Project-specific rules like API design, testing, Git conventions, code styling)

### `.agents/skills/` (Task Instructions)
These are invoked on-demand by the AI when a specific complex workflow is required.
- `caveman-*` (Token saving behaviors, e.g. `caveman-commit`)
- `crg-*` (Graph analysis behaviors, e.g. `crg-debug-issue`)
- `proj-*` (Project operations, e.g. `proj-create-pr`)
