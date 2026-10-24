import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AnimalProfile from './AnimalProfile'

const animal = {
  id: 'furnet.lukasre.ch:rusty',
  name: 'Rusty',
  species: 'Red Panda',
  description: 'A curious and playful red panda',
  instance_url: 'https://furnet.lukasre.ch',
  habitat: 'Bamboo forests',
  diet: 'Bamboo',
  fun_fact: 'Uses its tail as a blanket',
  emoji: '🐼',
  color: '#b7410e',
}

describe('AnimalProfile', () => {
  it('renders nothing without an animal', () => {
    const { container } = render(<AnimalProfile animal={null} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('shows the identity and links to the instance', () => {
    render(<AnimalProfile animal={animal} />)

    expect(screen.getByRole('heading', { name: 'Rusty' })).toBeInTheDocument()
    expect(screen.getByText('🐼')).toBeInTheDocument()
    expect(screen.getByText('Red Panda')).toBeInTheDocument()
    expect(screen.getByText('A curious and playful red panda')).toBeInTheDocument()
    expect(screen.getByText('furnet.lukasre.ch:rusty')).toBeInTheDocument()

    const link = screen.getByRole('link', { name: 'https://furnet.lukasre.ch' })
    expect(link).toHaveAttribute('href', 'https://furnet.lukasre.ch')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows the optional details with a color swatch', () => {
    render(<AnimalProfile animal={animal} />)

    expect(screen.getByText('Bamboo forests')).toBeInTheDocument()
    expect(screen.getByText('Bamboo')).toBeInTheDocument()
    expect(screen.getByText('Uses its tail as a blanket')).toBeInTheDocument()
    expect(screen.getByText('#b7410e').previousSibling).toHaveStyle({ backgroundColor: '#b7410e' })
  })

  it('hides optional details that are not set', () => {
    render(
      <AnimalProfile
        animal={{ ...animal, habitat: null, diet: null, fun_fact: null, emoji: null, color: null }}
      />
    )

    for (const label of ['Habitat', 'Diet', 'Fun Fact', 'Color']) {
      expect(screen.queryByText(label)).not.toBeInTheDocument()
    }
    expect(screen.queryByText('🐼')).not.toBeInTheDocument()
  })
})
