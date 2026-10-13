import { test, expect, type Page } from '@playwright/test'

const ids = JSON.parse(process.env.QA_IDS!) as { orgs: number[]; companies: number[] }
const evidence = process.env.QA_EVIDENCE_DIR!
const api = process.env.QA_API!
async function signIn(page: Page, email = 'member@example.com') {
  await page.goto('/companies')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill('Synthetic-QA-password-2026')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}
// Exercise the router's real popstate path while keeping the detail component mounted.
async function routeTo(page: Page, id: number) {
  await page.evaluate(id => { history.pushState({}, '', `/companies/${id}`); dispatchEvent(new PopStateEvent('popstate')) }, id)
}
async function shot(page: Page, name: string) { await page.screenshot({ path: `${evidence}/${name}.png`, fullPage: true }) }

test('company list, details, contact methods, reload and responsive navigation', async ({ page }, info) => {
  await signIn(page)
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: 'Synthetic Customer A', exact: true }) }).click()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.getByText('synthetic.contact@example.com', { exact: false })).toBeVisible()
  await expect(page.getByText('UNVERIFIED', { exact: false }).first()).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await shot(page, `${info.project.name}-company-detail`)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('link', { name: 'Back to companies', exact: false }).click()
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: 'Synthetic Customer B', exact: true }) }).click()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Companies', exact: true })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
})

test('company identity changes clear stale data and recover from prior failures', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop')
  await signIn(page); await routeTo(page, ids.companies[0])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route(`**/companies/${ids.companies[1]}`, async route => { await gate; await route.continue() })
  await routeTo(page, ids.companies[1])
  try {
    await expect(page.getByText('Loading company intelligence...', { exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toHaveCount(0)
  } finally { release() }
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
  await page.unroute(`**/companies/${ids.companies[1]}`)
  await routeTo(page, 999999)
  await expect(page.getByText('Company record not found.', { exact: true })).toBeVisible()
  await routeTo(page, ids.companies[0])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.getByText('Company record not found.', { exact: true })).toHaveCount(0)
  await routeTo(page, ids.companies[1])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
})

test('viewer reads only permitted companies and server denies writes and foreign subresources', async ({ page, request }, info) => {
  test.skip(info.project.name !== 'desktop')
  await signIn(page, 'viewer@example.com')
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toHaveCount(0)
  const token = await page.evaluate(() => sessionStorage.getItem('bwip_access_token')!)
  const headers = { Authorization: `Bearer ${token}` }
  expect((await request.put(`${api}/companies/${ids.companies[0]}`, { headers, data: { company_name: 'Forbidden edit' } })).status()).toBe(403)
  expect((await request.delete(`${api}/companies/${ids.companies[0]}`, { headers })).status()).toBe(403)
  for (const suffix of ['', '/contacts', '/prospect-priority', '/decision-maker-priorities', '/commercial-context', '/intelligence-profile', '/contact-activity-history']) {
    expect((await request.get(`${api}/companies/${ids.companies[1]}${suffix}`, { headers })).status()).toBe(403)
  }
  await routeTo(page, ids.companies[1])
  await expect(page.getByText('Access to this company intelligence is not permitted.', { exact: true })).toBeVisible()
  await expect(page.getByText('Synthetic Customer B', { exact: true })).toHaveCount(0)
  await shot(page, 'viewer-foreign-company-denied')
  await routeTo(page, ids.companies[0])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.locator('main').getByRole('button')).toHaveCount(0)
})

test('empty dataset and search states use actual backend results', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop')
  await signIn(page, 'empty@example.com')
  await expect(page.getByText('No company records are available.', { exact: true })).toBeVisible()
  await shot(page, 'empty-company-list')
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await signIn(page)
  await page.getByRole('searchbox').fill('No synthetic company matches this')
  await expect(page.getByText('No companies match your search.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Clear', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
})

test('network and optional-section errors recover without invented data', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop')
  await signIn(page)
  await page.route('**/companies/', route => route.abort('failed'))
  await page.reload()
  await expect(page.getByText('Unable to connect to the BWIP backend.', { exact: true })).toBeVisible()
  await page.unroute('**/companies/'); await page.reload()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await page.route('**/companies/', route => route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"Synthetic service failure"}' }))
  await page.reload()
  await expect(page.getByText('Company intelligence could not be loaded.', { exact: true })).toBeVisible()
  await page.unroute('**/companies/'); await page.reload()
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await page.route(`**/companies/${ids.companies[0]}/contacts`, route => route.abort('failed'))
  await routeTo(page, ids.companies[0])
  await expect(page.getByText('Unable to connect to the BWIP backend.', { exact: true })).toBeVisible()
  await page.unroute(`**/companies/${ids.companies[0]}/contacts`)
  await routeTo(page, ids.companies[1])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
  await page.route(`**/companies/${ids.companies[0]}/prospect-priority`, route => route.abort('failed'))
  await routeTo(page, ids.companies[0])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.getByText('Could not connect to the backend.', { exact: true })).toBeVisible()
  await shot(page, 'company-optional-error')
  await routeTo(page, ids.companies[1])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer B', exact: true })).toBeVisible()
  await expect(page.getByText('Stored contacts not available.', { exact: true })).toBeVisible()
  await expect(page.getByText('Warehouse intelligence profile not available.', { exact: true })).toBeVisible()
  await expect(page.getByText('Could not connect to the backend.', { exact: true })).toHaveCount(0)
  await page.unroute(`**/companies/${ids.companies[0]}/prospect-priority`); await routeTo(page, ids.companies[0])
  await expect(page.getByRole('heading', { name: 'Synthetic Customer A', exact: true })).toBeVisible()
  await expect(page.getByText('Could not connect to the backend.', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Stored contacts not available.', { exact: true })).toHaveCount(0)
})
