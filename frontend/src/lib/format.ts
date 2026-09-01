export function formatINR(amount: number): string {
  if (Math.abs(amount) >= 100000) return `₹${(amount / 100000).toFixed(2)}L`
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export const ACTION_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  allow: { bg: 'bg-slate-100', text: 'text-slate-700', dot: 'bg-slate-400', label: 'Allow' },
  monitor: { bg: 'bg-sky-50', text: 'text-sky-700', dot: 'bg-sky-500', label: 'Monitor' },
  verify: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', label: 'Verify' },
  investigate_cluster: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', label: 'Investigate Cluster' },
  hold: { bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500', label: 'Hold' },
  block: { bg: 'bg-risk-50', text: 'text-risk-700', dot: 'bg-risk-600', label: 'Block' },
}

export function actionStyle(action: string) {
  return ACTION_STYLES[action] ?? { bg: 'bg-slate-100', text: 'text-slate-700', dot: 'bg-slate-400', label: action }
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-risk-500'
  if (confidence >= 0.5) return 'bg-amber-500'
  return 'bg-slate-400'
}

export const RECOMMENDATION_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  CONTEST: { bg: 'bg-brand-50', text: 'text-brand-700', dot: 'bg-brand-500', label: 'Contest' },
  ACCEPT: { bg: 'bg-risk-50', text: 'text-risk-700', dot: 'bg-risk-600', label: 'Accept' },
  ESCALATE: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', label: 'Escalate' },
}

export function recommendationStyle(recommendation: string) {
  return RECOMMENDATION_STYLES[recommendation] ?? { bg: 'bg-slate-100', text: 'text-slate-700', dot: 'bg-slate-400', label: recommendation }
}

export const REASON_CODE_LABELS: Record<string, string> = {
  non_receipt: 'Non-Receipt',
  not_as_described: 'Not as Described',
  quality_issue: 'Quality Issue',
  unauthorized: 'Unauthorized',
  duplicate_charge: 'Duplicate Charge',
}

export function reasonCodeLabel(code: string): string {
  return REASON_CODE_LABELS[code] ?? code
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  coordinated_return_ring: 'Coordinated Return Ring',
  coordinated_abuse: 'Coordinated Abuse',
  fraud_spike: 'Fraud Spike',
  chargeback_wave: 'Chargeback Wave',
  return_spike: 'Return Spike',
}

export function eventTypeLabel(eventType: string): string {
  return EVENT_TYPE_LABELS[eventType] ?? eventType
}
