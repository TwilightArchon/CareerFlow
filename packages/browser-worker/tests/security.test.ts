import { describe, expect, it } from 'vitest';

import { rejectObviousPrivateTarget, requireLoopbackWebSocketUrl } from '../src/security';
import { classifySensitivity } from '../src/runtime';
import { SYNTHETIC_FORM_HTML, SYNTHETIC_FORM_URL } from '../src/synthetic-form';

describe('browser worker local endpoint validation', () => {
  it('allows loopback', () => {
    expect(requireLoopbackWebSocketUrl('ws://127.0.0.1:4321/v1/browser/ws').port).toBe('4321');
  });

  it('rejects remote and encrypted endpoints', () => {
    expect(() => requireLoopbackWebSocketUrl('wss://example.com/ws')).toThrow();
    expect(() => requireLoopbackWebSocketUrl('ws://example.com/ws')).toThrow();
  });

  it('blocks obvious private navigation targets', () => {
    expect(() => rejectObviousPrivateTarget('http://127.0.0.1/admin')).toThrow();
    expect(() => rejectObviousPrivateTarget('http://192.168.1.20/form')).toThrow();
    expect(() => rejectObviousPrivateTarget('http://localhost/form')).toThrow();
    expect(rejectObviousPrivateTarget('https://jobs.example.com/role').hostname).toBe(
      'jobs.example.com',
    );
  });
});

describe('controlled synthetic form', () => {
  it('is an app-owned non-network fixture with submission disabled', () => {
    expect(SYNTHETIC_FORM_URL).toBe('https://synthetic.careerflow.invalid/application');
    expect(SYNTHETIC_FORM_HTML).toContain('NO EMPLOYER CONNECTION');
    expect(SYNTHETIC_FORM_HTML).toContain('Submission disabled in safe lab');
    expect(SYNTHETIC_FORM_HTML).not.toContain('<button type="submit"');
  });

  it('classifies contact and legal controls before policy evaluation', () => {
    expect(classifySensitivity('First name', 'text')).toBe('ordinary');
    expect(classifySensitivity('Email address', 'email')).toBe('sensitive');
    expect(classifySensitivity('Will you require sponsorship?', 'select')).toBe('legal');
  });
});
