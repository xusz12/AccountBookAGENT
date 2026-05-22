#!/usr/bin/env python3
"""
记账引擎测试套件 — 使用独立测试库，不触碰正式账本。
运行: cd accounting && python test_ledger.py
覆盖: init_db (含 time 字段) / parse_nl 时间解析 / CRUD / query / echo / check_consistency / 边界
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_ledger.sqlite')

import ledger
ledger.DB_PATH = TEST_DB

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
    for s in ['-wal', '-shm']:
        p = TEST_DB + s
        if os.path.exists(p):
            os.remove(p)

PASS = 0
FAIL = 0

def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


today = '2026-05-22'

# ============================================================
# 1. init_db — 含 time 字段
# ============================================================
section("1. init_db (12列含time)")

ledger.init_db()
check(os.path.exists(TEST_DB), "测试库文件已创建")

with sqlite3.connect(TEST_DB) as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    check(('transactions',) in tables, "transactions 表已创建")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    expected = {'id', 'date', 'time', 'type', 'parent_category', 'child_category',
                'amount', 'note', 'tags', 'source', 'created_at', 'updated_at'}
    check(cols == expected, "12列含time")
    col_order = [row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()]
    check(col_order[2] == 'time', f"time 在第3列 (实际位置 {col_order.index('time')+1})")
    idxs = {row[1] for row in conn.execute("PRAGMA index_list(transactions)").fetchall()}
    check('idx_date' in idxs and 'idx_type' in idxs, "索引存在")

ledger.init_db()
check(True, "重复 init_db 幂等")


# ============================================================
# 2. parse_nl — 含 time 解析
# ============================================================
section("2. parse_nl")

record, _ = ledger.parse_nl('午饭 35', today)
check(record['amount'] == 35.0 and record['type'] == '支出' and record['parent_category'] == '餐饮', "基本解析")
check(record['time'].startswith(today) and len(record['time']) == 16, f"默认 time 格式 (实际 {record['time']})")

record, _ = ledger.parse_nl('12:30 午饭 35', today)
check(record['time'] == '2026-05-22 12:30', f"HH:MM→{record['time']}")

record, _ = ledger.parse_nl('下午3点 咖啡 15', today)
check(record['time'] == '2026-05-22 15:00', f"下午3点→{record['time']}")

record, _ = ledger.parse_nl('晚上9点 电影 60', today)
check(record['time'] == '2026-05-22 21:00', f"晚上9点→{record['time']}")

record, _ = ledger.parse_nl('中午 午饭 35', today)
check(record['time'] == '2026-05-22 12:00', "中午→12:00")

record, _ = ledger.parse_nl('早上 咖啡 15', today)
check(record['time'] == '2026-05-22 08:00', "早上→08:00")

record, _ = ledger.parse_nl('昨天 午饭 35', today)
check(record['date'] == '2026-05-21', "昨天")

record, _ = ledger.parse_nl('前天 午饭 35', today)
check(record['date'] == '2026-05-20', "前天")

record, _ = ledger.parse_nl('15号 午饭 35', today)
check(record['date'] == '2026-05-15', "X号")

# 歧义
record, confirm = ledger.parse_nl('红包 200', today)
check(record is None and confirm is not None, "红包→歧义")

record, _ = ledger.parse_nl('发红包 100', today)
check(record is not None and record['child_category'] == '红包支出', "发红包→不走歧义")

record, _ = ledger.parse_nl('收红包 100', today)
check(record is not None and record['child_category'] == '红包收入', "收红包→红包收入")

# 新关键词
record, _ = ledger.parse_nl('剪头发 30', today)
check(record['child_category'] == '理发', "剪头发→理发")

# 兜底
record, _ = ledger.parse_nl('随便买 50', today)
check(record['type'] == '支出', "兜底→支出")

record, _ = ledger.parse_nl('到账 10000', today)
check(record['type'] == '收入', "到账+大额→收入")

record, confirm = ledger.parse_nl('无金额', today)
check(record is None, "无金额→None")

# 关键词覆盖
for nl, etype, eparent, echild in [
    ('地铁 5', '支出', '交通', '交通费'),
    ('工资 15000', '收入', '工作', '工资'),
    ('股票卖出 1000', '收入', '投资', '投资收益'),
    ('股票亏了 300', '支出', '投资', '投资亏损'),
    ('电费 200', '支出', '住房', '电费'),
    ('房贷 8000', '支出', '住房', '房贷'),
    ('ChatGPT 20', '支出', '订阅', 'AI'),
    ('电影 60', '支出', '娱乐', '电影'),
    ('车险 3000', '支出', '汽车', '车险'),
    ('停车费 10', '支出', '交通', '停车费'),
]:
    record, _ = ledger.parse_nl(nl, today)
    if record:
        ok = record['type'] == etype and record['parent_category'] == eparent and record['child_category'] == echild
        check(ok, f"「{nl}」→ {etype}/{eparent}/{echild}")
    else:
        check(False, f"「{nl}」→ None")

# 备注和标签
record, _ = ledger.parse_nl('午饭 35，和朋友一起', today)
check('朋友' in record['note'], "备注提取")

record, _ = ledger.parse_nl('午饭 35，日本游旅行', today)
tags = json.loads(record['tags']) if isinstance(record['tags'], str) else record['tags']
check('日本游' in tags and '旅行' in tags, "标签提取")


# ============================================================
# 3. CRUD
# ============================================================
section("3. CRUD")

r1, _ = ledger.parse_nl('午饭 35 12:30', today)
ledger.insert(r1)
check(ledger.total_count() == 1, "insert")
saved = ledger.get(r1['id'])
check(saved is not None and saved['amount'] == 35.0, "get 金额")
check('time' in saved, "get 含 time")

r2, _ = ledger.parse_nl('工资 15000', today)
ledger.insert(r2)
check(ledger.total_count() == 2, "insert 2条")

r3, _ = ledger.parse_nl('地铁 5', today)
ledger.insert(r3)
check(ledger.total_count() == 3, "insert 3条")

updated = ledger.update(r1['id'], {'amount': 40.0, 'note': '加鸡腿'})
check(updated['amount'] == 40.0 and updated['note'] == '加鸡腿', "update")

deleted = ledger.delete(r3['id'])
check(deleted is not None and ledger.total_count() == 2, "delete")

r = ledger.get(r1['id'])
check(r['date'] == today and r['time'] and r['source'] == 'chat' and r['created_at'], "字段完整")


# ============================================================
# 4. query
# ============================================================
section("4. query")

r_old, _ = ledger.parse_nl('电费 200', today)
r_old['date'] = '2026-05-15'
r_old['time'] = '2026-05-15 10:00'
ledger.insert(r_old)

check(ledger.total_count() == 3, "3条总计")

summary, results = ledger.query(period='今天')
check(len(results) == 2, "今天=2条")

summary, results = ledger.query(period='本月')
check(len(results) == 3, "本月=3条")

summary, results = ledger.query(period='本月', type_='收入')
check(len(results) == 1, "本月收入=1条")

summary, results = ledger.query(period='本月', parent='餐饮')
check(all(r['parent_category'] == '餐饮' for r in results), "parent过滤")

summary, results = ledger.query(period='全部')
total_inc = sum(r['amount'] for r in results if r['type'] == '收入')
total_exp = sum(r['amount'] for r in results if r['type'] == '支出')
check(f'¥{total_inc:,.2f}' in summary, "汇总收入")


# ============================================================
# 5. echo
# ============================================================
section("5. echo")

msg = ledger.echo(saved, action='已记录')
check('txn_' in msg and '账本共' in msg and '✅' in msg, "echo 格式")
check('12:30' in msg or '13:00' in msg, "echo 含时间")


# ============================================================
# 6. check_consistency
# ============================================================
section("6. check_consistency")

ok, msg = ledger.check_consistency()
check(ok, "一致性通过")
check('✅' in msg, "含✅")

# 插入不一致记录验证检测能力
with sqlite3.connect(TEST_DB) as conn:
    conn.execute("""
        INSERT INTO transactions (id, date, time, type, parent_category, child_category, amount, note, tags, source, created_at, updated_at)
        VALUES ('bad01', '2026-01-01', '2026-05-22 10:00', '支出', '餐饮', '吃饭', 1.0, '', '[]', 'chat', '2026-05-22 10:00:00', '2026-05-22 10:00:00')
    """)
    conn.commit()

ok2, msg2 = ledger.check_consistency()
check(not ok2 and '❌' in msg2 and 'txn_bad01' in msg2, "检测不一致")
ledger.delete('bad01')


# ============================================================
# 7. 四字段确认 (Task #6)
# ============================================================
section("7. 四时间字段 (Task #6)")

r, _ = ledger.parse_nl('午饭 35 12:30', '2026-05-20')
ledger.insert(r)
saved2 = ledger.get(r['id'])

check(saved2['date'] == '2026-05-20', "date=交易日期")
check(saved2['time'] == '2026-05-20 12:30', "time=交易时间")
check(saved2['created_at'] is not None, "created_at=入库时间")
check(saved2['updated_at'] is not None, "updated_at=修改时间")

# date = substr(time,1,10)
check(saved2['date'] == saved2['time'][:10], "date=substr(time,1,10)")


# ============================================================
# 8. 边界
# ============================================================
section("8. 边界")

record, _ = ledger.parse_nl('', today)
check(record is None, "空输入→None")

record, _ = ledger.parse_nl('股票 99999999.99', today)
check(record and record['amount'] == 99999999.99, "超大金额")

record, _ = ledger.parse_nl('午饭 35，3个人AA', today)
check(record['amount'] == 35.0, "备注数字不影响金额")

r_now, _ = ledger.parse_nl('测试 100', today)
check(r_now['created_at'] == r_now['updated_at'], "新建 created_at==updated_at")


# ============================================================
# 9. audit_block
# ============================================================
section("9. audit_block")

block = ledger.audit_block("测试", [{'amount': 100, 'type': '收入', 'parent_category': '工作'}], 100, 0, "2026-05-01 ~ 2026-05-22")
check('📊 测试' in block and '¥100.00' in block, "audit_block")


# ============================================================
# 结果
# ============================================================
section("结果")
print(f"\n  通过: {PASS} / 失败: {FAIL} / 总计: {PASS + FAIL}")
if FAIL == 0:
    print("  🎉 全部通过!")
else:
    print(f"  ⚠️ {FAIL} 项失败")

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
    for s in ['-wal', '-shm']:
        p = TEST_DB + s
        if os.path.exists(p):
            os.remove(p)
print("  测试库已清理。")

sys.exit(0 if FAIL == 0 else 1)
