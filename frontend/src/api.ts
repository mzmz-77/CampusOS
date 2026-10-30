export interface RawMessage { id:number; source:string; external_id:string|null; content:string; source_url:string|null; published_at:string|null; received_at:string }
export interface Notice { id:number; title:string; summary:string; category:string; priority:'normal'|'high'; deadline:string|null; warnings:string; parser_version:string; created_at:string }
export interface Task { id:number; title:string; notes:string; status:'todo'|'doing'|'done'; priority:'normal'|'high'; deadline:string|null; notification_id:number|null }
export interface Detail extends Notice { sources:RawMessage[]; task:Task|null }
export type TaskInput = Pick<Task,'title'|'notes'|'priority'|'deadline'> & {notification_id?:number|null};
export async function api<T>(path:string, options:RequestInit = {}):Promise<T> {
 const token = sessionStorage.getItem('campusos-token');
 const response = await fetch(`/api${path}`,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`} : {}),...options.headers}});
 if(!response.ok){let message = `请求失败（${response.status}）`;try{const body = await response.json();message = typeof body.detail === 'string'?body.detail: '输入格式有误，请检查必填项、链接和时间。';}catch{/* Keep status */} throw new Error(message);}
 return response.json() as Promise<T>;
}
export async function all<T>(path:string):Promise<T[]> {
 const rows:T[]=[];
 for(let offset=0;;offset+=500){const page=await api<T[]>(`${path}?limit=500&offset=${offset}`);rows.push(...page);if(page.length<500)return rows;}
}
export function date(value:string|null,full=false){ if(!value)return '未设置';const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value)?value:`${value}Z`; return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',...(full?{year:'numeric' as const,hour:'2-digit' as const,minute:'2-digit' as const}:{hour:'2-digit' as const,minute:'2-digit' as const})}).format(new Date(normalized));}
export function overdue(t:Task){return t.status!=='done' && !!t.deadline && new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(t.deadline)?t.deadline:`${t.deadline}Z`).getTime()<Date.now();}
