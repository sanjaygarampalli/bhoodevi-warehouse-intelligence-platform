type EmptyStateProps = { title: string; children: string; compact?: boolean }

export function EmptyState({ title, children, compact = false }: EmptyStateProps) {
  return <div className={`empty-state ${compact ? 'empty-state-compact' : ''}`}>
    <span className="empty-state-mark" aria-hidden="true">—</span><strong>{title}</strong><p>{children}</p>
  </div>
}