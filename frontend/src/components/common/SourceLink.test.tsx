import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { SourceLink } from './SourceLink'
afterEach(cleanup)
it.each(['javascript:alert(1)', 'data:text/html,<script>alert(1)</script>', 'https://name:password@example.com', '/relative'])('does not navigate to an unsafe provenance URL: %s', (url) => {
  render(<SourceLink url={url} />)
  expect(screen.queryByRole('link')).toBeNull()
})
it('allows an absolute HTTPS provenance link without opener access', () => {
  render(<SourceLink url="https://example.com/evidence" />)
  expect(screen.getByRole('link').getAttribute('href')).toBe('https://example.com/evidence')
  expect(screen.getByRole('link').getAttribute('rel')).toContain('noopener')
})
