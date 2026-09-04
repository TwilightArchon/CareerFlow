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
  browserWorkerSessionId: z.string().uuid().nullable().default(null),
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
  'paused',
  'awaiting_human',
  'validating',
  'ready_to_submit',
  'submitting',
  'submitted',
  'failed',
  'cancelled',
  'outcome_uncertain',
]);

export const OutcomeTypeSchema = z.enum([
  'submitted',
  'failed',
  'cancelled',
  'abandoned',
  'outcome_uncertain',
]);

export const OutcomeReasonCodeSchema = z.enum([
  'user_confirmed_submitted',
  'ingestion_failed',
  'evidence_missing',
  'authentication_failed',
  'registration_failed',
  'verification_failed',
  'mapping_failed',
  'validation_failed',
  'submission_failed',
  'platform_changed',
  'policy_blocked',
  'user_cancelled',
  'user_abandoned',
  'confirmation_missing',
]);

export const ConfirmationEvidenceSchema = z.object({
  kind: z.enum(['confirmation_page', 'application_id', 'confirmation_email', 'user_correction']),
  capturedAt: z.string(),
  fingerprint: z.string().regex(/^[a-f0-9]{64}$/),
  artifactRef: z.string().nullable().default(null),
});

export const ApplicationOutcomeSchema = z
  .object({
    id: z.string().uuid(),
    runId: z.string().uuid(),
    revision: z.number().int().positive(),
    supersedesId: z.string().uuid().nullable().default(null),
    outcome: OutcomeTypeSchema,
    reasonCode: OutcomeReasonCodeSchema,
    confirmation: z.array(ConfirmationEvidenceSchema),
    recordedBy: z.literal('user'),
    recordedAt: z.string(),
  })
  .superRefine((value, context) => {
    if (value.outcome === 'submitted' && value.confirmation.length === 0) {
      context.addIssue({
        code: 'custom',
        path: ['confirmation'],
        message: 'Submitted outcomes require confirmation evidence',
      });
    }
  });

const allowedOutcomeReasons: Record<
  z.infer<typeof OutcomeTypeSchema>,
  ReadonlySet<z.infer<typeof OutcomeReasonCodeSchema>>
> = {
  submitted: new Set(['user_confirmed_submitted']),
  failed: new Set([
    'ingestion_failed',
    'evidence_missing',
    'authentication_failed',
    'registration_failed',
    'verification_failed',
    'mapping_failed',
    'validation_failed',
    'submission_failed',
    'platform_changed',
    'policy_blocked',
  ]),
  cancelled: new Set(['user_cancelled']),
  abandoned: new Set(['user_abandoned']),
  outcome_uncertain: new Set(['confirmation_missing']),
};

export const RecordApplicationOutcomeRequestSchema = z
  .object({
    outcome: OutcomeTypeSchema,
    reasonCode: OutcomeReasonCodeSchema,
    confirmedByUser: z.literal(true),
  })
  .superRefine((value, context) => {
    if (!allowedOutcomeReasons[value.outcome].has(value.reasonCode)) {
      context.addIssue({
        code: 'custom',
        path: ['reasonCode'],
        message: 'Reason is not valid for the selected outcome',
      });
    }
  });

