/** Browser-owned experience mode. Does not contact or impersonate any platform. */
import {ensureRegistry,previewSourceView,updatePreviewSource,previewMessageAuthorization,type RegistryState} from './preview-sources';
import type {RawMessage, Notice, Task, Detail} from './api';
type PreviewNotice=Notice & {canonical:string;sourceIds:number[]};
export interface PreviewState extends RegistryState {messages:RawMessage[];notices:PreviewNotice[];tasks:Task[]}
export const initialState=():PreviewState=>({messages:[],notices:[],tasks:[]});
class PreviewError extends Error{constructor(public status:number,message:string){super(message);}}
const fail=(status:number,message:string):never=>{throw new PreviewError(status,message);};
const id=(rows:{id:number}[])=>Math.max(0,...rows.map(row=>row.id))+1;
const field=(value:unknown,name:string,max:number)=>{if(typeof value!=='string'||!value.trim()||value.length>max)fail(422,`${name}不能为空且不能超过 ${max} 字。`);return value as string;};
function time(value:unknown){if(value===null||value===undefined||value==='')return null;if(typeof value!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(value)||!Number.isFinite(Date.parse(value)))return fail(422,'时间必须有效并包含时区。');return new Date(value).toISOString();}
export function extract(content:string){
 const lines=content.trim().split(/\r?\n/).map(line=>line.trim()).filter(Boolean),text=content.trim();
 const title=(lines[0].split(/[。！？]/)[0]||lines[0]).slice(0,100);let category='其他';
 const categories:[string,string[]][]=[['学业教务',['考试','课程','选课','教务','作业']],['奖助评优',['奖学金','助学','评优']],['校园活动',['讲座','活动','比赛','竞赛']],['行政事务',['报销','材料','登记','填报']]];
 for(const [label,words] of categories){if(words.some(word=>text.includes(word))){category=label;break;}}
 const candidates=lines.filter(line=>/截止|截至|最晚/.test(line)).flatMap(line=>Array.from(line.matchAll(/(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?\s*(\d{1,2})[:：](\d{2})/g)));
 let deadline:string|null=null;const warnings=['规则解析结果，请核对原文。'];
 if(candidates.length===1){const [year,month,day,hour,minute]=candidates[0].slice(1).map(Number);const local=Date.UTC(year,month-1,day,hour,minute);const checked=new Date(local);if(checked.getUTCFullYear()===year&&checked.getUTCMonth()===month-1&&checked.getUTCDate()===day&&checked.getUTCHours()===hour&&checked.getUTCMinutes()===minute)deadline=new Date(local-8*3600000).toISOString();else warnings.push('截止时间格式无效，请人工填写。');}
 else warnings.push(candidates.length?'出现多个候选时间，请人工确认截止时间。':'未找到完整、明确的截止时间。');
 return {title,summary:text.slice(0,500),category,priority:(['紧急','务必','逾期'].some(w=>text.includes(w))?'high':'normal') as Notice['priority'],deadline,warnings:warnings.join('\n'),parser_version:'rules-v1-browser'};
}
function publicNotice(n:PreviewNotice):Notice{const {canonical:_canonical,sourceIds:_sourceIds,...rest}=n;return rest;}
function detail(state:PreviewState,n:PreviewNotice):Detail{return {...publicNotice(n),sources:state.messages.filter(m=>n.sourceIds.includes(m.id)),task:state.tasks.find(t=>t.notification_id===n.id)||null};}
export function dispatch(state:PreviewState,path:string,method:string,payload:Record<string,unknown>={}):{body:unknown;status:number}{
 const url=new URL(path,'https://preview.local'),route=url.pathname;let body:unknown;let status=200;
 const registry=ensureRegistry(state);
 const pagination=<T,>(rows:T[])=>{const limit=Number(url.searchParams.get('limit')||100),offset=Number(url.searchParams.get('offset')||0);if(!Number.isInteger(limit)||limit<1||limit>500||!Number.isInteger(offset)||offset<0)fail(422,'分页参数无效。');return [...rows].reverse().slice(offset,offset+limit);};
 if(route==='/api/sources'&&method==='GET')body=[...registry.sources].slice(Number(url.searchParams.get('offset')||0),Number(url.searchParams.get('offset')||0)+Number(url.searchParams.get('limit')||100)).map(previewSourceView);
 else if(/^\/api\/sources\/\d+\/events$/.test(route)&&method==='GET'){const id=Number(route.split('/')[3]);if(!registry.sources.some(s=>s.id===id))return fail(404,'登记来源不存在。');body=pagination(registry.events.filter(e=>e.source_id===id));}
 else if(/^\/api\/sources\/\d+$/.test(route)){const id=Number(route.split('/')[3]),source=registry.sources.find(s=>s.id===id);if(!source)return fail(404,'登记来源不存在。');if(method==='GET')body=previewSourceView(source);else if(method==='PATCH')body=updatePreviewSource(state,id,payload,fail);else return fail(405,'体验版不支持此操作。');}
 else if(route==='/api/health'&&method==='GET')body={status:'ok',mode:'browser-owned-preview'};
 else if(route==='/api/messages'&&method==='GET')body=pagination(state.messages);
 else if(route==='/api/messages'&&method==='POST'){
  const source=field(payload.source,'来源',100),content=field(payload.content,'原文',50000),external=payload.external_id==null?null:field(payload.external_id,'来源编号',200),published=time(payload.published_at);
  let sourceUrl:string|null=null;
  if(payload.source_url){try{const parsed=new URL(String(payload.source_url));if(!['http:','https:'].includes(parsed.protocol))throw new Error();sourceUrl=parsed.href;}catch{fail(422,'原文链接必须为 HTTP 或 HTTPS。');}}
  const sourceId=payload.source_id??null;
  const snapshot=sourceId!==null?previewMessageAuthorization(state,sourceId,fail):null;
  const existing=external===null?null:state.messages.find(m=>m.source===source&&m.external_id===external);
  if(existing){if(existing.content!==content||existing.source_url!==sourceUrl||existing.published_at!==published||(existing.source_id??null)!==sourceId)fail(409,'相同来源编号的原文或元数据冲突');body=existing;}
  else{const message:RawMessage={id:id(state.messages),source,content,external_id:external,source_url:sourceUrl,published_at:published,source_id:sourceId as number|null,authorization_snapshot:snapshot,received_at:new Date().toISOString()};state.messages.push(message);body=message;}status=201;
 }
 else if(/^\/api\/messages\/\d+\/parse$/.test(route)&&method==='POST'){
  const message=state.messages.find(m=>m.id===Number(route.split('/')[3]));if(!message)return fail(404,'消息不存在');
  const canonical=message.content.normalize('NFC').replace(/\s+/gu,' ').trim();let notice=state.notices.find(n=>n.canonical===canonical);
  if(!notice){notice={id:id(state.notices),...extract(message.content),created_at:new Date().toISOString(),canonical,sourceIds:[]};state.notices.push(notice);}if(!notice.sourceIds.includes(message.id))notice.sourceIds.push(message.id);body=publicNotice(notice);
 }
 else if(/^\/api\/messages\/\d+$/.test(route)&&method==='GET'){body=state.messages.find(m=>m.id===Number(route.split('/')[3]))||fail(404,'消息不存在');}
 else if(route==='/api/notifications'&&method==='GET')body=pagination(state.notices.map(publicNotice));
 else if(/^\/api\/notifications\/\d+$/.test(route)&&method==='GET'){const n=state.notices.find(n=>n.id===Number(route.split('/')[3]));if(!n)return fail(404,'通知不存在');body=detail(state,n);}
 else if(route==='/api/tasks'&&method==='GET')body=pagination(state.tasks);
 else if(route==='/api/tasks'&&method==='POST'){
  const title=field(payload.title,'任务标题',200),priority=payload.priority||'normal',deadline=time(payload.deadline),notes=payload.notes??'';
  if(!['normal','high'].includes(String(priority))||typeof notes!=='string'||notes.length>10000)fail(422,'优先级或备注无效。');
  const notificationId=payload.notification_id??null;if(notificationId!==null&&!state.notices.some(n=>n.id===notificationId))fail(404,'通知不存在');if(notificationId!==null&&state.tasks.some(t=>t.notification_id===notificationId))fail(409,'该通知已有任务');
  const task:Task={id:id(state.tasks),title,notes:notes as string,priority:priority as Task['priority'],deadline,status:'todo',notification_id:notificationId as number|null};state.tasks.push(task);body=task;status=201;
 }
 else if(/^\/api\/tasks\/\d+$/.test(route)&&method==='PATCH'){
  const t=state.tasks.find(t=>t.id===Number(route.split('/')[3]));if(!t)return fail(404,'任务不存在');const changes:Partial<Task>={};
  if('title' in payload)changes.title=field(payload.title,'任务标题',200);
  if('notes' in payload){if(typeof payload.notes!=='string'||payload.notes.length>10000)fail(422,'备注格式无效。');changes.notes=payload.notes as string;}
  if('status' in payload){if(!['todo','doing','done'].includes(String(payload.status)))fail(422,'任务状态无效。');changes.status=payload.status as Task['status'];}
  if('priority' in payload){if(!['normal','high'].includes(String(payload.priority)))fail(422,'任务优先级无效。');changes.priority=payload.priority as Task['priority'];}
  if('deadline' in payload)changes.deadline=time(payload.deadline);Object.assign(t,changes);body=t;
 }
 else if(/^\/api\/tasks\/\d+\/trace$/.test(route)&&method==='GET'){const t=state.tasks.find(t=>t.id===Number(route.split('/')[3]));if(!t)return fail(404,'任务不存在');const n=state.notices.find(n=>n.id===t.notification_id);body={task:t,notification:n?detail(state,n):null};}
 else return fail(405,'体验版不支持此操作。');
 return {body,status};
}
export function installPreview(){
 const open=new Promise<IDBDatabase>((resolve,reject)=>{const request=indexedDB.open('campusos-xdu-experience-v1',1);request.onupgradeneeded=()=>request.result.createObjectStore('workspace');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
 const networkFetch=window.fetch.bind(window);
 window.fetch=async(input:RequestInfo|URL,options:RequestInit={})=>{
  const request=input instanceof Request?input:null,url=new URL(request?.url||String(input),window.location.href);
  if(url.origin!==window.location.origin||!url.pathname.startsWith('/api/'))return networkFetch(input,options);
  try{
   const db=await open,method=options.method||request?.method||'GET',payload=options.body?JSON.parse(String(options.body)):request&&method!=='GET'?await request.clone().json():{};
   const result=await new Promise<{body:unknown;status:number}>((resolve,reject)=>{const tx=db.transaction('workspace','readwrite'),store=tx.objectStore('workspace'),read=store.get('state');let result:{body:unknown;status:number};read.onsuccess=()=>{try{const state:PreviewState=read.result||initialState();result=dispatch(state,url.pathname+url.search,method,payload);store.put(state,'state');}catch(error){reject(error);tx.abort();}};tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('存储操作未完成。'));});
   return Response.json(result.body,{status:result.status});
  }catch(error){const known=error instanceof PreviewError;return Response.json({detail:known?error.message:'无法访问浏览器存储。请退出隐私模式或允许本站保存数据后重试。'},{status:known?error.status:503});}
 };
 return ()=>{window.fetch=networkFetch;void open.then(db=>db.close());};
}
