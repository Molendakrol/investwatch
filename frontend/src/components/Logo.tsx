export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-3.5">
      <span className="text-[1.375rem] font-bold tracking-tight text-navy-800">InvestWatch</span>
      {!compact && (
        <>
          <span aria-hidden className="h-9 w-px bg-navy-800" />
          <span className="text-[0.625rem] font-semibold uppercase leading-[1.25] tracking-[0.08em] text-navy-800">
            System analizy
            <br />
            materiałów
            <br />
            inwestycyjnych
          </span>
        </>
      )}
    </span>
  )
}
