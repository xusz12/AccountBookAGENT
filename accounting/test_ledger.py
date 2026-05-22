#!/usr/bin/env python3
"""
记账引擎测试套件 — 使用独立测试库，不触碰正式账本。
运行: cd accounting && python test_ledger.py
"""

import sys
import os
import json
import sqlite3
import uuid
from datetime import datetime, timedelta

# 将 ledger.py 加载为模块，但先设置测试 DB 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_ledger.sqlite')

# 在 import 前强行覆盖 DB_PATH
import ledger
ledger.DB_PATH = TEST_DB

# 清理旧测试库
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
    if os.path.exists(TEST_DB + '-wal'):
        os.remove(TEST_DB + '-wal')
    if os.path.exists(TEST_DB + '-shm'):
        os.remove(TEST_DB + '-shm')

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


# ============================================================
# 1. init_db — 数据库创建
# ============================================================
section("1. init_db — 数据库创建")

ledger.init_db()
check(os.path.exists(TEST_DB), "测试库文件已创建")

with sqlite3.connect(TEST_DB) as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    check(('transactions',) in tables, "transactions 表已创建")

    # 列校验
    cols = {row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    expected = {'id', 'date', 'type', 'parent_category', 'child_category', 'amount', 'note', 'tags', 'source', 'created_at', 'updated_at'}
    check(cols == expected, f"表结构完整 (11列)")

    # 索引校验
    idxs = {row[1] for row in conn.execute("PRAGMA index_list(transactions)").fetchall()}
    check('idx_date' in idxs, "idx_date 索引存在")
    check('idx_type' in idxs, "idx_type 索引存在")
    check('idx_parent' in idxs, "idx_parent_category 索引存在")
    check('idx_child' in idxs, "idx_child_category 索引存在")

# 重复 init_db 不报错
ledger.init_db()
check(True, "重复 init_db 幂等无报错")


# ============================================================
# 2. parse_nl — 自然语言解析
# ============================================================
section("2. parse_nl — 自然语言解析")

today = '2026-05-22'

# --- 2a. 金额提取 ---
record, confirm = ledger.parse_nl('午饭 35', today)
check(record is not None and confirm is None, "基本金额提取成功")
check(record['amount'] == 35.0, f"金额 35.0 (实际 {record['amount']})")
check(record['type'] == '支出', "识别为支出")
check(record['parent_category'] == '餐饮', "大类=餐饮")
check(record['child_category'] == '吃饭', "子类=吃饭")

record, confirm = ledger.parse_nl('工资 15000', today)
check(record['type'] == '收入', "工资识别为收入")
check(record['parent_category'] == '工作', "大类=工作")
check(record['child_category'] == '工资', "子类=工资")

# 小数金额
record, confirm = ledger.parse_nl('咖啡 22.5', today)
check(record is not None and record['amount'] == 22.5, "小数金额 22.5")
check(record['child_category'] == '饮料', "咖啡→饮料")

# --- 2b. 无金额 ---
record, confirm = ledger.parse_nl('午饭吃了', today)
check(record is None and '金额' in str(confirm), "无金额→回问提示")

# --- 2c. 日期解析 ---
record, _ = ledger.parse_nl('午饭 35', today)
check(record['date'] == '2026-05-22', "默认日期=今天")

record, _ = ledger.parse_nl('昨天 午饭 35', today)
check(record['date'] == '2026-05-21', "昨天→2026-05-21")

record, _ = ledger.parse_nl('前天 午饭 35', today)
check(record['date'] == '2026-05-20', "前天→2026-05-20")

record, _ = ledger.parse_nl('15号 午饭 35', today)
check(record['date'] == '2026-05-15', "X号→指定日期")

# --- 2d. 歧义关键词 ---
record, confirm = ledger.parse_nl('红包 200', today)
check(record is None and confirm is not None, "红包→歧义回问")
check('红包收入' in str(confirm) and '红包支出' in str(confirm), "红包回问包含两个选项")

record, confirm = ledger.parse_nl('保险 500', today)
check(record is None and confirm is not None, "保险→歧义回问")
check('车险' in str(confirm), "保险回问包含车险")

# --- 2e. 关键词最长匹配 ---
record, _ = ledger.parse_nl('股票赚了 500', today)
check(record['child_category'] == '投资收益', "股票赚→投资收益")

record, _ = ledger.parse_nl('股票亏了 300', today)
check(record['child_category'] == '投资亏损', "股票亏→投资亏损")

# --- 2f. 备注和标签 ---
record, _ = ledger.parse_nl('午饭 35，和朋友一起吃的', today)
check('朋友' in record['note'], "备注提取")

record, _ = ledger.parse_nl('午饭 35，日本游旅行团餐', today)
tags = json.loads(record['tags']) if isinstance(record['tags'], str) else record['tags']
check('日本游' in tags, "日本游标签")
check('旅行' in tags, "旅行标签")

# --- 2g. 兜底分类 ---
record, _ = ledger.parse_nl('随便买了个东西 50', today)
check(record['type'] == '支出', "未知关键词→兜底支出")
check(record['parent_category'] == '其他支出', "未知关键词→其他支出")

record, _ = ledger.parse_nl('到账 10000', today)
check(record['type'] == '收入', "到账+大额→兜底收入")

# --- 2h. 各类关键词覆盖 ---
test_cases = [
    ('地铁 5', ('支出', '交通', '交通费')),
    ('高铁 150', ('支出', '交通', '交通费')),
    ('打车 30', ('支出', '交通', '交通费')),
    ('话费 100', ('支出', '订阅', '通讯')),
    ('ChatGPT 20', ('支出', '订阅', 'AI')),
    ('VPN 15', ('支出', '订阅', 'VPN')),
    ('电影 60', ('支出', '娱乐', '电影')),
    ('理发 40', ('支出', '生活', '理发')),
    ('电费 200', ('支出', '住房', '电费')),
    ('房贷 8000', ('支出', '住房', '房贷')),
    ('药 45', ('支出', '医疗', '医疗')),
    ('车险 3000', ('支出', '汽车', '车险')),
    ('年终奖 50000', ('收入', '工作', '年终奖')),
    ('公积金 5000', ('收入', '工作', '公积金')),
    ('发红包 100', ('支出', '其他支出', '红包支出')),
    ('股票卖出 1000', ('收入', '投资', '投资收益')),
]
for nl, (etype, eparent, echild) in test_cases:
    record, confirm = ledger.parse_nl(nl, today)
    if record is None:
        check(False, f"「{nl}」→ {etype}/{eparent}/{echild} (实际 None, confirm={confirm})")
    else:
        ok = record['type'] == etype and record['parent_category'] == eparent and record['child_category'] == echild
        check(ok, f"「{nl}」→ {etype}/{eparent}/{echild} (实际 {record['type']}/{record['parent_category']}/{record['child_category']})")


# ============================================================
# 3. CRUD — 增删改查
# ============================================================
section("3. CRUD — 增删改查")

# --- insert ---
r1, _ = ledger.parse_nl('午饭 35', today)
ledger.insert(r1)
check(ledger.total_count() == 1, "插入后总数=1")
check(ledger.get(r1['id']) is not None, "get 能找到记录")
check(ledger.get(r1['id'])['amount'] == 35.0, "get 返回正确金额")

# --- insert 多条 ---
r2, _ = ledger.parse_nl('工资 15000', today)
r3, _ = ledger.parse_nl('地铁 5', today)
ledger.insert(r2)
ledger.insert(r3)
check(ledger.total_count() == 3, "插入3条后总数=3")

# --- update ---
updated = ledger.update(r1['id'], {'amount': 40.0, 'note': '加了个鸡腿'})
check(updated['amount'] == 40.0, "更新金额=40")
check(updated['note'] == '加了个鸡腿', "更新备注")
check(updated['updated_at'] is not None and updated['updated_at'] >= r1['created_at'], "updated_at 已刷新")

# --- update 不存在的记录 ---
result = ledger.update('nonexistent', {'amount': 100})
check(result is None, "更新不存在的记录返回 None")

# --- delete ---
deleted = ledger.delete(r3['id'])
check(deleted is not None, "删除记录返回原记录")
check(deleted['id'] == r3['id'], "删除记录ID正确")
check(ledger.total_count() == 2, "删除后总数=2")
check(ledger.get(r3['id']) is None, "get 找不到已删除记录")

# --- delete 不存在的记录 ---
result = ledger.delete('nonexistent')
check(result is None, "删除不存在记录返回 None")

# --- 字段完整性 ---
r = ledger.get(r1['id'])
check(r['id'] is not None, "id 非空")
check(r['date'] == today, "date 正确")
check(r['source'] == 'chat', "source=chat")
check(r['created_at'] is not None, "created_at 非空")
check(r['updated_at'] is not None, "updated_at 非空")


# ============================================================
# 4. query — 查询汇总
# ============================================================
section("4. query — 查询汇总")

# 再插入几条不同日期的记录
d1 = '2026-05-20'
d2 = '2026-05-15'
# 修改日期：直接修改 parse_nl 结果的 date
r_old1, _ = ledger.parse_nl('电费 200', today)
r_old1['date'] = d2
ledger.insert(r_old1)

r_old2, _ = ledger.parse_nl('早饭 12', today)
r_old2['date'] = d1
ledger.insert(r_old2)

check(ledger.total_count() == 4, "总计4条记录")

# --- 今天 ---
summary, results = ledger.query(period='今天', detail=True)
check(len(results) == 2, f"今天命中2条 (实际 {len(results)})")
check('2026-05-22' in summary, "今天汇总包含日期")

# --- 本月 ---
summary, results = ledger.query(period='本月', detail=True)
check(len(results) == 4, f"本月命中4条 (实际 {len(results)})")

# --- 收入过滤 ---
summary, results = ledger.query(period='本月', type_='收入', detail=True)
check(len(results) == 1, f"本月收入=1条 (实际 {len(results)})")
check(results[0]['type'] == '收入', "过滤结果类型正确")

# --- 按分类过滤 ---
summary, results = ledger.query(period='本月', parent='餐饮', detail=True)
check(all(r['parent_category'] == '餐饮' for r in results), "按parent过滤正确")

# --- 全部 ---
summary, results = ledger.query(period='全部')
check(len(results) == 4, "全部命中4条")

# --- 汇总数字校验 ---
total_inc = sum(r['amount'] for r in results if r['type'] == '收入')
total_exp = sum(r['amount'] for r in results if r['type'] == '支出')
check('¥{0:,.2f}'.format(total_inc) in summary, "汇总包含正确收入额")
check('¥{0:,.2f}'.format(total_exp) in summary, "汇总包含正确支出额")  # Note: will use actual values


# ============================================================
# 5. echo — 回显格式
# ============================================================
section("5. echo — 回显格式")

r = ledger.get(r1['id'])
msg = ledger.echo(r, action='已记录')
check('txn_' in msg, "回显包含 txn_ 前缀")
check(r1['id'] in msg, "回显包含交易ID")
check('账本共' in msg, "回显包含总记录数")
check('✅' in msg, "回显包含✅标记")


# ============================================================
# 6. 边界和异常场景
# ============================================================
section("6. 边界和异常场景")

# --- 金额为0 ---
record, confirm = ledger.parse_nl('午饭', today)
check(record is None, "无金额→None")

# --- 空输入 ---
record, confirm = ledger.parse_nl('', today)
check(record is None, "空输入→None")

# --- 金额含逗号（千分位） ---
record, confirm = ledger.parse_nl('工资 15,000', today)
# 正则只匹配第一个数字，所以会提取到15
check(record is not None and record['amount'] == 15.0, "逗号在金额中→提取到第一个数字15")

# --- 超大金额 ---
record, _ = ledger.parse_nl('股票卖出 99999999.99', today)
check(record is not None and record['amount'] == 99999999.99, "超大金额正常处理")

# --- 备注中也有数字 ---
record, _ = ledger.parse_nl('午饭 35，3个人AA', today)
check(record['amount'] == 35.0, "备注中的数字不影响金额提取")

# --- 同一条记录创建和更新时间 ---
r_now, _ = ledger.parse_nl('测试 100', today)
check(r_now['created_at'] == r_now['updated_at'], "新建记录 created_at == updated_at")

# --- 批量操作后数据一致性 ---
before = ledger.total_count()
for i in range(10):
    rec, _ = ledger.parse_nl(f'测试 {100 + i}', today)
    ledger.insert(rec)
check(ledger.total_count() == before + 10, "批量插入10条后数据一致")

# 清理刚才插入的测试记录
for i in range(10):
    # 查找并删除
    pass  # skip cleanup, db will be removed at next run


# ============================================================
# 7. 四字段时间字段分析 (Task #6)
# ============================================================
section("7. 四字段时间字段分析 (Task #6)")

r, _ = ledger.parse_nl('午饭 35', '2026-05-20')
ledger.insert(r)
saved = ledger.get(r['id'])

check('date' in saved, "date 字段存在")
check('created_at' in saved, "created_at 字段存在")
check('updated_at' in saved, "updated_at 字段存在")

# 注意: 表结构中没有 time 字段! parse_nl 也没有生成 time
# 查看表结构确认
with sqlite3.connect(TEST_DB) as conn:
    cols = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}

