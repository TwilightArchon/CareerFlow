import { describe, expect, it } from 'vitest';

import {
  ActionEnvelopeSchema,
  ApplicationMaterialPlanSchema,
  ApplicationOutcomeSchema,
  ApplicationStatisticsSchema,
  ApplicationRunSchema,
  BrowserCommandSchema,
  CandidateProfileInputSchema,
  FieldExplanationSchema,
  JobPostingSchema,
  ResumePreviewResultSchema,
  RecordApplicationOutcomeRequestSchema,
  RunControlRequestSchema,
  SourceDocumentSchema,
  SCHEMA_VERSION,
} from '../src/index';

describe('ActionEnvelope', () => {
  it('rejects a short idempotency key', () => {
    const result = ActionEnvelopeSchema.safeParse({
      schemaVersion: SCHEMA_VERSION,
      runId: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      stepId: 'scan',
      idempotencyKey: 'short',
      authorizationScope: 'inspect',
      redactionPolicy: 'metadata_only',
      traceContext: {},
    });

    expect(result.success).toBe(false);
  });
});

describe('ApplicationRun', () => {
  it('validates the durable renderer projection', () => {
    const parsed = ApplicationRunSchema.parse({
      id: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      jobId: 'ca7dcf7f-ce0a-4a3c-991a-f5a96f30700d',
      candidateProfileId: 'cf33db30-39ee-4cd6-bae3-0c2d9156b5bf',
      candidateProfileVersion: 1,
      jobUrl: 'https://example.com/jobs/1',
      state: 'filling',
      autoSubmitAuthorized: false,
      createdAt: '2026-08-23T00:00:00Z',
      updatedAt: '2026-08-23T00:01:00Z',
    });

    expect(parsed.state).toBe('filling');
    expect(parsed.latestOutcome).toBeNull();
  });
});

describe('application outcomes', () => {
  it('requires a reason that matches the explicitly confirmed outcome', () => {
    expect(
      RecordApplicationOutcomeRequestSchema.safeParse({
        outcome: 'submitted',
        reasonCode: 'user_confirmed_submitted',
        confirmedByUser: true,
      }).success,
    ).toBe(true);
    expect(
      RecordApplicationOutcomeRequestSchema.safeParse({
        outcome: 'submitted',
        reasonCode: 'validation_failed',
        confirmedByUser: true,
      }).success,
    ).toBe(false);
    expect(
      RecordApplicationOutcomeRequestSchema.safeParse({
        outcome: 'submitted',
        reasonCode: 'user_confirmed_submitted',
        confirmedByUser: false,
      }).success,
    ).toBe(false);
    expect(
      ApplicationOutcomeSchema.safeParse({
        id: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
        runId: 'ca7dcf7f-ce0a-4a3c-991a-f5a96f30700d',
        revision: 1,
        supersedesId: null,
        outcome: 'submitted',
        reasonCode: 'user_confirmed_submitted',
        confirmation: [],
        recordedBy: 'user',
        recordedAt: '2026-09-03T00:00:00Z',
      }).success,
    ).toBe(false);
  });

  it('validates aggregate statistics derived from durable records', () => {
    const parsed = ApplicationStatisticsSchema.parse({
      totalRuns: 4,
      resolvedRuns: 3,
      pendingRuns: 1,
      submitted: 2,
      failed: 1,
      cancelled: 0,
      abandoned: 0,
      outcomeUncertain: 0,
      resolutionRate: 0.75,
      submittedRate: 0.5,
      generatedAt: '2026-09-03T00:00:00Z',
    });
    expect(parsed.pendingRuns).toBe(1);
  });
});

describe('CandidateProfileInput', () => {
  it('requires identity and contact fields without requiring legal answers', () => {
    const parsed = CandidateProfileInputSchema.parse({
      firstName: 'Synthetic',
      lastName: 'Candidate',
      email: 'synthetic@example.com',
    });

    expect(parsed.workAuthorization).toBe('unspecified');
    expect(parsed.requiresSponsorship).toBeNull();
  });
});

describe('SourceDocument', () => {
  it('validates encrypted artifact metadata without exposing file contents', () => {
    const parsed = SourceDocumentSchema.parse({
      id: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      filename: 'Synthetic Resume.pdf',
      mediaType: 'application/pdf',
      sha256: 'a'.repeat(64),
      encryptedArtifactRef: 'artifacts/document.cfenc',
      status: 'parsed',
      parseErrorCode: null,
      extractedEvidenceCount: 3,
      importedAt: '2026-08-24T00:00:00Z',
    });

    expect(parsed.status).toBe('parsed');
    expect(parsed.extractedEvidenceCount).toBe(3);
  });
});

