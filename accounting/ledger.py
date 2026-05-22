#!/usr/bin/env python3
"""
v1 记账引擎 — SQLite 主账本
字段: id / date / type / parent_category / child_category / amount / note / tags / source / created_at / updated_at
"""

import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ledger.sqlite')

# ============================================================
# 分类体系
# ============================================================
CATEGORIES = {
    '收入': {
        '工作': ['工资', '绩效', '奖金', '公积金', '年终奖', '过节费'],
        '投资': ['投资收益'],
        '其他收入': ['副业', '二手', '红包收入', '援助', '退款', '调整收入'],
    },
    '支出': {
        '餐饮': ['吃饭', '饮料', '零食', '烟酒'],
        '住房': ['电费', '水费', '燃气费', '物业费', '房租', '房贷', '装修', '家政服务'],
        '汽车': ['车贷', '车险', '维护'],
        '交通': ['停车费', '加油费', '高速费', '交通费', '租车'],
        '购物': ['日用', '电器', '数码', '服饰', '玩具', '旅游购物', '礼物', '书籍', '运动器材'],
        '订阅': ['通讯', 'AI', 'VPN', '其他订阅'],
        '娱乐': ['网吧', '电影', '游戏', '游玩', '按摩'],
        '生活': ['运动', '学习', '育儿', '宠物', '家庭', '理发'],
        '医疗': ['医疗', '保险'],
        '投资': ['投资亏损'],
        '其他支出': ['红包支出', '借出', '调整支出', '证件办理'],
    }
}

