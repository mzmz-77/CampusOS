/** Registry for the browser-owned experience. It never contacts a campus platform. */
import {canEnableSource,type Source,type SourceRecord,type SourceEvent,type AuthorizationSnapshot} from './source-types';
const catalog: [string,string,boolean][] = [
  ['xdu_website','西电学校官网',true],['cs_website','西电计算机科学与技术学院官网',true],
  ['wechat_official','学校微信公众号',false],['wechat_enterprise','学校微信企业号',false],
  ['qq_group','QQ 群',false],['wechat_group','微信群',false],['learning_xdu','学在西电',false],['xdyou','XDYou',false],
];
export interface RegistryState {sources?:SourceRecord[];sourceEvents?:SourceEvent[]}
type Failure = (status:number,message:string)=>never;
const copy = <T,>(value:T):T=>JSON.parse(JSON.stringify(value));
export function ensureRegistry(state:RegistryState) {
  if(!state.sources)state.sources=catalog.map(([code,name,public_website],index)=>({id:index+1,code,name,public_website,access_method:public_website?'public_web':'unconfigured',authorization_status:'not_requested',authorization_scope:'',authorization_reference:'',authorization_expires_at:null,enabled:false,revision:1,created_at:new Date().toISOString(),updated_at:new Date().toISOString()}));
  if(!state.sourceEvents)state.sourceEvents=state.sources.map((source,index)=>({id:index+1,source_id:source.id,action:'registered',reason:'登记目标来源；尚未取得接入授权。',before:null,after:copy(source),occurred_at:new Date().toISOString()}));
  return {sources:state.sources,events:state.sourceEvents};
}
export function previewSourceView(source:SourceRecord):Source {
  let status:Source['integration_status'];
  const authorized=source.authorization_status==='granted'&&!!source.authorization_scope.trim()&&!!source.authorization_reference.trim();
  if(source.authorization_status==='granted'&&source.authorization_expires_at&&Date.parse(source.authorization_expires_at)<=Date.now())status='authorization_expired';
  else if(!authorized)status='authorization_required';
  else if(source.access_method==='unconfigured')status='unconfigured';
  else if(source.access_method==='public_web')status='not_implemented';
  else if(!source.enabled)status='disabled';
  else status='ready_for_manual_import';
  return {...source,integration_status:status,effective_enabled:status==='ready_for_manual_import',capabilities:{manual_import:true,public_web:false}};
}
export function updatePreviewSource(state:RegistryState,id:number,payload:Record<string,unknown>,fail:Failure):Source {
  const {sources,events}=ensureRegistry(state),source=sources.find(s=>s.id===id);
  if(!source)return fail(404,'登记来源不存在。');
  const allowed=['expected_revision','reason','access_method','authorization_status','authorization_scope','authorization_reference','authorization_expires_at','authorization_confirmed','enabled'];
  if(Object.keys(payload).some(key=>!allowed.includes(key)))return fail(422,'包含未知或不可修改的来源字段。');
  if(!Number.isInteger(payload.expected_revision)||Number(payload.expected_revision)<1)return fail(422,'缺少有效的来源版本。');
  if(payload.expected_revision!==source.revision)return fail(409,'来源已被更新，请刷新后重试。');
  if(typeof payload.reason!=='string'||!payload.reason.trim()||payload.reason.length>1000)return fail(422,'请填写有效的变更原因。');
  const next={...source};
  if('access_method' in payload){if(!['unconfigured','manual_import','public_web'].includes(String(payload.access_method)))return fail(422,'接入方式无效。');next.access_method=payload.access_method as SourceRecord['access_method'];}
  if(next.access_method==='public_web'&&!source.public_website)return fail(422,'该来源未被登记为公开网站，不能选择公开网页方式。');
  if('authorization_status' in payload){if(!['not_requested','pending','granted','revoked'].includes(String(payload.authorization_status)))return fail(422,'授权状态无效。');next.authorization_status=payload.authorization_status as SourceRecord['authorization_status'];}
  for(const [key,max] of [['authorization_scope',2000],['authorization_reference',1000]] as const){if(key in payload){if(typeof payload[key]!=='string'||String(payload[key]).length>max)return fail(422,'授权说明格式无效。');next[key]=payload[key] as string;}}
  if('enabled' in payload){if(typeof payload.enabled!=='boolean')return fail(422,'启用设置无效。');next.enabled=payload.enabled;}
  if('authorization_confirmed' in payload&&typeof payload.authorization_confirmed!=='boolean')return fail(422,'授权确认格式无效。');
  if('authorization_expires_at' in payload){const expires=payload.authorization_expires_at;if(expires===null)next.authorization_expires_at=null;else{if(typeof expires!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(expires)||!Number.isFinite(Date.parse(expires)))return fail(422,'授权时间必须有效并包含时区。');next.authorization_expires_at=new Date(expires).toISOString();}}
  if(next.authorization_status==='granted'&&['authorization_status','authorization_scope','authorization_reference','authorization_expires_at','access_method'].some(key=>key in payload)){
    if(payload.authorization_confirmed!==true||!next.authorization_scope.trim()||!next.authorization_reference.trim())return fail(422,'登记已授权状态必须确认真实授权，并填写授权范围与依据。');
    if(next.authorization_expires_at&&Date.parse(next.authorization_expires_at)<=Date.now())return fail(422,'授权有效期必须晚于当前时间。');
  }
  if(payload.enabled===true&&!canEnableSource(next))return fail(409,'仅真实授权有效且选择手工录入的来源可启用；自动采集尚未实现。');
  if(!canEnableSource(next))next.enabled=false;
  next.revision++;next.updated_at=new Date().toISOString();
  events.push({id:Math.max(0,...events.map(e=>e.id))+1,source_id:id,action:payload.authorization_status==='granted'?'authorization_granted':'updated',reason:payload.reason,before:copy(source),after:copy(next),occurred_at:new Date().toISOString()});
  Object.assign(source,next);return previewSourceView(source);
}
export function previewMessageAuthorization(state:RegistryState,id:unknown,fail:Failure):AuthorizationSnapshot {
  if(!Number.isInteger(id)||Number(id)<1)return fail(422,'登记来源编号无效。');
  const {sources,events}=ensureRegistry(state),source=sources.find(s=>s.id===id);
  if(!source)return fail(404,'登记来源不存在。');
  if(!previewSourceView(source).effective_enabled)return fail(409,'该来源尚未启用、授权无效或接入方式未实现，请先检查来源设置。');
  const event=[...events].reverse().find(e=>e.source_id===id&&e.action==='authorization_granted');
  return {source_id:source.id,source_name:source.name,access_method:source.access_method,authorization_status:source.authorization_status,scope:source.authorization_scope,reference:source.authorization_reference,expires_at:source.authorization_expires_at,authorization_event_id:event?.id||null,captured_at:new Date().toISOString()};
}
