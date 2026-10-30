import {render,screen,within,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {test,expect} from 'vitest';
import 'fake-indexeddb/auto';
import App from './App';
import {installPreview} from './preview';

test('source settings, gated intake and historical evidence work through the complete interface',async()=>{
  const original=window.fetch,restore=installPreview(),user=userEvent.setup();
  try{
    render(<App/>);await screen.findByText('给重要的事，一个位置');
    await user.click(screen.getByRole('button',{name:'消息接入'}));
    await user.click(await screen.findByRole('button',{name:'管理授权 QQ 群'}));
    const settings=screen.getByRole('dialog');
    await user.selectOptions(within(settings).getByLabelText('接入方式'),'manual_import');
    await user.selectOptions(within(settings).getByLabelText('授权状态'),'granted');
    await user.type(within(settings).getByLabelText('授权范围 *'),'仅合成测试通知');
    await user.type(within(settings).getByLabelText('授权依据 *'),'integration-test-only');
    await user.type(within(settings).getByLabelText('变更原因 *'),'test fixture');
    await user.click(within(settings).getByRole('checkbox'));
    await user.click(within(settings).getByRole('button',{name:'保存来源设置'}));
    await screen.findByText('来源设置已保存，授权与启用状态分别管理。');
    await user.click(screen.getByRole('button',{name:'启用手工接入 QQ 群'}));
    await screen.findByText('该来源已启用，仅支持主动手工录入。');
    await user.click(screen.getByRole('button',{name:'录入消息'}));
    const intake=screen.getByRole('dialog');
    await user.selectOptions(within(intake).getByLabelText('关联登记来源'),'5');
    await user.type(within(intake).getByLabelText(/来源名称/),'测试来源标签');
    await user.type(within(intake).getByLabelText(/消息原文/),'合成测试通知，保留原文。');
    await user.click(within(intake).getByRole('button',{name:'保存消息'}));
    const detail=await screen.findByRole('dialog',{name:'通知详情与来源'});
    await user.click(within(detail).getByText('录入时的来源与授权记录'));
    expect(within(detail).getByText(/integration-test-only/)).toBeVisible();
    const messages=await (await window.fetch('/api/messages')).json();
    expect(messages[0].source_id).toBe(5);
    expect(messages[0].authorization_snapshot.reference).toBe('integration-test-only');
  }finally{cleanup();restore();window.fetch=original;}
});