# ============================================================
# 关键词 → (type, parent, child) 规则表
# 每次用户纠正后追加
# ============================================================
KEYWORD_RULES = {
    # --- 餐饮 ---
    '午饭': ('支出', '餐饮', '吃饭'),
    '晚饭': ('支出', '餐饮', '吃饭'),
    '早餐': ('支出', '餐饮', '吃饭'),
    '外卖': ('支出', '餐饮', '吃饭'),
    '聚餐': ('支出', '餐饮', '吃饭'),
    '吃饭': ('支出', '餐饮', '吃饭'),
    '咖啡': ('支出', '餐饮', '饮料'),
    '奶茶': ('支出', '餐饮', '饮料'),
    '饮料': ('支出', '餐饮', '饮料'),
    '烟': ('支出', '餐饮', '烟酒'),
    '酒': ('支出', '餐饮', '烟酒'),
    '零食': ('支出', '餐饮', '零食'),
    '水果': ('支出', '餐饮', '零食'),
    # --- 交通 ---
    '打车': ('支出', '交通', '交通费'),
    '出租车': ('支出', '交通', '交通费'),
    '滴滴': ('支出', '交通', '交通费'),
    '加油': ('支出', '交通', '加油费'),
    '地铁': ('支出', '交通', '交通费'),
    '公交': ('支出', '交通', '交通费'),
    '机票': ('支出', '交通', '交通费'),
    '火车票': ('支出', '交通', '交通费'),
    '高铁': ('支出', '交通', '交通费'),
    '高速费': ('支出', '交通', '高速费'),
    '停车费': ('支出', '交通', '停车费'),
    '停车': ('支出', '交通', '停车费'),
    # --- 订阅 ---
    'ChatGPT': ('支出', '订阅', 'AI'),
    'Claude': ('支出', '订阅', 'AI'),
    'Midjourney': ('支出', '订阅', 'AI'),
    'VPN': ('支出', '订阅', 'VPN'),
    '话费': ('支出', '订阅', '通讯'),
    '网费': ('支出', '订阅', '通讯'),
    '流量': ('支出', '订阅', '通讯'),
    '订阅费': ('支出', '订阅', '其他订阅'),
    # --- 收入 ---
    '工资': ('收入', '工作', '工资'),
    '绩效': ('收入', '工作', '绩效'),
    '奖金': ('收入', '工作', '奖金'),
    '年终奖': ('收入', '工作', '年终奖'),
    '公积金': ('收入', '工作', '公积金'),
    '过节费': ('收入', '工作', '过节费'),
    '投资收益': ('收入', '投资', '投资收益'),
    '股票赚': ('收入', '投资', '投资收益'),
    '股票卖出': ('收入', '投资', '投资收益'),
    '基金赚': ('收入', '投资', '投资收益'),
    'ETF': ('收入', '投资', '投资收益'),
    '副业': ('收入', '其他收入', '副业'),
    '二手卖': ('收入', '其他收入', '二手'),
    '退款': ('收入', '其他收入', '退款'),
    '援助': ('收入', '其他收入', '援助'),
    '收红包': ('收入', '其他收入', '红包收入'),
    '发红包': ('支出', '其他支出', '红包支出'),
    # --- 住房 ---
    '房贷': ('支出', '住房', '房贷'),
    '电费': ('支出', '住房', '电费'),
    '水费': ('支出', '住房', '水费'),
    '燃气费': ('支出', '住房', '燃气费'),
    '物业费': ('支出', '住房', '物业费'),
    '物业': ('支出', '住房', '物业费'),
    '房租': ('支出', '住房', '房租'),
    '租金': ('支出', '住房', '房租'),
    '装修': ('支出', '住房', '装修'),
    # --- 医疗 ---
    '医疗': ('支出', '医疗', '医疗'),
    '药': ('支出', '医疗', '医疗'),
    '看医生': ('支出', '医疗', '医疗'),
    '医院': ('支出', '医疗', '医疗'),
    '门诊': ('支出', '医疗', '医疗'),
    # --- 娱乐 ---
    '电影': ('支出', '娱乐', '电影'),
    '网吧': ('支出', '娱乐', '网吧'),
    '游戏': ('支出', '娱乐', '游戏'),
    '按摩': ('支出', '娱乐', '按摩'),
    # --- 生活 ---
    '理发': ('支出', '生活', '理发'),
    '剪头发': ('支出', '生活', '理发'),
    '学习': ('支出', '生活', '学习'),
    '书': ('支出', '购物', '书籍'),
    '宠物': ('支出', '生活', '宠物'),
    # --- 其他支出 ---
    '办证': ('支出', '其他支出', '证件办理'),
    '身份证': ('支出', '其他支出', '证件办理'),
    # --- 购物 ---
    '日用': ('支出', '购物', '日用'),
    '服饰': ('支出', '购物', '服饰'),
    '衣服': ('支出', '购物', '服饰'),
    '鞋子': ('支出', '购物', '服饰'),
    '玩具': ('支出', '购物', '玩具'),
    '数码': ('支出', '购物', '数码'),
    '礼物': ('支出', '购物', '礼物'),
    # --- 投资 ---
    '股票亏': ('支出', '投资', '投资亏损'),
    '投资亏损': ('支出', '投资', '投资亏损'),
    # --- 汽车 ---
    '车险': ('支出', '汽车', '车险'),
    '车贷': ('支出', '汽车', '车贷'),
    '保养': ('支出', '汽车', '维护'),
    '修车': ('支出', '汽车', '维护'),
}

# 方向不明确时需回问的关键词
AMBIGUOUS_KEYWORDS = {
    '红包': [('收入', '其他收入', '红包收入'), ('支出', '其他支出', '红包支出')],
    '保险': [('支出', '医疗', '保险'), ('支出', '汽车', '车险')],
    '转账': [('收入', '其他收入', '调整收入'), ('支出', '其他支出', '调整支出')],
}


