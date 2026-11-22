interface Option<T extends string> {
  value: T
  label: string
  count?: number
}

interface SegmentedControlProps<T extends string> {
  options: Option<T>[]
  value: T
  onChange: (value: T) => void
  ariaLabel: string
}

export function SegmentedControl<T extends string>({ options, value, onChange, ariaLabel }: SegmentedControlProps<T>) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="inline-flex flex-wrap gap-1 rounded-lg border border-line bg-white p-1">
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active ? 'bg-navy-800 text-white' : 'text-ink-muted hover:bg-navy-50 hover:text-navy-800'
            }`}
          >
            {opt.label}
            {opt.count !== undefined && (
              <span className={`tabular text-xs ${active ? 'text-navy-100' : 'text-ink-subtle'}`}>{opt.count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
