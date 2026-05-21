#!/usr/bin/env python3
"""查询账本"""

import csv
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '账本.csv')

def parse_date(s):
    """Parse Chinese date format: 2025年01月07日 07:47:03 or 2025-01-07"""
    formats = ['%Y年%m月%d日 %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt)
        except:
            continue
    return None

def load():
    with open(LEDGER, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def parse_period(arg):
    """Parse period argument: 'today', '本月', '上月', '本季', '今年', '最近N'"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today.replace(hour=23, minute=59, second=59)

    if arg == 'today' or arg == '今天':
        return today, today_end, '今天'
    elif arg == 'yesterday' or arg == '昨天':
        return today - timedelta(days=1), today - timedelta(seconds=1), '昨天'
    elif arg in ('本月', '这个月', 'month'):
        start = today.replace(day=1)
        return start, today_end, f'{start.strftime("%Y-%m")}'
    elif arg in ('上月', '上个月', 'lastmonth'):
        first = today.replace(day=1)
        start = (first - timedelta(days=1)).replace(day=1)
        end = (first - timedelta(seconds=1))
        return start, end, f'{start.strftime("%Y-%m")}'
    elif arg in ('今年', 'year', '本年'):
        start = today.replace(month=1, day=1)
        return start, today_end, f'{start.strftime("%Y")}'
    elif arg.startswith('最近'):
        try:
            n = int(arg[2:])
        except:
            return None, None, None
        return today - timedelta(days=n), today_end, f'最近{n}天'
    elif arg in ('全部', 'all'):
        return datetime(2000,1,1), today_end, '全部'
    return None, None, None

def query(period='本月', parent=None, sub=None, type_=None):
    rows = load()
    start, end, label = parse_period(period)
    if start is None:
        print(f"未知查询周期: {period}")
        return

    filtered = []
    for r in rows:
        if r['Status'] in ('内部流转-转账收入', '内部流转-转账支出', '待确认-退款'):
            continue
        dt = parse_date(r['Date'])
        if not dt:
            continue
        if not (start <= dt <= end):
            continue
        if type_ and r['Type'] != type_:
            continue
        if parent and r['ParentCategory'] != parent:
            continue
        if sub and r['SubCategory'] != sub:
            continue
        filtered.append(r)

    # Summary by parent
    by_parent = defaultdict(lambda: {'收入': 0.0, '支出': 0.0, 'count': 0})
    total_income = 0.0
    total_expense = 0.0
    for r in filtered:
        amt = float(r['Amount'])
        ie = r['Type']
        by_parent[r['ParentCategory']][ie] += amt
        by_parent[r['ParentCategory']]['count'] += 1
        if ie == '收入':
            total_income += amt
        else:
            total_expense += amt

    print(f"\n📊 {label} 汇总:")
    print(f"   收入: ¥{total_income:,.2f} | 支出: ¥{total_expense:,.2f} | 净额: ¥{total_income - total_expense:,.2f}")
    print(f"   共 {len(filtered)} 笔交易\n")

    print(f"   {'大类':<6} {'笔数':>4} {'收入':>12} {'支出':>12} {'净额':>12}")
    print(f"   {'-'*48}")
    for p in sorted(by_parent.keys()):
        info = by_parent[p]
        net = info['收入'] - info['支出']
        inc_str = f"¥{info['收入']:,.2f}" if info['收入'] > 0 else '-'
        exp_str = f"¥{info['支出']:,.2f}" if info['支出'] > 0 else '-'
        print(f"   {p:<6} {info['count']:>4} {inc_str:>12} {exp_str:>12} {net:>+12,.2f}")

    # Recent items
    if len(filtered) <= 20:
        print(f"\n   明细:")
        for r in sorted(filtered, key=lambda x: x['Date'], reverse=True):
            note_str = f" | {r['Note']}" if r['Note'] else ''
            acc_str = f" [{r['Account']}]" if r['Account'] else ''
            print(f"   {r['Date']} | {r['Type']} | {r['ParentCategory']}:{r['SubCategory']} | ¥{float(r['Amount']):,.2f}{acc_str}{note_str}")
    else:
        print(f"\n   (共 {len(filtered)} 条，用 --detail 查看明细)")

if __name__ == '__main__':
    period = sys.argv[1] if len(sys.argv) > 1 else '本月'
    parent = sys.argv[2] if len(sys.argv) > 2 else None
    query(period=period, parent=parent)