def init_db():
    """创建数据库和表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id              TEXT PRIMARY KEY,
                date            TEXT NOT NULL,
                time            TEXT DEFAULT '',
                type            TEXT NOT NULL CHECK(type IN ('收入','支出')),
                parent_category TEXT NOT NULL,
                child_category  TEXT NOT NULL,
                amount          REAL NOT NULL CHECK(amount > 0),
                note            TEXT DEFAULT '',
                tags            TEXT DEFAULT '[]',
                source          TEXT DEFAULT 'chat',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON transactions(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_parent ON transactions(parent_category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_child ON transactions(child_category)")
        conn.commit()


def parse_nl(nl_input, today=None):
    """
    解析自然语言输入，返回 (record_dict, needs_confirm_msg)。
    needs_confirm_msg 不为 None 表示需要回问。
    """
    import re
    if today is None:
        today = datetime.now().strftime('%Y-%m-%d')

    # 金额提取
    amount_match = re.search(r'(\d+(?:\.\d+)?)', nl_input)
    amount = float(amount_match.group(1)) if amount_match else 0.0
    if amount == 0.0:
        return None, "没识别到金额，请重新说（例如：午饭 35）"

    # 日期
    date_str = today
    if '昨天' in nl_input:
        d = datetime.strptime(today, '%Y-%m-%d') - timedelta(days=1)
        date_str = d.strftime('%Y-%m-%d')
    elif '前天' in nl_input:
        d = datetime.strptime(today, '%Y-%m-%d') - timedelta(days=2)
        date_str = d.strftime('%Y-%m-%d')
    day_match = re.search(r'(\d{1,2})号', nl_input)
    if day_match:
        day = int(day_match.group(1))
        date_str = f"{today[:8]}{day:02d}"

    # 时间提取
    now = datetime.now()
    time_str = f"{date_str} {now.strftime('%H:%M')}"
    hm_match = re.search(r'(\d{1,2}):(\d{2})', nl_input)
    hour_match = re.search(r'(\d{1,2})点', nl_input)
    if hm_match:
        h, m = int(hm_match.group(1)), int(hm_match.group(2))
        time_str = f"{date_str} {h:02d}:{m:02d}"
    elif hour_match:
        h = int(hour_match.group(1))
        if '下午' in nl_input or '晚上' in nl_input:
            if h < 12: h += 12
        elif '中午' in nl_input and h < 12:
            h += 12
        time_str = f"{date_str} {h:02d}:00"
    elif '中午' in nl_input:
        time_str = f"{date_str} 12:00"
    elif '早上' in nl_input:
        time_str = f"{date_str} 08:00"
    elif '晚上' in nl_input:
        time_str = f"{date_str} 20:00"

    # 关键词匹配
    ie_type, parent, child = None, None, None
    matched_kw = None
    for keyword, (t, p, c) in KEYWORD_RULES.items():
        if keyword in nl_input:
            if matched_kw is None or len(keyword) > len(matched_kw):
                ie_type, parent, child = t, p, c
                matched_kw = keyword

    # 仅关键词未命中时才检查歧义关键词
    if ie_type is None:
        for keyword, options in AMBIGUOUS_KEYWORDS.items():
            if keyword in nl_input:
                opts_str = ' 还是 '.join([f'{t}-{p}›{c}' for t, p, c in options])
                return None, f"「{keyword}」是 {opts_str}？"

    # 兜底
    if ie_type is None:
        # 尝试智能判断
        if amount >= 100 and any(kw in nl_input for kw in ['到账', '退还', '入账', '收入']):
            ie_type, parent, child = '收入', '其他收入', '调整收入'
        elif '订阅' in nl_input:
            ie_type, parent, child = '支出', '订阅', '其他订阅'
        elif '付' in nl_input or '买' in nl_input or '花了' in nl_input:
            ie_type, parent, child = '支出', '其他支出', '调整支出'
        else:
            ie_type, parent, child = '支出', '其他支出', '调整支出'

    # 备注提取
    note = ''
    parts = re.split(r'[，,]\s*', nl_input, maxsplit=1)
    if len(parts) > 1:
        note = parts[1].strip()
    # 去掉金额和已知关键词
    note = re.sub(r'\d+(?:\.\d+)?', '', note).strip()

    # 标签
    tags = []
    for tag_kw in ['旅行', '社交', '家庭', '报销', '装修', '宠物', 'AA', '日本游']:
        if tag_kw in nl_input:
            tags.append(tag_kw)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    record = {
        'id': str(uuid.uuid4())[:8],
        'date': date_str,
        'time': time_str,
        'type': ie_type,
        'parent_category': parent,
        'child_category': child,
        'amount': amount,
        'note': note,
        'tags': json.dumps(tags, ensure_ascii=False) if tags else '[]',
        'source': 'chat',
        'created_at': now_str,
        'updated_at': now_str,
    }
    return record, None


def total_count():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def insert(record):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO transactions (id, date, time, type, parent_category, child_category, amount, note, tags, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['id'], record['date'], record.get('time', ''),
            record['type'], record['parent_category'], record['child_category'],
            record['amount'], record['note'], record['tags'],
            record['source'], record['created_at'], record['updated_at']
        ))
        conn.commit()
    return record


def update(record_id, updates):
    """更新记录。updates 是 {field: new_value} 的字典"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [now, record_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE transactions SET {set_clause}, updated_at = ? WHERE id = ?", values)
        conn.commit()
    return get(record_id)


