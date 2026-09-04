import { FormEvent, useEffect, useMemo, useState } from 'react';

import type {
  ApplicationMaterialPlan,
  ApplicationRun,
  ApplicationStatistics,
  CandidateProfileSnapshot,
  FieldExplanation,
  HealthStatus,
  JobPosting,
  OutcomeReasonCode,
  OutcomeType,
  WorkflowState,
} from '@careerflow/contracts';

import { ProfileView } from './ProfileView';

type View = 'control' | 'applications' | 'profile';
type OutcomeFilter = 'all' | 'pending' | OutcomeType;
type PlatformFilter = 'all' | NonNullable<ApplicationRun['platform']>;

const emptyHealth: HealthStatus = {
  status: 'starting',
  service: 'careerflow-agent',
  version: '0.1.9',
  browserWorkerConnected: false,
  databaseReady: false,
  telemetryReady: false,
};

const terminalStates = new Set<WorkflowState>([
  'submitted',
  'failed',
  'cancelled',
  'outcome_uncertain',
]);

function stateLabel(state: WorkflowState): string {
  const labels: Partial<Record<WorkflowState, string>> = {
    created: 'Queued',
    ingesting_job: 'Opening job',
    preparing_materials: 'Preparing',
    opening_application: 'Opening browser',
    filling: 'Browser opened',
    awaiting_human: 'Needs attention',
    ready_to_submit: 'Ready to submit',
    outcome_uncertain: 'Outcome uncertain',
  };
  return labels[state] ?? state.replaceAll('_', ' ');
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

interface RunListProps {
  runs: ApplicationRun[];
  showDetails?: boolean | undefined;
  expandedRunId?: string | undefined;
  explanations?: Record<string, FieldExplanation[]> | undefined;
  loadingRunId?: string | undefined;
  explanationError?: string | undefined;
  onToggleExplanations?: ((runId: string) => void) | undefined;
  savingOutcomeRunId?: string | undefined;
  outcomeErrorRunId?: string | undefined;
  outcomeError?: string | undefined;
  onRecordOutcome?:
    ((runId: string, outcome: OutcomeType, reasonCode: OutcomeReasonCode) => void) | undefined;
}

const outcomeOptions: { value: OutcomeType; label: string }[] = [
  { value: 'submitted', label: 'Submitted' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'abandoned', label: 'Abandoned' },
  { value: 'outcome_uncertain', label: 'Outcome uncertain' },
];

const failedReasonOptions: { value: OutcomeReasonCode; label: string }[] = [
  { value: 'ingestion_failed', label: 'Job ingestion failed' },
  { value: 'evidence_missing', label: 'Required evidence missing' },
  { value: 'authentication_failed', label: 'Authentication failed' },
  { value: 'registration_failed', label: 'Account registration failed' },
  { value: 'verification_failed', label: 'Email verification failed' },
  { value: 'mapping_failed', label: 'Field mapping failed' },
  { value: 'validation_failed', label: 'Form validation failed' },
  { value: 'submission_failed', label: 'Submission failed' },
  { value: 'platform_changed', label: 'Platform changed' },
  { value: 'policy_blocked', label: 'Stopped by safety policy' },
];

export function defaultOutcomeReason(outcome: OutcomeType): OutcomeReasonCode {
  const reasons: Record<Exclude<OutcomeType, 'failed'>, OutcomeReasonCode> = {
    submitted: 'user_confirmed_submitted',
    cancelled: 'user_cancelled',
    abandoned: 'user_abandoned',
    outcome_uncertain: 'confirmation_missing',
  };
  return outcome === 'failed' ? 'validation_failed' : reasons[outcome];
}

function readableReason(reason: OutcomeReasonCode): string {
  return reason.replaceAll('_', ' ');
}

function fieldLabel(explanation: FieldExplanation): string {
  return (explanation.canonicalPath ?? explanation.controlId)
    .replace(/\.0\./g, ' · ')
    .replaceAll('_', ' ')
    .replaceAll('.', ' · ');
}

function RunList({
  runs,
  showDetails = false,
  expandedRunId,
  explanations = {},
  loadingRunId,
  explanationError,
  onToggleExplanations,
  savingOutcomeRunId,
  outcomeErrorRunId,
  outcomeError,
  onRecordOutcome,
}: RunListProps) {
  const [outcomeDrafts, setOutcomeDrafts] = useState<Record<string, OutcomeType>>({});
  const [failedReasonDrafts, setFailedReasonDrafts] = useState<Record<string, OutcomeReasonCode>>(
    {},
  );
  return (
    <div className="run-list">
      {runs.map((run) => {
        const url = new URL(run.jobUrl);
        const expanded = expandedRunId === run.id;
        const runExplanations = explanations[run.id];
        const outcomeDraft = outcomeDrafts[run.id] ?? run.latestOutcome?.outcome ?? 'submitted';
        const reasonDraft =
          outcomeDraft === 'failed'
            ? (failedReasonDrafts[run.id] ??
              (run.latestOutcome?.outcome === 'failed'
                ? run.latestOutcome.reasonCode
                : 'validation_failed'))
            : defaultOutcomeReason(outcomeDraft);
        return (
          <article className="run-card" key={run.id}>
            <div className="run-card-main">
              <div className="run-copy">
                <strong>{run.jobTitle || url.hostname}</strong>
                {run.company && (
                  <small>
                    {run.company}
                    {run.platform ? ` · ${run.platform}` : ''}
                  </small>
                )}
                <p title={run.jobUrl}>{run.jobUrl}</p>
                {showDetails && (
                  <small>
                    Updated {formatDate(run.updatedAt)} · Submission permission{' '}
                    {run.autoSubmitAuthorized ? 'granted for this run' : 'not granted'}
                  </small>
                )}
                {showDetails && run.latestOutcome && (
                  <div className="recorded-outcome">
                    <span className={`outcome-badge ${run.latestOutcome.outcome}`}>
                      {run.latestOutcome.outcome.replaceAll('_', ' ')}
                    </span>
                    <small>
                      {readableReason(run.latestOutcome.reasonCode)} · confirmed{' '}
                      {formatDate(run.latestOutcome.recordedAt)}
                    </small>
                  </div>
                )}
              </div>
              <div className="run-card-actions">
                <span className={`run-state ${run.state}`}>{stateLabel(run.state)}</span>
                {showDetails && onToggleExplanations && (
                  <button
                    className="field-detail-button"
                    type="button"
                    aria-expanded={expanded}
                    onClick={() => onToggleExplanations(run.id)}
                  >
                    {loadingRunId === run.id
                      ? 'Loading…'
                      : expanded
                        ? 'Hide field decisions'
                        : 'View field decisions'}
                  </button>
                )}
              </div>
            </div>
            {showDetails && onRecordOutcome && (
              <details className="outcome-editor">
                <summary>
                  {run.latestOutcome ? 'Correct recorded outcome' : 'Record outcome'}
                </summary>
                <div className="outcome-editor-controls">
                  <label>
                    Outcome
                    <select
                      value={outcomeDraft}
                      onChange={(event) => {
                        const selected = event.target.value as OutcomeType;
                        setOutcomeDrafts((current) => ({ ...current, [run.id]: selected }));
                      }}
                    >
                      {outcomeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  {outcomeDraft === 'failed' && (
                    <label>
                      Reason
                      <select
                        value={reasonDraft}
                        onChange={(event) =>
                          setFailedReasonDrafts((current) => ({
                            ...current,
                            [run.id]: event.target.value as OutcomeReasonCode,
                          }))
                        }
                      >
                        {failedReasonOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={savingOutcomeRunId === run.id}
                    onClick={() => onRecordOutcome(run.id, outcomeDraft, reasonDraft)}
                  >
                    {savingOutcomeRunId === run.id ? 'Saving…' : 'Confirm outcome'}
                  </button>
                </div>
                <p>
                  This is an explicit user correction. Previous revisions remain in the local audit
                  history.
                </p>
                {outcomeErrorRunId === run.id && outcomeError && (
                  <p className="error" role="alert">
                    {outcomeError}
                  </p>
                )}
              </details>
            )}
            {expanded && (
              <section className="field-explanations" aria-live="polite">
                <div>
                  <h3>Field decisions</h3>
                  <p>Values are never shown here—only mapping and policy reasons.</p>
                </div>
                {explanationError ? (
                  <p className="error">{explanationError}</p>
                ) : runExplanations === undefined || loadingRunId === run.id ? (
                  <p className="field-explanation-empty">Loading saved decisions…</p>
                ) : runExplanations.length === 0 ? (
                  <p className="field-explanation-empty">
                    No field decisions have been recorded for this run yet.
                  </p>
                ) : (
                  <ul>
                    {runExplanations.map((explanation) => (
                      <li key={explanation.id}>
                        <div>
                          <strong>{fieldLabel(explanation)}</strong>
                          <p>{explanation.rationale}</p>
                        </div>
                        <span
                          className={`field-decision ${explanation.filled ? 'filled' : explanation.decision}`}
                        >
                          {explanation.filled
                            ? 'Filled'
                            : explanation.decision.replaceAll('_', ' ')}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </article>
        );
      })}
    </div>
  );
}

export function App(): React.JSX.Element {
  const [view, setView] = useState<View>('control');
  const [health, setHealth] = useState<HealthStatus>(emptyHealth);
  const [jobUrl, setJobUrl] = useState('');
  const [jobReview, setJobReview] = useState<JobPosting | null>(null);
  const [materialPlan, setMaterialPlan] = useState<ApplicationMaterialPlan | null>(null);
  const [autoSubmitAuthorized, setAutoSubmitAuthorized] = useState(false);
  const [runs, setRuns] = useState<ApplicationRun[]>([]);
  const [runsLoaded, setRunsLoaded] = useState(false);
  const [statistics, setStatistics] = useState<ApplicationStatistics | null>(null);
  const [profile, setProfile] = useState<CandidateProfileSnapshot | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileLoadError, setProfileLoadError] = useState<string>();
  const [error, setError] = useState<string>();
  const [reviewingJob, setReviewingJob] = useState(false);
  const [preparingMaterials, setPreparingMaterials] = useState(false);
  const [startingRun, setStartingRun] = useState(false);
  const [startingDemo, setStartingDemo] = useState(false);
  const [demoMessage, setDemoMessage] = useState<string>();
  const [expandedRunId, setExpandedRunId] = useState<string>();
  const [loadingExplanationRunId, setLoadingExplanationRunId] = useState<string>();
  const [fieldExplanations, setFieldExplanations] = useState<Record<string, FieldExplanation[]>>(
    {},
  );
  const [fieldExplanationError, setFieldExplanationError] = useState<string>();
  const [savingOutcomeRunId, setSavingOutcomeRunId] = useState<string>();
  const [outcomeErrorRunId, setOutcomeErrorRunId] = useState<string>();
  const [outcomeError, setOutcomeError] = useState<string>();
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>('all');
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>('all');

  useEffect(() => {
    let active = true;
    const refresh = async (): Promise<void> => {
      try {
        const next = await window.careerflow.getHealth();
        if (active) setHealth(next);
      } catch {
        if (active) setHealth((current) => ({ ...current, status: 'degraded' }));
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!health.databaseReady) return undefined;
    let active = true;
    const refresh = async (): Promise<void> => {
      try {
        const [savedRuns, savedStatistics] = await Promise.all([
          window.careerflow.listRuns(),
          window.careerflow.getApplicationStatistics(),
        ]);
        if (active) {
          setRuns(savedRuns);
          setStatistics(savedStatistics);
          setRunsLoaded(true);
        }
      } catch {
        // Startup can briefly race the local service. Retry without discarding durable data.
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [health.databaseReady]);

  useEffect(() => {
    if (!health.databaseReady) return undefined;
    let active = true;
    void window.careerflow
      .getProfile()
      .then((savedProfile) => {
        if (active) {
          setProfile(savedProfile);
          setProfileLoaded(true);
          setProfileLoadError(undefined);
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setProfileLoaded(true);
          setProfileLoadError(
            caught instanceof Error ? caught.message : 'The encrypted profile could not be loaded.',
          );
        }
      });
    return () => {
      active = false;
    };
  }, [health.databaseReady]);

  const readyCount = useMemo(
    () => [health.databaseReady, health.browserWorkerConnected].filter(Boolean).length,
    [health],
  );
  const activeRuns = useMemo(
    () => runs.filter((run) => !terminalStates.has(run.state) && run.latestOutcome === null),
    [runs],
  );
  const filteredRuns = useMemo(
    () =>
      runs.filter((run) => {
        const outcomeMatches =
          outcomeFilter === 'all' ||
          (outcomeFilter === 'pending'
            ? run.latestOutcome === null
            : run.latestOutcome?.outcome === outcomeFilter);
        const platformMatches = platformFilter === 'all' || run.platform === platformFilter;
        return outcomeMatches && platformMatches;
      }),
    [outcomeFilter, platformFilter, runs],
  );

  async function reviewJob(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(undefined);
    let normalized: URL;
    try {
      normalized = new URL(jobUrl);
      if (!['https:', 'http:'].includes(normalized.protocol)) throw new Error();
    } catch {
      setError('Paste a complete http or https job link.');
      return;
    }

    setReviewingJob(true);
    try {
      setJobReview(await window.careerflow.ingestJob({ url: normalized.toString() }));
      setMaterialPlan(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The job posting could not be reviewed.');
    } finally {
      setReviewingJob(false);
    }
  }

  async function prepareMaterials(): Promise<void> {
    if (!jobReview || !profile) return;
    setPreparingMaterials(true);
    setError(undefined);
    try {
      setMaterialPlan(
        await window.careerflow.prepareMaterials({
          jobId: jobReview.id,
          candidateProfileId: profile.profile.id,
          candidateProfileVersion: profile.profile.version,
        }),
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'Application materials could not be prepared.',
      );
    } finally {
      setPreparingMaterials(false);
    }
  }

  async function openApplication(): Promise<void> {
    if (!jobReview || !profile) return;
    setStartingRun(true);
    setError(undefined);
    try {
      const run = await window.careerflow.createRun({
        jobId: jobReview.id,
        jobUrl: jobReview.resolvedUrl,
        autoSubmitAuthorized,
      });
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setRunsLoaded(true);
      setJobUrl('');
      setJobReview(null);
      setMaterialPlan(null);
      setAutoSubmitAuthorized(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The run could not be created.');
    } finally {
      setStartingRun(false);
    }
  }

  async function startSyntheticDemo(): Promise<void> {
    setStartingDemo(true);
    setDemoMessage(undefined);
    setError(undefined);
    try {
      const run = await window.careerflow.startSyntheticDemo();
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setRunsLoaded(true);
      setDemoMessage(
        'Safe Autofill Lab opened. Ordinary verified fields will be highlighted in green; contact and legal fields remain for review.',
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'The safe autofill demo could not start.',
      );
    } finally {
      setStartingDemo(false);
    }
  }

  async function toggleFieldExplanations(runId: string): Promise<void> {
    if (expandedRunId === runId) {
      setExpandedRunId(undefined);
      setFieldExplanationError(undefined);
      return;
    }
    setExpandedRunId(runId);
    setLoadingExplanationRunId(runId);
    setFieldExplanationError(undefined);
    try {
      const saved = await window.careerflow.listFieldExplanations({ runId });
      setFieldExplanations((current) => ({ ...current, [runId]: saved }));
    } catch (caught) {
      setFieldExplanationError(
        caught instanceof Error ? caught.message : 'Field decisions could not be loaded.',
      );
    } finally {
      setLoadingExplanationRunId(undefined);
    }
  }

  async function recordOutcome(
    runId: string,
    outcome: OutcomeType,
    reasonCode: OutcomeReasonCode,
  ): Promise<void> {
    setSavingOutcomeRunId(runId);
    setOutcomeErrorRunId(undefined);
    setOutcomeError(undefined);
    try {
      await window.careerflow.recordApplicationOutcome({
        runId,
        outcome: { outcome, reasonCode, confirmedByUser: true },
      });
      const [savedRuns, savedStatistics] = await Promise.all([
        window.careerflow.listRuns(),
        window.careerflow.getApplicationStatistics(),
      ]);
      setRuns(savedRuns);
      setStatistics(savedStatistics);
    } catch (caught) {
      setOutcomeErrorRunId(runId);
      setOutcomeError(
        caught instanceof Error ? caught.message : 'The application outcome could not be saved.',
      );
    } finally {
      setSavingOutcomeRunId(undefined);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">CF</span>
          <span>CareerFlow</span>
        </div>
        <nav aria-label="Primary navigation">
          <button
            className={`nav-item ${view === 'control' ? 'active' : ''}`}
            aria-current={view === 'control' ? 'page' : undefined}
            onClick={() => setView('control')}
          >
            <span>⌂</span>Control center
          </button>
          <button
            className={`nav-item ${view === 'applications' ? 'active' : ''}`}
            aria-current={view === 'applications' ? 'page' : undefined}
            onClick={() => setView('applications')}
          >
            <span>◫</span>Applications
            {runs.length > 0 && <small className="nav-count">{runs.length}</small>}
          </button>
          <button
            className={`nav-item ${view === 'profile' ? 'active' : ''}`}
            aria-current={view === 'profile' ? 'page' : undefined}
            onClick={() => setView('profile')}
          >
            <span>◇</span>Profile & evidence
            {profile && <small className="nav-check">✓</small>}
          </button>
          <button className="nav-item" disabled title="Interventions are not implemented yet">
            <span>!</span>Interventions
          </button>
        </nav>
        <div className="sidebar-footer">
          <button className="nav-item" disabled title="Settings are not implemented yet">
            <span>⚙</span>Settings
          </button>
          <p>Local data only</p>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">
              {view === 'control'
                ? 'CONTROL CENTER'
                : view === 'applications'
                  ? 'APPLICATIONS'
                  : 'PROFILE & EVIDENCE'}
            </p>
            <h1>
              {view === 'control'
                ? 'Good applications, without the busywork.'
                : view === 'applications'
                  ? 'Your application activity.'
                  : 'Your verified application facts.'}
            </h1>
          </div>
          <div className={`status-pill ${health.status}`}>
            <span className="status-dot" />
            {health.status === 'ready'
              ? 'Ready'
              : health.status === 'degraded'
                ? 'Needs attention'
                : 'Starting'}
          </div>
        </header>

        {view === 'control' ? (
          <>
            <section className="hero-card">
              <div className="hero-copy">
                <span className="step-label">NEW APPLICATION</span>
                <h2>Where would you like to apply?</h2>
                <p>
                  Paste a public job link. CareerFlow extracts deterministic metadata and
                  requirements for your review before opening its visible browser.
                </p>
              </div>
              <form onSubmit={(event) => void reviewJob(event)}>
                <label htmlFor="job-url">Job posting link</label>
                <div className="url-row">
                  <input
                    id="job-url"
                    type="url"
                    required
                    value={jobUrl}
                    onChange={(event) => {
                      setJobUrl(event.target.value);
                      setJobReview(null);
                      setMaterialPlan(null);
                    }}
                    placeholder="https://company.com/jobs/software-engineer"
                    autoComplete="url"
                  />
                  <button type="submit" disabled={reviewingJob || health.status !== 'ready'}>
                    {reviewingJob ? 'Extracting…' : 'Review role'}
                  </button>
                </div>
                {profileLoaded && !profile && (
                  <button
                    className="profile-required"
                    type="button"
                    onClick={() => setView('profile')}
                  >
                    Complete your encrypted profile before creating a new application run.
                  </button>
                )}
                <label className="authorization">
                  <input
                    type="checkbox"
                    checked={autoSubmitAuthorized}
                    onChange={(event) => setAutoSubmitAuthorized(event.target.checked)}
                  />
                  <span>
                    <strong>Allow submission for this run</strong>
                    <small>
                      This permission is stored, but automated form filling and submission are not
                      implemented in this foundation build.
                    </small>
                  </span>
                </label>
                {error && (
                  <p className="error" role="alert">
                    {error}
                  </p>
                )}
              </form>
            </section>

            {jobReview && (
              <section className="panel job-review-panel" aria-live="polite">
                <div className="job-review-heading">
                  <div>
                    <p className="eyebrow">EXTRACTED JOB · VERSION {jobReview.version}</p>
                    <h2>{jobReview.title || 'Title needs review'}</h2>
                    <p className="job-review-meta">
                      {jobReview.company || 'Company needs review'}
                      {jobReview.location ? ` · ${jobReview.location}` : ''}
                    </p>
                  </div>
                  <span className={`job-status ${jobReview.status}`}>
                    {jobReview.status === 'complete' ? 'Ready for review' : 'Check details'}
                  </span>
                </div>
                <div className="job-review-summary">
                  <div>
                    <span>Platform</span>
                    <strong>{jobReview.platform.platform}</strong>
                  </div>
                  <div>
                    <span>Detection confidence</span>
                    <strong>{Math.round(jobReview.platform.confidence * 100)}%</strong>
                  </div>
                  <div>
                    <span>Requirements found</span>
                    <strong>{jobReview.requirements.length}</strong>
                  </div>
                </div>
                {jobReview.warnings.length > 0 && (
                  <div className="job-warnings" role="status">
                    {jobReview.warnings.map((warning) => (
                      <p key={warning}>! {warning}</p>
                    ))}
                  </div>
                )}
                <div className="requirements-list">
                  <h3>Extracted requirements</h3>
                  {jobReview.requirements.length ? (
                    <ul>
                      {jobReview.requirements.map((requirement) => (
                        <li key={requirement.id}>
                          <span>{requirement.text}</span>
                          <small>{requirement.required ? 'Required' : 'Preferred'}</small>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>
                      No deterministic requirements were found. Review the visible posting before
                      continuing.
                    </p>
                  )}
                </div>
                {materialPlan && (
                  <section className="material-plan" aria-live="polite">
                    <div className="material-plan-heading">
                      <div>
                        <p className="eyebrow">GROUNDED MATERIAL PLAN</p>
                        <h3>{materialPlan.resumeDraft.title}</h3>
                      </div>
                      <span className={`material-status ${materialPlan.status}`}>
                        {materialPlan.status === 'needs_review'
                          ? 'Review required'
                          : 'Verify evidence first'}
                      </span>
                    </div>
                    <div className="material-summary">
                      <div>
                        <strong>{Math.round(materialPlan.coverageRatio * 100)}%</strong>
                        <span>weighted coverage</span>
                      </div>
                      <div>
                        <strong>{materialPlan.supportedCount}</strong>
                        <span>supported</span>
                      </div>
                      <div>
                        <strong>{materialPlan.partialCount}</strong>
                        <span>partial</span>
                      </div>
                      <div>
                        <strong>{materialPlan.unsupportedCount}</strong>
                        <span>gaps</span>
                      </div>
                    </div>
                    <p className="material-boundary">
                      Deterministic local matching · 0 AI tokens · only verified evidence is used.
                    </p>
                    <div className="mapping-list">
                      {materialPlan.mappings.map((mapping) => (
                        <article className="mapping-item" key={mapping.requirementId}>
                          <div className="mapping-title">
                            <strong>{mapping.requirementText}</strong>
                            <span className={`support-badge ${mapping.support}`}>
                              {mapping.support}
                            </span>
                          </div>
                          <p>{mapping.explanation}</p>
                          {mapping.matches.length > 0 && (
                            <ul>
                              {mapping.matches.map((match) => (
                                <li key={match.evidenceId}>
                                  <span>{match.statement}</span>
                                  <small>{Math.round(match.score * 100)}% lexical match</small>
                                </li>
                              ))}
                            </ul>
                          )}
                        </article>
                      ))}
                    </div>
                    <div className="grounded-draft">
                      <h4>Exact evidence selected for the résumé draft</h4>
                      {materialPlan.resumeDraft.entries.length ? (
                        <ul>
                          {materialPlan.resumeDraft.entries.map((entry) => (
                            <li key={entry.evidenceId}>
                              <span>{entry.statement}</span>
                              <small>
                                {entry.sourceSpan?.page
                                  ? `Page ${entry.sourceSpan.page}`
                                  : 'Verified profile'}
                                {entry.sourceSpan?.section ? ` · ${entry.sourceSpan.section}` : ''}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>
                          No supported evidence is ready. Verify relevant résumé statements in
                          Profile & evidence, then prepare again.
                        </p>
                      )}
                    </div>
                  </section>
                )}
                <div className="job-review-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      setJobReview(null);
                      setMaterialPlan(null);
                    }}
                  >
                    Edit URL
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={preparingMaterials || !profile || health.status !== 'ready'}
                    onClick={() => void prepareMaterials()}
                  >
                    {preparingMaterials
                      ? 'Matching evidence…'
                      : materialPlan
                        ? 'Rebuild grounded draft'
                        : 'Prepare grounded draft'}
                  </button>
                  <button
                    className="primary-button"
                    type="button"
                    disabled={
                      startingRun ||
                      !profile ||
                      !materialPlan ||
                      materialPlan.status === 'needs_evidence' ||
                      health.status !== 'ready'
                    }
                    title={
                      !profile
                        ? 'Create your verified profile before opening the application'
                        : !materialPlan
                          ? 'Prepare and review a grounded draft before opening the application'
                          : materialPlan.status === 'needs_evidence'
                            ? 'Verify relevant résumé evidence before continuing'
                            : undefined
                    }
                    onClick={() => void openApplication()}
                  >
                    {startingRun ? 'Opening browser…' : 'Confirm and open application'}
                  </button>
                </div>
                {!profile && (
                  <button
                    className="profile-required"
                    type="button"
                    onClick={() => setView('profile')}
                  >
                    Create your encrypted profile before continuing with this role.
                  </button>
                )}
              </section>
            )}

            <section className="content-grid">
              <div className="panel queue-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">APPLICATION QUEUE</p>
                    <h2>{activeRuns.length ? `${activeRuns.length} active` : 'All clear'}</h2>
                  </div>
                  <span className="count">{activeRuns.length}</span>
                </div>
                {!runsLoaded ? (
                  <div className="empty-state">
                    <div className="empty-icon">…</div>
                    <h3>Loading saved applications.</h3>
                  </div>
                ) : activeRuns.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">↗</div>
                    <h3>Your next role starts above.</h3>
                    <p>Add a job link to create a supervised application run.</p>
                  </div>
                ) : (
                  <RunList runs={activeRuns} />
                )}
              </div>

              <div className="panel system-panel">
                <p className="eyebrow">LOCAL SYSTEM</p>
                <h2>{readyCount}/2 services ready</h2>
                <div className="service-row">
                  <span className={health.databaseReady ? 'ok' : ''}>Database</span>
                  <small>{health.databaseReady ? 'Connected' : 'Starting'}</small>
                </div>
                <div className="service-row">
                  <span className={health.browserWorkerConnected ? 'ok' : ''}>Browser worker</span>
                  <small>{health.browserWorkerConnected ? 'Connected' : 'Starting'}</small>
                </div>
                <div className="privacy-note">
                  <span>⌾</span>
                  <p>
                    <strong>Your data stays on this Mac.</strong>
                    <br />
                    External diagnostics are off by default.
                  </p>
                </div>
                <div className="autofill-lab">
                  <p className="eyebrow">SAFE AUTOFILL LAB</p>
                  <p>
                    Open an app-owned test form, scan its fields, and fill only ordinary verified
                    profile values. Contact and legal answers stay blank for human review. The lab
                    has no submit action and sends nothing to an employer.
                  </p>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={startingDemo || !profile || health.status !== 'ready'}
                    title={
                      !profile ? 'Create your verified profile before testing autofill' : undefined
                    }
                    onClick={() => void startSyntheticDemo()}
                  >
                    {startingDemo ? 'Opening safe lab…' : 'Test profile autofill'}
                  </button>
                  {demoMessage && <p className="success">{demoMessage}</p>}
                </div>
              </div>
            </section>
          </>
        ) : view === 'applications' ? (
          <section className="panel applications-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">SAVED LOCALLY</p>
                <h2>
                  {runs.length === 1 ? '1 application run' : `${runs.length} application runs`}
                </h2>
              </div>
              <span className="count">{runs.length}</span>
            </div>
            <p className="panel-intro">
              This history is restored from SQLite whenever CareerFlow starts and includes the
              normalized role, company, platform, workflow state, submission permission, and any
              outcome you explicitly confirm. Statistics are rebuilt from these durable records.
            </p>
            {statistics && (
              <section className="statistics-grid" aria-label="Application statistics">
                <div>
                  <strong>{statistics.totalRuns}</strong>
                  <span>tracked</span>
                </div>
                <div>
                  <strong>{statistics.pendingRuns}</strong>
                  <span>pending outcome</span>
                </div>
                <div>
                  <strong>{statistics.submitted}</strong>
                  <span>submitted</span>
                </div>
                <div>
                  <strong>{Math.round(statistics.resolutionRate * 100)}%</strong>
                  <span>outcomes recorded</span>
                </div>
              </section>
            )}
            <div className="application-filters" aria-label="Application filters">
              <label>
                Outcome
                <select
                  value={outcomeFilter}
                  onChange={(event) => setOutcomeFilter(event.target.value as OutcomeFilter)}
                >
                  <option value="all">All outcomes</option>
                  <option value="pending">Pending outcome</option>
                  {outcomeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Platform
                <select
                  value={platformFilter}
                  onChange={(event) => setPlatformFilter(event.target.value as PlatformFilter)}
                >
                  <option value="all">All platforms</option>
                  <option value="synthetic">Synthetic lab</option>
                  <option value="workday">Workday</option>
                  <option value="greenhouse">Greenhouse</option>
                  <option value="lever">Lever</option>
                  <option value="unknown">Other / unknown</option>
                </select>
              </label>
              <span>
                Showing {filteredRuns.length} of {runs.length}
              </span>
            </div>
            {!runsLoaded ? (
              <div className="empty-state">
                <div className="empty-icon">…</div>
                <h3>Loading saved applications.</h3>
              </div>
            ) : runs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">◫</div>
                <h3>No saved applications yet.</h3>
                <p>Open a job from the control center to create your first durable run.</p>
              </div>
            ) : filteredRuns.length === 0 ? (
              <div className="empty-state filtered-empty">
                <div className="empty-icon">⌕</div>
                <h3>No applications match these filters.</h3>
                <p>Choose a different outcome or platform.</p>
              </div>
            ) : (
              <RunList
                runs={filteredRuns}
                showDetails
                expandedRunId={expandedRunId}
                explanations={fieldExplanations}
                loadingRunId={loadingExplanationRunId}
                explanationError={fieldExplanationError}
                onToggleExplanations={(runId) => void toggleFieldExplanations(runId)}
                savingOutcomeRunId={savingOutcomeRunId}
                outcomeErrorRunId={outcomeErrorRunId}
                outcomeError={outcomeError}
                onRecordOutcome={(runId, outcome, reasonCode) =>
                  void recordOutcome(runId, outcome, reasonCode)
                }
              />
            )}
          </section>
        ) : (
          <ProfileView
            snapshot={profile}
            loading={!profileLoaded}
            loadError={profileLoadError}
            onSaved={(savedProfile) => {
              setProfile(savedProfile);
              setMaterialPlan(null);
              setProfileLoadError(undefined);
            }}
          />
        )}
      </main>
    </div>
  );
}
