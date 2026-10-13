import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { CompanyProfilePage } from './CompanyProfilePage'
import { Router } from '../routing/Router'
import * as api from '../api/companies'
import { ApiError } from '../api/client'

vi.mock('../api/companies', () => ({ getCompany: vi.fn(), getPriority: vi.fn(), getContacts: vi.fn(), getDecisionMakers: vi.fn(), getCommercialContext: vi.fn(), getIntelligenceProfile: vi.fn(), getActivity: vi.fn() }))
const company = (id: number) => ({ id, company_name: `Synthetic Company ${id}`, organization_id: id, industry: 'Logistics', company_type: 'Private', created_at: '2026-10-11', updated_at: '2026-10-11' })
const view = (id: number) => <Router><CompanyProfilePage companyId={id} /></Router>
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getCompany).mockImplementation(async id => company(id))
  vi.mocked(api.getPriority).mockRejectedValue(new ApiError(404, 'Not available'))
  vi.mocked(api.getContacts).mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 })
  vi.mocked(api.getDecisionMakers).mockRejectedValue(new ApiError(404, 'Not available'))
  vi.mocked(api.getCommercialContext).mockRejectedValue(new ApiError(404, 'Not available'))
  vi.mocked(api.getIntelligenceProfile).mockRejectedValue(new ApiError(404, 'Not available'))
  vi.mocked(api.getActivity).mockResolvedValue([])
})
afterEach(cleanup)

it('recovers from a denied company when navigating to an authorized company', async () => {
  vi.mocked(api.getCompany).mockRejectedValueOnce(new ApiError(403, 'Denied'))
  const { rerender } = render(view(1))
  await screen.findByText('Access to this company intelligence is not permitted.')
  rerender(view(2))
  await screen.findByRole('heading', { name: 'Synthetic Company 2' })
  expect(screen.queryByText('Access to this company intelligence is not permitted.')).toBeNull()
})

it('hides the previous company while loading and ignores a late abandoned response', async () => {
  const { rerender } = render(view(1))
  await screen.findByRole('heading', { name: 'Synthetic Company 1' })
  let complete!: (value: api.Company) => void
  vi.mocked(api.getCompany).mockImplementationOnce(() => new Promise(resolve => { complete = resolve }))
  rerender(view(2))
  expect(screen.queryByRole('heading', { name: 'Synthetic Company 1' })).toBeNull()
  await screen.findByText('Loading company intelligence...')
  rerender(view(3))
  await screen.findByRole('heading', { name: 'Synthetic Company 3' })
  complete(company(2))
  await waitFor(() => expect(screen.queryByRole('heading', { name: 'Synthetic Company 2' })).toBeNull())
})