def delete(record_id):
    """物理删除一条记录"""
    record = get(record_id)
    if record:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM transactions WHERE id = ?", (record_id,))
            conn.commit()
    return record


def get(record_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (record_id,)).fetchone()
    if row:
        cols = ['id', 'date', 'type', 'parent_category', 'child_category', 'amount', 'note', 'tags', 'source', 'created_at', 'updated_at', 'time']
        return dict(zip(cols, row))
    return None


def query(period='本月', parent=None, child=None, type_=None, limit=50, detail=False):
    """通用查询"""
    today = datetime.now().replace(hour=23, minute=59, second=59)
    start = None
    label = ''

    if period in ('今天', 'today'):
        start = today.replace(hour=0, minute=0, second=0)
        label = '今天'
    elif period in ('昨天', 'yesterday'):
        start = today - timedelta(days=1)
        start = start.replace(hour=0, minute=0, second=0)
        end = start.replace(hour=23, minute=59, second=59)
        label = '昨天'
    elif period in ('本月', '这个月'):
        start = today.replace(day=1, hour=0, minute=0, second=0)
        label = today.strftime('%Y-%m')
    elif period in ('上月', '上个月'):
        first = today.replace(day=1)
        start = (first - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0)
        end = first - timedelta(seconds=1)
        label = start.strftime('%Y-%m')
    elif period in ('今年', '本年'):
        start = today.replace(month=1, day=1, hour=0, minute=0, second=0)
        label = today.strftime('%Y')
    elif period.startswith('最近'):
        try:
            n = int(period[2:])
        except:
            n = 7
        start = today - timedelta(days=n)
        start = start.replace(hour=0, minute=0, second=0)
        label = f'最近{n}天'
    else:
        start = datetime(2000, 1, 1)
        label = '全部'

    where = ["date >= ?"]
    params = [start.strftime('%Y-%m-%d')]
    if period in ('昨天', 'yesterday', '上月', '上个月'):
        where.append("date <= ?")
        params.append(end.strftime('%Y-%m-%d') if period in ('上月', '上个月') else end.strftime('%Y-%m-%d'))

    if type_:
        where.append("type = ?")
        params.append(type_)
    if parent:
        where.append("parent_category = ?")
        params.append(parent)
    if child:
        where.append("child_category = ?")
        params.append(child)

    sql = f"SELECT * FROM transactions WHERE {' AND '.join(where)} ORDER BY date DESC, time DESC, created_at DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(sql, params).fetchall()

    cols = ['id', 'date', 'type', 'parent_category', 'child_category', 'amount', 'note', 'tags', 'source', 'created_at', 'updated_at', 'time']
    results = [dict(zip(cols, r)) for r in rows]

    # Aggregation
    by_parent = defaultdict(lambda: {'收入': 0.0, '支出': 0.0, 'count': 0})
    total_income = 0.0
    total_expense = 0.0
    for r in results:
        amt = r['amount']
        ie = r['type']
        by_parent[r['parent_category']][ie] += amt
        by_parent[r['parent_category']]['count'] += 1
        if ie == '收入':
            total_income += amt
        else:
            total_expense += amt

    # Build summary
    lines = []
    # Scope line
    scope_parts = [f"范围: {start.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}"]
    if type_:
        scope_parts.append(f"type={type_}")
    if parent:
        scope_parts.append(f"parent={parent}")
    if child:
        scope_parts.append(f"child={child}")
    lines.append(f"📊 {label} 汇总")
    lines.append(f"   {' | '.join(scope_parts)}")
    lines.append(f"   收入 ¥{total_income:,.2f} | 支出 ¥{total_expense:,.2f} | 净额 ¥{total_income - total_expense:,.2f}")
    lines.append(f"   命中 {len(results)} 笔（账本共 {total_count()} 条）")

    if by_parent:
        max_p = max(len(p) for p in by_parent.keys())
        lines.append(f"\n   {'大类':<{max_p}} {'笔数':>4} {'收入':>10} {'支出':>10}")
        for p in sorted(by_parent.keys()):
            info = by_parent[p]
            inc = f"¥{info['收入']:,.2f}" if info['收入'] > 0 else '-'
            exp = f"¥{info['支出']:,.2f}" if info['支出'] > 0 else '-'
            lines.append(f"   {p:<{max_p}} {info['count']:>4} {inc:>10} {exp:>10}")

    if detail and results:
        lines.append(f"\n   明细:")
        for r in results[:20]:
            tags_list = json.loads(r['tags']) if r['tags'] and r['tags'] != '[]' else []
            tags_str = f" [{', '.join(tags_list)}]" if tags_list else ''
            note_str = f" — {r['note']}" if r['note'] else ''
            time_val = r.get('time', '')
            time_display = f" {time_val[11:]}" if time_val and ' ' in time_val else (f" {time_val}" if time_val else '')
            lines.append(f"   {r['date']}{time_display} | {r['type']} | {r['parent_category']}›{r['child_category']} | ¥{r['amount']:,.2f}{tags_str}{note_str}")

    return '\n'.join(lines), results


