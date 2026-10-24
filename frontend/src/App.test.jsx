import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { mockFetch } from './test/fetch'

const animal = {
  id: 'furnet.lukasre.ch:rusty',
  name: 'Rusty',
  species: 'Red Panda',
  description: 'A curious and playful red panda',
  instance_url: 'https://furnet.lukasre.ch',
  emoji: '🐼',
}

const buddy = {
  unique_id: 'buddy.vsos.ethz.ch:buddy',
  dns_name: 'buddy.vsos.ethz.ch',
  name: 'Buddy',
  connected_at: '2026-10-24T12:00:00Z',
}

function mockBackend(routes = {}) {
  return mockFetch({
    'GET /api/me': { body: animal },
    'GET /api/friends': { body: [] },
    'POST /api/health-check': { body: [] },
    ...routes,
  })
}

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  )
}

async function addFriend(url) {
  await userEvent.type(await screen.findByLabelText('Friend Instance URL'), url)
  await userEvent.click(screen.getByRole('button', { name: 'Add Friend' }))
}

describe('home page', () => {
  it('shows the profile and the current friends', async () => {
    mockBackend({ 'GET /api/friends': { body: [buddy] } })
    renderApp()

    expect(screen.getByText('Loading profile...')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Rusty' })).toBeInTheDocument()
    expect(screen.getByText('Connected Friends (1)')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Buddy' })).toBeInTheDocument()
    expect(screen.queryByText('Loading profile...')).not.toBeInTheDocument()
  })

  it('shows an error when the profile cannot be loaded', async () => {
    mockBackend({ 'GET /api/me': { status: 500 } })
    renderApp()

    expect(await screen.findByText('Failed to fetch animal profile')).toBeInTheDocument()
    expect(screen.queryByText('Add a Friend')).not.toBeInTheDocument()
  })

  it('still shows the profile when the friend list cannot be loaded', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mockBackend({ 'GET /api/friends': { status: 500 } })
    renderApp()

    expect(await screen.findByRole('heading', { name: 'Rusty' })).toBeInTheDocument()
    expect(screen.getByText('Connected Friends (0)')).toBeInTheDocument()
    expect(console.error).toHaveBeenCalled()
  })

  it('adds a friend by instance URL', async () => {
    const fetch = mockBackend({ 'POST /api/friends/add': { body: buddy } })
    renderApp()

    await addFriend('  buddy.vsos.ethz.ch  ')

    expect(await screen.findByText('Successfully added Buddy as a friend!')).toBeInTheDocument()
    expect(screen.getByText('Connected Friends (1)')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Buddy' })).toBeInTheDocument()
    expect(screen.getByLabelText('Friend Instance URL')).toHaveValue('')

    const [, request] = fetch.mock.calls.find(([url]) => url === '/api/friends/add')
    expect(request.method).toBe('POST')
    expect(request.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(request.body)).toEqual({ instance_url: 'buddy.vsos.ethz.ch' })
  })

  it('shows the reason when adding a friend fails', async () => {
    mockBackend({
      'POST /api/friends/add': {
        status: 403,
        body: { detail: 'Friends must be from one of these domains: vsos.ethz.ch, furnet.lukasre.ch. Got: example.com' },
      },
    })
    renderApp()

    await addFriend('example.com')

    expect(
      await screen.findByText('ERROR: Friends must be from one of these domains: vsos.ethz.ch, furnet.lukasre.ch. Got: example.com')
    ).toBeInTheDocument()
    expect(screen.getByText('Connected Friends (0)')).toBeInTheDocument()
    expect(screen.getByLabelText('Friend Instance URL')).toHaveValue('example.com')
  })

  it('clears an earlier error when adding a friend succeeds', async () => {
    let attempt = 0
    mockBackend({
      'POST /api/friends/add': () =>
        ++attempt === 1 ? { status: 400, body: { detail: 'Failed to connect to friend instance' } } : { body: buddy },
    })
    renderApp()

    await addFriend('buddy.vsos.ethz.ch')
    expect(await screen.findByText('ERROR: Failed to connect to friend instance')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Add Friend' }))
    expect(await screen.findByText('Successfully added Buddy as a friend!')).toBeInTheDocument()
    expect(screen.queryByText(/^ERROR:/)).not.toBeInTheDocument()
  })

  it('only enables the add button once a URL is entered', async () => {
    mockBackend()
    renderApp()
    const input = await screen.findByLabelText('Friend Instance URL')
    const button = screen.getByRole('button', { name: 'Add Friend' })

    expect(button).toBeDisabled()
    await userEvent.type(input, '   ')
    expect(button).toBeDisabled()
    await userEvent.type(input, 'buddy.vsos.ethz.ch')
    expect(button).toBeEnabled()
  })

  it('navigates to the monitoring page and back', async () => {
    mockBackend()
    renderApp()

    await userEvent.click(await screen.findByRole('link', { name: 'Monitoring' }))
    expect(screen.getByRole('heading', { name: 'FurNet Monitoring' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('link', { name: 'Home' }))
    expect(await screen.findByRole('heading', { name: 'Rusty' })).toBeInTheDocument()
  })
})
