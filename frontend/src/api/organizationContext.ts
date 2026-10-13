import { apiRequest } from './client'

export type OrganizationContext = {
  organization_id: number
  public_id: string
  org_code: string
  legal_name: string
  trading_name: string | null
  role: string
  status: string
}

export type AuthenticatedContext = {
  user: {
    id: number
    full_name: string
    email: string
    role: string | null
    is_active: boolean
  }
  organizations: OrganizationContext[]
}

export function getAuthenticatedContext() {
  return apiRequest<AuthenticatedContext>('/auth/me')
}