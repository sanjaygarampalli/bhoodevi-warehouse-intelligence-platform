import { RouteLink, useRouter } from '../../routing/Router'

export function TopHeader({ onMenuOpen, onLogout }: { onMenuOpen: () => void; onLogout: () => void }) {
  const { path } = useRouter()
  const title = path.startsWith('/requirement-intelligence') ? 'Requirement Intelligence' : path.startsWith('/f5/companies') || path.startsWith('/companies') ? 'Company Intelligence' : path.startsWith('/market-intelligence') ? 'Market Intelligence' : path.startsWith('/leads') ? 'Leads' : path.startsWith('/deals') ? 'Deals' : 'Command Center'
  return <header className="top-header"><div className="header-leading"><button className="menu-toggle" onClick={onMenuOpen} aria-label="Open navigation">Menu</button><div><p className="header-kicker">BWIP / INTERNAL PLATFORM</p><h1>{title}</h1><p className="header-subtitle">Evidence, explainable assessments and human-controlled progression.</p></div></div><div className="header-actions"><RouteLink className="text-link" to="/companies">Search companies</RouteLink><button className="logout-button" onClick={onLogout}>Sign out</button></div></header>
}