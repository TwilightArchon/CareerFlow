import { describe, expect, it } from 'vitest';

import {
  ActionEnvelopeSchema,
  ApplicationRunSchema,
  CandidateProfileInputSchema,
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
