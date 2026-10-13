export function SourceLink({ url }: { url: string }) {
  let safe: URL
  try { safe = new URL(url) } catch { return <span>Source URL unavailable</span> }
  if (!['http:', 'https:'].includes(safe.protocol) || safe.username || safe.password) return <span>Source URL unavailable</span>
  return <a className="text-link" href={safe.href} target="_blank" rel="noreferrer noopener">View source</a>
}
