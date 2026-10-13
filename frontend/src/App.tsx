import { AppShell } from './components/layout/AppShell'
import { CommandCenter } from './pages/LiveCommandCenter'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { CompaniesPage } from './pages/CompaniesPage'
import { CompanyProfilePage } from './pages/CompanyProfilePage'
import { MarketIntelligencePage } from './pages/MarketIntelligencePage'
import { F5CompaniesPage } from './pages/F5CompaniesPage'
import { EmptyState } from './components/common/EmptyState'
import { Router, useRouter } from './routing/Router'
import { useEffect, useState } from 'react'
import { ApiError, clearAccessToken, getAccessToken, logoutAccount } from './api/client'
import { getAuthenticatedContext } from './api/organizationContext'
import { LoginPage } from './pages/LoginPage'
import { ConversionResultPage } from './pages/ConversionResultPage'
import { RequirementIntelligencePage } from './pages/RequirementIntelligencePage'

function RoutedPage() {
  const { path } = useRouter()
  if (path === '/command-center' || path === '/') return <CommandCenter />
  if (path === '/companies') return <CompaniesPage />
  if (path === '/market-intelligence') return <MarketIntelligencePage />
  if (path === '/f5/companies') return <F5CompaniesPage />
  if (path === '/requirement-intelligence') return <RequirementIntelligencePage />
  const resultMatch = path.match(/^\/(leads|deals)\/(\d+)$/)
  if (resultMatch) return <ConversionResultPage kind={resultMatch[1] as 'leads' | 'deals'} id={Number(resultMatch[2])} key={path} />
  const requirementMatch = path.match(/^\/requirement-intelligence\/(\d+)$/)
  if (requirementMatch) return <RequirementIntelligencePage requirementId={requirementMatch[1]} />
  const f5CompanyMatch = path.match(/^\/f5\/companies\/(\d+)$/)
  if (f5CompanyMatch) return <F5CompaniesPage companyId={Number(f5CompanyMatch[1])} />
  const signalMatch = path.match(/^\/market-intelligence\/([^/]+)$/)
  if (signalMatch) return <MarketIntelligencePage signalId={signalMatch[1]} />
  const companyMatch = path.match(/^\/companies\/(\d+)$/)
  if (companyMatch) return <CompanyProfilePage companyId={Number(companyMatch[1])} />
  if (path.startsWith('/companies/')) return <main className="dashboard"><EmptyState title="Company ID is not valid.">Return to Companies and choose a company record from the backend.</EmptyState></main>
  const title = path.split('/').filter(Boolean).map((part) => part.replace(/-/g, ' ')).join(' / ')
  return <PlaceholderPage title={title || 'BWIP workspace'} />
}

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  useEffect(() => {
    const expired = () => setAuthenticated(false)
    window.addEventListener('bwip-session-expired', expired)
    return () => window.removeEventListener('bwip-session-expired', expired)
  }, [])
  useEffect(() => {
    if (!getAccessToken()) { setAuthenticated(false); return }
    getAuthenticatedContext().then(() => setAuthenticated(true)).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 401) clearAccessToken()
      setAuthenticated(false)
    })
  }, [])
  if (authenticated === null) return <main className="login-page"><p>Checking your session…</p></main>
  if (!authenticated) return <Router><LoginPage onAuthenticated={() => setAuthenticated(true)} /></Router>
  async function logout() {
    setLogoutError(null)
    try { await logoutAccount(); setAuthenticated(false) }
    catch (error) { setLogoutError(error instanceof Error ? error.message : 'Sign-out could not be completed. Retry.') }
  }
  return <Router><AppShell onLogout={logout}>{logoutError && <p role="alert">{logoutError}</p>}<RoutedPage /></AppShell></Router>
}

export default App
