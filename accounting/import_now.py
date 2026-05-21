#!/usr/bin/env python3
"""正式导入：从 preview 库 → ledger.sqlite"""

import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import init_db, DB_PATH

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW_DB = os.path.join(HERE, 'ledger_import_preview.sqlite')

def main():
    # 1. Run preview to regenerate with updated mappings
    print("重新生成 preview...")
    import import_preview
    import_preview.main()

    # 2. Init formal ledger
    print("\n初始化正式账本...")
    init_db()

    # 3. Copy from preview to ledger
    src = sqlite3.connect(PREVIEW_DB)
    dst = sqlite3.connect(DB_PATH)

    count = 0
    for row in src.execute("SELECT id, date, type, parent_category, child_category, amount, note, tags, source, created_at, updated_at FROM transactions"):
        dst.execute("""
            INSERT INTO transactions (id, date, type, parent_category, child_category, amount, note, tags, source, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, row)
        count += 1

    dst.commit()
    src.close()
    dst.close()

    # 4. Verify
    vrf = sqlite3.connect(DB_PATH)
    total = vrf.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    income = vrf.execute("SELECT SUM(amount) FROM transactions WHERE type='收入'").fetchone()[0]
    expense = vrf.execute("SELECT SUM(amount) FROM transactions WHERE type='支出'").fetchone()[0]
    vrf.close()

    print(f"\n✅ 正式导入完成！")
    print(f"   总记录: {total} 条")
    print(f"   收入: ¥{income:,.2f}")
    print(f"   支出: ¥{expense:,.2f}")
    print(f"   净额: ¥{income - expense:,.2f}")
    print(f"   账本: {DB_PATH}")

if __name__ == '__main__':
    main()
