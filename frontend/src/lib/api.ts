/**
 * API client for LossGraph frontend
 */

import axios from 'axios'
import type {
  CommandCenterResponse, GraphData, IncidentDetail, Merchant,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const incidentApi = {
  getCommandCenter: (merchantId: string = 'ALL') =>
    apiClient.get<CommandCenterResponse>('/risk/incidents', { params: { merchant_id: merchantId } }),
  getIncidentDetails: (eventId: string) =>
    apiClient.get<IncidentDetail>(`/risk/incidents/${eventId}`),
  getIncidentGraph: (eventId: string) =>
    apiClient.get<GraphData>(`/risk/incidents/${eventId}/graph`),
}

export const merchantApi = {
  list: () => apiClient.get<Merchant[]>('/risk/merchants'),
}

export const healthApi = {
  check: () => apiClient.get('/health'),
}

export default apiClient
