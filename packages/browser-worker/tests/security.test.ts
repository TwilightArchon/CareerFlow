import { describe, expect, it } from 'vitest';

import { rejectObviousPrivateTarget, requireLoopbackWebSocketUrl } from '../src/security';

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
