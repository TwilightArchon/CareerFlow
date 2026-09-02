# ADR 0003: Embedded Python Runtime for macOS Packages

Status: accepted  
Date: 2026-08-23

## Context

The first unsigned DMG launched its Python service through `uv` on the destination Mac. This made Finder launches depend on shell path configuration and made the first launch wait for package downloads. A packaged-build test reproduced an unreliable initialization timeout even after development dependencies were excluded.

## Decision

Apple Silicon packages embed a relocatable CPython 3.13 runtime and the locked runtime-only Python dependencies. Electron launches the packaged interpreter directly and exposes only the packaged agent source through `PYTHONPATH`. Development and CI continue to use `uv` and `uv.lock`.

The generated runtime directory is excluded from version control. `pnpm package:mac` prepares it when absent, and the post-package verifier rejects an app that lacks the interpreter, compiled contracts, browser worker, or required Node dependencies.

## Consequences

- Installing CareerFlow does not require Node.js, pnpm, Python, `uv`, or first-launch dependency downloads.
- The DMG is larger and remains architecture-specific.
- Runtime dependency changes require regenerating the embedded runtime before packaging.
- Intel packaging needs a separate Python distribution and dependency set.
- Signing and notarization remain separate distribution work.
