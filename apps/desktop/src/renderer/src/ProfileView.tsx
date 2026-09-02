import { FormEvent, useEffect, useState } from 'react';

import type { CandidateProfileInput, CandidateProfileSnapshot } from '@careerflow/contracts';

const emptyProfile: CandidateProfileInput = {
  firstName: '',
  lastName: '',
  preferredName: '',
  email: '',
  phone: '',
  city: '',
  region: '',
  country: 'United States',
  postalCode: '',
  linkedinUrl: null,
  githubUrl: null,
  school: '',
  degree: '',
  fieldOfStudy: '',
  graduationYear: null,
  workAuthorization: 'unspecified',
  requiresSponsorship: null,
};

function fromSnapshot(snapshot: CandidateProfileSnapshot | null): CandidateProfileInput {
  if (!snapshot) return emptyProfile;
  const values = new Map(snapshot.profile.facts.map((fact) => [fact.canonicalPath, fact.value]));
  const value = (path: string): string => values.get(path) ?? '';
  const authorization = value('work_authorization.status');
  const sponsorship = value('work_authorization.requires_sponsorship').toLowerCase();
  const graduationYear = Number(value('education.0.graduation_year'));
  return {
    firstName: value('identity.first_name'),
    lastName: value('identity.last_name'),
    preferredName: value('identity.preferred_name'),
    email: value('contact.email'),
    phone: value('contact.phone'),
    city: value('address.city'),
    region: value('address.region'),
    country: value('address.country') || 'United States',
    postalCode: value('address.postal_code'),
    linkedinUrl: value('links.linkedin') || null,
    githubUrl: value('links.github') || null,
    school: value('education.0.school'),
    degree: value('education.0.degree'),
    fieldOfStudy: value('education.0.field_of_study'),
    graduationYear: Number.isInteger(graduationYear) && graduationYear > 0 ? graduationYear : null,
    workAuthorization:
      authorization === 'authorized' ||
      authorization === 'requires_sponsorship' ||
      authorization === 'not_authorized'
        ? authorization
        : 'unspecified',
    requiresSponsorship: sponsorship === 'true' ? true : sponsorship === 'false' ? false : null,
  };
}

