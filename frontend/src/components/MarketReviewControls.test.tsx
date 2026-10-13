import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MarketReviewControls } from './MarketReviewControls'
import { getAuthenticatedContext } from '../api/organizationContext'
import { apiRequest } from '../api/client'
vi.mock('../api/organizationContext', () => ({ getAuthenticatedContext: vi.fn() }))
vi.mock('../api/client', () => ({ apiRequest: vi.fn(), ApiError: class extends Error {} }))
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.resetAllMocks() })
it('only accepts a candidate after the human action, without converting it', async () => {
  vi.mocked(getAuthenticatedContext).mockResolvedValue({ user: { role: 'user' }, organizations: [{ organization_id: 1, role: 'MEMBER' }] } as never)
  vi.mocked(apiRequest).mockResolvedValue({})
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  const saved = vi.fn()
  render(<MarketReviewControls signal={{ id: 3, organization_id: 1, status: 'VERIFIED' } as never} candidate={{ id: 4, status: 'UNDER_REVIEW' } as never} onSaved={saved} />)
  await screen.findByText('Accept candidate')
  expect(apiRequest).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('Accept candidate'))
  await waitFor(() => expect(saved).toHaveBeenCalledTimes(1))
  const [path, options] = vi.mocked(apiRequest).mock.calls[0]
  expect(path).toBe('/requirement-candidates/4/transition')
  expect(JSON.parse(options!.body as string)).toEqual({ target_status: 'ACCEPTED' })
  expect(apiRequest).toHaveBeenCalledTimes(1)
})
