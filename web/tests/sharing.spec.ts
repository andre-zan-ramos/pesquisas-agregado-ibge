import { test, expect, type Page, type Download } from '@playwright/test'
import fs from 'node:fs/promises'

const query = { agregado_id: '900001', nivel_id: 'N6', localidade_ids: ['0000001', '0000002'], variavel_ids: ['000101', '102'], periodo_ids: ['202401', '202403'], classificacoes: [{ classificacao_id: '9001', categoria_ids: ['01', '02'] }, { classificacao_id: '9002', categoria_ids: ['00'] }] }
const document = (consulta: unknown = query) => JSON.stringify({ version: 1, consulta })
const link = (consulta: unknown = query) => '/#' + new URLSearchParams({ consulta: document(consulta) })
const text = async (download: Download) => fs.readFile((await download.path())!, 'utf8')
async function exportFile(page: Page, button: string) {
  const downloaded = page.waitForEvent('download')
  await page.getByRole('button', { name: button, exact: true }).click()
  return text(await downloaded)
}
test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error })
  await page.route('https://**/*', route => { throw new Error(`External network forbidden ${route.request().url()}`) })
})

test('URL restaura e revalida todas as dimensões; somente Buscar executa; link oficial copiável', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  const executed: string[] = [], validated: unknown[] = []
  page.on('request', r => {
    if (r.url().includes('/executar/')) executed.push(r.url())
    if (r.url().includes('/validar/')) validated.push(r.postDataJSON())
  })
  await page.goto(link())
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  expect(validated.length).toBeGreaterThan(0)
  for (const submitted of validated) expect(submitted).toEqual(query)
  expect(executed).toHaveLength(0)
  for (const code of [/000101/, /102 ·/, /0000001/, /0000002/, /202401/, /202403/, /01 · Grupo A/, /02 · Grupo B/, /00 · Condição A/]) await expect(page.getByRole('checkbox', { name: code })).toBeChecked()
  await page.getByRole('button', { name: 'Copiar URL oficial', exact: true }).click()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('/variaveis/000101|102')
  await page.getByRole('button', { name: 'Copiar link da aplicação' }).click()
  const shared = await page.evaluate(() => navigator.clipboard.readText())
  await page.goto(shared)
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  expect(executed).toHaveLength(0)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  expect(executed).toHaveLength(1)
})

test('importação estrita rejeita tipos, campos, versões, duplicatas e tamanho; resultado permanece', async ({ page }) => {
  await page.goto(link()); await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  for (const content of [document({ ...query, agregado_id: 900001 }), document({ ...query, url: 'https://evil.test' }), document({ ...query, periodo_ids: [] }), document({ ...query, localidade_ids: ['0000001', '0000001'] }), JSON.stringify({ version: 2, consulta: query }), document().replace('"version":1', '"version":1,"version":1'), 'x'.repeat(65537), '{']) {
    await page.getByLabel('Importar JSON de consulta').setInputFiles({ name: 'consulta.json', mimeType: 'application/json', buffer: Buffer.from(content) })
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Resultado · 900001' })).toBeVisible()
  }
  await page.getByLabel('Importar JSON de consulta').setInputFiles({ name: 'consulta.json', mimeType: 'application/json', buffer: Buffer.from(document({ ...query, periodo_ids: ['202401'] })) })
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await expect(page.getByText(/Alterações pendentes/)).toBeVisible()
  expect(JSON.parse(await exportFile(page, 'Exportar JSON de consulta')).consulta.periodo_ids).toEqual(['202401'])
})

test('revalidação semântica rejeita cada dimensão e orçamento sem séries', async ({ page }) => {
  let executions = 0
  page.on('request', r => { if (r.url().includes('/executar/')) executions++ })
  for (const invalid of [{ ...query, variavel_ids: ['999'] }, { ...query, localidade_ids: ['999'] }, { ...query, periodo_ids: ['999'] }, { ...query, nivel_id: 'N999' }, { ...query, classificacoes: [] }, { ...query, classificacoes: [{ classificacao_id: '9001', categoria_ids: ['999'] }, query.classificacoes[1]] }, { ...query, variavel_ids: ['1','2','3','4','5','6','7'] }]) {
    await page.goto(link(invalid))
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Buscar', exact: true })).toBeDisabled()
    await expect(page.getByRole('region', { name: 'Consulta validada' })).toHaveCount(0)
  }
  expect(executions).toBe(0)
})

