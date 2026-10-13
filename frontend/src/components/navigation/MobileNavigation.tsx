import { Icon } from '../common/Icon'
import { RouteLink, useRouter } from '../../routing/Router'

const items = [
  ['Home', '/command-center', 'grid'],
  ['Search', '/search', 'pulse'],
  ['Opportunities', '/opportunities', 'briefcase'],
  ['Actions', '/engagement/follow-ups', 'activity'],
] as const

export function MobileNavigation() {
  const { path } = useRouter()
  return <nav className="mobile-navigation" aria-label="Mobile primary navigation">{items.map(([label, to, icon]) => <RouteLink className={path === to || (to !== '/command-center' && path.startsWith(to)) ? 'is-active' : undefined} to={to} key={to}><Icon name={icon} /><span>{label}</span></RouteLink>)}<button type="button" className="mobile-more" onClick={() => document.querySelector<HTMLButtonElement>('.menu-toggle')?.click()}><span className="mobile-more-icon">•••</span><span>More</span></button></nav>
}