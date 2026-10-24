import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FriendList from './FriendList'

const buddy = {
  unique_id: 'buddy.vsos.ethz.ch:buddy',
  dns_name: 'buddy.vsos.ethz.ch',
  name: 'Buddy',
  connected_at: '2026-10-24T12:00:00Z',
}

describe('FriendList', () => {
  it('shows a hint when there are no friends', () => {
    render(<FriendList friends={[]} />)

    expect(screen.getByText(/No friends yet/)).toBeInTheDocument()
  })

  it('shows each friend with a link to their instance', () => {
    render(
      <FriendList
        friends={[buddy, { ...buddy, unique_id: 'cleo.vsos.ethz.ch:cleo', dns_name: 'cleo.vsos.ethz.ch', name: 'Cleo' }]}
      />
    )

    expect(screen.getAllByRole('heading').map((heading) => heading.textContent)).toEqual(['Buddy', 'Cleo'])
    expect(screen.getByText('buddy.vsos.ethz.ch:buddy')).toBeInTheDocument()

    const link = screen.getByTitle("Visit Buddy's profile")
    expect(link).toHaveAttribute('href', 'https://buddy.vsos.ethz.ch')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows when the friendship started in local time', () => {
    render(<FriendList friends={[buddy]} />)

    expect(
      screen.getByText(`Connected: ${new Date('2026-10-24T12:00:00Z').toLocaleString()}`)
    ).toBeInTheDocument()
  })

  it('renders markup in friend data as text', () => {
    const { container } = render(
      <FriendList friends={[{ ...buddy, name: '<img src=x onerror=alert(1)>' }]} />
    )

    expect(screen.getByRole('heading', { name: '<img src=x onerror=alert(1)>' })).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
  })
})
