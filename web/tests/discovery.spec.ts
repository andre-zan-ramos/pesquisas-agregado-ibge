import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const prefix = '/api/v1/agregados-ibge'
const metadata = JSON.parse(readFileSync(new URL('../../backend/agregados/tests/fixtures/synthetic/metadados_normalizados.json', import.meta.url), 'utf8'))
const envelope = (data: unknown) => ({ data, sources: [] })
const catalog = (id = '900001') => envelope({ items: [{ id: 'SINTETICA', nome: 'Pesquisa sintética', agregados: [{ id, nome: `Agregado ${id}` }] }], pagination: { page: 1, page_size: 50, total_count: 1, has_next: false } })
const fulfill = (data: unknown) => ({ json: data })

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', route => { throw new Error(`Rede externa proibida: ${route.request().url()}`) })
  page.on('pageerror', error => { throw error })
  page.on('request', request => {
    expect(request.url()).not.toMatch(/\/consultas\/|\/variaveis\/|\/localidades\//)
  })
})

async function choose(page: import('@playwright/test').Page) {
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  await expect(page.getByRole('heading', { name: /900001/ })).toBeVisible()
}

test('Django com transporte mock: domínios, seleção e metadados completos', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('combobox', { name: 'Nível de descoberta', exact: true })).toHaveValue('N6')
  await choose(page)
  await expect(page.getByRole('combobox', { name: 'Nível publicado do agregado', exact: true })).toHaveValue('N6')
  await expect(page.getByRole('heading', { name: 'IBGE', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Especial', exact: true })).toBeVisible()
  await page.getByText('Variáveis e unidades (2)', { exact: true }).click()
  await expect(page.getByRole('heading', { name: '000101 · Indicador sintético A' })).toBeVisible()
  await page.getByText('Classificações e categorias (2)', { exact: true }).click()
  await expect(page.getByText(/Variáveis com exceção de total: 102/)).toBeVisible()
  await expect(page.getByText(/00 · Condição A/)).toBeVisible()
  await page.getByText('Períodos publicados (2)', { exact: true }).click()
  await expect(page.getByText(/202401 · Janeiro 2024 \/ Jan 2024/)).toBeVisible()
})

test('busca por código/nome e filtros limpam seleções', async ({ page }) => {
  await page.goto('/')
  await choose(page)
  await page.getByRole('textbox', { name: 'Buscar assunto por código ou nome', exact: true }).fill('001')
  await page.getByRole('combobox', { name: 'Assunto', exact: true }).selectOption('001')
  await expect(page.getByRole('combobox', { name: 'Pesquisa', exact: true })).toHaveValue('')
  await expect(page.getByRole('heading', { name: /900001/ })).toHaveCount(0)
  await page.getByRole('textbox', { name: 'Buscar pesquisas e agregados por código ou nome', exact: true }).fill('900001')
  await choose(page)
  await page.getByRole('combobox', { name: 'Período de descoberta', exact: true }).selectOption('202403')
  await expect(page.getByRole('combobox', { name: 'Agregado', exact: true })).toHaveValue('')
  await page.getByRole('combobox', { name: 'Nível de descoberta', exact: true }).selectOption('N123')
  await expect(page.getByRole('combobox', { name: 'Pesquisa', exact: true })).toHaveValue('')
})

test('carregamento, vazio, erro e recuperação são distintos', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let mode = 'loading'
  await page.route(`**${prefix}/pesquisas/**`, async route => {
    if (mode === 'loading') await gate
    if (mode === 'error') await route.fulfill({ status: 504, json: { error: { code: 'upstream_timeout', message: 'Tempo excedido no mock.' } } })
    else await route.fulfill(fulfill(mode === 'success' ? catalog() : envelope({ items: [], pagination: { page: 1, page_size: 50, total_count: 0, has_next: false } })))
  })
  await page.goto('/')
  await expect(page.getByText('Carregando…', { exact: true })).toBeVisible()
  release()
  await expect(page.getByText('Nenhuma pesquisa encontrada para os filtros.')).toBeVisible()
  mode = 'error'
  await page.getByRole('combobox', { name: 'Assunto', exact: true }).selectOption('001')
  await expect(page.getByRole('alert')).toContainText('Tempo excedido no mock.')
  await expect(page.getByText('Nenhuma pesquisa encontrada para os filtros.')).toHaveCount(0)
  mode = 'success'
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await choose(page)
})

test('catálogo obsoleto não substitui filtro atual', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let started!: () => void
  const pending = new Promise<void>(resolve => { started = resolve })
  await page.route(`**${prefix}/pesquisas/**`, async route => {
    if (new URL(route.request().url()).searchParams.get('assunto') === '001') {
      started(); await gate
      await route.fulfill(fulfill(catalog('111111'))).catch(() => {})
    } else await route.fulfill(fulfill(catalog()))
  })
  await page.goto('/')
  await choose(page)
  await page.getByRole('combobox', { name: 'Assunto', exact: true }).selectOption('001')
  await pending
  await page.getByRole('combobox', { name: 'Assunto', exact: true }).selectOption('')
  release()
  await choose(page)
  await expect(page.getByRole('option', { name: /111111/ })).toHaveCount(0)
})

