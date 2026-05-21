#!/usr/bin/env python3
"""
历史数据导入 Preview 脚本
- 读取原始 CSV，映射到 v1 分类，写入临时 preview 库
- 不写正式 ledger.sqlite
- 输出：映射表、记录数对账、金额对账、按月汇总、按父类汇总、待确认清单、样例
"""

import csv
import sqlite3
import json
import uuid
import os
from datetime import datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(os.path.dirname(HERE), '导出数据_2026年05月21日.csv')
PREVIEW_DB = os.path.join(HERE, 'ledger_import_preview.sqlite')

# ============================================================
# 旧分类 → (type, parent, child) 映射表
# ============================================================
INCOME_MAP = {
    '工资':       ('收入', '工作', '工资'),
    '奖金':       ('收入', '工作', '绩效'),
    '年终奖':     ('收入', '工作', '年终奖'),
    '公积金':     ('收入', '工作', '公积金'),
    '过节费':     ('收入', '工作', '过节费'),
    '投资收益':   ('收入', '投资', '投资收益'),
    '二手收入':   ('收入', '其他收入', '二手'),
    '红包收入':   ('收入', '其他收入', '红包收入'),
    '副业收入':   ('收入', '其他收入', '副业'),
    '调整收入':   ('收入', '其他收入', '调整收入'),
    '退款':       ('收入', '其他收入', '退款'),
    '转账收入':   ('收入', '其他收入', '援助'),      # 老爸 → 援助
}

EXPENSE_MAP = {
    '吃饭':       ('支出', '餐饮', '吃饭'),
    '饮料':       ('支出', '餐饮', '饮料'),
    '零食':       ('支出', '餐饮', '零食'),
    '旅游饮食':   ('支出', '餐饮', '吃饭'),
    '住房':       ('支出', '住房', '房贷'),
    '装修':       ('支出', '住房', '装修'),
    '交通':       ('支出', '交通', '交通费'),
    '旅游交通':   ('支出', '交通', '交通费'),
    '汽车':       ('支出', '汽车', '维护'),
    '日用':       ('支出', '购物', '日用'),
    '电器数码':   ('支出', '购物', '数码'),
    '服饰':       ('支出', '购物', '服饰'),
    '玩具':       ('支出', '购物', '玩具'),
    '旅游购物':   ('支出', '购物', '旅游购物'),
    '礼物':       ('支出', '购物', '礼物'),
    '通讯':       ('支出', '订阅', '通讯'),
    '订阅':       ('支出', '订阅', '其他订阅'),
    '网吧':       ('支出', '娱乐', '网吧'),
    '电影':       ('支出', '娱乐', '电影'),
    '游戏':       ('支出', '娱乐', '游戏'),
    '旅游娱乐':   ('支出', '娱乐', '游玩'),
    '按摩':       ('支出', '娱乐', '按摩'),
    '运动':       ('支出', '生活', '运动'),
    '学习':       ('支出', '生活', '学习'),
    '育儿':       ('支出', '生活', '育儿'),
    '宠物':       ('支出', '生活', '宠物'),
    '家庭':       ('支出', '生活', '家庭'),
    '理发':       ('支出', '生活', '理发'),
    '公共服务':   ('支出', '生活', '家庭'),
    '医疗':       ('支出', '医疗', '医疗'),
    '投资亏损':   ('支出', '投资', '投资亏损'),
    '红包支出':   ('支出', '其他支出', '红包支出'),
    '借出':       ('支出', '其他支出', '借出'),
    '调整支出':   ('支出', '其他支出', '调整支出'),
    '转账支出':   ('支出', '生活', '家庭'),          # 家庭基金 → 家庭
}

TOTAL_MAP = {**INCOME_MAP, **EXPENSE_MAP}


