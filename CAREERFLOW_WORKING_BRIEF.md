# CareerFlow Working Brief

Updated: 2026-08-26

This public brief preserves the market research, engineering rationale, and product direction behind CareerFlow. It intentionally excludes candidate-specific résumé details, education records, contact information, credentials, application history, and other personal data. The canonical, change-controlled product definition is `docs/PROJECT.md`; architecture is `docs/ARCHITECTURE.md`; capability specifications are indexed by `docs/INDEX.md`.

## 1. Portfolio objective

CareerFlow is designed as a portfolio-quality software and AI infrastructure project for Software Development Engineer, Applied AI Engineer, AI Product Engineer, and Agent Platform Engineer roles.

The project is intended to demonstrate an integrated set of engineering abilities:

- Full-stack product delivery across an Electron/React desktop interface, typed local APIs, and a Python workflow service.
- Reliable agent orchestration using explicit states, durable events, checkpoints, retries, idempotency, and human intervention.
- Evidence-grounded AI behavior with provenance, structured outputs, deterministic validation, and anti-fabrication controls.
- Secure local execution using sandboxed process boundaries, operating-system keychain storage, encryption at rest, and least-privilege tools.
- Production-oriented quality practices including automated tests, evaluation datasets, OpenTelemetry, failure analysis, and CI/CD.
- Clear technical communication through architecture documents, feature specifications, ADRs, troubleshooting records, and measurable results.

These abilities are emphasized because dependable agent orchestration, evaluation, AI-specific observability, context engineering, secure tool execution, and human-controlled automation are important differentiators in applied-AI software roles.

## 2. What current agentic-AI SDE roles expect

The market signal is software engineering first and AI agents second. Employers do not primarily want prompt writers. They want engineers who can build reliable products around probabilistic models.

### Core software-engineering abilities

- Data structures, algorithms, operating systems, networking, databases, and distributed systems.
- Python and TypeScript/Node.js for agent backends and user-facing products.
- API design, typed schemas, asynchronous programming, concurrency, and background jobs.
- PostgreSQL, Redis, object storage, caching, indexing, and query optimization.
- React/Next.js or another modern frontend stack for review and operations interfaces.
- Testing at unit, integration, end-to-end, performance, and fault-injection levels.
- Docker, cloud deployment, CI/CD, secrets management, and infrastructure fundamentals.
- System design, technical writing, debugging, incident analysis, and product ownership.

### Agent and AI-system abilities

- Tool/function calling with typed inputs and outputs.
- Explicit state machines, durable workflows, checkpoints, retries, timeouts, and idempotency.
- Context engineering: ingestion, chunking, retrieval, reranking, metadata filters, citations, and context budgeting.
- Short-term state, long-term memory, and user-controlled personalization.
- Evaluation datasets, deterministic graders, model-based graders, regression suites, and online feedback.
- Tracing of model calls, tool calls, latency, tokens, cost, errors, and user outcomes.
- Model and prompt versioning, release gates, canaries, rollback, and cost controls.
- Human-in-the-loop approval, escalation, confidence policies, and explainable evidence.
- Prompt-injection defenses, least privilege, PII handling, sandboxing, audit logs, and red-team tests.

### Useful tools and keywords

- Languages: Python, TypeScript, JavaScript, Go as an optional systems language, SQL.
- APIs/backend: FastAPI, Pydantic, Node.js, REST, WebSocket/SSE where appropriate.
- Data: PostgreSQL, pgvector, Redis, object storage, SQLAlchemy.
- Agent runtimes: LangGraph or another explicit workflow runtime; raw model SDKs should also be understood.
- Retrieval: embeddings, hybrid search, reranking, document parsing, vector search, knowledge graphs when justified.
- Workflow infrastructure: Redis-backed workers, queues, Temporal as a later durable-workflow option, Kafka only when scale requires it.
- Observability: OpenTelemetry, structured logs, trace replay, dashboards, alerting, SLOs.
- Quality: pytest, Playwright, evaluation harnesses, golden datasets, adversarial cases, load testing.
- Delivery: Docker Compose, GitHub Actions, AWS/GCP/Azure, Terraform and Kubernetes after the core system works.
- Integration standards: OAuth, webhooks, browser extensions, MCP where it improves tool interoperability.

Framework names are secondary. The portfolio must demonstrate reliable behavior, measurable quality, security, and end-to-end ownership.

## 3. How SDEs should use AI to accelerate engineering

AI-native engineering does not mean accepting generated code without review. It means using agents to shorten feedback loops while the engineer owns architecture, correctness, security, and outcomes.

### High-value AI acceleration workflow

