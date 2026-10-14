import type { Page } from '@playwright/test'

export async function selectCatalogOption(page: Page, label: string, value: string) {
  await page.getByRole('combobox', { name: label, exact: true }).click()
  await page.getByRole('listbox').getByRole('option', { name: label === 'Ano da pesquisa' ? value : value ? new RegExp(`^${value} ·`) : 'Selecione…', exact: !value || label === 'Ano da pesquisa' }).click()
}
