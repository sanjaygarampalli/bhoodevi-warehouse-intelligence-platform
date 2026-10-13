import { EmptyState } from '../components/common/EmptyState'
import { SectionHeader } from '../components/common/SectionHeader'

export function PlaceholderPage({ title }: { title: string }) {
  return <main className="dashboard page-placeholder"><section className="panel"><SectionHeader kicker="BWIP workspace" title={title} /><EmptyState title="This workspace is not connected yet.">The navigation foundation is ready. Records and workflows will appear when this module is implemented and connected to the backend.</EmptyState></section></main>
}