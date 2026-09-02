import { z } from 'zod';

export const SCHEMA_VERSION = '1.0.0' as const;

export const TraceContextSchema = z.object({
  traceparent: z.string().optional(),
  tracestate: z.string().optional(),
});

export const ActionEnvelopeSchema = z.object({
  schemaVersion: z.literal(SCHEMA_VERSION),
  runId: z.string().uuid(),
  stepId: z.string().min(1),
  idempotencyKey: z.string().min(16),
  authorizationScope: z.enum(['inspect', 'fill', 'navigate', 'upload', 'submit']),
  redactionPolicy: z.enum(['metadata_only', 'pii_redacted', 'sensitive']),
  traceContext: TraceContextSchema,
});

export const HealthStatusSchema = z.object({
  status: z.enum(['starting', 'ready', 'degraded', 'stopped']),
  service: z.string(),
  version: z.string(),
  browserWorkerConnected: z.boolean(),
  databaseReady: z.boolean(),
  telemetryReady: z.boolean(),
});

export const WorkflowStateSchema = z.enum([
  'created',
  'ingesting_job',
  'preparing_materials',
  'opening_application',
  'authenticating',
  'registering',
  'verifying_email',
  'filling',
  'awaiting_human',
  'validating',
  'ready_to_submit',
  'submitting',
  'submitted',
  'failed',
  'cancelled',
  'outcome_uncertain',
]);

export const ApplicationRunSchema = z.object({
  id: z.string().uuid(),
  jobId: z.string().uuid(),
  candidateProfileId: z.string().uuid(),
  candidateProfileVersion: z.number().int().positive(),
  jobUrl: z.url(),
  state: WorkflowStateSchema,
  autoSubmitAuthorized: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const CandidateProfileInputSchema = z.object({
  firstName: z.string().min(1).max(100),
  lastName: z.string().min(1).max(100),
  preferredName: z.string().max(100).default(''),
  email: z.string().min(3).max(320),
  phone: z.string().max(50).default(''),
  city: z.string().max(120).default(''),
  region: z.string().max(120).default(''),
  country: z.string().max(120).default('United States'),
  postalCode: z.string().max(30).default(''),
  linkedinUrl: z.url().nullable().default(null),
  githubUrl: z.url().nullable().default(null),
  school: z.string().max(200).default(''),
  degree: z.string().max(200).default(''),
  fieldOfStudy: z.string().max(200).default(''),
  graduationYear: z.number().int().min(1950).max(2100).nullable().default(null),
  workAuthorization: z
    .enum(['unspecified', 'authorized', 'requires_sponsorship', 'not_authorized'])
    .default('unspecified'),
  requiresSponsorship: z.boolean().nullable().default(null),
});

export const CandidateFactSchema = z.object({
  id: z.string().uuid(),
  canonicalPath: z.string(),
  value: z.string(),
  state: z.enum(['extracted', 'needs_review', 'verified', 'superseded', 'deleted']),
  evidenceIds: z.array(z.string().uuid()),
  sensitivity: z.enum(['ordinary', 'sensitive', 'legal', 'demographic']),
});

export const SourceSpanSchema = z.object({
  page: z.number().int().positive().nullable().default(null),
  section: z.string().nullable().default(null),
  start: z.number().int().nonnegative(),
  end: z.number().int().positive(),
});

export const SourceDocumentSchema = z.object({
  id: z.string().uuid(),
  filename: z.string(),
  mediaType: z.enum([
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ]),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  encryptedArtifactRef: z.string(),
  status: z.enum(['parsed', 'needs_ocr', 'failed']),
  parseErrorCode: z.string().nullable().default(null),
  extractedEvidenceCount: z.number().int().nonnegative(),
  importedAt: z.string(),
});

export const EvidenceItemSchema = z.object({
  id: z.string().uuid(),
  sourceDocumentId: z.string().uuid().nullable().default(null),
  sourceSpan: SourceSpanSchema.nullable().default(null),
  statement: z.string(),
  extractionMethod: z.enum(['deterministic', 'model', 'user']),
  confidence: z.number().min(0).max(1),
  verified: z.boolean(),
});

export const CandidateProfileSnapshotSchema = z.object({
  profile: z.object({
    id: z.string().uuid(),
    version: z.number().int().positive(),
    facts: z.array(CandidateFactSchema),
    evidence: z.array(EvidenceItemSchema),
    sourceDocuments: z.array(SourceDocumentSchema),
  }),
  updatedAt: z.string(),
});

export const ResumeImportResultSchema = z.object({
  snapshot: CandidateProfileSnapshotSchema,
  document: SourceDocumentSchema,
});

export const BrowserWorkerMessageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('ready'), workerVersion: z.string() }),
  z.object({ type: z.literal('heartbeat'), timestamp: z.string().datetime() }),
  z.object({
    type: z.literal('action_result'),
    actionId: z.string(),
    runId: z.string().uuid(),
    ok: z.boolean(),
    pageStateHash: z.string().optional(),
    errorCode: z.string().optional(),
  }),
]);

export const BrowserCommandSchema = z.object({
  type: z.literal('command'),
  commandId: z.string().uuid(),
  action: z.enum(['navigate', 'scan', 'pause', 'resume', 'cancel']),
  url: z.url().optional(),
  browserProfileDir: z.string().optional(),
  envelope: ActionEnvelopeSchema,
});

export type TraceContext = z.infer<typeof TraceContextSchema>;
export type ActionEnvelope = z.infer<typeof ActionEnvelopeSchema>;
export type HealthStatus = z.infer<typeof HealthStatusSchema>;
export type WorkflowState = z.infer<typeof WorkflowStateSchema>;
export type ApplicationRun = z.infer<typeof ApplicationRunSchema>;
export type CandidateProfileInput = z.infer<typeof CandidateProfileInputSchema>;
export type CandidateProfileSnapshot = z.infer<typeof CandidateProfileSnapshotSchema>;
export type ResumeImportResult = z.infer<typeof ResumeImportResultSchema>;
export type SourceDocument = z.infer<typeof SourceDocumentSchema>;
export type BrowserWorkerMessage = z.infer<typeof BrowserWorkerMessageSchema>;
export type BrowserCommand = z.infer<typeof BrowserCommandSchema>;
