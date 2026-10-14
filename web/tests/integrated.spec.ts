import { selectCatalogOption } from './catalog-picker'
import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs/promises'

async function exported(page: Page, name: string) {
  const pending = page.waitForEvent('download')
  await page.getByRole('button', { name, exact: true }).click()
  return fs.readFile((await (await pending).path())!, 'utf8')
}

test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error })
  await page.route('https://**/*', route => { throw Error(`Rede externa proibida: ${route.request().url()}`) })
})

for (const failure of ['network', 'invalid-json', '503'] as const) {
  test(`fase 6: recuperação de ${failure} mantém resultado e exige Buscar`, async ({ page }) => {
    const query = JSON.parse(await fs.readFile('../backend/agregados/tests/fixtures/synthetic/consulta.json', 'utf8'))
    await page.goto('/#' + new URLSearchParams({ consulta: JSON.stringify({ version: 1, consulta: query }) }))
    await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
    const search = page.getByRole('button', { name: 'Buscar', exact: true })
    await search.click()
    await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
    const original = JSON.parse(await exported(page, 'Exportar JSON com proveniência'))
    let failures = 0
    await page.route('**/consultas/executar/', async route => {
      failures++
      if (failure === 'network') await route.abort('failed')
      else if (failure === 'invalid-json') await route.fulfill({ status: 200, contentType: 'application/json', body: '{' })
      else await route.fulfill({ status: 503, json: { error: { code: 'upstream_unavailable', message: 'Indisponibilidade simulada.' } } })
    })
    await search.click()
    await expect(page.getByRole('alert')).toBeVisible()
    expect(JSON.parse(await exported(page, 'Exportar JSON com proveniência'))).toEqual(original)
    expect(failures).toBe(1)
    await page.unroute('**/consultas/executar/')
    const recovered = page.waitForResponse(r => r.url().includes('/executar/'))
    await search.focus(); await page.keyboard.press('Enter')
    expect((await recovered).status()).toBe(200)
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(JSON.parse(await exported(page, 'Exportar JSON com proveniência')).data).toEqual(original.data)
    expect(failures).toBe(1)
  })
}

test('fase 6: catálogo até restauração e exportação, teclado e mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  let executions = 0
  page.on('request', r => { if (r.url().includes('/executar/')) executions++ })
  await page.goto('/')
  await selectCatalogOption(page, 'Pesquisa', 'SINTETICA')
  await selectCatalogOption(page, 'Agregado', '900001')
  for (const name of [/000101/, /102 ·/, /0000001/, /0000002/, /202401/, /202403/, /01 · Grupo A/, /02 · Grupo B/, /00 · Condição A/]) {
    const control = page.getByRole('checkbox', { name })
    await control.focus(); await page.keyboard.press('Space'); await expect(control).toBeChecked()
  }
  const validate = page.getByRole('button', { name: 'Validar seleção e gerar URL' })
  await validate.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  const shared = await page.getByLabel('URL da aplicação').inputValue()
  const query = JSON.parse(await exported(page, 'Exportar JSON de consulta')).consulta
  expect(executions).toBe(0)
  const search = page.getByRole('button', { name: 'Buscar', exact: true })
  await search.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  const original = JSON.parse(await exported(page, 'Exportar JSON com proveniência'))
  expect(original.data.consulta_aplicada).toEqual(query)
  expect(original.data.observacoes).toHaveLength(15)
  await page.getByRole('checkbox', { name: /202403/ }).uncheck()
  await expect(page.getByText(/Alterações pendentes/)).toBeVisible()
  expect(executions).toBe(1)
  expect(JSON.parse(await exported(page, 'Exportar JSON com proveniência'))).toEqual(original)
  await page.goto(shared)
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  expect(executions).toBe(1)
  await search.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  const restored = JSON.parse(await exported(page, 'Exportar JSON com proveniência'))
  expect(restored.data).toEqual(original.data)
  expect(restored.sources.every((s: { cache_hit: boolean }) => s.cache_hit)).toBe(true)
  expect(restored.sources.map((s: { fetched_at: string }) => s.fetched_at)).toEqual(original.sources.map((s: { fetched_at: string }) => s.fetched_at))
  expect(await exported(page, 'Exportar CSV completo')).toContain('000101')
  expect(executions).toBe(2)
  const table = page.getByRole('region', { name: 'Tabela longa rolável' })
  await table.focus(); await page.keyboard.press('ArrowRight')
  await expect.poll(() => table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: '../var/phase6-mobile.png', fullPage: true })
})

test('fase 6: medição limitada de resposta, apresentação e exportação', async ({ page, browserName }) => {
  const query = JSON.parse(await fs.readFile('../backend/agregados/tests/fixtures/synthetic/consulta.json', 'utf8'))
  await page.goto('/#' + new URLSearchParams({ consulta: JSON.stringify({ version: 1, consulta: query }) }))
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  const samples = []
  for (const count of [15, 10000]) {
    await page.route('**/consultas/executar/', async route => {
      const body = await (await route.fetch()).json()
      if (count === 10000) body.data.observacoes = Array.from({ length: count }, (_, i) => ({ ...body.data.observacoes[0], origem_indice: { variavel: 0, resultado: 0, serie: i } }))
      await route.fulfill({ json: body })
    })
    for (let run = 0; run < 3; run++) {
      const responsePending = page.waitForResponse(r => r.url().includes('/executar/'))
      const start = performance.now()
      await page.getByRole('button', { name: 'Buscar', exact: true }).click()
      const response = await responsePending
      const bytes = (await response.body()).length
      const received = performance.now()
      await expect(page.getByRole('heading', { name: `Tabela longa · ${count === 15 ? 7 : count} ocorrências` })).toBeVisible()
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))))
      const presented = performance.now()
      const exportStart = performance.now()
      const exportedJSON = await exported(page, 'Exportar JSON com proveniência')
      const exportMs = performance.now() - exportStart
      expect(JSON.parse(exportedJSON).data.observacoes).toHaveLength(count)
      const rows = await page.getByRole('region', { name: 'Tabela longa rolável' }).getByRole('row').count()
      expect(rows).toBe(count === 15 ? 8 : 51)
      samples.push({ observations: count, run, response_bytes: bytes, click_to_body_ms: received - start, body_to_two_frames_ms: presented - received, click_to_two_frames_ms: presented - start, json_download_ms: exportMs, export_bytes: Buffer.byteLength(exportedJSON), table_rows_with_header: rows })
    }
    await page.unroute('**/consultas/executar/')
  }
  await fs.mkdir('../var', { recursive: true })
  await fs.writeFile('../var/phase6-browser.json', JSON.stringify({ browserName, evidence: 'offline; Vite dev + Django MockTransport; 10000 rows duplicated only in browser mock, analyses unchanged; timings include Playwright polling and IPC', samples }, null, 2))
})
