/**
 * frontend/src/tests/TimelinePlayback.test.tsx
 *
 * Dedicated tests for Timeline & Events playback UX:
 * - Play from 100% (final position) resets to 0% and starts playback
 * - Play from 0% starts advancing normally
 * - Pause and resume preserve current time index
 * - Play from 50% (middle position) continues advancing
 * - Natural completion reaches 100% and halts playback
 * - Clicking Play after natural completion restarts from 0%
 * - Empty timeline/nodes does not crash
 * - Rapid Play/Pause clicks do not leak timers
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { D3NetworkGraph, type D3GraphNode, type D3GraphEdge } from '@/components/nexus/D3NetworkGraph'

const mockNodes: D3GraphNode[] = [
  { id: 'N1', label: 'Case 141', entity_type: 'Case', timestamp: '2026-02-11T10:00:00Z' },
  { id: 'N2', label: 'Suspect A', entity_type: 'Person', timestamp: '2026-02-12T11:00:00Z' },
  { id: 'N3', label: 'Phone B', entity_type: 'Phone', timestamp: '2026-02-14T12:00:00Z' },
]

const mockEdges: D3GraphEdge[] = [
  { id: 'E1', source: 'N1', target: 'N2', edge_type: 'ACCUSED_IN', timestamp: '2026-02-12T11:00:00Z' },
  { id: 'E2', source: 'N2', target: 'N3', edge_type: 'USES_PHONE', timestamp: '2026-02-14T12:00:00Z' },
]

describe('Timeline Playback Controls', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('resets to 0% and starts playback when Play is clicked at 100%', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    // Initial state is 100%
    expect(slider.value).toBe('100')

    // Click Play while at 100%
    act(() => {
      fireEvent.click(playButton)
    })

    // Slider should have reset to 0%
    expect(slider.value).toBe('0')
    expect(screen.getByTitle(/Pause Timeline/i)).toBeInTheDocument()

    // Advance timer 250ms -> should advance by 2
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('2')

    // Advance another 250ms -> should advance to 4
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('4')
  })

  it('plays normally from 0% when manually reset first', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const resetButton = screen.getByTitle(/Reset Timeline to Start/i)
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    // Manually reset to 0
    act(() => {
      fireEvent.click(resetButton)
    })
    expect(slider.value).toBe('0')

    // Click Play
    act(() => {
      fireEvent.click(playButton)
    })

    // Advance 500ms
    act(() => {
      vi.advanceTimersByTime(500)
    })
    expect(Number(slider.value)).toBeGreaterThanOrEqual(4)
  })

  it('pauses and resumes without resetting time position', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    // Start playback from 100% -> resets to 0%
    act(() => {
      fireEvent.click(playButton)
    })

    // Advance to 10% (5 ticks of 250ms)
    act(() => {
      vi.advanceTimersByTime(1250)
    })
    expect(slider.value).toBe('10')

    // Pause
    const pauseButton = screen.getByTitle(/Pause Timeline/i)
    act(() => {
      fireEvent.click(pauseButton)
    })

    // Verify time does not advance while paused
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(slider.value).toBe('10')

    // Resume
    const resumeButton = screen.getByTitle(/Play Timeline Evolution/i)
    act(() => {
      fireEvent.click(resumeButton)
    })

    // Advance 250ms -> advances from 10 to 12
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('12')
  })

  it('continues playing from 50% when slider is moved to middle', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    // Manually scrub to 50%
    act(() => {
      fireEvent.change(slider, { target: { value: '50' } })
    })
    expect(slider.value).toBe('50')

    // Click Play from 50%
    act(() => {
      fireEvent.click(playButton)
    })

    // Should NOT reset to 0; should continue from 50%
    expect(slider.value).toBe('50')

    // Advance 250ms
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('52')
  })

  it('stops naturally upon reaching 100% and clicking Play restarts from 0%', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    // Move to 96%
    act(() => {
      fireEvent.change(slider, { target: { value: '96' } })
    })

    // Click Play
    act(() => {
      fireEvent.click(playButton)
    })
    expect(slider.value).toBe('96')

    // Advance 250ms -> 98%
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('98')

    // Advance 250ms -> 100% (natural completion)
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('100')

    // Playback should stop naturally: Pause button disappears, Play button reappears
    expect(screen.getByTitle(/Play Timeline Evolution/i)).toBeInTheDocument()

    // Advancing timers further does nothing
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(slider.value).toBe('100')

    // Clicking Play again after natural completion restarts from 0%
    const replayButton = screen.getByTitle(/Play Timeline Evolution/i)
    act(() => {
      fireEvent.click(replayButton)
    })
    expect(slider.value).toBe('0')

    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('2')
  })

  it('handles empty timeline without crashing', () => {
    render(<D3NetworkGraph nodes={[]} edges={[]} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const playButton = screen.getByTitle(/Play Timeline Evolution/i)

    expect(slider).toBeInTheDocument()
    expect(slider.value).toBe('100')

    act(() => {
      fireEvent.click(playButton)
    })

    expect(slider.value).toBe('0')
    act(() => {
      vi.advanceTimersByTime(500)
    })
    expect(Number(slider.value)).toBe(4)
  })

  it('handles rapid Play/Pause clicks cleanly without timer leakage', () => {
    render(<D3NetworkGraph nodes={mockNodes} edges={mockEdges} enableTemporalScrubber={true} />)

    const slider = screen.getByRole('slider') as HTMLInputElement
    const button = () => screen.getByRole('button', { name: /(Play|Pause) Timeline/i })

    // Rapid toggle 5 times
    act(() => {
      fireEvent.click(button()) // Play (resets to 0)
      fireEvent.click(button()) // Pause (at 0)
      fireEvent.click(button()) // Play (from 0)
      fireEvent.click(button()) // Pause (at 0)
      fireEvent.click(button()) // Play (from 0)
    })

    expect(slider.value).toBe('0')

    // Advance 250ms -> should only advance exactly 1 step (2), not accelerated by leaked timers
    act(() => {
      vi.advanceTimersByTime(250)
    })
    expect(slider.value).toBe('2')
  })
})