def init_preview_db():
    if os.path.exists(PREVIEW_DB):
        os.remove(PREVIEW_DB)
    conn = sqlite3.connect(PREVIEW_DB)
    conn.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY, date TEXT, type TEXT, parent_category TEXT,
            child_category TEXT, amount REAL, note TEXT, tags TEXT,
            source TEXT, created_at TEXT, updated_at TEXT,
            old_type TEXT, old_account TEXT, status TEXT
        )
    """)
    conn.commit()
    return conn


def load_csv():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def parse_date(date_str):
    """2024年07月18日 11:01:00 → 2024-07-18"""
    try:
        dt = datetime.strptime(date_str.strip(), '%Y年%m月%d日 %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str[:10]


def map_record(row):
    old_type = row['Type'].strip()
    ie = row['TypeOfIE'].strip()
    amount = float(row['Amount'])
    date_str = parse_date(row['Date'].strip())
    note = row['Remark'].strip() if row['Remark'].strip() else ''
    old_account = row['FromAccountName'].strip()

    status = 'auto'
    tags = '[]'

    # Map
    if ie == '收入':
        if old_type in INCOME_MAP:
            t, p, c = INCOME_MAP[old_type]
        else:
            t, p, c = '收入', '其他收入', '调整收入'
            status = 'fallback'
    elif ie == '支出':
        if old_type in EXPENSE_MAP:
            t, p, c = EXPENSE_MAP[old_type]
        else:
            t, p, c = '支出', '其他支出', '调整支出'
            status = 'fallback'
    else:
        t, p, c = ie, '其他支出', '调整支出'
        status = 'fallback'

    # Fix: 汽车旧分类里含"保险"备注 → 汽车›车险
    if old_type == '汽车' and '保险' in note:
        t, p, c = '支出', '汽车', '车险'
        status = 'auto'

    # Tags: detect travel-related
    if '旅游' in old_type or '旅行' in note:
        try:
            tags_list = json.loads('["旅行"]')
        except:
            tags_list = ['旅行']
        tags = json.dumps(tags_list, ensure_ascii=False)

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    record = {
        'id': str(uuid.uuid4())[:8],
        'date': date_str,
        'type': t,
        'parent_category': p,
        'child_category': c,
        'amount': amount,
        'note': note,
        'tags': tags,
        'source': 'import',
        'created_at': now,
        'updated_at': now,
    }
    meta = {
        'old_type': old_type,
        'old_account': old_account,
        'status': status,
    }
    return (record, meta), None


def run_import():
    rows = load_csv()
    conn = init_preview_db()
    auto_count = 0
    fallback_count = 0
    pending_list = []
    # Track old→new mapping coverage
    mapping_used = defaultdict(int)
    unknown_types = set()

    for row in rows:
        result, pending = map_record(row)
        if pending:
            pending_list.append(pending)
            continue

        record, meta = result
        if meta['status'] == 'fallback':
            fallback_count += 1
            unknown_types.add(row['Type'].strip())
        else:
            auto_count += 1
            mapping_used[(record['type'], record['parent_category'], record['child_category'])] += 1

        conn.execute("""
            INSERT INTO transactions (id, date, type, parent_category, child_category,
                amount, note, tags, source, created_at, updated_at, old_type, old_account, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record['id'], record['date'], record['type'], record['parent_category'],
            record['child_category'], record['amount'], record['note'], record['tags'],
            record['source'], record['created_at'], record['updated_at'],
            meta['old_type'], meta['old_account'], meta['status']
        ))

    conn.commit()
    return conn, auto_count, fallback_count, pending_list, unknown_types, mapping_used


