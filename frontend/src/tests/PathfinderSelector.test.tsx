import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PathfinderEntitySelector, GOLDEN_SUGGESTIONS } from '@/components/nexus/PathfinderEntitySelector'
import React from 'react'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('PathfinderEntitySelector', () => {
  it('renders selected entity badge and label', () => {
    const onSelect = vi.fn()
    render(
      <PathfinderEntitySelector
        label="Source Entity / Case"
        dotColor="blue"
        selectedId="CASE-141"
        onSelect={onSelect}
        testId="source-selector"
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText('Source Entity / Case')).toBeInTheDocument()
    expect(screen.getByText('445+ Graph Entities')).toBeInTheDocument()
    expect(screen.getByText(/FIR 141\/2026/i)).toBeInTheDocument()
    expect(screen.getByText('(CASE-141)')).toBeInTheDocument()
  })

  it('opens dropdown and displays golden and non-golden suggestions', async () => {
    const onSelect = vi.fn()
    render(
      <PathfinderEntitySelector
        label="Source Entity / Case"
        dotColor="blue"
        selectedId="CASE-141"
        onSelect={onSelect}
        testId="source-selector"
      />,
      { wrapper: createWrapper() }
    )

    const button = screen.getByTestId('source-selector')
    fireEvent.click(button)

    expect(screen.getByPlaceholderText(/Search cases, suspects, phones, accounts/i)).toBeInTheDocument()
    expect(screen.getByText(/Suggested & Golden demo entities/i)).toBeInTheDocument()

    // Golden entities present
    expect(screen.getAllByText(/FIR 207\/2026/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Rafiq Khan').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Deepak Rao').length).toBeGreaterThan(0)

    // Non-golden syndicate bridge entities present in suggestions
    expect(screen.getAllByText('Ramesh Hegde').length).toBeGreaterThan(0)
    expect(screen.getAllByText('The Broker • Articulation Bridge Between Syndicates').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Praveen Iyer').length).toBeGreaterThan(0)
  })

  it('filters suggestions and selects a non-golden entity', async () => {
    const onSelect = vi.fn()
    render(
      <PathfinderEntitySelector
        label="Target Entity / Case"
        dotColor="rose"
        selectedId="CASE-207"
        onSelect={onSelect}
        testId="target-selector"
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByTestId('target-selector'))

    const input = screen.getByPlaceholderText(/Search cases, suspects, phones, accounts/i)
    fireEvent.change(input, { target: { value: 'Ramesh' } })

    await waitFor(() => {
      expect(screen.getAllByText('Ramesh Hegde').length).toBeGreaterThan(0)
    })

    const rameshItem = screen.getAllByText('Ramesh Hegde')[0]
    fireEvent.click(rameshItem)

    expect(onSelect).toHaveBeenCalledWith('person-0051')
  })

  it('distinguishes entities by ID and contextual metadata', async () => {
    const onSelect = vi.fn()
    const activeNodes = [
      { id: 'person-0047', label: 'Rohit Bhat', entity_type: 'Person', properties: { full_name: 'Rohit Bhat', district: 'Bengaluru' } },
      { id: 'person-0050', label: 'Rohit Bhat', entity_type: 'Person', properties: { full_name: 'Rohit Bhat', district: 'Mangaluru' } },
    ]

    render(
      <PathfinderEntitySelector
        label="Source Entity / Case"
        dotColor="blue"
        selectedId="person-0047"
        onSelect={onSelect}
        activeGraphNodes={activeNodes}
        testId="source-selector"
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByTestId('source-selector'))

    const input = screen.getByPlaceholderText(/Search cases, suspects, phones, accounts/i)
    fireEvent.change(input, { target: { value: 'Rohit' } })

    // Both Rohit Bhat nodes visible with distinct IDs
    expect(screen.getAllByText('(person-0047)').length).toBeGreaterThan(0)
    expect(screen.getAllByText('(person-0050)').length).toBeGreaterThan(0)
    expect(screen.getByText('Bengaluru')).toBeInTheDocument()
    expect(screen.getByText('Mangaluru')).toBeInTheDocument()
  })

  it('displays empty state when no matching entities are found', async () => {
    const onSelect = vi.fn()
    render(
      <PathfinderEntitySelector
        label="Target Entity / Case"
        dotColor="rose"
        selectedId="CASE-207"
        onSelect={onSelect}
        testId="target-selector"
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByTestId('target-selector'))

    const input = screen.getByPlaceholderText(/Search cases, suspects, phones, accounts/i)
    fireEvent.change(input, { target: { value: 'NonExistentEntityXYZ123' } })

    expect(screen.getByText(/No entities found/i)).toBeInTheDocument()
  })
})
