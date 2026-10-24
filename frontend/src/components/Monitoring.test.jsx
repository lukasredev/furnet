import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../test/fetch'
import Monitoring from './Monitoring'

const FIRST = 'https://viscon.monomorphic.party'
const SECOND = 'https://dj-viscon-workshop-0.vsos.ethz.ch'

// Mirrors the backend: one result per requested URL, in order, with the URL normalized
function normalize(url) {
  const trimmed = url.trim()
  return (/^https?:\/\//.test(trimmed) ? trimmed : `https://${trimmed}`).replace(/\/+$/, '')
}

// Fakes /api/health-check: instances listed in `online` are up, everything else is down
function mockHealthCheck(online = {}) {
  return mockFetch({
    'POST /api/health-check': (options) => ({
      body: JSON.parse(options.body).instance_urls.map((url) => {
        const animal = online[normalize(url)]
        return animal
          ? { instance_url: normalize(url), is_alive: true, response_time_ms: 12.5, error: null, ...animal }
          : { instance_url: normalize(url), is_alive: false, response_time_ms: 3, error: 'HTTP 502', name: null, emoji: null }
      }),
    }),
  })
}

function requestedUrls(fetch, call = -1) {
  return JSON.parse(fetch.mock.calls.at(call)[1].body).instance_urls
}

function card(hostname) {
  return screen.getByRole('link', { name: hostname }).closest('div.border')
}

function renderMonitoring() {
  return render(
    <MemoryRouter>
      <Monitoring />
    </MemoryRouter>
  )
}

afterEach(() => {
  vi.useRealTimers()
})

describe('Monitoring', () => {
  it('checks the default workshop instances', async () => {
    const fetch = mockHealthCheck()
    renderMonitoring()

    expect(screen.getByText('Monitored Instances (16)')).toBeInTheDocument()
    await screen.findAllByText('OFFLINE')
    expect(fetch).toHaveBeenCalledOnce()
    expect(requestedUrls(fetch)).toHaveLength(16)
    expect(requestedUrls(fetch)[0]).toBe(FIRST)
  })

  it('shows PENDING until the first check returns', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    renderMonitoring()

    expect(screen.getAllByText('PENDING')).toHaveLength(16)
  })

  it('shows online instances with name, emoji and response time, and offline ones with the error', async () => {
    mockHealthCheck({ [FIRST]: { name: 'Buddy', emoji: '🦊' } })
    renderMonitoring()

    const online = card('viscon.monomorphic.party')
    expect(await within(online).findByText('ONLINE')).toBeInTheDocument()
    expect(within(online).getByText('Buddy')).toBeInTheDocument()
    expect(within(online).getByText('🦊')).toBeInTheDocument()
    expect(within(online).getByText('12.5ms')).toBeInTheDocument()

    const offline = card('dj-viscon-workshop-0.vsos.ethz.ch')
    expect(within(offline).getByText('OFFLINE')).toBeInTheDocument()
    expect(within(offline).getByText('HTTP 502')).toBeInTheDocument()
  })

  it('renders markup in remote animal names as text', async () => {
    mockHealthCheck({ [FIRST]: { name: '<img src=x onerror=alert(1)>', emoji: null } })
    const { container } = renderMonitoring()

    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
  })

  it('adds an instance and checks it', async () => {
    const fetch = mockHealthCheck({ 'https://buddy.vsos.ethz.ch': { name: 'Buddy', emoji: null } })
    renderMonitoring()

    await userEvent.type(screen.getByLabelText('Instance URL'), '  https://buddy.vsos.ethz.ch ')
    await userEvent.click(screen.getByRole('button', { name: 'Add Instance' }))

    expect(screen.getByText('Monitored Instances (17)')).toBeInTheDocument()
    expect(screen.getByLabelText('Instance URL')).toHaveValue('')
    expect(requestedUrls(fetch)).toContain('https://buddy.vsos.ethz.ch')
    expect(await within(card('buddy.vsos.ethz.ch')).findByText('ONLINE')).toBeInTheDocument()
  })

  it('shows the status of an instance entered without a scheme or with a trailing slash', async () => {
    mockHealthCheck({
      'https://buddy.vsos.ethz.ch': { name: 'Buddy', emoji: null },
      'https://cleo.vsos.ethz.ch': { name: 'Cleo', emoji: null },
    })
    renderMonitoring()

    for (const url of ['buddy.vsos.ethz.ch', 'https://cleo.vsos.ethz.ch/']) {
      await userEvent.type(screen.getByLabelText('Instance URL'), url)
      await userEvent.click(screen.getByRole('button', { name: 'Add Instance' }))
    }

    expect(await within(card('buddy.vsos.ethz.ch')).findByText('ONLINE')).toBeInTheDocument()
    expect(await within(card('cleo.vsos.ethz.ch/')).findByText('ONLINE')).toBeInTheDocument()
  })

  it('refuses to add an instance twice', async () => {
    mockHealthCheck()
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    renderMonitoring()

    await userEvent.type(screen.getByLabelText('Instance URL'), FIRST)
    await userEvent.click(screen.getByRole('button', { name: 'Add Instance' }))

    expect(alert).toHaveBeenCalledWith('This instance is already in the monitoring list')
    expect(screen.getByText('Monitored Instances (16)')).toBeInTheDocument()
  })

  it('refuses to monitor more instances than the backend checks at once', async () => {
    const fetch = mockHealthCheck()
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    renderMonitoring()
    const input = screen.getByLabelText('Instance URL')
    const submit = screen.getByRole('button', { name: 'Add Instance' })

    for (let n = 0; n < 35; n++) {
      fireEvent.change(input, { target: { value: `https://extra-${n}.vsos.ethz.ch` } })
      fireEvent.click(submit)
    }

    expect(screen.getByText('Monitored Instances (50)')).toBeInTheDocument()
    expect(alert).toHaveBeenCalledOnce()
    expect(alert).toHaveBeenCalledWith('You can monitor at most 50 instances')
    expect(fetch.mock.calls.every((_, i) => requestedUrls(fetch, i).length <= 50)).toBe(true)
  })

  it('removes an instance', async () => {
    const fetch = mockHealthCheck()
    renderMonitoring()
    await screen.findAllByText('OFFLINE')

    await userEvent.click(within(card('viscon.monomorphic.party')).getByTitle('Remove instance'))

    expect(screen.getByText('Monitored Instances (15)')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'viscon.monomorphic.party' })).not.toBeInTheDocument()
    expect(requestedUrls(fetch)).not.toContain(FIRST)
    expect(requestedUrls(fetch)[0]).toBe(SECOND)
  })

  it('shows an empty state when every instance is removed', async () => {
    const fetch = mockHealthCheck()
    renderMonitoring()

    for (const button of screen.getAllByTitle('Remove instance')) {
      await userEvent.click(button)
    }

    expect(screen.getByText(/No instances added yet/)).toBeInTheDocument()
    expect(screen.queryByText(/Auto-refreshing/)).not.toBeInTheDocument()
    // The last check covered the last remaining instance; an empty list is never sent
    expect(requestedUrls(fetch)).toHaveLength(1)
  })

  it('re-checks every 5 seconds and stops when unmounted', async () => {
    vi.useFakeTimers()
    const fetch = mockHealthCheck()
    const { unmount } = renderMonitoring()
    await act(() => vi.advanceTimersByTimeAsync(0))
    expect(fetch).toHaveBeenCalledTimes(1)

    await act(() => vi.advanceTimersByTimeAsync(5000))
    expect(fetch).toHaveBeenCalledTimes(2)
    await act(() => vi.advanceTimersByTimeAsync(5000))
    expect(fetch).toHaveBeenCalledTimes(3)

    unmount()
    await vi.advanceTimersByTimeAsync(15000)
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('keeps the page usable when the health check fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mockFetch({ 'POST /api/health-check': { status: 500, body: { detail: 'boom' } } })
    renderMonitoring()

    await vi.waitFor(() => expect(console.error).toHaveBeenCalledWith('Failed to check health'))
    expect(screen.getAllByText('PENDING')).toHaveLength(16)
  })
})