def validate(conn, pending_list, rows):
    """Run validation checks"""

    # 1. 记录数对账
    imported = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    pending = len(pending_list)
    original = len(rows)
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("  导入 Preview 验证报告")
    report_lines.append("=" * 60)
    report_lines.append(f"\n## 1. 记录数对账")
    report_lines.append(f"   原始 CSV:   {original} 条")
    report_lines.append(f"   自动导入:   {imported} 条")
    report_lines.append(f"   待确认:     {pending} 条")
    report_lines.append(f"   合计:       {imported + pending} 条")
    report_lines.append(f"   ✅ {'一致' if imported + pending == original else '⚠️ 不一致!'}")

    # 2. 金额对账
    orig_income = sum(float(r['Amount']) for r in rows if r['TypeOfIE'] == '收入')
    orig_expense = sum(float(r['Amount']) for r in rows if r['TypeOfIE'] == '支出')
    new_income = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='收入'").fetchone()[0] or 0
    new_expense = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='支出'").fetchone()[0] or 0
    pending_income = sum(p['amount'] for p in pending_list if p['old_ie'] == '收入')
    pending_expense = sum(p['amount'] for p in pending_list if p['old_ie'] == '支出')

    report_lines.append(f"\n## 2. 金额对账")
    report_lines.append(f"   收入: 原始 ¥{orig_income:,.2f} → 导入 ¥{new_income:,.2f} + 待确认 ¥{pending_income:,.2f} = ¥{new_income + pending_income:,.2f}")
    report_lines.append(f"   支出: 原始 ¥{orig_expense:,.2f} → 导入 ¥{new_expense:,.2f} + 待确认 ¥{pending_expense:,.2f} = ¥{new_expense + pending_expense:,.2f}")
    inc_ok = abs((new_income + pending_income) - orig_income) < 0.02
    exp_ok = abs((new_expense + pending_expense) - orig_expense) < 0.02
    report_lines.append(f"   {'✅ 收入一致' if inc_ok else '⚠️ 收入不一致!'}")
    report_lines.append(f"   {'✅ 支出一致' if exp_ok else '⚠️ 支出不一致!'}")

    # 3. 按月汇总
    report_lines.append(f"\n## 3. 按月汇总")
    monthly_orig = defaultdict(lambda: {'收入': 0.0, '支出': 0.0})
    for r in rows:
        month = r['Date'].strip()[:7].replace('年', '-').replace('月', '')
        monthly_orig[month][r['TypeOfIE']] += float(r['Amount'])
    monthly_new = defaultdict(lambda: {'收入': 0.0, '支出': 0.0})
    for r in conn.execute("SELECT date, type, amount FROM transactions").fetchall():
        month = r[0][:7]
        monthly_new[month][r[1]] += r[2]

    all_months = sorted(set(list(monthly_orig.keys()) + list(monthly_new.keys())))
    report_lines.append(f"   {'月份':<10} {'原始收入':>12} {'导入收入':>12} {'原始支出':>12} {'导入支出':>12} {'状态'}")
    all_ok = True
    for m in all_months:
        oi = monthly_orig[m]['收入']
        ni = monthly_new[m]['收入']
        oe = monthly_orig[m]['支出']
        ne = monthly_new[m]['支出']
        di = abs(oi - ni) < 0.02
        de = abs(oe - ne) < 0.02
        ok = "✅" if (di and de) else "⚠️"
        if not (di and de):
            all_ok = False
        report_lines.append(f"   {m:<10} ¥{oi:>10,.2f} ¥{ni:>10,.2f} ¥{oe:>10,.2f} ¥{ne:>10,.2f} {ok}")
    if not all_ok:
        report_lines.append(f"   ⚠️ 部分月份有差异（待确认记录未纳入导入），待确认记录确认后可消除")

    # 4. 按新父类汇总
    report_lines.append(f"\n## 4. 按父类汇总")
    parent_agg = conn.execute("""
        SELECT parent_category, type, COUNT(*), SUM(amount)
        FROM transactions GROUP BY parent_category, type ORDER BY SUM(amount) DESC
    """).fetchall()
    report_lines.append(f"   {'父类':<10} {'类型':>4} {'笔数':>5} {'金额':>12}")
    for p, t, cnt, amt in parent_agg:
        report_lines.append(f"   {p:<10} {t:>4} {cnt:>5} ¥{amt:>10,.2f}")

    # 5. 待确认清单
    report_lines.append(f"\n## 5. 待确认清单 ({len(pending_list)}条)")
    for p in sorted(pending_list, key=lambda x: x['date']):
        report_lines.append(f"   {p['date']} | {p['old_type']} | ¥{p['amount']:,.2f} | {p['account']} | {p['note']} | {p['reason']}")

    # 6. 样例
    report_lines.append(f"\n## 6. 随机样例 (20条)")
    samples = conn.execute("SELECT * FROM transactions ORDER BY RANDOM() LIMIT 20").fetchall()
    cols = ['id','date','type','parent_category','child_category','amount','note','tags','source','created_at','updated_at','old_type','old_account','status']
    for r in samples:
        d = dict(zip(cols, r))
        report_lines.append(f"   {d['date']} | {d['type']} | {d['parent_category']}›{d['child_category']} | ¥{d['amount']:,.2f} | 旧:{d['old_type']} | {d['note'][:20] if d['note'] else '-'}")

    # 7. 边界样例：重点分类
    report_lines.append(f"\n## 7. 边界分类样例")
    boundary_types = ['电器数码', '旅游交通', '旅游饮食', '旅游娱乐',
                      '红包支出', '红包收入', '退款', '转账收入', '转账支出',
                      '汽车', '订阅', '运动', '理发']
    for bt in boundary_types:
        rows_bt = conn.execute("SELECT * FROM transactions WHERE old_type=? LIMIT 3", (bt,)).fetchall()
        if rows_bt:
            report_lines.append(f"\n   [{bt}]:")
            for r in rows_bt:
                d = dict(zip(cols, r))
                report_lines.append(f"   → {d['date']} | {d['parent_category']}›{d['child_category']} | ¥{d['amount']:,.2f} | {d['note'][:20] if d['note'] else '-'}")
        else:
            # Check if in pending
            pends = [p for p in pending_list if p['old_type'] == bt]
            if pends:
                report_lines.append(f"\n   [{bt}]: ⚠️ 待确认 ({len(pends)}条)")
                for p in pends:
                    report_lines.append(f"   → {p['date']} | ¥{p['amount']:,.2f} | {p['reason']}")

    return '\n'.join(report_lines)


def main():
    print("读取 CSV...")
    rows = load_csv()
    print(f"共 {len(rows)} 条记录")

    print("导入中...")
    conn, auto, fallback, pending_list, unknown_types, mapping_used = run_import()
    print(f"自动映射: {auto} 条, 兜底: {fallback} 条, 待确认: {len(pending_list)} 条")

    if unknown_types:
        print(f"兜底分类(unknown): {unknown_types}")

    print("\n生成验证报告...")
    report = validate(conn, pending_list, rows)
    print(report)

    # Save report
    report_path = os.path.join(HERE, 'import_preview_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n报告已保存: {report_path}")
    print(f"Preview 库: {PREVIEW_DB}")
    print("正式账本 ledger.sqlite 未受影响。")


if __name__ == '__main__':
    main()
