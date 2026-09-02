# Documentation Conventions

Last updated: 2026-08-22

## Chosen convention

`AGENTS.md` is the canonical repository instruction file. `CLAUDE.md`, `.github/copilot-instructions.md`, and `.cursor/rules/documentation-sync.mdc` are compatibility entry points that direct their tools to the same documentation workflow. Project rules must not be copied into several files because duplicated instructions drift.

Codex automatically discovers `AGENTS.md`, but it does not automatically load every feature document on every task. The root instruction therefore requires the agent to open `docs/INDEX.md` and the relevant capability specifications before editing. The always-applied Cursor rule repeats this workflow for Cursor-based sessions. Claude's entry file imports the canonical instructions and documentation index.

## Repository Markdown files in use

- `README.md`: public project overview, status, planned stack, and starting links.
- `AGENTS.md`: canonical instructions for Codex and other agents that support the convention.
- `CLAUDE.md`: Claude Code entry point importing the canonical instructions.
- `.github/copilot-instructions.md`: GitHub Copilot repository instructions.
- `CONTRIBUTING.md`: documentation-first contribution and validation workflow.
- `SECURITY.md`: sensitive-data rules and vulnerability-handling expectations.
- `TODO.md`: phased implementation checklist with exit criteria.
- `CHANGELOG.md`: versioned prototype and release history.
- `docs/TROUBLESHOOTING.md`: significant problems, verified causes, solutions, open issues, and regression prevention.
- `docs/PROJECT.md`: canonical product requirements and non-goals.
- `docs/ARCHITECTURE.md`: system boundaries, data flow, stack, and target layout.
- `docs/features/*.md`: one contract per user-facing capability or independently owned subsystem.
- `docs/adr/*.md`: architecture decision records for expensive-to-reverse choices.

## Files to add when they become meaningful

- `LICENSE`: add only after the owner chooses how the project may be reused.
- `CODE_OF_CONDUCT.md`: add before accepting public community contributions.
- API documentation: add beside the versioned contracts when stable service interfaces exist.
- Nested `AGENTS.md`: add inside a subsystem only when it needs rules that differ from the repository root.

## Granularity rule

Create one Markdown specification per product capability or stable subsystem, not per source-code function. Ordinary functions should use clear names, types, tests, and comments where necessary. A separate Markdown file is justified when behavior has its own user flow, policy, state model, interface contract, or acceptance criteria.

## Official references

- [OpenAI: Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Anthropic: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [GitHub: Adding repository custom instructions for Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [Cursor: Rules](https://docs.cursor.com/context/rules-for-ai)
