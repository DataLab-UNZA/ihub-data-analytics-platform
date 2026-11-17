import assert from 'node:assert/strict';
import test from 'node:test';
import { localRedirect } from '../src/lib/redirect.js';

test('OTP redirect stays on the browser origin and supports session cookies', () => {
  const response = localRedirect('/verify-code');
  response.cookies.set('ihub_pending', 'test', { httpOnly: true, secure: true });
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('location'), '/verify-code');
  assert.equal(new URL(response.headers.get('location'), 'https://public.example/login').href,
    'https://public.example/verify-code');
  assert.match(response.headers.get('set-cookie'), /HttpOnly/);
});

test('session redirects retain return paths and reject external destinations', () => {
  assert.equal(localRedirect('/login?next=%2Faccount', 307).status, 307);
  assert.equal(localRedirect('/account').headers.get('location'), '/account');
  for (const target of ['https://evil.example', '//evil.example', '/\\evil.example']) {
    assert.equal(localRedirect(target).headers.get('location'), '/overview');
  }
});
