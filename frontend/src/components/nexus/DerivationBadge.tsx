/**
 * Derivation class badge: Fact / Derived / Hypothesis.
 */
import { ShieldCheck, GitFork, ShieldQuestion } from 'lucide-react'

const CONFIG: Record<string, { icon: typeof ShieldCheck; style: string; label: string }> = {
  FACT: { icon: ShieldCheck, style: 'border-emerald-300 bg-emerald-50 text-emerald-800', label: 'Fact' },
  DERIVED: { icon: GitFork, style: 'border-blue-300 bg-blue-50 text-blue-800', label: 'Derived' },
  HYPOTHESIS: { icon: ShieldQuestion, style: 'border-amber-300 bg-amber-50 text-amber-900', label: 'Hypothesis' },
}

export function DerivationBadge({ klass, size = 'sm' }: { klass: string; size?: 'xs' | 'sm' }) {
  const cfg = CONFIG[klass] ?? CONFIG.FACT
  const Icon = cfg.icon
  const sizeClass = size === 'xs' ? 'text-[8px] px-1 py-px gap-0.5' : 'text-[10px] px-1.5 py-0.5 gap-1'
  return (
    <span className={`inline-flex items-center rounded-md border font-bold uppercase tracking-wider ${cfg.style} ${sizeClass}`}>
      <Icon className={size === 'xs' ? 'h-2.5 w-2.5' : 'h-3 w-3'} />
      {cfg.label}
    </span>
  )
}
