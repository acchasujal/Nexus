/**
 * frontend/src/tests/EntitySearchNavigation.test.tsx
 *
 * Tests for Case Detail → Entity Search navigation and Entity Registry autofill:
 * - Direct visit to /entities starts with empty fields (not Vikram Sharma)
 * - Navigation or URL params (?name=Deepak%20Khan&phone=9884045292&vehicle=KA-46-NR-1158)
 *   populates the Entity Search form with Deepak Khan's attributes
 * - CaseDetail "Query Entity Registry →" button passes the accused entity's specific attributes
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import Entities from '@/pages/Entities'
import CaseDetail from '@/pages/CaseDetail'

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function createWrapper(initialEntries: string[] = ['/entities']) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return ({ children }: { children?: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Entity Search & Case Detail Navigation', () => {
  it('renders empty query fields by default when visiting /entities without parameters', () => {
    const Wrapper = createWrapper(['/entities'])
    render(
      <Wrapper>
        <Entities />
      </Wrapper>
    )

    const nameInput = screen.getByLabelText(/Full Name \/ Suspect Name/i, { selector: 'input' }) as HTMLInputElement
    const phoneInput = screen.getByLabelText(/Phone Number/i, { selector: 'input' }) as HTMLInputElement
    const vehicleInput = screen.getByLabelText(/Vehicle Registration Number/i, { selector: 'input' }) as HTMLInputElement
    const addressInput = screen.getByLabelText(/Address \/ Known Hideout/i, { selector: 'input' }) as HTMLInputElement

    expect(nameInput.value).toBe('')
    expect(phoneInput.value).toBe('')
    expect(vehicleInput.value).toBe('')
    expect(addressInput.value).toBe('')
    expect(nameInput.value).not.toBe('Vikram Sharma')
  })

  it('populates Entity Search fields from URL search parameters', () => {
    const searchUrl = '/entities?name=Deepak%20Khan&phone=9884045292&vehicle=KA-46-NR-1158&address=Bengaluru'
    const Wrapper = createWrapper([searchUrl])
    render(
      <Wrapper>
        <Entities />
      </Wrapper>
    )

    const nameInput = screen.getByLabelText(/Full Name \/ Suspect Name/i, { selector: 'input' }) as HTMLInputElement
    const phoneInput = screen.getByLabelText(/Phone Number/i, { selector: 'input' }) as HTMLInputElement
    const vehicleInput = screen.getByLabelText(/Vehicle Registration Number/i, { selector: 'input' }) as HTMLInputElement
    const addressInput = screen.getByLabelText(/Address \/ Known Hideout/i, { selector: 'input' }) as HTMLInputElement

    expect(nameInput.value).toBe('Deepak Khan')
    expect(phoneInput.value).toBe('9884045292')
    expect(vehicleInput.value).toBe('KA-46-NR-1158')
    expect(addressInput.value).toBe('Bengaluru')
  })

  it('renders Query Entity Registry link on Case Detail with entity-specific query parameters', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/cases/CASE-207']}>
          <Routes>
            <Route path="/cases/:caseId" element={<CaseDetail />} />
            <Route path="/entities" element={<Entities />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Wait for accused cards to load
    await waitFor(() => {
      expect(screen.getByText(/Accused Entities & Suspects/i)).toBeInTheDocument()
    })

    // Find links for accused suspects
    const queryButtons = screen.getAllByRole('link', { name: /Query Entity Registry →/i })
    expect(queryButtons.length).toBeGreaterThan(0)

    // Verify href contains entity-specific query params, not generic or Vikram Sharma
    const targetHref = queryButtons[0].getAttribute('href')
    expect(targetHref).toContain('/entities?name=')
    expect(targetHref).not.toContain('Vikram+Sharma')

    // Clicking Query Entity Registry navigates to Entity Search with populated fields
    fireEvent.click(queryButtons[0])

    await waitFor(() => {
      const nameInput = screen.getByLabelText(/Full Name \/ Suspect Name/i, { selector: 'input' }) as HTMLInputElement
      expect(nameInput.value).toBeTruthy()
      expect(nameInput.value).not.toBe('Vikram Sharma')
    })
  })
})
