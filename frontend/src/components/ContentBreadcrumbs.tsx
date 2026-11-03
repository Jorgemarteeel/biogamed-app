import Link from "next/link";

export default function ContentBreadcrumbs({ subject, block }: { subject?: { id: number; name: string } | null; block?: { name: string } | null }) {
  const items = [
    { label: "Panel", href: "/dashboard" },
    { label: "Asignaturas", href: subject ? "/gestion/asignaturas" : undefined },
    ...(subject ? [{ label: subject.name, href: block ? `/gestion/asignaturas/${subject.id}` : undefined }] : []),
    ...(block ? [{ label: block.name, href: undefined }] : []),
  ];
  return <nav aria-label="Ruta de gestión"><ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold">
    {items.map((item, index) => <li key={`${index}-${item.label}`} className="flex min-w-0 items-center gap-2">
      {index > 0 && <span aria-hidden="true" className="text-slate-400">›</span>}
      {item.href ? <Link href={item.href} className="text-link inline-flex min-h-11 items-center break-words">{item.label}</Link>
        : <span aria-current="page" className="break-words text-blue-950">{item.label}</span>}
    </li>)}
  </ol></nav>;
}
