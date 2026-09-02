# CareerFlow Product Definition

Status: active implementation  
Last updated: 2026-08-23

## Product statement

CareerFlow is a desktop-first, supervised job-application agent. The user pastes a job URL into an independent desktop UI. CareerFlow extracts the posting, selects evidence from the user's verified profile, prepares application material, opens a visible controlled browser, handles routine account registration and form completion, and records the result.

The automation continues while actions are supported, authorized, and sufficiently confident. It pauses when a human must resolve CAPTCHA, 2FA, mailbox authorization, legal or sensitive questions, ambiguity, unexpected site behavior, or an unsafe action.

## Primary user

The first user is the project owner, applying to software-engineering and applied-AI roles. The same workflow must be designed so it can later support other job seekers without sharing profiles, credentials, browser sessions, documents, or histories.

## User outcomes

- Reduce repetitive application work without reducing accuracy or user control.
- Tailor resumes and answers only from verifiable candidate evidence.
- Complete routine application steps across multiple ATS platforms.
- Make every automated decision inspectable and correctable.
- Track successful and unsuccessful attempts and explain why attempts failed.
- Produce measurable evidence of time saved, quality, reliability, and safety.

## Version-one scope

- Desktop control center with onboarding, job URL intake, live run status, intervention inbox, and application dashboard.
- Encrypted candidate profile, reusable answers, source documents, and evidence ledger.
- Job extraction, platform detection, requirement mapping, and grounded resume/answer generation.
- Visible persistent-browser automation with ATS adapters and a generic semantic fallback.
- Assisted registration and authorized email-verification handling.
- Multi-page form filling, document upload, validation, submission policy, confirmation capture, and recovery.
- Application history, failure taxonomy, statistics, traces, and evaluation suite.

## Locked release constraints

- macOS 14+ on Apple Silicon, distributed initially as an unsigned local build.
- One visible, dedicated Chromium profile and one active run with a reorderable queue.
- Workday is the first real ATS adapter; Greenhouse, Lever, and semantic fallback follow.
- Gmail is the first optional mailbox connector and always has a manual fallback.
- Each installation executes independently on the user's device; no shared automation backend is required.
- OpenAI is bring-your-own-key. The default is `gpt-5.6-terra` with medium reasoning, strict structured outputs, and response storage disabled.

## Explicit non-goals

- High-volume or indiscriminate mass application.
- Bypassing CAPTCHA, 2FA, anti-bot controls, rate limits, or platform access rules.
- Fabricating qualifications, experience, identity, preferences, or legal answers.
- Answering demographic or disability questions without explicit user choices.
- Depending on employer-only ATS APIs for applicant submission.
- Hiding browser activity or making irreversible actions impossible to stop.

## Automation policy

The user authorizes each application run and chooses whether that run may submit automatically after all checks pass. CareerFlow may auto-fill only fields allowed by the field policy. It must pause when a required answer is missing, ambiguous, sensitive, legally meaningful, outside the evidence ledger, or rejected by the site.

Successful submission requires a confirmation signal such as a confirmation page, application identifier, or confirmation email. Absence of proof is recorded as an uncertain or failed result, never as success.

## Success measures

- Zero unsupported or fabricated claims.
- 100% policy coverage for sensitive and legal fields.
- Field-mapping accuracy by platform and field category.
- Resume and job extraction accuracy with provenance coverage.
- Completion, failure, and human-intervention rates.
- Safe recovery after navigation, session, process, and model failures.
- Median user time and total elapsed time per application.
- Adapter regression rate, latency, token use, and model cost.