def echo(record, action='已记录'):
    """格式化回显，带交易ID和总记录数"""
    tags_list = json.loads(record.get('tags', '[]')) if isinstance(record.get('tags'), str) else []
    if isinstance(tags_list, str):
        try:
            tags_list = json.loads(tags_list)
        except:
            tags_list = []
    tags_str = f" [{', '.join(tags_list)}]" if tags_list else ''
    note_str = f" — {record.get('note', '')}" if record.get('note') else ''
    total = total_count()
    time_val = record.get('time', '')
    time_display = f" {time_val[11:]}" if time_val and ' ' in time_val else (f" {time_val}" if time_val else '')
    return (f"✅ {action}：txn_{record['id']} | {record['date']}{time_display} | {record['type']} | "
            f"{record['parent_category']} › {record['child_category']} | "
            f"¥{record['amount']:,.2f}{tags_str}{note_str}\n"
            f"   (账本共 {total} 条记录)")


# ============================================================
# 通用审计块生成
# ============================================================
def audit_block(label, results, total_inc, total_exp, scope_info):
    """统一审计输出块，所有查询命令共用"""
    lines = [f"📊 {label}"]
    lines.append(f"   范围: {scope_info}")
    lines.append(f"   收入 ¥{total_inc:,.2f} | 支出 ¥{total_exp:,.2f} | 净额 ¥{total_inc - total_exp:,.2f}")
    lines.append(f"   命中 {len(results)} 笔（账本共 {total_count()} 条）")
    return '\n'.join(lines)


def check_consistency():
    """只读一致性校验：date=substr(time,1,10)。返回 (ok, message)。失败时带代表性交易 ID。"""
    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        bad_date = conn.execute("SELECT COUNT(*) FROM transactions WHERE date != substr(time, 1, 10)").fetchone()[0]
        no_time = conn.execute("SELECT COUNT(*) FROM transactions WHERE time = ''").fetchone()[0]
        inc = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='收入'").fetchone()[0] or 0
        exp = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='支出'").fetchone()[0] or 0
        # 失败时取代表性交易 ID
        bad_samples = []
        if bad_date > 0:
            rows = conn.execute("SELECT id, date, time FROM transactions WHERE date != substr(time, 1, 10) LIMIT 5").fetchall()
            bad_samples = [f"txn_{r[0]} (date={r[1]} time={r[2]})" for r in rows]
        if no_time > 0:
            rows = conn.execute("SELECT id, date FROM transactions WHERE time = '' LIMIT 5").fetchall()
            bad_samples.extend([f"txn_{r[0]} (date={r[1]} time='')" for r in rows])
    ok = bad_date == 0 and no_time == 0
    lines = [f"🔍 一致性: {'✅ 通过' if ok else '❌ 异常'}"]
    lines.append(f"   总记录: {total} | date=substr(time,1,10): {'✅' if bad_date == 0 else f'❌ {bad_date}条'} | time有值: {total - no_time}/{total}")
    lines.append(f"   收入 ¥{inc:,.2f} | 支出 ¥{exp:,.2f} | 净额 ¥{inc - exp:,.2f}")
    if bad_samples:
        lines.append(f"   异常样本: {', '.join(bad_samples[:5])}")
    return ok, '\n'.join(lines)


