import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { F5CompaniesPage } from './F5CompaniesPage'
import { Router } from '../routing/Router'
import { listF5Companies, getF5Company } from '../api/companies'
import { getAuthenticatedContext } from '../api/organizationContext'
import { ApiError } from '../api/client'

vi.mock('../api/companies', () => ({ listF5Companies: vi.fn(), getF5Company: vi.fn() }))
vi.mock('../api/organizationContext', () => ({ getAuthenticatedContext: vi.fn() }))
afterEach(cleanup)
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getAuthenticatedContext).mockResolvedValue({ organizations: [{ organization_id: 1, legal_name: 'One' }, { organization_id: 2, legal_name: 'Two' }] } as never)
})
function result(name: string, id = 1) { return { items: [{ id, company_name: name, industry: 'Logistics' }], total: 1 } as never }

it('does not display a late response from the previous organization', async () => {
  let finishOld!: (value: never) => void
  vi.mocked(listF5Companies).mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve }))
  vi.mocked(listF5Companies).mockResolvedValueOnce(result('Current organization company'))
  render(<Router><F5CompaniesPage /></Router>)
  await screen.findByText('Select an organization', { selector: 'strong' })
  const picker = screen.getAllByRole('combobox')[0]
  fireEvent.change(picker, { target: { value: '1' } })
  await waitFor(() => expect(listF5Companies).toHaveBeenCalledTimes(1))
  fireEvent.change(picker, { target: { value: '2' } })
  await screen.findByText('Current organization company')
  await act(async () => finishOld(result('Previous organization company')))
  expect(screen.queryByText('Previous organization company')).toBeNull()
  expect(screen.getByText('Current organization company')).toBeTruthy()
})

it('recovers from a failed filter request', async () => {
  vi.mocked(listF5Companies).mockRejectedValueOnce(new ApiError(500, 'Synthetic failure'))
  vi.mocked(listF5Companies).mockResolvedValueOnce(result('Recovered company'))
  render(<Router><F5CompaniesPage /></Router>)
  await screen.findByText('Select an organization', { selector: 'strong' })
  fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: '1' } })
  await screen.findByText('F5 intelligence could not be loaded.')
  fireEvent.change(screen.getByPlaceholderText('Company, industry, geography...'), { target: { value: 'new' } })
  await screen.findByText('Recovered company')
  expect(screen.queryByText('F5 intelligence could not be loaded.')).toBeNull()
})

it('can navigate from discovery to detail and back without changing hook counts', async () => {
  vi.mocked(getF5Company).mockResolvedValue({ id: 1, company_name: 'Detail company', industry: 'Logistics', presence: [], evidence: [] } as never)
  const { rerender } = render(<Router><F5CompaniesPage /></Router>)
  await screen.findByText('Select an organization', { selector: 'strong' })
  rerender(<Router><F5CompaniesPage companyId={1} /></Router>)
  await screen.findByText('Detail company')
  rerender(<Router><F5CompaniesPage /></Router>)
  await screen.findByText('Select an organization', { selector: 'strong' })
})
