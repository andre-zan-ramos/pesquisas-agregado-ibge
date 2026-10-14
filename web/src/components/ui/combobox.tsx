import { Check, ChevronDown, LoaderCircle, Search } from 'lucide-react'
import { type KeyboardEvent, type RefObject, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from './popover'

export type ComboboxOption = { label: string; value: string }

type ComboboxProps = {
  'aria-label': string
  disabled?: boolean
  emptyMessage?: string
  loading?: boolean
  maxVisibleItems?: number
  onChange: (value: string) => void
  onOpenChange?: (open: boolean) => void
  options: ComboboxOption[]
  portalContainerRef?: RefObject<HTMLElement | null>
  searchPlaceholder?: string
  value: string
}

function normalizeSearch(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR')
}

export function Combobox({ 'aria-label': ariaLabel, disabled = false, emptyMessage = 'Nenhuma opção encontrada.', loading = false, maxVisibleItems = 10, onChange, onOpenChange, options, portalContainerRef, searchPlaceholder = 'Pesquisar…', value }: ComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const listboxId = useId()
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const selected = options.find((option) => option.value === value)
  const filteredOptions = useMemo(() => {
    const normalizedQuery = normalizeSearch(query.trim())
    return normalizedQuery ? options.filter((option) => normalizeSearch(option.label).includes(normalizedQuery)) : options
  }, [options, query])

  useEffect(() => {
    if (!open) return
    const selectedIndex = filteredOptions.findIndex((option) => option.value === value)
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0)
  }, [filteredOptions, open, value])

  useEffect(() => {
    if (open) menuRef.current?.querySelector<HTMLElement>(`[data-option-index="${activeIndex}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, open])

  const changeOpen = (nextOpen: boolean) => {
    setOpen(nextOpen)
    onOpenChange?.(nextOpen)
    if (!nextOpen) setQuery('')
  }
  const close = () => {
    changeOpen(false)
    triggerRef.current?.focus()
  }
  const selectOption = (option: ComboboxOption) => {
    onChange(option.value)
    close()
  }
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Escape' && open) {
      event.preventDefault(); close()
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (!open) { changeOpen(true); return }
      const direction = event.key === 'ArrowDown' ? 1 : -1
      setActiveIndex((current) => filteredOptions.length ? (current + direction + filteredOptions.length) % filteredOptions.length : 0)
    } else if (event.key === 'Enter' && open && filteredOptions[activeIndex]) {
      event.preventDefault(); selectOption(filteredOptions[activeIndex])
    }
  }

  return <Popover onOpenChange={changeOpen} open={open}><div className="combobox">
    <PopoverTrigger asChild><button aria-activedescendant={open && filteredOptions[activeIndex] ? `${listboxId}-${activeIndex}` : undefined} aria-busy={loading || undefined} aria-controls={listboxId} aria-expanded={open} aria-haspopup="listbox" aria-label={ariaLabel} className="combobox-trigger" disabled={disabled || loading} onKeyDown={handleKeyDown} ref={triggerRef} role="combobox" title={loading ? 'Carregando…' : selected?.label ?? options[0]?.label ?? ''} type="button"><span>{loading ? 'Carregando…' : selected?.label ?? options[0]?.label ?? ''}</span>{loading ? <LoaderCircle aria-hidden="true" className="spin" size={15} /> : <ChevronDown aria-hidden="true" size={16} />}</button></PopoverTrigger>
    <PopoverContent align="start" className="combobox-menu" container={portalContainerRef?.current} onKeyDown={handleKeyDown} ref={menuRef} style={{ maxHeight: 'var(--radix-popover-content-available-height)', width: 'var(--radix-popover-trigger-width)' }}>
      <label className="combobox-search"><Search aria-hidden="true" size={15} /><span className="sr-only">Pesquisar {ariaLabel}</span><input autoFocus onChange={(event) => setQuery(event.target.value)} placeholder={searchPlaceholder} type="search" value={query} /></label>
      <div className="combobox-options" id={listboxId} role="listbox" style={{ maxHeight: `${maxVisibleItems * 36 + 8}px` }}>{filteredOptions.length ? filteredOptions.map((option, index) => <button aria-selected={option.value === value} className={`combobox-option ${index === activeIndex ? 'active' : ''}`} data-option-index={index} id={`${listboxId}-${index}`} key={option.value} onClick={() => selectOption(option)} onMouseEnter={() => setActiveIndex(index)} role="option" tabIndex={-1} title={option.label} type="button"><Check aria-hidden="true" className={option.value === value ? '' : 'hidden-check'} size={15} /><span>{option.label}</span></button>) : <p className="combobox-empty">{emptyMessage}</p>}</div>
    </PopoverContent>
  </div></Popover>
}
