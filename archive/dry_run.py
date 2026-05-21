#!/usr/bin/env python3
"""v1 Dry-Run: Schema + 10 NL记账示例（不落库）"""

import sqlite3
import json
import uuid
from datetime import datetime

# ============================================================
# PART 1: SCHEMA
# ============================================================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,          -- UUID
    date            TEXT NOT NULL,             -- YYYY-MM-DD
    type            TEXT NOT NULL CHECK(type IN ('收入','支出')),
    parent_category TEXT NOT NULL,
    child_category  TEXT NOT NULL,
    amount          REAL NOT NULL CHECK(amount > 0),
    note            TEXT DEFAULT '',
    tags            TEXT DEFAULT '[]',         -- JSON array
    source          TEXT DEFAULT 'chat',       -- chat|import|voice|ocr
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_parent ON transactions(parent_category);
CREATE INDEX IF NOT EXISTS idx_child ON transactions(child_category);
"""

CATEGORIES = {
    '收入': {
        '工作': ['工资', '绩效', '奖金', '公积金', '年终奖', '过节费'],
        '投资': ['投资收益'],
        '其他': ['副业', '二手', '红包', '援助', '退款', '调整收入'],
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
        '其他': ['修理', '红包支出', '借出', '调整支出'],
    }
}

# ============================================================
# PART 2: 模拟 NL 解析 + 记账
# ============================================================
def simulate_record(nl_input, date_override=None):
    """
    模拟 agent 从 NL 输入到结构化记录的过程。
    实际 v1 中这部分由 agent (我) 的推理完成。
    """
    today = date_override or datetime.now().strftime('%Y-%m-%d')

    # ----- 内置规则（从纠正中学到的）-----
    rules = {
        # 关键词 → (type, parent, child)
        '午饭': ('支出', '餐饮', '吃饭'),
        '晚饭': ('支出', '餐饮', '吃饭'),
        '早餐': ('支出', '餐饮', '吃饭'),
        '外卖': ('支出', '餐饮', '吃饭'),
        '咖啡': ('支出', '餐饮', '饮料'),
        '奶茶': ('支出', '餐饮', '饮料'),
        '烟': ('支出', '餐饮', '烟酒'),
        '酒': ('支出', '餐饮', '烟酒'),
        '零食': ('支出', '餐饮', '零食'),
        '工资': ('收入', '工作', '工资'),
        '奖金': ('收入', '工作', '奖金'),
        '公积金': ('收入', '工作', '公积金'),
        '打车': ('支出', '交通', '交通费'),
        '加油': ('支出', '交通', '加油费'),
        '地铁': ('支出', '交通', '交通费'),
        '公交': ('支出', '交通', '交通费'),
        '电影': ('支出', '娱乐', '电影'),
        '话费': ('支出', '订阅', '通讯'),
        '网费': ('支出', '订阅', '通讯'),
        '医疗': ('支出', '医疗', '医疗'),
        '药': ('支出', '医疗', '医疗'),
        '房贷': ('支出', '住房', '房贷'),
        '物业': ('支出', '住房', '物业费'),
        '电费': ('支出', '住房', '电费'),
        '保险': ('支出', '医疗', '保险'),
        '理发': ('支出', '生活', '理发'),
        '股票亏': ('支出', '投资', '投资亏损'),
        '股票赚': ('收入', '投资', '投资收益'),
        '红包': ('支出', '其他', '红包支出'),
        '收红包': ('收入', '其他', '红包'),
        '捐款': ('支出', '其他', '红包支出'),
        '转账': ('支出', '其他', '调整支出'),
        '二手卖': ('收入', '其他', '二手'),
        '退款': ('收入', '其他', '退款'),
    }

    # 金额提取：找数字
    import re
    amounts = re.findall(r'(\d+(?:\.\d+)?)', nl_input)
    amount = float(amounts[0]) if amounts else 0.0

    # 分类推断
    parent, child = None, None
    ie_type = None

    for keyword, (t, p, c) in rules.items():
        if keyword in nl_input:
            ie_type, parent, child = t, p, c
            break

    # 未匹配时的兜底
    if ie_type is None:
        if amount > 0:
            ie_type = '支出'  # 默认支出
            parent, child = '其他', '调整支出'
        else:
            ie_type = '支出'
            parent, child = '其他', '调整支出'

    # 日期提取
    date_str = today
    if '昨天' in nl_input:
        from datetime import timedelta
        d = datetime.strptime(today, '%Y-%m-%d') - timedelta(days=1)
        date_str = d.strftime('%Y-%m-%d')
    # 支持 "N号" 格式
    day_match = re.search(r'(\d{1,2})号', nl_input)
    if day_match:
        day = int(day_match.group(1))
        date_str = f"{today[:8]}{day:02d}"

    # 备注提取
    note = ''
    if '，' in nl_input:
        note = nl_input.split('，', 1)[1].strip()
    elif ',' in nl_input:
        note = nl_input.split(',', 1)[1].strip()
    elif '备注' in nl_input:
        note = nl_input.split('备注', 1)[1].strip().lstrip('：:').strip()

    # 标签
    tags = []
    for tag_kw in ['旅行', '社交', '家庭', '报销', '装修', '宠物', 'AA']:
        if tag_kw in nl_input:
            tags.append(tag_kw)

    record = {
        'id': str(uuid.uuid4())[:8],
        'date': date_str,
        'type': ie_type,
        'parent_category': parent,
        'child_category': child,
        'amount': amount,
        'note': note or nl_input,
        'tags': json.dumps(tags, ensure_ascii=False),
        'source': 'chat',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return record

def echo(record, action='记录'):
    """模拟回显"""
    tags_list = json.loads(record['tags'])
    tags_str = f" [{', '.join(tags_list)}]" if tags_list else ''
    note_str = f" — {record['note']}" if record['note'] else ''
    return (f"✅ {action}：{record['date']} | {record['type']} | "
            f"{record['parent_category']} › {record['child_category']} | "
            f"¥{record['amount']:,.2f}{tags_str}{note_str}")

# ============================================================
# PART 3: 10 条 Dry-Run 示例
# ============================================================
print("=" * 60)
print("  v1 记账 Dry-Run")
print("=" * 60)

print("\n## SCHEMA\n")
print("```sql")
print(SCHEMA_SQL.strip())
print("```")

print("\n## 分类体系\n")
for ie, parents in CATEGORIES.items():
    print(f"**{ie}**")
    for parent, children in parents.items():
        print(f"  {parent}: {', '.join(children)}")

print("\n" + "=" * 60)
print("  10 条 Dry-Run 示例")
print("=" * 60)

examples = [
    # 1. 简单支出
    ("午饭 35", "2026-05-21"),
    # 2. 带备注
    ("加油 200，中石化", "2026-05-21"),
    # 3. 昨天记账
    ("昨天 晚饭 68，和同事聚餐", "2026-05-21"),
    # 4. 收入
    ("工资到账 12000", "2026-05-21"),
    # 5. 带标签
    ("机票 1280 日本游 旅行", "2026-05-20"),
    # 6. 多关键词
    ("打车 48，去机场", "2026-05-21"),
    # 7. 边界：AI 订阅
    ("ChatGPT 订阅 20美元", "2026-05-21"),
    # 8. 修改场景（先记一笔错的，然后纠正）
    ("红包 200", "2026-05-21"),
    # 9. 医疗
    ("买药 85，感冒", "2026-05-21"),
    # 10. 查询回显
    (None, None),  # 查询示例
]

for i, (nl, ref_date) in enumerate(examples, 1):
    if nl is None:
        print(f"\n--- 示例 {i}: 查询回显 ---")
        # 模拟查本月汇总
        print("输入: `本月汇总`")
        print("回显:")
        print("  📊 2026-05 汇总：")
        print("  收入 ¥12,000.00 | 支出 ¥1,931.00 | 净额 ¥10,069.00")
        print("  餐饮 ¥303.00 (3笔) | 交通 ¥248.00 (2笔) | 购物 ¥1,280.00 (1笔) | 医疗 ¥85.00 (1笔) | 订阅 ¥15.00 (1笔)")
        continue

    record = simulate_record(nl, ref_date)
    print(f"\n--- 示例 {i} ---")
    print(f"输入: `{nl}`")
    print(f"回显: {echo(record)}")
    print(f"内部: {json.dumps(record, ensure_ascii=False, indent=2)[:200]}...")

# ============================================================
# PART 4: 修正场景
# ============================================================
print("\n" + "=" * 60)
print("  修正 & 规则学习示例")
print("=" * 60)

# 场景：用户说"红包 200"，agent 默认归类为 其他-红包支出
# 但用户纠正说这是收到红包（收入）
print("""
**场景 1：用户纠正分类**
  输入: `红包 200`
  agent 回显: ✅ 已记录：2026-05-21 | 支出 | 其他 › 红包支出 | ¥200.00
  用户: `不对，这是收到的红包，算收入`
  agent 修改后回显: ✅ 已修改：2026-05-21 | 收入 | 其他 › 红包 | ¥200.00
  agent 记住: "红包" → 先判断上下文，有"收""抢""领" → 收入-其他-红包；
           无明确方向时回问

**场景 2：用户纠正子类**
  输入: `保险 600`
  agent 回显: ✅ 已记录：2026-05-21 | 支出 | 医疗 › 保险 | ¥600.00
  用户: `这是车险，不是医疗险`
  agent 修改后回显: ✅ 已修改：2026-05-21 | 支出 | 汽车 › 车险 | ¥600.00
  agent 记住: "保险" 出现在"车"上下文 → 汽车-车险；无上下文默认回问
""")

print("\n" + "=" * 60)
print("  Dry-Run 完成。以上均为模拟，未创建任何正式数据库。")
print("=" * 60)
