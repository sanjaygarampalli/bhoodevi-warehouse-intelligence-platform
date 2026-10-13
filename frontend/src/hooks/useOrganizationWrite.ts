import { useEffect, useState } from 'react'
import { getAuthenticatedContext } from '../api/organizationContext'

export function useOrganizationWrite(organizationId: number): boolean {
  const [allowed, setAllowed] = useState(false)
  useEffect(() => {
    let active = true
    setAllowed(false)
    getAuthenticatedContext().then(context => {
      if (active) setAllowed(context.user.role === 'admin' || context.organizations.some(org =>
        org.organization_id === organizationId && ['OWNER', 'ADMIN', 'MANAGER', 'MEMBER'].includes(org.role)))
    }).catch(() => { if (active) setAllowed(false) })
    return () => { active = false }
  }, [organizationId])
  return allowed
}
