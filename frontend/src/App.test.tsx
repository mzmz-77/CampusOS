import {render,screen,waitFor,within,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,test,expect,vi} from 'vitest';
import App from './App';
import type {RawMessage,Notice,Task} from './api';
let messages:RawMessage[],notices:Notice[],tasks:Task[];
beforeEach(()=>{messages=[];notices=[];tasks=[];sessionStorage.clear();vi.stubGlobal('fetch',vi.fn(async(input:string,options:RequestInit={})=>{
 const url=new URL(input,'http://localhost');const path=url.pathname;const method=options.method||'GET';const payload=options.body?JSON.parse(String(options.body)):{};let data:unknown=[];
 if(path==='/api/messages'&&method==='GET')data=messages;
 else if(path==='/api/notifications'&&method==='GET')data=notices;
 else if(path==='/api/tasks'&&method==='GET')data=tasks;
 else if(path==='/api/messages'&&method==='POST'){const r:RawMessage={id:1,source_url:null,external_id:null,published_at:null,received_at:'2026-10-30T12:00:00Z',...payload};messages.push(r);data=r;}
 else if(path==='/api/messages/1/parse'){const n:Notice={id:1,title:'提交测试材料',summary:messages[0].content,category:'行政事务',priority:'normal',deadline:null,warnings:'规则解析结果，请核对原文。',parser_version:'rules-v1',created_at:'2026-10-30T12:00:00Z'};notices.push(n);data=n;}
 else if(path==='/api/notifications/1')data={...notices[0],sources:messages,task:tasks[0]||null};
 else if(path==='/api/tasks'&&method==='POST'){const t:Task={id:1,status:'todo',notification_id:null,...payload};tasks.push(t);data=t;}
 else if(path==='/api/tasks/1'&&method==='PATCH'){tasks[0]={...tasks[0],...payload};data=tasks[0];}
 else throw new Error(`Unexpected test route: ${method} ${path}`);
 return {ok:true,json:async()=>JSON.parse(JSON.stringify(data))};
}));});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
test('starts with honest empty states and navigates',async()=>{render(<App/>);expect(await screen.findByText('给重要的事，一个位置')).toBeVisible();expect(screen.getByText('通知中心，准备就绪')).toBeVisible();await userEvent.click(screen.getByRole('button',{name:'原始消息'}));expect(await screen.findByText('还没有原始消息')).toBeVisible();});
test('records raw message, parses, traces original and creates a task',async()=>{
 const user=userEvent.setup();render(<App/>);await screen.findByText('给重要的事，一个位置');await user.click(screen.getByRole('button',{name:'录入消息'}));const dialog=screen.getByRole('dialog');await user.type(within(dialog).getByLabelText(/来源名称/),'手工测试');await user.type(within(dialog).getByLabelText(/消息原文/),'提交测试材料\n截止时间需人工核对。');await user.click(within(dialog).getByRole('button',{name:'保存消息'}));
 const detail=await screen.findByRole('dialog',{name:'通知详情与来源'});expect(within(detail).getByText('手工测试')).toBeVisible();expect(within(detail).getByText(/截止时间需人工核对/,{selector:'pre'})).toBeVisible();await user.click(within(detail).getByRole('button',{name:'转为任务'}));await waitFor(()=>expect(tasks).toHaveLength(1));expect(tasks[0].notification_id).toBe(1);await screen.findByText('已加入任务，请核对截止时间。');
});
test('creates a manual task, filters and completes it',async()=>{
 const user=userEvent.setup();render(<App/>);await screen.findByText('给重要的事，一个位置');await user.click(screen.getByRole('button',{name:'我的任务'}));await user.click(screen.getByRole('button',{name:'新建任务'}));await user.type(screen.getByLabelText(/任务标题/),'整理学习计划');await user.click(screen.getByRole('button',{name:'保存任务'}));await screen.findByText('任务已保存。');await user.click(screen.getByRole('button',{name:'完成任务 整理学习计划'}));await waitFor(()=>expect(tasks[0].status).toBe('done'));await user.selectOptions(screen.getByLabelText('筛选任务'),'todo');expect(await screen.findByText('暂无匹配任务')).toBeVisible();
});
test('displays API failures without inventing data',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,status:401,json:async()=>({detail:'访问令牌无效'})})));render(<App/>);expect(await screen.findByRole('alert')).toHaveTextContent('访问令牌无效');});
