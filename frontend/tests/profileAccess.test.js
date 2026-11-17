import test from 'node:test';
import assert from 'node:assert/strict';
import { createProfileAccess } from '../src/services/profileAccess.js';

test('create retains a capability only for its profile and sends it on reads and updates', async () => {
  const calls = [];
  const api = Object.fromEntries(['post', 'get', 'put'].map(method => [method, async (...args) => {
    calls.push([method, ...args]);
    return { data: method === 'post' ? { profile_id: 'owner', access_token: 'private' } : { success: true } };
  }]));
  const access = createProfileAccess(api);
  await access.create({ age: 25 });
  await access.read('owner');
  await access.update('owner', { age: 26 });
  await access.history('owner');
  assert.equal(calls[1][2].headers.Authorization, 'Bearer private');
  assert.equal(calls[2][3].headers.Authorization, 'Bearer private');
  assert.equal(calls[3][2].headers.Authorization, 'Bearer private');
  await assert.rejects(access.read('someone-else'));
  access.clear();
  await assert.rejects(access.read('owner'));
  assert.equal(calls.length, 4);
});

test('orchestrator capability can be remembered without accepting an ID alone', async () => {
  const access = createProfileAccess({ get: async (_url, config) => ({ data: config.headers }) });
  access.remember({ profile_id: 'owner', access_token: 'private' });
  assert.equal((await access.read('owner')).Authorization, 'Bearer private');
  access.remember({ profile_id: 'old-short-id' });
  await assert.rejects(access.read('old-short-id'));
});
