import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'

async function prepare(page: Page) {
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Pesquisa', exact: true }).selectOption('SINTETICA')
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('900001')
  for (const pattern of [/000101/, /102 ·/, /0000001/, /0000002/, /202401/, /202403/, /01 · Grupo A/, /02 · Grupo B/, /00 · Condição A/]) await page.getByRole('checkbox', { name: pattern }).check()
}
test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error })
  await page.route('https://**/*', route => { throw new Error(`External network forbidden ${route.request().url()}`) })
})

test('Buscar explícito integrado: grupos, homônimos, literais, edição e cache', async ({ page }) => {
  const calls: string[] = []
  page.on('request', r => { if (r.url().includes('consultas/executar')) calls.push(r.url()) })
  await prepare(page)
  await page.getByRole('button', { name: 'Validar seleção e gerar URL' }).click()
  await expect(page.getByLabel('URL oficial', { exact: true })).toBeVisible()
  expect(calls).toHaveLength(0)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  const result = page.getByRole('region', { name: 'Resultado aplicado' })
  await expect(result.getByRole('heading', { name: 'Tabela longa · 7 ocorrências' })).toBeVisible()
  await expect(result.getByRole('row')).toHaveCount(8)
  await expect(result.getByRole('cell', { name: 'X', exact: true })).toBeVisible()
  await expect(result.getByRole('cell', { name: '...', exact: true })).toBeVisible()
  await expect(result.getByRole('cell', { name: 'N6/0000001 · Localidade homônima', exact: true })).toHaveCount(4)
  await expect(result.getByRole('cell', { name: 'N6/0000002 · Localidade homônima', exact: true })).toHaveCount(3)
  await result.getByLabel('Combinação para gráfico e estatísticas').selectOption('3')
  await expect(result.getByText(/Lacunas \(não retornadas\): 202403/)).toBeVisible()
  await result.getByLabel('Variável do resultado').selectOption('102')
  await expect(result.getByRole('cell', { name: 'null (JSON)', exact: true })).toBeVisible()
  await expect(result.getByRole('cell', { name: '"" (vazio)', exact: true })).toBeVisible()
  await expect(result.getByRole('cell', { name: '-0.00', exact: true })).toBeVisible()
  await page.getByRole('checkbox', { name: /202403/ }).uncheck()
  await expect(result.getByText(/Alterações pendentes/)).toBeVisible()
  await expect(result.getByRole('row')).toHaveCount(9)
  expect(calls).toHaveLength(1)
  await page.getByRole('checkbox', { name: /202403/ }).check()
  await expect(result.getByText(/Alterações pendentes/)).toHaveCount(0)
  expect(calls).toHaveLength(1)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(result.getByText(/Alterações pendentes/)).toHaveCount(0)
  await result.getByText('Consulta aplicada e proveniência').click()
  await expect(result.getByText(/expira em .*cache/).first()).toBeVisible()
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('')
  await expect(result).toBeVisible()
  await expect(result.getByText(/Alterações pendentes/)).toBeVisible()
})

