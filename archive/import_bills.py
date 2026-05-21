#!/usr/bin/env python3
"""将旧CSV导入为新二级分类账本"""

import csv
import sys
from datetime import datetime
from collections import defaultdict

# 旧分类 → (父类, 子类) 映射表
INCOME_MAP = {
    '工资':       ('工作', '工资'),
    '奖金':       ('工作', '绩效'),
    '年终奖':     ('工作', '年终奖'),
    '公积金':     ('工作', '公积金'),
    '过节费':     ('工作', '过节费'),
    '投资收益':   ('投资', '投资收益'),
    '二手收入':   ('其他', '二手'),
    '红包收入':   ('其他', '红包'),
    '副业收入':   ('其他', '副业'),
    '调整收入':   ('其他', '调整收入'),
}

EXPENSE_MAP = {
    '吃饭':       ('餐饮', '吃饭'),
    '饮料':       ('餐饮', '饮料'),
    '零食':       ('餐饮', '零食'),
    '旅游饮食':   ('餐饮', '吃饭'),
    '住房':       ('住房', '房贷'),
    '装修':       ('住房', '装修'),
    '交通':       ('交通', '交通费'),
    '旅游交通':   ('交通', '交通费'),
    '汽车':       ('汽车', '维护'),
    '日用':       ('购物', '日用'),
    '电器数码':   ('购物', '数码'),
    '服饰':       ('购物', '服饰'),
    '玩具':       ('购物', '玩具'),
    '旅游购物':   ('购物', '旅游购物'),
    '礼物':       ('购物', '礼物'),
    '通讯':       ('订阅', '通讯'),
    '订阅':       ('订阅', '其他订阅'),
    '网吧':       ('娱乐', '网吧'),
    '电影':       ('娱乐', '电影'),
    '游戏':       ('娱乐', '游戏'),
    '旅游娱乐':   ('娱乐', '游玩'),
    '按摩':       ('娱乐', '按摩'),
    '运动':       ('生活', '运动'),
    '学习':       ('生活', '学习'),
    '育儿':       ('生活', '育儿'),
    '宠物':       ('生活', '宠物'),
    '家庭':       ('生活', '家庭'),
    '理发':       ('生活', '理发'),
    '公共服务':   ('生活', '家庭'),
    '医疗':       ('医疗', '医疗'),
    '投资亏损':   ('投资', '投资亏损'),
    '红包支出':   ('其他', '红包支出'),
    '借出':       ('其他', '借出'),
    '调整支出':   ('其他', '调整支出'),
}

# 需要标记为待确认/内部流转的旧分类
PENDING_TYPES = {
    '退款':       '待确认-退款',
    '转账收入':   '内部流转-转账收入',
    '转账支出':   '内部流转-转账支出',
}

def main():
    input_file = '导出数据_2026年05月18日.csv'
    output_file = '账本.csv'

    stats = defaultdict(lambda: {'count': 0, 'amount': 0.0, 'pending': 0, 'pending_amount': 0.0})
    pending_records = []
    mapped_count = 0
    pending_count = 0

    with open(input_file, 'r', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        rows = list(reader)

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['Date', 'Type', 'ParentCategory', 'SubCategory', 'Amount', 'Account', 'Note', 'Status'])

        for r in rows:
            old_type = r['Type'].strip()
            ie = r['TypeOfIE'].strip()
            amount = float(r['Amount'])
            date_str = r['Date'].strip()
            account = r['FromAccountName'].strip()
            note = r['Remark'].strip() if r['Remark'].strip() else ''

            # Determine new parent + sub
            if old_type in PENDING_TYPES:
                parent, sub = ('内部流转', old_type)
                status = PENDING_TYPES[old_type]
                pending_count += 1
                pending_records.append({
                    'date': date_str, 'old_type': old_type, 'amount': amount,
                    'account': account, 'note': note, 'status': status
                })
            elif ie == '收入':
                if old_type in INCOME_MAP:
                    parent, sub = INCOME_MAP[old_type]
                    status = 'auto'
                else:
                    parent, sub = ('待分类', old_type)
                    status = 'unknown'
            elif ie == '支出':
                if old_type in EXPENSE_MAP:
                    parent, sub = EXPENSE_MAP[old_type]
                    status = 'auto'
                else:
                    parent, sub = ('待分类', old_type)
                    status = 'unknown'
            else:
                parent, sub = ('待分类', old_type)
                status = 'unknown'

            writer.writerow([date_str, ie, parent, sub, amount, account, note, status])

            if status == 'auto':
                stats[parent]['count'] += 1
                stats[parent]['amount'] += amount
                mapped_count += 1
            elif status.startswith('内部流转') or status.startswith('待确认'):
                stats['内部流转']['pending'] += 1
                stats['内部流转']['pending_amount'] += amount

    # Print summary
    print(f"导入完成: {mapped_count} 条已分类, {pending_count} 条标记待确认/内部流转")
    print(f"\n新分类分布:")
    for parent in ['收入'] + sorted([k for k in stats if k not in ('收入', '内部流转')]):
        if parent == '收入':
            # Show income subcategories from work/invest/other
            income_total = sum(stats[p]['amount'] for p in ['工作', '投资', '其他'] if p in stats)
        else:
            pass

    print(f"\n各大类统计:")
    for parent in sorted(stats.keys()):
        info = stats[parent]
        if parent == '内部流转':
            print(f"  ⚠️ {parent}: {info['pending']}条 / ¥{info['pending_amount']:,.2f}")
        else:
            print(f"  {parent}: {info['count']}条 / ¥{info['amount']:,.2f}")

    if pending_records:
        print(f"\n⚠️ 待确认/内部流转明细 ({len(pending_records)}条):")
        for pr in pending_records:
            print(f"  {pr['date']} | {pr['old_type']} | ¥{pr['amount']:,.2f} | {pr['account']} | {pr['note']} | → {pr['status']}")

    # Validate totals
    original_total_income = sum(float(r['Amount']) for r in rows if r['TypeOfIE'] == '收入')
    original_total_expense = sum(float(r['Amount']) for r in rows if r['TypeOfIE'] == '支出')
    print(f"\n校验: 原CSV收入 ¥{original_total_income:,.2f} / 支出 ¥{original_total_expense:,.2f}")

if __name__ == '__main__':
    main()