export const ApplicationRunSchema = z.object({
  id: z.string().uuid(),
  jobId: z.string().uuid(),
  candidateProfileId: z.string().uuid(),
  candidateProfileVersion: z.number().int().positive(),
  jobUrl: z.url(),
  jobTitle: z.string().nullable().default(null),
  company: z.string().nullable().default(null),
  platform: z
    .enum(['synthetic', 'workday', 'greenhouse', 'lever', 'unknown'])
    .nullable()
    .default(null),
  state: WorkflowStateSchema,
  latestOutcome: ApplicationOutcomeSchema.nullable().default(null),
  autoSubmitAuthorized: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const ApplicationStatisticsSchema = z.object({
  totalRuns: z.number().int().nonnegative(),
  resolvedRuns: z.number().int().nonnegative(),
  pendingRuns: z.number().int().nonnegative(),
  submitted: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
  cancelled: z.number().int().nonnegative(),
  abandoned: z.number().int().nonnegative(),
  outcomeUncertain: z.number().int().nonnegative(),
  resolutionRate: z.number().min(0).max(1),
  submittedRate: z.number().min(0).max(1),
  generatedAt: z.string(),
});

export const RunControlRequestSchema = z.object({
  command: z.enum(['pause', 'resume', 'cancel']),
  idempotencyKey: z.string().min(16).max(128),
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

export const JobRequirementSchema = z.object({
  id: z.string().uuid(),
  text: z.string(),
  required: z.boolean(),
  sourceSpan: SourceSpanSchema,
});

export const PlatformDetectionSchema = z.object({
  platform: z.enum(['synthetic', 'workday', 'greenhouse', 'lever', 'unknown']),
  confidence: z.number().min(0).max(1),
  signals: z.array(z.string()),
});

export const JobPostingSchema = z.object({
  id: z.string().uuid(),
  version: z.number().int().positive(),
  supersedesId: z.string().uuid().nullable().default(null),
  sourceUrl: z.url(),
  canonicalUrl: z.url(),
  resolvedUrl: z.url(),
  title: z.string(),
  company: z.string(),
  location: z.string(),
  description: z.string(),
  descriptionHash: z.string().regex(/^[a-f0-9]{64}$/),
  requirements: z.array(JobRequirementSchema),
  platform: PlatformDetectionSchema,
  status: z.enum(['complete', 'needs_review']),
  warnings: z.array(z.string()),
  retrievedAt: z.string(),
});

export const EvidenceMatchSchema = z.object({
  evidenceId: z.string().uuid(),
  statement: z.string(),
  sourceDocumentId: z.string().uuid().nullable().default(null),
  sourceSpan: SourceSpanSchema.nullable().default(null),
  score: z.number().min(0).max(1),
  matchedTerms: z.array(z.string()),
});

export const RequirementEvidenceMappingSchema = z.object({
  requirementId: z.string().uuid(),
  requirementText: z.string(),
  required: z.boolean(),
  support: z.enum(['supported', 'partial', 'unsupported']),
  confidence: z.number().min(0).max(1),
  matches: z.array(EvidenceMatchSchema),
  explanation: z.string(),
});

export const GroundedResumeEntrySchema = z.object({
  evidenceId: z.string().uuid(),
  statement: z.string(),
  sourceDocumentId: z.string().uuid().nullable().default(null),
  sourceSpan: SourceSpanSchema.nullable().default(null),
  supportsRequirementIds: z.array(z.string().uuid()),
});

export const ApplicationMaterialPlanSchema = z.object({
  jobId: z.string().uuid(),
  jobVersion: z.number().int().positive(),
  candidateProfileId: z.string().uuid(),
  candidateProfileVersion: z.number().int().positive(),
  generatorVersion: z.literal('deterministic-v1'),
  status: z.enum(['needs_review', 'needs_evidence']),
  coverageRatio: z.number().min(0).max(1),
  supportedCount: z.number().int().nonnegative(),
  partialCount: z.number().int().nonnegative(),
  unsupportedCount: z.number().int().nonnegative(),
  mappings: z.array(RequirementEvidenceMappingSchema),
  resumeDraft: z.object({
    title: z.string(),
    entries: z.array(GroundedResumeEntrySchema),
  }),
  modelUsed: z.literal(false),
  createdAt: z.string(),
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

export const ResumeFieldSuggestionSchema = z.object({
  canonicalPath: z.enum([
    'identity.first_name',
    'identity.last_name',
    'contact.email',
    'contact.phone',
    'links.linkedin',
    'links.github',
    'education.0.school',
    'education.0.degree',
    'education.0.field_of_study',
    'education.0.graduation_year',
  ]),
  value: z.string(),
  confidence: z.number().min(0).max(1),
  sourceSpan: SourceSpanSchema,
});

export const ResumePreviewResultSchema = z.object({
  status: z.enum(['parsed', 'needs_ocr', 'failed']),
  parseErrorCode: z.string().nullable().default(null),
  extractedEvidenceCount: z.number().int().nonnegative(),
  suggestions: z.array(ResumeFieldSuggestionSchema),
});

export const SensitivitySchema = z.enum(['ordinary', 'sensitive', 'legal', 'demographic']);
export const MappingDecisionSchema = z.enum([
  'auto_fill',
  'review',
  'human_required',
  'unsupported',
]);

export const FormControlSchema = z.object({
  controlId: z.string().min(1),
  label: z.string(),
  kind: z.enum(['text', 'email', 'tel', 'select', 'checkbox', 'radio', 'file', 'textarea']),
  required: z.boolean(),
  sensitivity: SensitivitySchema,
  options: z.array(z.string()).default([]),
  autocomplete: z.string().nullable().default(null),
});

export const ObservedFormSchema = z.object({
  pageUrl: z.url(),
  pageStateHash: z.string().min(1),
  controls: z.array(FormControlSchema),
});

export const FieldMappingSchema = z.object({
  controlId: z.string().min(1),
  canonicalPath: z.string().nullable(),
  source: z.enum(['adapter', 'deterministic', 'model', 'user']),
  confidence: z.number().min(0).max(1),
  sensitivity: SensitivitySchema,
  decision: MappingDecisionSchema,
  rationale: z.string(),
});

export const FieldExplanationSchema = FieldMappingSchema.extend({
  id: z.string().uuid(),
  runId: z.string().uuid(),
  stepId: z.string().min(1).max(128),
  pageStateHash: z.string().min(1).max(128),
  filled: z.boolean(),
  recordedAt: z.string(),
});

export const BrowserFieldFillSchema = z.object({
  controlId: z.string().min(1).max(200),
  canonicalPath: z.string().min(1).max(200),
  value: z.string().max(10_000),
  evidenceIds: z.array(z.string().uuid()),
  rationale: z.string().min(1).max(500),
});

export const BrowserWorkerMessageSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('ready'),
    workerVersion: z.string(),
    workerSessionId: z.string().uuid(),
  }),
  z.object({ type: z.literal('heartbeat'), timestamp: z.string().datetime() }),
  z.object({
    type: z.literal('action_result'),
    actionId: z.string(),
    runId: z.string().uuid(),
    action: z.enum([
      'navigate',
      'open_synthetic_form',
      'fill',
      'scan',
      'pause',
      'resume',
      'cancel',
    ]),
    ok: z.boolean(),
    pageStateHash: z.string().optional(),
    errorCode: z.string().optional(),
  }),
  z.object({
    type: z.literal('form_observed'),
    actionId: z.string().uuid(),
    runId: z.string().uuid(),
    observedForm: ObservedFormSchema,
  }),
  z.object({
    type: z.literal('fill_result'),
    actionId: z.string().uuid(),
    runId: z.string().uuid(),
    ok: z.boolean(),
    pageStateHash: z.string().optional(),
    filledMappings: z.array(FieldMappingSchema),
    blockedMappings: z.array(FieldMappingSchema),
    errorCode: z.string().optional(),
  }),
]);

export const BrowserCommandSchema = z.object({
  type: z.literal('command'),
  commandId: z.string().uuid(),
  action: z.enum(['navigate', 'open_synthetic_form', 'fill', 'scan', 'pause', 'resume', 'cancel']),
  url: z.url().optional(),
  browserProfileDir: z.string().optional(),
  expectedPageStateHash: z.string().min(1).max(128).optional(),
  fills: z.array(BrowserFieldFillSchema).default([]),
  blockedMappings: z.array(FieldMappingSchema).default([]),
  envelope: ActionEnvelopeSchema,
});

export type TraceContext = z.infer<typeof TraceContextSchema>;
export type ActionEnvelope = z.infer<typeof ActionEnvelopeSchema>;
export type HealthStatus = z.infer<typeof HealthStatusSchema>;
export type WorkflowState = z.infer<typeof WorkflowStateSchema>;
export type OutcomeType = z.infer<typeof OutcomeTypeSchema>;
export type OutcomeReasonCode = z.infer<typeof OutcomeReasonCodeSchema>;
export type ConfirmationEvidence = z.infer<typeof ConfirmationEvidenceSchema>;
export type ApplicationOutcome = z.infer<typeof ApplicationOutcomeSchema>;
export type RecordApplicationOutcomeRequest = z.infer<typeof RecordApplicationOutcomeRequestSchema>;
export type ApplicationRun = z.infer<typeof ApplicationRunSchema>;
export type ApplicationStatistics = z.infer<typeof ApplicationStatisticsSchema>;
export type RunControlRequest = z.infer<typeof RunControlRequestSchema>;
export type CandidateProfileInput = z.infer<typeof CandidateProfileInputSchema>;
export type CandidateProfileSnapshot = z.infer<typeof CandidateProfileSnapshotSchema>;
export type ResumeImportResult = z.infer<typeof ResumeImportResultSchema>;
export type ResumeFieldSuggestion = z.infer<typeof ResumeFieldSuggestionSchema>;
export type ResumePreviewResult = z.infer<typeof ResumePreviewResultSchema>;
export type SourceDocument = z.infer<typeof SourceDocumentSchema>;
export type JobPosting = z.infer<typeof JobPostingSchema>;
export type JobRequirement = z.infer<typeof JobRequirementSchema>;
export type ApplicationMaterialPlan = z.infer<typeof ApplicationMaterialPlanSchema>;
export type RequirementEvidenceMapping = z.infer<typeof RequirementEvidenceMappingSchema>;
export type EvidenceMatch = z.infer<typeof EvidenceMatchSchema>;
export type GroundedResumeEntry = z.infer<typeof GroundedResumeEntrySchema>;
export type FormControl = z.infer<typeof FormControlSchema>;
export type ObservedForm = z.infer<typeof ObservedFormSchema>;
export type FieldMapping = z.infer<typeof FieldMappingSchema>;
export type FieldExplanation = z.infer<typeof FieldExplanationSchema>;
export type BrowserFieldFill = z.infer<typeof BrowserFieldFillSchema>;
export type BrowserWorkerMessage = z.infer<typeof BrowserWorkerMessageSchema>;
export type BrowserCommand = z.infer<typeof BrowserCommandSchema>;