test('resposta obsoleta após edição não substitui último resultado', async ({ page }) => {
  await prepare(page)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  let release!: () => void, started!: () => void
  const gate = new Promise<void>(r => { release = r })
  const pending = new Promise<void>(r => { started = r })
  await page.route('**/consultas/executar/', async route => {
    const response = await route.fetch()
    const body = await response.json()
    body.data.consulta_aplicada.agregado_id = '999999'
    started(); await gate
    await route.fulfill({ json: body }).catch(() => {})
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click(); await pending
  await page.getByRole('checkbox', { name: /202403/ }).uncheck(); release()
  await expect(page.getByRole('heading', { name: 'Resultado · 900001' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Resultado · 999999' })).toHaveCount(0)
})

test('falha mantém resultado e Buscar recupera; vazio é sucesso distinto', async ({ page }) => {
  await prepare(page)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  await page.route('**/consultas/executar/', route => route.fulfill({ status: 504, json: { error: { message: 'Timeout simulado.' } } }))
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Timeout simulado.')
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    body.data.observacoes = []; body.data.analises = []
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByText('Nenhuma observação retornada para a consulta aplicada.')).toBeVisible()
})

test('captura oficial: conflito de unidade suspende gráfico e estatística, mantém literal', async ({ page }) => {
  const expected = JSON.parse(fs.readFileSync('../backend/agregados/tests/fixtures/derived/resultado_1712_esperado.json', 'utf8'))
  await prepare(page)
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    const a = body.data.analises[0]
    const row = expected.data.observacoes.find((r: { unidade_status: string }) => r.unidade_status === 'conflitante')
    body.data = { ...body.data, ...expected.data, analises: [{ ...a, variavel_id: row.variavel_id, localidade_id: row.localidade_id, nivel_id: row.nivel_id, classificacoes: row.classificacoes, suspensa: true, grafico_linhas: false, unidade: null, avisos: ['Unidade conflitante.'] }] }
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  const result = page.getByRole('region', { name: 'Resultado aplicado' })
  await expect(result.getByText('Estatísticas suspensas: unidade conflitante ou não confirmada.')).toBeVisible()
  await expect(result.getByRole('img')).toHaveCount(0)
  await expect(result.getByRole('cell', { name: '86804', exact: true })).toHaveCount(2)
  await expect(result.getByRole('cell', { name: /Toneladas/ })).toBeVisible()
})

test('mobile: tabela contida, gráfico acessível e lacunas sem ligação', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await prepare(page)
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    body.data.analises[0].pontos = [{ periodo_id: '202401', valor: 10, lacuna: false }, { periodo_id: '202402', valor: null, lacuna: true }, { periodo_id: '202403', valor: 10, lacuna: false }]
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  const result = page.getByRole('region', { name: 'Resultado aplicado' })
  await expect(result.getByRole('img')).toBeVisible()
  await expect(result.getByText('Resumo descritivo do recorte; a adequação da escala ao CV não foi certificada.')).toBeVisible()
  const path = await result.getByTestId('series-path').getAttribute('d')
  expect(path?.match(/M/g)).toHaveLength(2)
  expect(path).not.toContain('L')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const table = result.getByRole('region', { name: 'Tabela longa rolável' })
  await table.focus()
  await page.keyboard.press('ArrowRight')
  await expect.poll(() => table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
  await table.evaluate(el => { el.scrollLeft = 0 })
  await result.screenshot({ path: '../var/phase4-mobile.png' })
})

test('tabela pagina ocorrências e cronologia desconhecida suspende linhas', async ({ page }) => {
  await prepare(page)
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    body.data.observacoes = Array.from({ length: 61 }, (_, i) => ({ ...body.data.observacoes[0], valor_original: `ocorrência ${i}` }))
    body.data.analises[0].grafico_linhas = false
    body.data.analises[0].avisos = ['Cronologia não confirmada.']
    await route.fulfill({ json: body })
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  const result = page.getByRole('region', { name: 'Resultado aplicado' })
  await expect(result.getByRole('img')).toHaveCount(0)
  await expect(result.getByText('Gráfico de linhas suspenso. Cronologia não confirmada.')).toBeVisible()
  await expect(result.getByRole('row')).toHaveCount(51)
  await result.getByRole('button', { name: 'Próximas observações' }).click()
  await expect(result.getByRole('row')).toHaveCount(12)
  await expect(result.getByRole('cell', { name: 'ocorrência 60', exact: true })).toBeVisible()
  await expect(result.getByRole('button', { name: 'Próximas observações' })).toBeDisabled()
})

test('troca de agregado durante execução descarta resposta obsoleta', async ({ page }) => {
  await prepare(page)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Resultado aplicado' })).toBeVisible()
  let release!: () => void, started!: () => void
  const gate = new Promise<void>(r => { release = r })
  const pending = new Promise<void>(r => { started = r })
  await page.route('**/consultas/executar/', async route => {
    const body = await (await route.fetch()).json()
    body.data.consulta_aplicada.agregado_id = '999999'
    started(); await gate
    await route.fulfill({ json: body }).catch(() => {})
  })
  await page.getByRole('button', { name: 'Buscar', exact: true }).click(); await pending
  await page.getByRole('combobox', { name: 'Agregado', exact: true }).selectOption('')
  release()
  await expect(page.getByRole('region', { name: 'Editor de consulta' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Resultado · 900001' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Resultado · 999999' })).toHaveCount(0)
})
