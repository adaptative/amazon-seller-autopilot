export type TenantId = string & { readonly __brand: 'TenantId' };

export type AgentType =
  | 'listing-optimizer'
  | 'review-responder'
  | 'inventory-forecaster'
  | 'ppc-manager'
  | 'competitor-tracker';

export interface AgentAction {
  id: string;
  tenantId: TenantId;
  agentType: AgentType;
  action: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
}

export interface ApiResponse<T = unknown> {
  data: T;
  success: boolean;
  error?: string;
  meta?: {
    page?: number;
    pageSize?: number;
    total?: number;
  };
}
