import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CommandCenter } from './LiveCommandCenter'
import { Router } from '../routing/Router'
import { getAuthenticatedContext } from '../api/organizationContext'
import { apiRequest } from '../api/client'

vi.mock('../api/organizationContext', () => ({ getAuthenticatedContext: vi.fn() }))
vi.mock('../api/client', () => ({ apiRequest: vi.fn(), ApiError: class extends Error {} }))
afterEach(() => { cleanup(); vi.resetAllMocks() })
it('loads the organization-scoped dashboard and displays real zero counts', async () => {
  vi.mocked(getAuthenticatedContext).mockResolvedValue({ organizations: [{ organization_id: 7 }] } as never)
  vi.mocked(apiRequest).mockResolvedValue({ generated_at: '2026-10-10T12:00:00Z', executive_summary: { total_active_leads: 0, high_priority_leads: 0, critical_priority_leads: 0, active_opportunities: 0, overdue_follow_ups: 0, follow_ups_due_today: 0 }, top_priorities: [], todays_attention: [] })
  render(<Router><CommandCenter /></Router>)
  await screen.findByText('No priority items')
  expect(apiRequest).toHaveBeenCalledWith('/operational-dashboard?organization_id=7')
  expect(screen.getAllByText('0')).toHaveLength(4)
  expect(screen.queryByText('Backend data not connected')).toBeNull()
})
