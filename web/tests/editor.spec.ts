import { test, expect, type Page } from '@playwright/test'
const prefix = '/api/v1/agregados-ibge'
async function choose(page: Page) {
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  await expect(page.getByRole('region', { name: 'Editor de consulta' })).toBeVisible()
}
async function fill(page: Page) {
  await page.getByRole('checkbox', { name: /000101/ }).check()
  await page.getByRole('checkbox', { name: /0000001/ }).check()
  await page.getByRole('checkbox', { name: /202401/ }).check()
  await page.getByRole('checkbox', { name: /01 · Grupo A/ }).check()
  await page.getByRole('checkbox', { name: /00 · Condição A/ }).check()
}
test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error })
  await page.route('https://**/*', route => { throw new Error(`External network forbidden ${route.request().url()}`) })
  page.on('request', request => expect(request.url()).not.toMatch(/consultas\/executar|\/variaveis\//))
})
test('validação integrada, URL literal, cópia e invalidação', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await choose(page)
  await expect(page.getByRole('button', { name: 'Validar seleção e gerar URL' })).toBeDisabled()
  await fill(page)
  await page.getByRole('button', { name: 'Validar seleção e gerar URL' }).click()
  await expect(page.getByLabel('URL oficial', { exact: true })).toHaveValue(/variaveis\/000101/)
  await page.getByRole('button', { name: 'Copiar URL oficial' }).click()
  await expect(page.getByText('URL copiada.', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('9001%5B01%5D')
  await page.getByRole('checkbox', { name: /202403/ }).check()
  await expect(page.getByLabel('URL oficial', { exact: true })).toHaveCount(0)
})
test('total explícito é limpo por exceção e nível limpa localidades', async ({ page }) => {
  await choose(page); await fill(page)
  await page.getByRole('checkbox', { name: /Total especial da API/ }).check()
  await page.getByRole('checkbox', { name: /102 ·/ }).check()
  await expect(page.getByRole('checkbox', { name: /Total especial da API/ })).toHaveCount(0)
  await page.getByRole('checkbox', { name: /102 ·/ }).uncheck()
  await expect(page.getByRole('checkbox', { name: /Total especial da API/ })).not.toBeChecked()
  await page.getByRole('combobox', { name: 'Nível publicado do agregado' }).selectOption('N123')
  await expect(page.getByRole('list', { name: 'Localidades selecionadas' }).getByRole('listitem')).toHaveCount(0)
})
test('resposta de validação obsoleta não restaura URL', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let started!: () => void
  const pending = new Promise<void>(resolve => { started = resolve })
  await page.route(`**${prefix}/consultas/validar/`, async route => { started(); await gate; await route.fulfill({ json: { data: { source_url: 'https://invalid.example', estimated_observations: 1 }, sources: [] } }).catch(() => {}) })
  await choose(page); await fill(page)
  await page.getByRole('button', { name: 'Validar seleção e gerar URL' }).click(); await pending
  await page.getByRole('checkbox', { name: /202403/ }).check(); release()
  await expect(page.getByLabel('URL oficial', { exact: true })).toHaveCount(0)
})
test('localidades: vazio e falha recuperável', async ({ page }) => {
  let mode = 'empty'
  await page.route(`**${prefix}/agregados/900001/localidades/**`, route => route.fulfill(mode === 'error' ? { status: 504, json: { error: { message: 'Falha local mock.' } } } : { json: { data: { items: [], pagination: { page: 1, total_count: 0, has_next: false } }, sources: [] } }))
  await choose(page)
  await expect(page.getByText('Nenhum item encontrado em Localidades da consulta.')).toBeVisible()
  mode = 'error'; await page.getByLabel('Buscar localidades por código ou nome', { exact: true }).fill('x')
  await expect(page.getByRole('alert')).toContainText('Falha local mock.')
  mode = 'empty'; await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByText('Nenhum item encontrado em Localidades da consulta.')).toBeVisible()
})

test('localidades: paginação preserva seleção e resposta obsoleta não altera nível', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let started!: () => void
  const pending = new Promise<void>(resolve => { started = resolve })
  await page.route(`**${prefix}/agregados/900001/localidades/**`, async route => {
    const params = new URL(route.request().url()).searchParams
    const level = params.get('nivel')
    if (params.get('q') === 'lento') { started(); await gate }
    const id = level === 'N123' ? '00123' : params.get('page') === '2' ? '0000002' : '0000001'
    await route.fulfill({ json: { data: { items: [{ id, nome: `Nome ${id}`, nivel_id: level, uf_sigla: null }], pagination: { page: Number(params.get('page')), total_count: 2, has_next: params.get('page') === '1' } }, sources: [] } }).catch(() => {})
  })
  await choose(page)
  await page.getByRole('checkbox', { name: /0000001/ }).check()
  await page.getByRole('button', { name: 'Próximas localidades' }).click()
  await page.getByRole('checkbox', { name: /0000002/ }).check()
  await expect(page.getByRole('list', { name: 'Localidades selecionadas' }).getByRole('listitem')).toHaveCount(2)
  await page.getByLabel('Buscar localidades por código ou nome', { exact: true }).fill('lento'); await pending
  await expect(page.getByText('Carregando dimensões…')).toBeVisible()
  await page.getByRole('combobox', { name: 'Nível publicado do agregado' }).selectOption('N123'); release()
  await expect(page.getByRole('checkbox', { name: /00123/ })).toBeVisible()
  await expect(page.getByRole('checkbox', { name: /0000001/ })).toHaveCount(0)
})

test('validação rejeitada não gera URL', async ({ page }) => {
  await page.route(`**${prefix}/consultas/validar/`, route => route.fulfill({ status: 422, json: { error: { code: 'query_too_large', message: 'Reduza o recorte mock.' } } }))
  await choose(page); await fill(page)
  await page.getByRole('button', { name: 'Validar seleção e gerar URL' }).click()
  await expect(page.getByRole('alert')).toContainText('Reduza o recorte mock.')
  await expect(page.getByLabel('URL oficial', { exact: true })).toHaveCount(0)
})

test('períodos: vazio e erro recuperável não habilitam validação', async ({ page }) => {
  let mode = 'error'
  await page.route(`**${prefix}/agregados/900001/periodos/`, route => route.fulfill(mode === 'error' ? { status: 502, json: { error: { message: 'Períodos indisponíveis mock.' } } } : { json: { data: { items: [] }, sources: [] } }))
  await choose(page)
  await expect(page.getByRole('alert')).toContainText('Períodos indisponíveis mock.')
  mode = 'empty'; await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByText('Nenhum item encontrado em Períodos da consulta.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Validar seleção e gerar URL' })).toBeDisabled()
})
