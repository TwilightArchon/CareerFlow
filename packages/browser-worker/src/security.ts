import { isIP } from 'node:net';
import { lookup } from 'node:dns/promises';

export function requireLoopbackWebSocketUrl(rawUrl: string): URL {
  const url = new URL(rawUrl);
  if (url.protocol !== 'ws:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) {
    throw new Error('Browser worker accepts only unencrypted loopback WebSocket URLs');
  }
  return url;
}

export function rejectObviousPrivateTarget(rawUrl: string): URL {
  const url = new URL(rawUrl);
  if (!['https:', 'http:'].includes(url.protocol)) {
    throw new Error('Only http and https navigation is permitted');
  }
  const hostname = url.hostname.toLowerCase();
  if (
    hostname === 'localhost' ||
    hostname.endsWith('.localhost') ||
    hostname.endsWith('.local') ||
    isPrivateAddress(hostname)
  ) {
    throw new Error('Local and private-network navigation is blocked');
  }
  return url;
}

export async function requirePublicNavigationUrl(rawUrl: string): Promise<URL> {
  const url = rejectObviousPrivateTarget(rawUrl);
  const addresses = await lookup(url.hostname, { all: true, verbatim: true });
  if (addresses.length === 0 || addresses.some(({ address }) => isPrivateAddress(address))) {
    throw new Error('The navigation target resolved to a private network');
  }
  return url;
}

function isPrivateAddress(hostname: string): boolean {
  if (isIP(hostname) === 4) {
    const [first = 0, second = 0] = hostname.split('.').map(Number);
    return (
      first === 0 ||
      first === 10 ||
      first === 127 ||
      (first === 169 && second === 254) ||
      (first === 172 && second >= 16 && second <= 31) ||
      (first === 192 && second === 168) ||
      first >= 224
    );
  }
  if (isIP(hostname) === 6) {
    const normalized = hostname.toLowerCase();
    return (
      normalized === '::' ||
      normalized === '::1' ||
      normalized.startsWith('fc') ||
      normalized.startsWith('fd') ||
      normalized.startsWith('fe8') ||
      normalized.startsWith('fe9') ||
      normalized.startsWith('fea') ||
      normalized.startsWith('feb')
    );
  }
  return false;
}
