import { RouteLink } from '../../routing/Router'
import logo from '../../assets/bwip-logo.png'

export function Brand({ onClick }: { onClick?: () => void }) {
  return <RouteLink className="brand" to="/command-center" onClick={onClick} aria-label="BWIP Command Center">
    <img className="brand-logo" src={logo} alt="BHOODEVI Warehouse Intelligence Platform" />
  </RouteLink>
}