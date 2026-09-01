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

export const ACTION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  allow: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Allow' },
  monitor: { bg: 'bg-sky-100', text: 'text-sky-700', label: 'Monitor' },
  verify: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Verify' },
  investigate_cluster: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Investigate Cluster' },
  hold: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Hold' },
  block: { bg: 'bg-red-100', text: 'text-red-800', label: 'Block' },
}

export function actionStyle(action: string) {
  return ACTION_STYLES[action] ?? { bg: 'bg-gray-100', text: 'text-gray-700', label: action }
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-red-500'
  if (confidence >= 0.5) return 'bg-amber-500'
  return 'bg-gray-400'
}

export const RECOMMENDATION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  CONTEST: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Contest' },
  ACCEPT: { bg: 'bg-red-100', text: 'text-red-800', label: 'Accept' },
  ESCALATE: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Escalate' },
}

export function recommendationStyle(recommendation: string) {
  return RECOMMENDATION_STYLES[recommendation] ?? { bg: 'bg-gray-100', text: 'text-gray-700', label: recommendation }
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