# ============================================================
# CLI
# ============================================================
if __name__ == '__main__':
    import sys, csv, os
    if len(sys.argv) < 2:
        print("Usage: python ledger.py init|add|get|del|today|month|category|invest|recent|export|check")
        sys.exit(0)

    cmd = sys.argv[1]
    init_db()

    if cmd == 'init':
        print("✅ 账本已就绪")

    elif cmd == 'check':
        ok, msg = check_consistency()
        print(msg)

    elif cmd == 'add':
        nl = ' '.join(sys.argv[2:])
        record, confirm = parse_nl(nl)
        if confirm:
            print(f"⚠️ {confirm}")
        elif record:
            insert(record)
            print(echo(record))
            ok, check_msg = check_consistency()
            if not ok:
                print(f"\n⚠️ CHECK FAILED — 账本需人工复核\n{check_msg}")
            else:
                print(check_msg)

    elif cmd == 'get':
        rid = sys.argv[2]
        r = get(rid)
        if r:
            print(echo(r))
        else:
            print("未找到")

    elif cmd == 'del':
        rid = sys.argv[2]
        r = delete(rid)
        if r:
            print(echo(r, action='已删除'))
            ok, check_msg = check_consistency()
            if not ok:
                print(f"\n⚠️ CHECK FAILED — 账本需人工复核\n{check_msg}")
            else:
                print(check_msg)
        else:
            print("未找到")

    # ============================================================
    # v1.1 固定查询意图库
    # ============================================================

    elif cmd == 'today':
        summary, results = query(period='今天', detail=True)
        print(summary)

    elif cmd == 'month':
        period = sys.argv[2] if len(sys.argv) > 2 else '本月'
        summary, results = query(period=period, detail=False)
        print(summary)

    elif cmd == 'category':
        parent = sys.argv[2] if len(sys.argv) > 2 else None
        child = sys.argv[3] if len(sys.argv) > 3 else None
        period = sys.argv[4] if len(sys.argv) > 4 else '本月'
        if not parent:
            print("Usage: python ledger.py category <父类> [子类] [period]")
            sys.exit(1)
        summary, results = query(period=period, parent=parent, child=child, detail=True)
        print(summary)

    elif cmd == 'invest':
        period = sys.argv[2] if len(sys.argv) > 2 else '本月'
        summary, results = query(period=period, parent='投资', detail=True)
        print(summary)

    elif cmd == 'recent':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        summary, results = query(period=f'最近{n}', detail=True)
        print(summary)

    elif cmd == 'export':
        period = sys.argv[2] if len(sys.argv) > 2 else '本月'
        parent = sys.argv[3] if len(sys.argv) > 3 else None
        summary, results = query(period=period, parent=parent, detail=False, limit=99999)
        print(summary)
        if results:
            today_str = datetime.now().strftime('%Y%m%d')
            safe_period = period.replace('/', '_').replace(' ', '_')
            exports_dir = os.path.join(os.path.dirname(DB_PATH), 'exports')
            os.makedirs(exports_dir, exist_ok=True)
            out_path = os.path.join(exports_dir, f'export_{safe_period}_{today_str}.csv')
            with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['id','date','time','type','parent_category','child_category','amount','note','tags','source'])
                writer.writeheader()
                for r in results:
                    writer.writerow({k: r.get(k, '') for k in writer.fieldnames})
            print(f"\n📁 已导出: {out_path} ({len(results)} 条)")

    else:
        print(f"未知命令: {cmd}")
        print("Usage: python ledger.py init|add|get|del|today|month|category|invest|recent|export|check")
