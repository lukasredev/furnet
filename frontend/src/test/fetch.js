import { vi } from 'vitest'

// Replaces fetch with a fake backend. `routes` maps "METHOD /path" to either
// { status, body } or a function (requestOptions) => { status, body }; a function
// may also throw to simulate a network failure.
export function mockFetch(routes) {
  const fetch = vi.fn(async (url, options = {}) => {
    const key = `${options.method ?? 'GET'} ${url}`
    const route = routes[key]
    if (!route) throw new Error(`Unexpected request: ${key}`)
    const { status = 200, body = {} } = typeof route === 'function' ? route(options) : route
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