1. Discovery and planning
   - Summarize an unfamiliar codebase.
   - Trace request and data flows.
   - Identify affected components and risks.
   - Draft an implementation plan and acceptance criteria.

2. Implementation
   - Generate scaffolding, repetitive integration code, migrations, test fixtures, and documentation.
   - Delegate small, bounded tasks with explicit contracts.
   - Use multiple candidate implementations when tradeoffs are unclear.

3. Testing and evaluation
   - Generate edge cases from requirements and production failures.
   - Create unit, integration, browser, fault-injection, and regression tests.
   - Convert every discovered bug into a permanent test case.
   - Run agent evaluations in CI rather than relying on subjective prompt inspection.

4. Review and security
   - Ask AI to review diffs for correctness, concurrency, data-loss, performance, and security risks.
   - Independently inspect important code and verify claims with tests and measurements.
   - Keep destructive operations and sensitive decisions behind explicit approval.

5. Debugging and operations
   - Correlate logs, traces, metrics, deployments, and incidents.
   - Generate ranked hypotheses and reproduction steps.
   - Propose fixes, but verify them against observable recovery criteria.

6. Documentation and communication
   - Maintain architecture decisions, API references, runbooks, release notes, and retrospectives.
   - Turn implementation evidence into concise explanations for reviewers and stakeholders.

### Principles for responsible AI-assisted development

- Give the agent bounded tasks, clear acceptance criteria, and the minimum required authority.
- Prefer generated tests and measurements over generated confidence.
- Review code according to risk, not according to how plausible it looks.
- Record prompts, tool calls, versions, and outcomes for important automated workflows.
- Do not expose credentials, production data, or unrestricted tools to a model.
- Measure whether AI improves lead time, defect rate, review effort, reliability, and cost.

## 4. Project exploration and decision

Projects considered included OpsPilot, PatchPilot, VendorFlow, StudyGraph, DayFlow, LifeAdmin, ScholarFlow, HomeFlow, and CareerFlow.

CareerFlow was selected because it solves a concrete workflow that an individual job seeker can use locally while preserving a path to support other job seekers, career coaches, universities, and career centers.

CareerFlow should be a complete job-search operating system, not only a resume generator and not a mass-application bot.

## 5. CareerFlow product definition

CareerFlow is a supervised application agent that:

- Imports job postings and extracts structured requirements.
- Extracts structured evidence from resumes, projects, education, GitHub, and approved profile data.
- Maps each job requirement to verifiable candidate evidence.
- Generates and versions ATS-friendly resumes and application answers without fabricating experience.
- Detects application platforms such as Greenhouse, Workday, Lever, Ashby, and SmartRecruiters.
- Assists with account registration and multi-page form completion.
- Uploads the correct documents and fills high-confidence fields.
- Pauses for CAPTCHA, email verification, two-factor authentication, consent, legal questions, sensitive questions, and ambiguous answers.
- Requires a final review before submission by default.
- Captures confirmations and tracks application state, documents, answers, contacts, interviews, and follow-ups.

### Recommended product form

CareerFlow should be a desktop-first product with an independent control center:

- Desktop application: onboarding, job URL intake, profile management, live workflow status, interventions, application history, and statistics.
- Visible browser worker: a dedicated persistent Chromium profile controlled through Playwright for registration, form filling, uploads, navigation, and confirmation capture.
- Local AI and workflow service: extraction, evidence retrieval, grounded generation, semantic field interpretation, durable state, evaluation, and observability.
- Operating-system keychain: passwords, OAuth tokens, and encryption keys stay outside CareerFlow's ordinary database.
- Optional cloud control plane later: multi-user authentication, tenancy, shared metadata, and scalable background services without moving browser credentials off-device by default.

The application page remains visible while automation works. When human interaction is required, the workflow checkpoints its state, brings the blocked step to the user's attention, and resumes only after revalidating the page and the user's response.

CareerFlow must not bypass CAPTCHA or 2FA, infer demographic answers, fabricate qualifications, or silently accept legal terms.

## 6. ATS and platform constraints

ATS means Applicant Tracking System. It is the employer software used to publish jobs, collect applications, store candidate information, parse resumes, manage recruiting stages, coordinate interviews, and support reporting and compliance.

Examples include Greenhouse, Lever, Ashby, SmartRecruiters, and Workday Recruiting. Workday is a broader human-capital-management platform containing recruiting functionality.

There is no universal ATS score. An ATS-friendly resume is simply structured so common parsers can read it accurately: conventional headings, selectable text, clear dates, simple layout, and honest role-relevant terminology.

