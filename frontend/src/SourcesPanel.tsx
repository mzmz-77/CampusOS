import {useState,type FormEvent} from 'react';
import {History,Network,RefreshCw,ShieldCheck} from 'lucide-react';
import {api,all,date} from './api';
import {Modal} from './Modal';
import {authLabels,methodLabels,integrationLabels,canEnableSource,type Source,type SourceEvent,type AuthorizationSnapshot,type AuthorizationStatus} from './source-types';

export function AuthorizationRecord({snapshot}:{snapshot:AuthorizationSnapshot|null|undefined}) {
  if(!snapshot)return <p className="muted">手工标注来源，未关联来源授权记录。</p>;
  return <details className="authorization-record"><summary><ShieldCheck size={13}/>录入时的来源与授权记录</summary>
    <p>登记来源：{snapshot.source_name}<br/>授权范围：{snapshot.scope}<br/>授权依据：{snapshot.reference}<br/>
      授权有效期：{date(snapshot.expires_at,true)}<br/>记录时间：{date(snapshot.captured_at,true)}<br/>
      授权变更记录：#{snapshot.authorization_event_id ?? '未提供'}</p>
    <small>保留录入时的状态，当前授权变更不会改写该历史记录。授权内容由操作者登记。</small>
  </details>;
}

export function SourcesPanel({sources,loading,refresh}:{sources:Source[];loading:boolean;refresh:()=>Promise<void>}) {
  const [editing,setEditing]=useState<Source|null>(null),[history,setHistory]=useState<{source:Source;events:SourceEvent[]}|null>(null);
  const [error,setError]=useState(''),[feedback,setFeedback]=useState(''),[busy,setBusy]=useState(false);
  async function toggle(source:Source){
    setBusy(true);setError('');
    try{
      await api(`/sources/${source.id}`,{method:'PATCH',body:JSON.stringify({expected_revision:source.revision,enabled:!source.effective_enabled,reason:source.effective_enabled?'手工禁用来源接入':'手工启用已登记授权的来源接入'})});
      await refresh();setFeedback(source.effective_enabled?'该来源已禁用。':'该来源已启用，仅支持主动手工录入。');
    }catch(e){setError((e as Error).message);await refresh();}
    finally{setBusy(false);}
  }
  async function showHistory(source:Source){
    setBusy(true);setError('');try{setHistory({source,events:await all<SourceEvent>(`/sources/${source.id}/events`)});}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <section className="source-registry">
    <div className="registry-heading"><div><h2><Network size={18}/>目标来源与授权 <span className="number-tag">{sources.length}</span></h2><p>登记来源不会连接平台。先记录真实授权，再单独启用手工接入；自动采集尚未开发。</p></div><button className="secondary" disabled={loading||busy} onClick={()=>void refresh()}><RefreshCw size={14}/>刷新来源</button></div>
    {error&&<div className="alert" role="alert">{error}</div>}{feedback&&<p className="feedback" role="status">{feedback}</p>}
    {loading?<p className="loading">正在读取来源…</p>:<div className="registry-grid">{sources.map(source=><article key={source.id} className="panel source-card">
      <div className="source-card-heading"><h3>{source.name}</h3><span className={`badge ${source.effective_enabled?'source-ready':''}`}>{integrationLabels[source.integration_status]}</span></div>
      <dl><div><dt>接入方式</dt><dd>{methodLabels[source.access_method]}</dd></div><div><dt>授权状态</dt><dd>{authLabels[source.authorization_status]}</dd></div><div><dt>有效期</dt><dd>{source.authorization_expires_at?date(source.authorization_expires_at,true):'未设置'}</dd></div></dl>
      <p className="source-scope">{source.authorization_scope||'尚未登记授权范围与依据。'}</p>
      <div className="source-actions"><button className="secondary" aria-label={`管理授权 ${source.name}`} onClick={()=>setEditing(source)}>管理授权</button><button className="secondary" disabled={busy||(!source.effective_enabled&&!canEnableSource(source))} aria-label={`${source.effective_enabled?'禁用':'启用手工接入'} ${source.name}`} onClick={()=>void toggle(source)}>{source.effective_enabled?'禁用':'启用手工接入'}</button><button className="icon-button" disabled={busy} aria-label={`变更记录 ${source.name}`} onClick={()=>void showHistory(source)}><History size={16}/></button></div>
    </article>)}</div>}
    {editing&&<SourceForm source={editing} close={()=>setEditing(null)} onSave={async payload=>{
      await api(`/sources/${editing.id}`,{method:'PATCH',body:JSON.stringify(payload)});setEditing(null);await refresh();setFeedback('来源设置已保存，授权与启用状态分别管理。');
    }}/>}
    {history&&<Modal title={`${history.source.name} · 变更记录`} close={()=>setHistory(null)}><div className="modal-body"><p className="form-intro">每次修改保留变更前后状态和原因。此记录不代表系统已向平台核验授权。</p>{history.events.map(event=><article className="source-event" key={event.id}><strong>{event.action==='registered'?'登记来源':event.action==='authorization_granted'?'登记授权':'修改设置'}</strong><span>{date(event.occurred_at,true)}</span><p>{event.reason}</p><dl><div><dt>授权状态</dt><dd>{event.before?authLabels[event.before.authorization_status]:'无'} → {authLabels[event.after.authorization_status]}</dd></div><div><dt>接入方式</dt><dd>{event.before?methodLabels[event.before.access_method]:'无'} → {methodLabels[event.after.access_method]}</dd></div><div><dt>启用设置</dt><dd>{event.before?.enabled?'启用':'禁用'} → {event.after.enabled?'启用':'禁用'}</dd></div></dl><details><summary>查看完整变更记录</summary><pre>{JSON.stringify({before:event.before,after:event.after},null,2)}</pre></details></article>)}</div></Modal>}
  </section>;
}

function toLocal(value:string|null){return value?new Date(Date.parse(value)+8*3600000).toISOString().slice(0,16):'';}
function SourceForm({source,close,onSave}:{source:Source;close:()=>void;onSave:(payload:Record<string,unknown>)=>Promise<void>}) {
  const [status,setStatus]=useState<AuthorizationStatus>(source.authorization_status),[saving,setSaving]=useState(false),[error,setError]=useState('');
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget);setSaving(true);setError('');
    try{await onSave({expected_revision:source.revision,reason:data.get('reason'),access_method:data.get('access_method'),authorization_status:status,authorization_scope:data.get('scope'),authorization_reference:data.get('reference'),authorization_expires_at:data.get('expires_at')?`${data.get('expires_at')}:00+08:00`:null,authorization_confirmed:data.get('confirmed')==='on'});}
    catch(e){setError((e as Error).message);}finally{setSaving(false);}
  }
  return <Modal title={`${source.name} · 授权设置`} close={close}><form onSubmit={e=>void submit(e)}><div className="modal-body"><p className="form-intro">只登记授权和允许的接入方式，不登录账号、不启动采集。不要填写账号密码、访问令牌或私人消息原文。</p>{error&&<p className="alert" role="alert">{error}</p>}
    <label>接入方式<select name="access_method" defaultValue={source.access_method}><option value="unconfigured">尚未选择</option><option value="manual_import">手工录入</option>{source.public_website&&<option value="public_web">公开网页（采集待开发，暂不可启用）</option>}</select></label>
    <label>授权状态<select name="authorization_status" value={status} onChange={e=>setStatus(e.target.value as AuthorizationStatus)}>{Object.entries(authLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    <label>授权范围{status==='granted'&&' *'}<textarea name="scope" maxLength={2000} rows={3} required={status==='granted'} defaultValue={source.authorization_scope} placeholder="准确说明允许处理哪些来源、哪些通知及用途…"/></label>
    <label>授权依据{status==='granted'&&' *'}<input name="reference" maxLength={1000} required={status==='granted'} defaultValue={source.authorization_reference} placeholder="可核验的授权文档编号或授权说明，不填密码或令牌"/></label>
    <label>授权有效期（北京时间，可留空）<input name="expires_at" type="datetime-local" defaultValue={toLocal(source.authorization_expires_at)}/></label>
    <label>变更原因 *<input name="reason" required maxLength={1000} placeholder="本次设置的原因，将保留在变更记录中"/></label>
    {status==='granted'&&<label className="checkbox-label"><input name="confirmed" type="checkbox" required/>我确认已取得所填范围内的真实授权。</label>}
  </div><div className="modal-actions"><button className="secondary" type="button" onClick={close}>取消</button><button className="primary" disabled={saving}>{saving?'正在保存…':'保存来源设置'}</button></div></form></Modal>;
}
