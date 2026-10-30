export type AccessMethod = 'unconfigured' | 'manual_import' | 'public_web';
export type AuthorizationStatus = 'not_requested' | 'pending' | 'granted' | 'revoked';
export interface SourceRecord {
  id: number;
  code: string;
  name: string;
  public_website: boolean;
  access_method: AccessMethod;
  authorization_status: AuthorizationStatus;
  authorization_scope: string;
  authorization_reference: string;
  authorization_expires_at: string | null;
  enabled: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
}
export interface Source extends SourceRecord {
  integration_status: 'authorization_required' | 'authorization_expired' | 'unconfigured' | 'not_implemented' | 'disabled' | 'ready_for_manual_import';
  effective_enabled: boolean;
  capabilities: {manual_import: boolean; public_web: boolean};
}
export interface SourceEvent {
  id: number;
  source_id: number;
  action: 'registered' | 'updated' | 'authorization_granted';
  reason: string;
  before: SourceRecord | null;
  after: SourceRecord;
  occurred_at: string;
}
export interface AuthorizationSnapshot {
  source_id: number;
  source_name: string;
  access_method: string;
  authorization_status: string;
  scope: string;
  reference: string;
  expires_at: string | null;
  authorization_event_id: number | null;
  captured_at: string;
}
export const authLabels: Record<AuthorizationStatus,string> = {
  not_requested: '未申请', pending: '待确认', granted: '已登记授权', revoked: '已撤销',
};
export const methodLabels: Record<AccessMethod,string> = {
  unconfigured: '尚未选择', manual_import: '手工录入', public_web: '公开网页（待开发）',
};
export const integrationLabels: Record<Source['integration_status'],string> = {
  authorization_required: '需要授权', authorization_expired: '授权已过期',
  unconfigured: '尚未配置', not_implemented: '采集待开发', disabled: '已禁用',
  ready_for_manual_import: '可手工接入',
};
export function canEnableSource(source: SourceRecord) {
  return source.access_method === 'manual_import' && source.authorization_status === 'granted'
    && !!source.authorization_scope.trim() && !!source.authorization_reference.trim()
    && (!source.authorization_expires_at || Date.parse(source.authorization_expires_at) > Date.now());
}
