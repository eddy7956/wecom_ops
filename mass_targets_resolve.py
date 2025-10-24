#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mass_targets_resolve.py
- 输入：手机号清单（--text / --file CSV|XLSX），表头“手机号”也支持
- 处理：清洗(+86/86/空白/符号)、去重、长度/纯数字校验
- 映射：third_party_user_import.user_name -> union_id -> ext_contact.unionid
- 输出：JSON 汇总（total/unique/valid/invalid/duplicate_count）与样例，以及可触达 external_userid 列表
"""
import os, sys, re, json, argparse, csv
from typing import List, Tuple, Dict
import mysql.connector

try:
    import openpyxl
except Exception:
    openpyxl = None

def norm_mobile(s: str) -> str:
    if s is None: return ""
    s = re.sub(r'\s+', '', str(s))
    s = s.replace('-', '').replace('—','').replace('–','').replace('_','').replace('＋','+').replace('＋','+')
    # 去 +86 / 0086 / 86 前缀（仅当去掉后剩余 >= 11 位）
    s = s.lstrip('+')
    if s.startswith('0086'): s = s[4:]
    elif s.startswith('86') and len(s) > 11: s = s[2:]
    # 只保留数字
    s = re.sub(r'\D', '', s)
    # 只接受 11 位中国大陆手机号；其他长度判为无效
    return s if len(s) == 11 else ""

def load_from_text(txt: str) -> List[str]:
    # 支持逗号、空格、换行、分号
    parts = re.split(r'[,\s;]+', txt.strip())
    return [p for p in parts if p]

def load_from_csv(path: str) -> List[str]:
    import io, chardet
    mobiles = []

    # 1) 自动识别编码并读入文本
    with open(path, 'rb') as fb:
        raw = fb.read()
    enc = (chardet.detect(raw) or {}).get('encoding') or 'utf-8'
    text = raw.decode(enc, errors='ignore')

    # 2) 优先用 csv.Sniffer 探测分隔符；失败就按“每行一个值”回退
    f = io.StringIO(text)
    rows = None
    try:
        snif = csv.Sniffer()
        dialect = snif.sniff(text[:2048])
        f.seek(0)
        reader = csv.reader(f, dialect)
        rows = list(reader)
    except Exception:
        # 回退：逐行当作单列表格
        rows = [[line.strip()] for line in text.splitlines() if line.strip()]

    # 3) 识别并跳过表头（包含“手机号”关键字）
    start = 1 if rows and rows[0] and any('手机号' in (c or '') for c in rows[0]) else 0

    for row in rows[start:]:
        for cell in row:
            if cell:
                mobiles.append(str(cell))
    return mobiles

def load_from_xlsx(path: str) -> List[str]:
    if not openpyxl:
        raise SystemExit("缺少 openpyxl，请先安装：pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    mobiles = []
    is_header = True
    for row in ws.iter_rows(values_only=True):
        cells = [str(c) if c is not None else "" for c in row]
        if is_header and any('手机号' in c for c in cells):
            is_header = False
            continue
        is_header = False
        for c in cells:
            if c: mobiles.append(c)
    return mobiles

def dbc():
    cfg = dict(
        host=os.getenv('MYSQL_HOST','127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT','3306')),
        user=os.getenv('MYSQL_USER','root'),
        password=os.getenv('MYSQL_PASSWORD',''),
        database=os.getenv('MYSQL_DB','wecom_ops'),
        charset='utf8mb4'
    )
    return mysql.connector.connect(**cfg)

def resolve(mobiles: List[str]) -> Dict:
    # 清洗 + 去重
    raw_cnt = len(mobiles)
    cleaned = [norm_mobile(m) for m in mobiles]
    cleaned = [m for m in cleaned if m]
    unique = list(dict.fromkeys(cleaned))  # 去重且保持顺序
    dup_count = len(cleaned) - len(unique)

    if not unique:
        return {"ok": True, "total": raw_cnt, "unique": 0, "duplicate_count": dup_count,
                "valid": 0, "invalid": 0, "valid_samples": [], "invalid_samples": [], "targets": []}

    # 批量查询（分段防止 SQL 太长）
    targets = []
    invalids = set()
    con = dbc()
    cur = con.cursor(dictionary=True)
    BATCH = 1000
    for i in range(0, len(unique), BATCH):
        seg = unique[i:i+BATCH]
        ph_in = ",".join(["%s"]*len(seg))
        sql = f"""
        SELECT 
          tp.user_name AS mobile,
          tp.union_id,
          ec.external_userid,
          ec.name,
          ec.unionid AS ec_unionid
        FROM third_party_user_import tp
        LEFT JOIN ext_contact ec
          ON ec.unionid = tp.union_id
        WHERE tp.user_name IN ({ph_in})
        """
        cur.execute(sql, seg)
        hit_map = {r["mobile"]: r for r in cur.fetchall()}

        for m in seg:
            r = hit_map.get(m)
            if r and r.get("external_userid"):
                targets.append({
                    "mobile": m,
                    "union_id": r.get("union_id"),
                    "external_userid": r.get("external_userid"),
                    "name": r.get("name"),
                })
            else:
                invalids.add(m)

    cur.close(); con.close()
    valid = len(targets); invalid = len(invalids)
    return {
        "ok": True,
        "total": raw_cnt,
        "unique": len(unique),
        "duplicate_count": dup_count,
        "valid": valid,
        "invalid": invalid,
        "valid_samples": targets[:5],
        "invalid_samples": list(sorted(invalids))[:5],
        "targets": targets  # 后续可选择写快照或仅返回
    }

def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="直接输入手机号列表（逗号/空格/换行/分号分隔）")
    src.add_argument("--file", help="CSV 或 XLSX 文件路径；CSV 首行可含“手机号”表头")
    args = ap.parse_args()

    if args.text:
        mobiles = load_from_text(args.text)
    else:
        path = args.file
        if not os.path.isfile(path):
            raise SystemExit(f"文件不存在：{path}")
        ext = os.path.splitext(path)[1].lower()
        if ext in (".csv", ".txt"):
            mobiles = load_from_csv(path)
        elif ext in (".xlsx", ".xlsm"):
            mobiles = load_from_xlsx(path)
        else:
            raise SystemExit("仅支持 CSV / XLSX")
    res = resolve(mobiles)
    print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    # 允许脚本直接读取 wecom_ops/.env 的 MySQL 连接
    env_path = "/www/wwwroot/wecom_ops/.env"
    if os.path.isfile(env_path):
        for line in open(env_path, 'r', encoding='utf-8'):
            if "=" in line and not line.strip().startswith("#"):
                k,v = line.strip().split("=",1)
                os.environ.setdefault(k, v)
    main()
