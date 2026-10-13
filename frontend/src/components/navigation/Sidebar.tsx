import { useState } from 'react'
import { Brand } from '../common/Brand'
import { Icon, type IconName } from '../common/Icon'
import { RouteLink, isRoute, useRouter } from '../../routing/Router'

type NavGroup = { label: string; icon: IconName; to: string; items: Array<[string, string]> }
const navGroups: NavGroup[] = [
  { label: 'Command Center', icon: 'grid', to: '/command-center', items: [] },
  { label: 'Market Intelligence', icon: 'pulse', to: '/market-intelligence', items: [['Market Signals', '/market-intelligence'], ['Company Discovery', '/companies'], ['Prospect Priorities', '/opportunities']] },
  { label: 'Companies', icon: 'building', to: '/companies', items: [['Companies', '/companies'], ['Company Intelligence', '/f5/companies'], ['Contacts', '/companies/contacts'], ['Decision Makers', '/companies/decision-makers']] },
  { label: 'Warehouses', icon: 'warehouse', to: '/warehouses', items: [['Warehouse Portfolio', '/warehouses'], ['Warehouse Details', '/warehouses/details'], ['Capabilities', '/warehouses/capabilities'], ['Availability', '/warehouses/availability'], ['Matching', '/warehouses/matches']] },
  { label: 'Opportunities', icon: 'briefcase', to: '/opportunities', items: [['Requirement Intelligence', '/requirement-intelligence'], ['Leads', '/leads'], ['Opportunities', '/opportunities'], ['Deals', '/deals']] },
  { label: 'Engagement', icon: 'activity', to: '/engagement', items: [['Investigations', '/engagement/investigations'], ['Outreach', '/engagement/outreach'], ['Follow-ups', '/engagement/follow-ups'], ['Activity', '/engagement/activity']] },
  { label: 'Intelligence', icon: 'chart', to: '/intelligence', items: [['Opportunity Intelligence', '/intelligence'], ['Commercial Intelligence', '/commercial-intelligence'], ['Analytics', '/analytics']] },
]
const ecosystemItems: Array<[string, string]> = [['Warehouse Services', '/ecosystem/services'], ['Providers', '/ecosystem/providers'], ['Products & Solutions', '/ecosystem/products']]
const adminItems: Array<[string, IconName, string]> = [['Organization', 'organization', '/admin'], ['Users', 'users', '/admin/users'], ['Settings', 'settings', '/admin/settings']]

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { path } = useRouter()
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggle = (label: string) => setExpanded((current) => ({ ...current, [label]: !current[label] }))
  return <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Primary navigation"><div className="sidebar-brand"><Brand onClick={onClose} /><button className="mobile-close" onClick={onClose} aria-label="Close navigation">×</button></div><nav className="sidebar-nav">{navGroups.map((group) => <div className="nav-group" key={group.label}><RouteLink className={`nav-parent ${isRoute(path, group.to) ? 'active' : ''}`} to={group.to} onClick={onClose}><Icon name={group.icon} /><span>{group.label}</span>{group.items.length > 0 && <button type="button" className="nav-expander" onClick={(event) => { event.preventDefault(); event.stopPropagation(); toggle(group.label) }} aria-label={`${expanded[group.label] ? 'Collapse' : 'Expand'} ${group.label}`} aria-expanded={Boolean(expanded[group.label])}><span className="chevron" aria-hidden="true">{expanded[group.label] ? '−' : '+'}</span></button>}</RouteLink>{group.items.length > 0 && expanded[group.label] && <div className="nav-children">{group.items.map(([item, to]) => <RouteLink to={to} key={item} onClick={onClose}>{item}</RouteLink>)}</div>}</div>)}<p className="nav-section-label">Ecosystem <span className="nav-label-note">future foundation</span></p>{ecosystemItems.map(([item, to]) => <RouteLink className={`nav-parent nav-placeholder ${isRoute(path, to) ? 'active' : ''}`} to={to} key={item} onClick={onClose}><Icon name="layers" /><span>{item}</span><span className="placeholder-dot" aria-label="Placeholder">·</span></RouteLink>)}<p className="nav-section-label administration-label">Administration</p>{adminItems.map(([item, icon, to]) => <RouteLink className={`nav-parent ${isRoute(path, to) ? 'active' : ''}`} to={to} key={item} onClick={onClose}><Icon name={icon} /><span>{item}</span></RouteLink>)}</nav><div className="sidebar-footer"><span className="status-dot" />Data workspace foundation<span className="version">F2</span></div></aside>
}