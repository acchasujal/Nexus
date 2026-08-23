/**
 * utils.test.ts
 *
 * Unit tests for shared utility functions in src/lib/utils.ts
 */

import { describe, it, expect } from 'vitest'
import { clockStatusToRisk, resolveObjectPath } from '@/lib/utils'
import type { ClockStatus } from '@shared/contracts/api'

describe('clockStatusToRisk', () => {
  it('maps "red" to HIGH', () => {
    expect(clockStatusToRisk('red')).toBe('HIGH')
  })

  it('maps "overdue" to HIGH', () => {
    expect(clockStatusToRisk('overdue')).toBe('HIGH')
  })

  it('maps "amber" to MEDIUM', () => {
    expect(clockStatusToRisk('amber')).toBe('MEDIUM')
  })

  it('maps "green" to LOW', () => {
    expect(clockStatusToRisk('green')).toBe('LOW')
  })

  it('covers all ClockStatus values without TypeScript error', () => {
    const statuses: ClockStatus[] = ['green', 'amber', 'red', 'overdue']
    const results = statuses.map(clockStatusToRisk)
    expect(results).toEqual(['LOW', 'MEDIUM', 'HIGH', 'HIGH'])
  })
})

describe('resolveObjectPath', () => {
  it('resolves a shallow key', () => {
    expect(resolveObjectPath({ name: 'test' }, 'name')).toBe('test')
  })

  it('resolves a nested path', () => {
    expect(resolveObjectPath({ clock: { days_remaining: 9 } }, 'clock.days_remaining')).toBe(9)
  })

  it('returns undefined for a missing shallow key', () => {
    expect(resolveObjectPath({ name: 'test' }, 'missing')).toBeUndefined()
  })

  it('returns undefined for a missing nested key without throwing', () => {
    expect(resolveObjectPath({ clock: {} }, 'clock.days_remaining')).toBeUndefined()
  })

  it('returns undefined when traversing through null', () => {
    expect(resolveObjectPath({ clock: null }, 'clock.days_remaining')).toBeUndefined()
  })

  it('handles deeply nested path (3 levels)', () => {
    expect(resolveObjectPath({ a: { b: { c: 42 } } }, 'a.b.c')).toBe(42)
  })
})