test('metadados obsoletos não substituem outro agregado', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let started!: () => void
  const pending = new Promise<void>(resolve => { started = resolve })
  await page.route(`**${prefix}/pesquisas/**`, route => route.fulfill(fulfill(envelope({ items: [{ id: 'SINTETICA', nome: 'Pesquisa', agregados: [{ id: '900001', nome: 'Primeiro' }, { id: '900002', nome: 'Segundo' }] }], pagination: { page: 1, page_size: 50, total_count: 1, has_next: false } }))))
  await page.route(`**${prefix}/agregados/*/metadados/`, async route => {
    if (route.request().url().includes('/900001/')) { started(); await gate; await route.fulfill(fulfill(envelope(metadata))).catch(() => {}) }
    else await route.fulfill(fulfill(envelope({ ...metadata, id: '900002', nome: 'Segundo', niveis: [{ id: 'N123', nome: null, grupo: 'Novo' }] })))
  })
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  await pending
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900002')
  await expect(page.getByRole('heading', { name: '900002 · Segundo' })).toBeVisible()
  release()
  await expect(page.getByRole('combobox', { name: 'Nível publicado do agregado', exact: true })).toHaveValue('')
  await expect(page.getByText('Grupo adicional publicado pela fonte.')).toBeVisible()
  await expect(page.getByRole('heading', { name: /900001/ })).toHaveCount(0)
})

test('falha de domínios recuperável e N6 ausente pede escolha', async ({ page }) => {
  let fail = true
  await page.route(`**${prefix}/dominios/`, route => route.fulfill(fail ? { status: 502, json: { error: { message: 'Domínios indisponíveis.' } } } : fulfill(envelope({ assuntos: [], niveis: [{ id: 'N1', nome: 'Brasil' }], periodos: [] }))))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Domínios indisponíveis.')
  fail = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('combobox', { name: 'Nível de descoberta', exact: true })).toHaveValue('')
})

test('falha de metadados recuperável', async ({ page }) => {
  let fail = true
  await page.route(`**${prefix}/agregados/900001/metadados/`, route => route.fulfill(fail ? { status: 502, json: { error: { message: 'Metadados indisponíveis.' } } } : fulfill(envelope(metadata))))
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  await expect(page.getByRole('alert')).toContainText('Metadados indisponíveis.')
  fail = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('heading', { name: /900001/ })).toBeVisible()
})

test('mobile sem overflow horizontal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await choose(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: '../var/phase2-mobile.png', fullPage: true })
})

test('paginação e troca de pesquisa limpam agregado', async ({ page }) => {
  await page.route(`**${prefix}/pesquisas/**`, route => {
    const pageNumber = Number(new URL(route.request().url()).searchParams.get('page'))
    return route.fulfill(fulfill(envelope({ items: pageNumber === 1 ? [
      { id: 'SINTETICA', nome: 'Pesquisa sintética', agregados: [{ id: '900001', nome: 'Primeiro' }] },
      { id: 'VAZIA', nome: 'Pesquisa sem agregados', agregados: [] },
    ] : [{ id: 'SEGUNDA', nome: 'Outra página', agregados: [] }], pagination: { page: pageNumber, page_size: 50, total_count: 51, has_next: pageNumber === 1 } })))
  })
  await page.goto('/')
  await choose(page)
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('VAZIA')
  await expect(page.getByRole('combobox', { name: 'Agregado', exact: true })).toHaveValue('')
  await expect(page.getByText('Nenhum agregado publicado nesta pesquisa.')).toBeVisible()
  await page.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page.getByRole('option', { name: 'SEGUNDA · Outra página', exact: true })).toHaveCount(1)
  await expect(page.getByRole('combobox', { name: 'Pesquisa', exact: true })).toHaveValue('')
  await expect(page.getByRole('button', { name: 'Próxima', exact: true })).toBeDisabled()
})

test('busca local não altera IDs e aceita nome do agregado', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Buscar pesquisa por código ou nome', exact: true }).fill('sintética')
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('textbox', { name: 'Buscar agregado por código ou nome', exact: true }).fill('classificações')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  await expect(page.getByRole('heading', { name: /900001/ })).toBeVisible()
  await page.getByRole('textbox', { name: 'Buscar pesquisas e agregados por código ou nome', exact: true }).fill('inexistente')
  await expect(page.getByText('Nenhuma pesquisa encontrada para os filtros.')).toBeVisible()
  await expect(page.getByRole('heading', { name: /900001/ })).toHaveCount(0)
})