test('exporta envelope literal completo e CSV de todas as ocorrências, além da página e variável', async ({ page }) => {
  await page.goto(link()); await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  let expected: any
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    const originals = body.data.observacoes
    const unsafe = ['=1+1', '+SUM(A1)', '-0.00', '@SUM(A1)', '\t=1', '\r=2', '  =3', 'a,"b"\nc', null, '']
    body.data.observacoes = [...originals, ...Array.from({ length: 61 }, (_, i) => ({ ...originals[0], valor_original: unsafe[i % unsafe.length], origem_indice: { variavel: 0, resultado: 0, serie: i + 2 } }))]
    expected = JSON.parse(JSON.stringify(body))
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  await page.getByRole('button', { name: 'Próximas observações' }).click()
  await page.getByLabel('Variável do resultado').selectOption('102')
  await page.getByRole('checkbox', { name: /202403/ }).uncheck()
  const json = JSON.parse(await exportFile(page, 'Exportar JSON com proveniência'))
  expect(json).toEqual(expected)
  const csv = await exportFile(page, 'Exportar CSV completo')
  expect(csv.charCodeAt(0)).toBe(0xfeff)
  // Parse quoted CSV, including embedded newlines and escaped quotes.
  const records: string[][] = []; let record: string[] = [], cell = '', quoted = false
  for (let i = 1; i < csv.length; i++) {
    const c = csv[i]
    if (c === '"') { if (quoted && csv[i + 1] === '"') { cell += '"'; i++ } else quoted = !quoted }
    else if (!quoted && c === ',') { record.push(cell); cell = '' }
    else if (!quoted && c === '\r' && csv[i+1] === '\n') { record.push(cell); records.push(record); record = []; cell = ''; i++ }
    else cell += c
  }
  expect(records).toHaveLength(expected.data.observacoes.length + 1)
  const index = (name: string) => records[0].indexOf(name)
  expect(records.slice(1).some(r => r[index('variavel_id')] === '000101')).toBe(true)
  expect(records.slice(1).some(r => r[index('variavel_id')] === '102')).toBe(true)
  for (const literal of ["'=1+1", "'+SUM(A1)", "'-0.00", "'@SUM(A1)", "'\t=1", "'\r=2", "'  =3", 'a,"b"\nc', 'null', '']) expect(records.slice(1).map(r => r[index('valor_original')])).toContain(literal)
  for (let i = 0; i < expected.data.observacoes.length; i++) {
    expect(JSON.parse(records[i+1][index('origem_indice')])).toEqual(expected.data.observacoes[i].origem_indice)
    expect(JSON.parse(records[i+1][index('classificacoes')])).toEqual(expected.data.observacoes[i].classificacoes)
    expect(JSON.parse(records[i+1][index('sources')])).toEqual(expected.sources)
  }
})

test('link excessivo oferece JSON importável e zero negativo é preservado', async ({ page }) => {
  await page.goto(link()); await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await page.evaluate(async () => {
    const { queryLink, queryJSON, parseQuery, literalJSON } = await import('/src/query-transfer.ts')
    if (!Object.is(JSON.parse(literalJSON({ number: -0 })).number, -0)) throw Error('Zero negativo perdido')
    const draft = parseQuery(new URLSearchParams(location.hash.slice(1)).get('consulta')!)
    draft.periodo_ids = Array.from({ length: 300 }, (_, i) => String(100000+i))
    if (queryLink(draft) !== null || JSON.stringify(parseQuery(queryJSON(draft))) !== JSON.stringify(draft)) throw Error('Fallback inválido')
  })
  await page.route('**/consultas/validar/', async route => {
    const body = await (await route.fetch()).json()
    body.data.consulta_resolvida.periodo_ids = Array.from({ length: 300 }, (_, i) => String(100000+i))
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Validar seleção e gerar URL' }).click()
  await expect(page.getByText(/A URL excede/)).toBeVisible()
  expect(JSON.parse(await exportFile(page, 'Exportar JSON de consulta')).consulta.periodo_ids).toHaveLength(300)
})

test('resultado vazio exporta cabeçalho e JSON completo; falha de clipboard mantém campo copiável', async ({ page }) => {
  await page.goto(link()); await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await page.evaluate(() => { Object.defineProperty(navigator.clipboard, 'writeText', { value: () => Promise.reject(Error('Indisponível')) }) })
  await page.getByRole('button', { name: 'Copiar link da aplicação' }).click()
  await expect(page.getByText('Selecione e copie o link no campo.')).toBeVisible()
  await expect(page.getByLabel('URL da aplicação')).toBeVisible()
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json(); body.data.observacoes = []; body.data.analises = []
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByText('Nenhuma observação retornada para a consulta aplicada.')).toBeVisible()
  expect((await exportFile(page, 'Exportar CSV completo')).split('\r\n')).toHaveLength(2)
  expect(JSON.parse(await exportFile(page, 'Exportar JSON com proveniência')).data.observacoes).toEqual([])
})

test('mudança de URL durante execução cancela resposta antiga e preserva resultado', async ({ page }) => {
  await page.goto(link()); await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Resultado · 900001' })).toBeVisible()
  let release!: () => void, started!: () => void
  const gate = new Promise<void>(r => { release = r }), pending = new Promise<void>(r => { started = r })
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json(); body.data.consulta_aplicada.agregado_id = '999999'
    started(); await gate; await route.fulfill({ json: body }).catch(() => {})
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click(); await pending
  await page.evaluate(hash => { location.hash = hash }, link({ ...query, periodo_ids: ['202401'] }).slice(2))
  release()
  await expect(page.getByRole('region', { name: 'Consulta validada' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Resultado · 900001' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Resultado · 999999' })).toHaveCount(0)
  await expect(page.getByText(/Alterações pendentes/)).toBeVisible()
})