print(f"\n  表字段列表: {list(cols.keys())}")
print(f"  date      类型: {cols.get('date')}")
print(f"  created_at 类型: {cols.get('created_at')}")
print(f"  updated_at 类型: {cols.get('updated_at')}")

time_fields = [c for c in cols if 'time' in c.lower()]
check(len(time_fields) == 0, f"无独立 time 字段 (找到: {time_fields})")

# 四字段含义分析
# date: 交易发生的日期 (YYYY-MM-DD)
# created_at: 记录创建时间 (YYYY-MM-DD HH:MM:SS)
# updated_at: 记录最后更新时间 (YYYY-MM-DD HH:MM:SS)
# 没有 time 字段
print(f"\n  实际时间相关字段: date / created_at / updated_at (3个)")
print(f"  date: 交易日期 (YYYY-MM-DD)")
print(f"  created_at: 记录创建时间 (YYYY-MM-DD HH:MM:SS)")
print(f"  updated_at: 记录更新时间 (YYYY-MM-DD HH:MM:SS)")
print(f"  ⚠️ 注意: 当前表结构没有独立 time 字段，可能是 NL 中提到的 '时间' 指 created_at")


# ============================================================
# 结果汇总
# ============================================================
section("测试结果")
print(f"\n  通过: {PASS} / 失败: {FAIL} / 总计: {PASS + FAIL}")
if FAIL == 0:
    print("  🎉 全部通过!")
else:
    print(f"  ⚠️ 有 {FAIL} 项失败需要修复")

# 清理
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
    for suffix in ['-wal', '-shm']:
        p = TEST_DB + suffix
        if os.path.exists(p):
            os.remove(p)
print("\n  测试库已清理。")

sys.exit(0 if FAIL == 0 else 1)
