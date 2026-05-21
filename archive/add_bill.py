#!/usr/bin/env python3
"""向账本追加一条记录"""

import csv
import sys
import os
from datetime import datetime

# 新账本字段: Date, Type, ParentCategory, SubCategory, Amount, Account, Note, Status

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '账本.csv')

def add_bill(date_str, type_, parent, sub, amount, account='', note='', status='manual'):
    """追加一条记录到账本"""
    # Ensure账本 exists
    if not os.path.exists(LEDGER):
        with open(LEDGER, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Type', 'ParentCategory', 'SubCategory', 'Amount', 'Account', 'Note', 'Status'])

    with open(LEDGER, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date_str, type_, parent, sub, amount, account, note, status])

    print(f"✅ 已记录: {date_str} | {type_} | {parent}:{sub} | ¥{amount:,.2f}" + (f" | {account}" if account else "") + (f" | {note}" if note else ""))

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("Usage: add_bill.py <date> <type> <parent> <sub> <amount> [account] [note] [status]")
        sys.exit(1)
    date_str = sys.argv[1]
    type_ = sys.argv[2]
    parent = sys.argv[3]
    sub = sys.argv[4]
    amount = float(sys.argv[5])
    account = sys.argv[6] if len(sys.argv) > 6 else ''
    note = sys.argv[7] if len(sys.argv) > 7 else ''
    status = sys.argv[8] if len(sys.argv) > 8 else 'manual'
    add_bill(date_str, type_, parent, sub, amount, account, note, status)
