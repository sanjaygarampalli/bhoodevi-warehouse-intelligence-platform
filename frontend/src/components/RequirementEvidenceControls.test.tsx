import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { RequirementEvidenceControls } from './RequirementEvidenceControls'
import { getAuthenticatedContext } from '../api/organizationContext'
import { apiRequest } from '../api/client'

vi.mock('../api/organizationContext', () => ({ getAuthenticatedContext: vi.fn() }))
vi.mock('../api/client', () => ({ apiRequest: vi.fn(), ApiError: class extends Error {} }))
afterEach(() => { cleanup(); vi.resetAllMocks() })

it('creates classified evidence as unverified and refreshes authoritative data', async () => {
  vi.mocked(getAuthenticatedContext).mockResolvedValue({ user: { role: 'user' }, organizations: [{ organization_id: 1, role: 'MEMBER' }] } as never)
  vi.mocked(apiRequest).mockResolvedValue({})
  const saved = vi.fn()
  render(<RequirementEvidenceControls requirementId={3} organizationId={1} evidence={[]} onSaved={saved} />)
  await screen.findByText('Add unverified evidence')
  fireEvent.change(screen.getByLabelText('Source'), { target: { value: 'Synthetic original source' } })
  fireEvent.change(screen.getByLabelText('Observed evidence'), { target: { value: 'Synthetic demand observation' } })
  fireEvent.change(screen.getByLabelText('Classification'), { target: { value: 'INFERENCE' } })
  fireEvent.click(screen.getByText('Add unverified evidence'))
  await waitFor(() => expect(saved).toHaveBeenCalledTimes(1))
  const [path, options] = vi.mocked(apiRequest).mock.calls[0]
  expect(path).toBe('/requirement-intelligence/3/evidence')
  expect(JSON.parse(options!.body as string)).toMatchObject({ classification: 'INFERENCE', verification_status: 'UNVERIFIED' })
})

it('does not expose evidence mutation controls to viewers', async () => {
  vi.mocked(getAuthenticatedContext).mockResolvedValue({ user: { role: 'user' }, organizations: [{ organization_id: 1, role: 'VIEWER' }] } as never)
  render(<RequirementEvidenceControls requirementId={3} organizationId={1} evidence={[]} onSaved={vi.fn()} />)
  await waitFor(() => expect(getAuthenticatedContext).toHaveBeenCalled())
  expect(screen.queryByRole('button')).toBeNull()
  expect(apiRequest).not.toHaveBeenCalled()
})
