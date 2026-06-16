import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Badge from './Badge.jsx'

describe('Badge', () => {
  it('renders the classification as a tier label', () => {
    render(<Badge value="CORE" />)
    expect(screen.getByText('Tier 1')).toBeTruthy()
  })

  it('applies the classification color class', () => {
    const { container } = render(<Badge value="AVOID" />)
    expect(container.firstChild.className).toContain('text-avoid')
  })
})
