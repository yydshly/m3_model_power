export function JsonView({ data }: { data: unknown }) {
  return (
    <pre className="text-xs bg-slate-900 text-slate-100 rounded p-3 overflow-auto max-h-[480px]">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}
