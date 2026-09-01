export interface IncidentSummary {
  event_id: string
  source: 'cluster' | 'temporal'
  event_type: string
  merchant_id: string
  merchant_name: string
  start_time: string
  detection_time: string
  confidence: number
  exposure_estimate: number
  affected_transaction_count: number
  affected_customer_count: number
  primary_driver: string | null
  recommended_action: string
}

export interface CommandCenterResponse {
  merchant_id: string
  current_exposure: number
  preventable_exposure: number
  active_incidents: number
  total_incidents: number
  net_benefit_vs_allow: number
  incidents: IncidentSummary[]
}

export interface EvidenceItem {
  id: string
  claim: string
  data: Record<string, unknown>
}

export interface GroundTruth {
  n_true_loss: number
  n_edge_case: number
  n_normal: number
  purity: number
  dominant_true_scenario: string | null
}

export interface PolicySimulation {
  action: string
  n_transactions_affected: number
  n_transactions_total: number
  expected_loss_prevented: number
  expected_residual_loss: number
  expected_legitimate_orders_affected: number
  false_positive_cost: number
  operational_cost: number
  net_benefit: number
}

export interface Counterfactual {
  recommended_action: string
  simulations: PolicySimulation[]
}

export interface Investigation {
  incident_summary: string
  primary_hypothesis: string
  supporting_evidence: string[]
  contradicting_evidence: string[]
  unknowns: string[]
  recommended_next_step: string
  confidence_commentary: string
  _source: 'llm' | 'deterministic_fallback'
  _fallback_reason?: string
}

export interface LinkedChargeback {
  case_id: string
  reason_code: string
  recommendation: string
  amount: number
}

export interface IncidentDetail extends IncidentSummary {
  gross_amount_at_risk: number
  affected_entity_count: number
  evidence: EvidenceItem[]
  transaction_ids: string[]
  ground_truth: GroundTruth
  counterfactual: Counterfactual
  investigation?: Investigation
  linked_chargebacks: LinkedChargeback[]
}

export interface ChargebackEvidenceItem {
  type: string
  status: 'present' | 'missing'
  detail: string
}

export interface Contradiction {
  type: string
  description: string
}

export interface ChargebackDraft {
  case_summary: string
  response_text: string
  evidence_notes: string[]
  caveats: string[]
  _source: 'llm' | 'deterministic_fallback'
  _fallback_reason?: string
}

export interface ChargebackCaseSummary {
  case_id: string
  transaction_id: string
  merchant_id: string
  merchant_name: string
  amount: number
  reason_code: string
  disputed_at: string
  recommendation: string
  evidence_completeness: number
  has_contradictions: boolean
  linked_loss_event: { event_id: string; event_type: string; confidence: number } | null
}

export interface ChargebackListResponse {
  total_cases: number
  recommendation_counts: Record<string, number>
  cases: ChargebackCaseSummary[]
}

export interface ChargebackCaseDetail extends ChargebackCaseSummary {
  customer_id: string
  order_timestamp: string
  evidence: ChargebackEvidenceItem[]
  contradictions: Contradiction[]
  recommendation_reasoning: string
  transaction_fused_score: number
  customer_context: {
    prior_transaction_count: number
    prior_successful_deliveries: number
    is_established: boolean
  }
  draft: ChargebackDraft
}

export interface GraphNode {
  id: string
  type: string
  label: string
  segment?: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  frequency: number
  confidence: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface Merchant {
  merchant_id: string
  name: string
  category: string
  risk_tolerance: string
  incident_count: number
}