describe('ResumePreviewResult', () => {
  it('validates local profile suggestions with source provenance', () => {
    const parsed = ResumePreviewResultSchema.parse({
      status: 'parsed',
      parseErrorCode: null,
      extractedEvidenceCount: 3,
      suggestions: [
        {
          canonicalPath: 'contact.email',
          value: 'synthetic@example.com',
          confidence: 1,
          sourceSpan: { page: 1, section: 'page:1', start: 20, end: 41 },
        },
      ],
    });

    expect(parsed.suggestions[0]?.canonicalPath).toBe('contact.email');
  });
});

describe('JobPosting', () => {
  it('validates a durable normalized job review', () => {
    const parsed = JobPostingSchema.parse({
      id: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      version: 1,
      supersedesId: null,
      sourceUrl: 'https://jobs.example.com/role?utm_source=test',
      canonicalUrl: 'https://jobs.example.com/role',
      resolvedUrl: 'https://jobs.example.com/role',
      title: 'Software Engineer',
      company: 'Example Company',
      location: 'Raleigh, NC',
      description: 'Qualifications\nExperience with TypeScript.',
      descriptionHash: 'a'.repeat(64),
      requirements: [
        {
          id: 'ca7dcf7f-ce0a-4a3c-991a-f5a96f30700d',
          text: 'Experience with TypeScript.',
          required: true,
          sourceSpan: { page: null, section: null, start: 15, end: 42 },
        },
      ],
      platform: { platform: 'unknown', confidence: 0.25, signals: ['hostname:unrecognized'] },
      status: 'complete',
      warnings: [],
      retrievedAt: '2026-09-02T00:00:00Z',
    });

    expect(parsed.requirements).toHaveLength(1);
  });
});

describe('ApplicationMaterialPlan', () => {
  it('validates exact grounded evidence and rejects model-generated plans', () => {
    const plan = {
      jobId: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      jobVersion: 1,
      candidateProfileId: 'cf33db30-39ee-4cd6-bae3-0c2d9156b5bf',
      candidateProfileVersion: 3,
      generatorVersion: 'deterministic-v1',
      status: 'needs_review',
      coverageRatio: 1,
      supportedCount: 1,
      partialCount: 0,
      unsupportedCount: 0,
      mappings: [],
      resumeDraft: { title: 'Grounded evidence draft', entries: [] },
      modelUsed: false,
      createdAt: '2026-09-03T00:00:00Z',
    };

    expect(ApplicationMaterialPlanSchema.parse(plan).modelUsed).toBe(false);
    expect(ApplicationMaterialPlanSchema.safeParse({ ...plan, modelUsed: true }).success).toBe(
      false,
    );
  });
});

describe('BrowserCommand', () => {
  it('validates a policy-approved fill without logging a value in its mapping rationale', () => {
    const parsed = BrowserCommandSchema.parse({
      type: 'command',
      commandId: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      action: 'fill',
      expectedPageStateHash: 'abc12345',
      fills: [
        {
          controlId: 'first-name',
          canonicalPath: 'identity.first_name',
          value: 'Synthetic',
          evidenceIds: ['cf33db30-39ee-4cd6-bae3-0c2d9156b5bf'],
          rationale: 'Autocomplete metadata identifies identity.first_name.',
        },
      ],
      blockedMappings: [],
      envelope: {
        schemaVersion: SCHEMA_VERSION,
        runId: 'ca7dcf7f-ce0a-4a3c-991a-f5a96f30700d',
        stepId: 'synthetic_form_fill',
        idempotencyKey: 'synthetic-form-fill-0001',
        authorizationScope: 'fill',
        redactionPolicy: 'sensitive',
        traceContext: {},
      },
    });

    expect(parsed.fills[0]?.canonicalPath).toBe('identity.first_name');
  });
});

describe('RunControlRequest', () => {
  it('allows only explicit pause, resume, and cancel commands with idempotency', () => {
    expect(
      RunControlRequestSchema.parse({
        command: 'pause',
        idempotencyKey: 'pause-request-0001',
      }).command,
    ).toBe('pause');
    expect(
      RunControlRequestSchema.safeParse({ command: 'stop', idempotencyKey: 'short' }).success,
    ).toBe(false);
  });
});

describe('FieldExplanation', () => {
  it('contains a decision rationale without a candidate value', () => {
    const explanation = FieldExplanationSchema.parse({
      id: '87c02b80-07e2-4fe1-b5d6-cb2553035ff5',
      runId: 'ca7dcf7f-ce0a-4a3c-991a-f5a96f30700d',
      stepId: 'synthetic_form_fill',
      pageStateHash: 'a'.repeat(64),
      controlId: 'email',
      canonicalPath: 'contact.email',
      source: 'deterministic',
      confidence: 0.99,
      sensitivity: 'sensitive',
      decision: 'human_required',
      rationale: 'Autocomplete metadata identifies contact.email.',
      filled: false,
      recordedAt: '2026-09-03T00:00:00Z',
    });

    expect(explanation.filled).toBe(false);
    expect(Object.hasOwn(explanation, 'value')).toBe(false);
  });
});
