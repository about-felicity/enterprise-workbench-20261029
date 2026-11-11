import assert from 'node:assert/strict';
import test, { afterEach } from 'node:test';
import { getVideos, postVideos } from '../app/api/videoProxy.ts';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const origin = 'https://ifbcy.com';
const url = origin + '/geo_monitor/api/geo-capture/creator-videos';
const body = JSON.stringify({ delete_work_id: 7, record_key: 'a'.repeat(32) });
const deletion = (extra = {}) => new Request(url, {
  method: 'POST', body,
  headers: { Origin: origin, Host: 'ifbcy.com', Cookie: 'geo_monitor_session=fixture',
    'Content-Type': 'application/json', 'Content-Length': String(Buffer.byteLength(body)), ...extra },
});

test('deletion forwards the identity verified from the signed session', async () => {
  const calls = [];
  globalThis.fetch = async (address, options) => {
    calls.push(address);
    if (address.endsWith('/auth')) {
      assert.equal(options.headers.Cookie, 'geo_monitor_session=fixture');
      assert.equal(options.headers['X-Original-URI'], '/geo_monitor/api/geo-capture/creator-videos');
      return new Response(null, { status: 204, headers: { 'X-Geo-User': 'superadmin' } });
    }
    assert.equal(address, 'http://127.0.0.1:8812/works');
    assert.equal(options.headers.get('X-Geo-User'), 'superadmin');
    assert.equal(Buffer.from(options.body).toString(), body);
    return Response.json({ works: [], can_delete: true });
  };
  const response = await postVideos(deletion());
  assert.equal(response.status, 200);
  assert.equal((await response.json()).can_delete, true);
  assert.equal(calls.length, 2);
});

test('a forged superadmin header cannot replace the signed employee identity', async () => {
  globalThis.fetch = async (address, options) => {
    if (address.endsWith('/auth')) return new Response(null, { status: 204, headers: { 'X-Geo-User': 'xuyan' } });
    assert.equal(options.headers.get('X-Geo-User'), 'xuyan');
    return Response.json({ error: 'forbidden' }, { status: 403 });
  };
  assert.equal((await postVideos(deletion({ 'X-Geo-User': 'superadmin' }))).status, 403);
});

test('cross-origin deletion is rejected before any upstream request', async () => {
  globalThis.fetch = () => { throw Error('unexpected upstream request'); };
  assert.equal((await postVideos(deletion({ Origin: 'https://foreign.example' }))).status, 403);
  assert.equal((await postVideos(deletion({ 'Sec-Fetch-Site': 'cross-site' }))).status, 403);
});

test('employee reads require a signed session and use the employee backend', async () => {
  globalThis.fetch = async (address, options) => {
    if (address.endsWith('/auth')) {
      assert.equal(options.headers['X-Original-URI'], '/geo_monitor/api/geo-capture/employee-videos');
      return new Response(null, { status: 204, headers: { 'X-Geo-User': 'fengyuan' } });
    }
    assert.equal(address, 'http://127.0.0.1:8813/works');
    assert.equal(options.headers.get('X-Geo-User'), 'fengyuan');
    return Response.json({ works: [], can_delete: false });
  };
  assert.equal((await getVideos(new Request(url), 'employee-videos')).status, 200);
  globalThis.fetch = async () => new Response(null, { status: 401 });
  assert.equal((await getVideos(new Request(url), 'employee-videos')).status, 401);
});

test('paid media reads and writes go to the independent ledger with verified identity', async () => {
  const ledger = 'paid-media-videos';
  const paidUrl = origin + '/geo_monitor/api/geo-capture/' + ledger;
  const writes = [];
  globalThis.fetch = async (address, options) => {
    if (address.endsWith('/auth')) {
      assert.equal(options.headers['X-Original-URI'], '/geo_monitor/api/geo-capture/paid-media-videos');
      return new Response(null, { status: 204, headers: { 'X-Geo-User': 'superadmin' } });
    }
    assert.equal(address, 'http://127.0.0.1:8814/works?day=2026-11-11');
    assert.equal(options.headers.get('X-Geo-User'), 'superadmin');
    if (options.method === 'POST') writes.push(JSON.parse(Buffer.from(options.body).toString()));
    return Response.json({ works: [], can_delete: true });
  };
  const datedUrl = paidUrl + '?day=2026-11-11';
  assert.equal((await getVideos(new Request(datedUrl), ledger)).status, 200);
  const feeBody = JSON.stringify({ text: 'https://v.douyin.com/fixture/', fee: '25.50' });
  const add = new Request(datedUrl, { method: 'POST', body: feeBody, headers: {
    Origin: origin, Host: 'ifbcy.com', 'Content-Type': 'application/json',
    'Content-Length': String(Buffer.byteLength(feeBody)),
  } });
  assert.equal((await postVideos(add, ledger)).status, 200);
  assert.deepEqual(writes, [{ text: 'https://v.douyin.com/fixture/', fee: '25.50' }]);
});

test('accounts restricted by edge auth cannot reach the paid media ledger', async () => {
  globalThis.fetch = async (address) => {
    assert.ok(address.endsWith('/auth'));
    return new Response(null, { status: 403 });
  };
  assert.equal((await getVideos(new Request(url.replace('creator-videos', 'paid-media-videos')), 'paid-media-videos')).status, 403);
});