export function ProfileView({
  snapshot,
  loading,
  loadError,
  onSaved,
}: {
  snapshot: CandidateProfileSnapshot | null;
  loading: boolean;
  loadError: string | undefined;
  onSaved: (snapshot: CandidateProfileSnapshot) => void;
}): React.JSX.Element {
  const [profile, setProfile] = useState<CandidateProfileInput>(() => fromSnapshot(snapshot));
  const [saving, setSaving] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [reviewingEvidenceId, setReviewingEvidenceId] = useState<string>();
  const [importMessage, setImportMessage] = useState<string>();
  const [error, setError] = useState<string>();
  const [saved, setSaved] = useState(false);

  useEffect(() => setProfile(fromSnapshot(snapshot)), [snapshot]);

  const update = <Key extends keyof CandidateProfileInput>(
    key: Key,
    value: CandidateProfileInput[Key],
  ): void => setProfile((current) => ({ ...current, [key]: value }));

  async function save(event: FormEvent): Promise<void> {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(undefined);
    try {
      const next = await window.careerflow.saveProfile({
        profile,
        expectedVersion: snapshot?.profile.version ?? null,
      });
      onSaved(next);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'The encrypted profile could not be saved.',
      );
    } finally {
      setSaving(false);
    }
  }

  async function importResume(): Promise<void> {
    if (!snapshot || !resumeFile) return;
    setImporting(true);
    setImportMessage(undefined);
    setError(undefined);
    try {
      const extension = resumeFile.name.toLowerCase().split('.').pop();
      const mediaType =
        resumeFile.type ||
        (extension === 'pdf'
          ? 'application/pdf'
          : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      const result = await window.careerflow.importResume({
        filename: resumeFile.name,
        mediaType,
        bytes: new Uint8Array(await resumeFile.arrayBuffer()),
        expectedVersion: snapshot.profile.version,
      });
      onSaved(result.snapshot);
      setResumeFile(null);
      setImportMessage(
        result.document.status === 'parsed'
          ? `${result.document.extractedEvidenceCount} evidence items extracted for review.`
          : result.document.status === 'needs_ocr'
            ? 'The encrypted PDF was retained, but it has no selectable text. OCR is not implemented yet.'
            : `The encrypted document was retained, but parsing failed (${result.document.parseErrorCode ?? 'unknown error'}).`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The résumé could not be imported.');
    } finally {
      setImporting(false);
    }
  }

  async function setEvidenceVerified(evidenceId: string, verified: boolean): Promise<void> {
    if (!snapshot) return;
    setReviewingEvidenceId(evidenceId);
    setError(undefined);
    try {
      const next = await window.careerflow.setEvidenceVerification({
        evidenceId,
        verified,
        expectedVersion: snapshot.profile.version,
      });
      onSaved(next);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'The evidence review could not be saved.',
      );
    } finally {
      setReviewingEvidenceId(undefined);
    }
  }

  if (loading) {
    return (
      <section className="panel profile-panel">
        <div className="empty-state">
          <div className="empty-icon">…</div>
          <h3>Loading your encrypted profile.</h3>
        </div>
      </section>
    );
  }

  return (
    <form className="profile-form" onSubmit={(event) => void save(event)}>
      <section className="panel profile-summary">
        <div>
          <p className="eyebrow">VERIFIED PROFILE</p>
          <h2>{snapshot ? `Version ${snapshot.profile.version}` : 'Complete your onboarding'}</h2>
          <p className="panel-intro">
            Saving creates a new immutable profile version. Entered fields become verified,
            user-sourced facts; sensitive values are encrypted before SQLite storage.
          </p>
        </div>
        <div className="vault-badge">⌾ Keychain protected</div>
      </section>

      {loadError && (
        <section className="profile-load-error" role="alert">
          {loadError} Profile operations will remain unavailable until Keychain access is restored.
        </section>
      )}

      <section className="panel profile-panel resume-import-panel">
        <div className="profile-section-heading">
          <p className="eyebrow">RÉSUMÉ EVIDENCE</p>
          <h2>Import a local PDF or DOCX</h2>
          <p>
            CareerFlow encrypts the original file and extracts selectable text locally. Imported
            statements stay unverified until you review them below.
          </p>
        </div>
        <div className="resume-import-row">
          <label className="file-picker">
            <span>{resumeFile?.name ?? 'Choose résumé'}</span>
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)}
              disabled={!snapshot || importing}
            />
          </label>
          <button
            type="button"
            className="secondary-button"
            disabled={!snapshot || !resumeFile || importing}
            onClick={() => void importResume()}
          >
            {importing ? 'Encrypting and extracting…' : 'Import résumé'}
          </button>
        </div>
        {!snapshot && <p className="form-hint">Create your encrypted profile before importing.</p>}
        {importMessage && <p className="success">{importMessage}</p>}
        {snapshot && snapshot.profile.sourceDocuments.length > 0 && (
          <div className="source-document-list">
            {snapshot.profile.sourceDocuments.map((document) => (
              <article className="source-document" key={document.id}>
                <div>
                  <strong>{document.filename}</strong>
                  <span>
                    {document.extractedEvidenceCount} extracted · profile version{' '}
                    {snapshot.profile.version}
                  </span>
                </div>
                <span className={`document-status status-${document.status}`}>
                  {document.status === 'parsed'
                    ? 'Parsed'
                    : document.status === 'needs_ocr'
                      ? 'OCR needed'
                      : 'Parse failed'}
                </span>
              </article>
            ))}
          </div>
        )}
        {snapshot && snapshot.profile.evidence.some((item) => item.sourceDocumentId !== null) && (
          <div className="evidence-review-list">
            <div className="evidence-review-heading">
              <strong>Extracted evidence</strong>
              <span>
                {
                  snapshot.profile.evidence.filter(
                    (item) => item.sourceDocumentId !== null && item.verified,
                  ).length
                }{' '}
                verified
              </span>
            </div>
            {snapshot.profile.evidence
              .filter((item) => item.sourceDocumentId !== null)
              .map((item) => (
                <article className="evidence-item" key={item.id}>
                  <div>
                    <p>{item.statement}</p>
                    <span>
                      {item.sourceSpan?.page ? `Page ${item.sourceSpan.page}` : 'DOCX'}
                      {item.sourceSpan?.section ? ` · ${item.sourceSpan.section}` : ''}
                    </span>
                  </div>
                  <button
                    type="button"
                    className={item.verified ? 'verified-button' : 'review-button'}
                    disabled={reviewingEvidenceId === item.id}
                    onClick={() => void setEvidenceVerified(item.id, !item.verified)}
                  >
                    {reviewingEvidenceId === item.id
                      ? 'Saving…'
                      : item.verified
                        ? 'Verified ✓'
                        : 'Verify'}
                  </button>
                </article>
              ))}
          </div>
        )}
      </section>

      <section className="panel profile-panel">
        <div className="profile-section-heading">
          <p className="eyebrow">IDENTITY & CONTACT</p>
          <h2>How applications should identify you</h2>
        </div>
        <div className="profile-grid">
          <label>
            First name
            <input
              required
              value={profile.firstName}
              onChange={(event) => update('firstName', event.target.value)}
              autoComplete="given-name"
            />
          </label>
          <label>
            Last name
            <input
              required
              value={profile.lastName}
              onChange={(event) => update('lastName', event.target.value)}
              autoComplete="family-name"
            />
          </label>
          <label>
            Preferred name
            <input
              value={profile.preferredName}
              onChange={(event) => update('preferredName', event.target.value)}
              autoComplete="nickname"
            />
          </label>
          <label>
            Email
            <input
              required
              type="email"
              value={profile.email}
              onChange={(event) => update('email', event.target.value)}
              autoComplete="email"
            />
          </label>
          <label>
            Phone
            <input
              type="tel"
              value={profile.phone}
              onChange={(event) => update('phone', event.target.value)}
              autoComplete="tel"
            />
          </label>
        </div>
      </section>

      <section className="panel profile-panel">
        <div className="profile-section-heading">
          <p className="eyebrow">LOCATION & LINKS</p>
          <h2>Reusable application details</h2>
        </div>
        <div className="profile-grid">
          <label>
            City
            <input
              value={profile.city}
              onChange={(event) => update('city', event.target.value)}
              autoComplete="address-level2"
            />
          </label>
          <label>
            State or region
            <input
              value={profile.region}
              onChange={(event) => update('region', event.target.value)}
              autoComplete="address-level1"
            />
          </label>
          <label>
            Postal code
            <input
              value={profile.postalCode}
              onChange={(event) => update('postalCode', event.target.value)}
              autoComplete="postal-code"
            />
          </label>
          <label>
            Country
            <input
              value={profile.country}
              onChange={(event) => update('country', event.target.value)}
              autoComplete="country-name"
            />
          </label>
          <label className="wide-field">
            LinkedIn URL
            <input
              type="url"
              value={profile.linkedinUrl ?? ''}
              onChange={(event) => update('linkedinUrl', event.target.value || null)}
              placeholder="https://www.linkedin.com/in/your-name"
            />
          </label>
          <label className="wide-field">
            GitHub URL
            <input
              type="url"
              value={profile.githubUrl ?? ''}
              onChange={(event) => update('githubUrl', event.target.value || null)}
              placeholder="https://github.com/your-name"
            />
          </label>
        </div>
      </section>

      <section className="panel profile-panel">
        <div className="profile-section-heading">
          <p className="eyebrow">EDUCATION</p>
          <h2>Your current or most relevant program</h2>
        </div>
        <div className="profile-grid">
          <label className="wide-field">
            School
            <input
              value={profile.school}
              onChange={(event) => update('school', event.target.value)}
            />
          </label>
          <label>
            Degree
            <input
              value={profile.degree}
              onChange={(event) => update('degree', event.target.value)}
            />
          </label>
          <label>
            Field of study
            <input
              value={profile.fieldOfStudy}
              onChange={(event) => update('fieldOfStudy', event.target.value)}
            />
          </label>
          <label>
            Graduation year
            <input
              type="number"
              min="1950"
              max="2100"
              value={profile.graduationYear ?? ''}
              onChange={(event) =>
                update('graduationYear', event.target.value ? Number(event.target.value) : null)
              }
            />
          </label>
        </div>
      </section>

      <section className="panel profile-panel legal-section">
        <div className="profile-section-heading">
          <p className="eyebrow">WORK AUTHORIZATION</p>
          <h2>Optional legal answers</h2>
          <p>
            CareerFlow will not infer these answers. Leave them unspecified if you do not want them
            reused.
          </p>
        </div>
        <div className="profile-grid">
          <label>
            United States work authorization
            <select
              value={profile.workAuthorization}
              onChange={(event) =>
                update(
                  'workAuthorization',
                  event.target.value as CandidateProfileInput['workAuthorization'],
                )
              }
            >
              <option value="unspecified">Unspecified</option>
              <option value="authorized">Authorized to work</option>
              <option value="requires_sponsorship">Authorization requires sponsorship</option>
              <option value="not_authorized">Not currently authorized</option>
            </select>
          </label>
          <label>
            Will you require sponsorship?
            <select
              value={
                profile.requiresSponsorship === null
                  ? 'unspecified'
                  : profile.requiresSponsorship
                    ? 'yes'
                    : 'no'
              }
              onChange={(event) =>
                update(
                  'requiresSponsorship',
                  event.target.value === 'unspecified' ? null : event.target.value === 'yes',
                )
              }
            >
              <option value="unspecified">Unspecified</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>
        </div>
      </section>

      <section className="profile-actions">
        <div>
          {error && <p className="error">{error}</p>}
          {saved && <p className="success">Encrypted profile saved as a new version.</p>}
        </div>
        <button className="primary-button" type="submit" disabled={saving}>
          {saving ? 'Encrypting…' : snapshot ? 'Save new version' : 'Create encrypted profile'}
        </button>
      </section>
    </form>
  );
}