Applicant-side CareerFlow cannot depend on employer ATS APIs. Submission endpoints commonly require employer-controlled credentials. The practical primary integration is therefore browser automation in the user's own authenticated session, with public or applicant-accessible APIs used only where available.

## 7. Platform adapters and semantic fallback

### Dedicated adapters

Known ATS platforms receive deterministic adapters that understand their page structure, repeated employment/education sections, uploads, validation, navigation, and review pages.

### Semantic fallback

Unknown or customized forms are interpreted using:

- Visible labels and instructions.
- HTML name, ID, input type, and placeholder.
- ARIA accessibility labels and autocomplete metadata.
- Nearby headings and section context.
- Dropdown and radio-button options.
- Required status, character limits, and validation errors.

The fallback maps each control to a canonical schema such as `personal.first_name`, `education.school`, or `work_authorization.requires_sponsorship`.

Deterministic parsing should run first. A model is used only when meaning is ambiguous. A policy layer then decides whether a value can be filled automatically, needs review, or requires explicit confirmation.

High-confidence examples: name, email, phone, school, degree, dates, saved links.

Medium-confidence examples: skills, location preferences, availability, and referral source.

Explicit-confirmation examples: sponsorship, salary, legal attestations, demographic information, disability information, and open-ended claims.

## 8. CareerFlow architecture and hiring-skill proof

| CareerFlow capability           | Engineering skills demonstrated                                                |
| ------------------------------- | ------------------------------------------------------------------------------ |
| Resume and document extraction  | Multimodal/document processing, typed schemas, ETL, data validation            |
| Candidate evidence ledger       | Data modeling, retrieval, provenance, citations, knowledge representation      |
| Job requirement mapping         | Context engineering, ranking, structured output, evaluation                    |
| Browser platform adapters       | TypeScript, browser APIs, DOM/accessibility semantics, integration testing     |
| Semantic form fallback          | Classification, confidence policy, hybrid deterministic/LLM systems            |
| Durable application workflow    | State machines, checkpoints, retries, idempotency, background jobs             |
| Account and form assistance     | Tool use, human-in-the-loop, security boundaries, OAuth/session handling       |
| Resume and answer generation    | Grounded generation, versioning, anti-fabrication guardrails                   |
| Review and approval queue       | Full-stack product engineering, RBAC, auditability, explainability             |
| Application tracking CRM        | PostgreSQL, APIs, event modeling, notifications, analytics                     |
| Tracing and replay              | OpenTelemetry, structured logging, observability, failure analysis             |
| Evaluation and regression suite | Golden datasets, deterministic checks, model graders, CI quality gates         |
| Multi-user SaaS expansion       | Authentication, tenancy, authorization, encryption, rate limits, cost controls |

## 9. Recommended version-one scope

1. Encrypted canonical candidate profile and evidence ledger.
2. PDF/DOCX resume extraction and versioned ATS-friendly resume generation.
3. Job-description extraction and requirement-to-evidence mapping.
4. Electron desktop control center with a visible Playwright-controlled browser.
5. Greenhouse, Lever, and Workday adapters.
6. Generic semantic fallback for conventional forms.
7. Assisted registration with checkpoints for verification and consent.
8. Multi-page autofill, document upload, validation, and progress recovery.
9. User-authorized submission mode with policy validation and a review pause whenever authorization or required evidence is incomplete.
10. Confirmation capture and application CRM.
11. Evaluation fixtures, adversarial tests, traces, failure taxonomy, and CI regression gates.

## 10. Success metrics

- Field-mapping accuracy by platform and field category.
- Percentage of deterministic fields filled correctly without edits.
- Unsupported-claim and fabricated-answer count: zero.
- Sensitive-question approval coverage: 100%.
- Successful recovery after navigation, session, or tool failure.
- Application completion rate after user approval.
- Median user time required per application.
- Resume parsing accuracy and citation/evidence coverage.
- Adapter regression rate after platform UI changes.
- Latency and model cost per prepared application.

## 11. Working decisions to preserve

- CareerFlow is a supervised application operator, not a mass auto-apply bot.
- A desktop control center is preferred over a browser-extension-first product.
- A dedicated visible persistent browser profile is the primary execution environment.
- Known platforms use deterministic adapters; unknown forms use semantic fallback.
- Models propose interpretations and answers; deterministic code validates and executes.
- Legal, sensitive, and low-confidence actions require human approval unless a valid explicit reusable policy applies. Submission requires authorization for the current run or configured scope.
- Framework choice is secondary to measurable reliability, security, evaluation, and product quality.
- The project must demonstrate how an SDE uses AI to accelerate work while retaining engineering ownership.
