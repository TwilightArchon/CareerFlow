import { FormEvent, useEffect, useMemo, useState } from 'react';

import type {
  ApplicationRun,
  CandidateProfileSnapshot,
  HealthStatus,
  WorkflowState,
} from '@careerflow/contracts';

import { ProfileView } from './ProfileView';

type View = 'control' | 'applications' | 'profile';

const emptyHealth: HealthStatus = {
  status: 'starting',
  service: 'careerflow-agent',
  version: '0.1.5',
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

function RunList({ runs, showDetails = false }: { runs: ApplicationRun[]; showDetails?: boolean }) {
  return (
    <div className="run-list">
      {runs.map((run) => {
        const url = new URL(run.jobUrl);
        return (
          <article className="run-card" key={run.id}>
            <div className="run-copy">
              <strong>{url.hostname}</strong>
              <p title={run.jobUrl}>{run.jobUrl}</p>
              {showDetails && (
                <small>
                  Updated {formatDate(run.updatedAt)} · Submission permission{' '}
                  {run.autoSubmitAuthorized ? 'granted for this run' : 'not granted'}
                </small>
              )}
            </div>
            <span className={`run-state ${run.state}`}>{stateLabel(run.state)}</span>
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
  const [autoSubmitAuthorized, setAutoSubmitAuthorized] = useState(false);
  const [runs, setRuns] = useState<ApplicationRun[]>([]);
  const [runsLoaded, setRunsLoaded] = useState(false);
  const [profile, setProfile] = useState<CandidateProfileSnapshot | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileLoadError, setProfileLoadError] = useState<string>();
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

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
        const savedRuns = await window.careerflow.listRuns();
        if (active) {
          setRuns(savedRuns);
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
  const activeRuns = useMemo(() => runs.filter((run) => !terminalStates.has(run.state)), [runs]);

  async function submit(event: FormEvent): Promise<void> {
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

    setSubmitting(true);
    try {
      const run = await window.careerflow.createRun({
        jobUrl: normalized.toString(),
        autoSubmitAuthorized,
      });
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setRunsLoaded(true);
      setJobUrl('');
      setAutoSubmitAuthorized(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The run could not be created.');
    } finally {
      setSubmitting(false);
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
                  Paste a public job link. This foundation build records the run and opens the
                  posting in CareerFlow&apos;s visible browser.
                </p>
              </div>
              <form onSubmit={(event) => void submit(event)}>
                <label htmlFor="job-url">Job posting link</label>
                <div className="url-row">
                  <input
                    id="job-url"
                    type="url"
                    value={jobUrl}
                    onChange={(event) => setJobUrl(event.target.value)}
                    placeholder="https://company.com/jobs/software-engineer"
                    autoComplete="url"
                  />
                  <button
                    type="submit"
                    disabled={submitting || health.status !== 'ready' || !profile}
                    title={
                      !profile ? 'Complete your profile before opening an application' : undefined
                    }
                  >
                    {submitting ? 'Opening…' : 'Open application'}
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
              This history is restored from SQLite whenever CareerFlow starts. Job titles,
              companies, outcomes, and statistics will appear after job extraction and outcome
              tracking are implemented.
            </p>
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
            ) : (
              <RunList runs={runs} showDetails />
            )}
          </section>
        ) : (
          <ProfileView
            snapshot={profile}
            loading={!profileLoaded}
            loadError={profileLoadError}
            onSaved={(savedProfile) => {
              setProfile(savedProfile);
              setProfileLoadError(undefined);
            }}
          />
        )}
      </main>
    </div>
  );
}
