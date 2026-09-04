import { describe, expect, it } from 'vitest';

import type { CandidateProfileInput, ResumeFieldSuggestion } from '@careerflow/contracts';

import { applyResumeSuggestions } from '../src/renderer/src/ProfileView';
import { defaultOutcomeReason } from '../src/renderer/src/App';
import { RestartBudget } from '../src/main/process-restart';

const existingProfile: CandidateProfileInput = {
  firstName: 'Existing',
  lastName: 'Candidate',
  preferredName: '',
  email: 'existing@example.com',
  phone: '',
  city: '',
  region: '',
  country: 'United States',
  postalCode: '',
  linkedinUrl: null,
  githubUrl: 'https://github.com/already-verified',
  school: '',
  degree: '',
  fieldOfStudy: '',
  graduationYear: null,
  workAuthorization: 'unspecified',
  requiresSponsorship: null,
};

const linkSuggestions: ResumeFieldSuggestion[] = [
  {
    canonicalPath: 'links.linkedin',
    value: 'https://www.linkedin.com/in/synthetic-candidate',
    confidence: 1,
    sourceSpan: { page: 1, section: 'page:1 · hyperlink', start: 10, end: 20 },
  },
  {
    canonicalPath: 'links.github',
    value: 'https://github.com/synthetic-candidate',
    confidence: 1,
    sourceSpan: { page: 1, section: 'page:1 · hyperlink', start: 21, end: 31 },
  },
];

describe('desktop foundation', () => {
  it('has a stable application identity', () => {
    expect('dev.careerflow.desktop').toMatch(/^dev\.careerflow\./);
  });

  it('keeps the safe autofill lab separate from employer submission', () => {
    expect('Test profile autofill').not.toMatch(/submit/i);
  });

  it('applies resume suggestions only to empty profile fields', () => {
    const result = applyResumeSuggestions(existingProfile, linkSuggestions);

    expect(result.appliedCount).toBe(1);
    expect(result.profile.linkedinUrl).toBe('https://www.linkedin.com/in/synthetic-candidate');
    expect(result.profile.githubUrl).toBe('https://github.com/already-verified');
    expect(existingProfile.linkedinUrl).toBeNull();
  });

  it('uses a stable reason code for each explicit outcome', () => {
    expect(defaultOutcomeReason('submitted')).toBe('user_confirmed_submitted');
    expect(defaultOutcomeReason('failed')).toBe('validation_failed');
    expect(defaultOutcomeReason('outcome_uncertain')).toBe('confirmation_missing');
  });

  it('bounds browser-worker restarts and resets after recovery', () => {
    const budget = new RestartBudget([10, 20]);

    expect(budget.claim()).toEqual({ attempt: 1, delayMs: 10 });
    expect(budget.claim()).toEqual({ attempt: 2, delayMs: 20 });
    expect(budget.claim()).toBeNull();
    budget.reset();
    expect(budget.claim()).toEqual({ attempt: 1, delayMs: 10 });
  });
});
