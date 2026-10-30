"""Local deterministic extraction. Never connects to external platforms or models."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def parse(content: str):
    text = content.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = re.split(r'[。！？]', lines[0])[0][:100] or lines[0][:100]
    category = '其他'
    for label, words in [('学业教务',('考试','课程','选课','教务','作业')),('奖助评优',('奖学金','助学','评优')),('校园活动',('讲座','活动','比赛','竞赛')),('行政事务',('报销','材料','登记','填报'))]:
        if any(word in text for word in words):
            category = label
            break
    priority = 'high' if any(w in text for w in ('紧急','务必','逾期')) else 'normal'
    warnings = ['规则解析结果，请核对原文。']
    deadline = None
    # Only an explicitly labelled, full year-month-day with a time is actionable.
    date_pattern = r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?\s*(\d{1,2})[:：](\d{2})'
    matches = []
    for line in lines:
        if re.search(r'截止|截至|最晚',line): matches.extend(re.findall(date_pattern,line))
    if len(matches) == 1:
        try: deadline = datetime(*map(int,matches[0]),tzinfo=ZoneInfo('Asia/Shanghai'))
        except ValueError: warnings.append('截止时间格式无效，请人工填写。')
    elif len(matches) > 1: warnings.append('出现多个候选时间，请人工确认截止时间。')
    else: warnings.append('未找到完整、明确的截止时间。')
    return dict(title=title,summary=text[:500],category=category,priority=priority,deadline=deadline,warnings='\n'.join(warnings),parser_version='rules-v1')
