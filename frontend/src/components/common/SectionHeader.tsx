type SectionHeaderProps = { kicker: string; title: string; action?: string }

export function SectionHeader({ kicker, title, action }: SectionHeaderProps) {
  return <div className="panel-heading"><div><p className="section-kicker">{kicker}</p><h2>{title}</h2></div>{action && <a className="text-link" href={`#${action.toLowerCase().replaceAll(' ', '-')}`}>{action} <span aria-hidden="true">→</span></a>}</div>
}