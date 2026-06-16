import { describe, it, expect } from 'vitest'
import { pct, signed, deltaColor, CLASS_COLOR } from './format.js'

describe('format helpers', () => {
  it('formats percentages', () => {
    expect(pct(0.355)).toBe('35.5%')
    expect(pct(1)).toBe('100.0%')
  })

  it('signs numbers', () => {
    expect(signed(0.25)).toBe('+0.250')
    expect(signed(-0.1)).toBe('-0.100')
  })

  it('colors deltas by direction', () => {
    expect(deltaColor(0.1)).toBe('text-core')
    expect(deltaColor(-0.1)).toBe('text-avoid')
    expect(deltaColor(0)).toBe('text-muted')
  })

  it('has a color for every classification', () => {
    for (const c of ['CORE', 'HIGH-ASYMMETRY', 'TACTICAL', 'AVOID']) {
      expect(CLASS_COLOR[c]).toBeTruthy()
    }
  })
})
