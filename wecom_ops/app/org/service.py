# -*- coding: utf-8 -*-
import os, json, pymysql
from app.wecom.client import wecom_get_json
from app.common.cache import get_with_singleflight

def _db():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        user=os.getenv("MYSQL_USER","root"),
        password=os.getenv("MYSQL_PASSWORD",""),
        database=os.getenv("MYSQL_DB"),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor)

def sync_departments(full=False):
    data = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/department/list","contacts")
    upserted = 0
    with _db().cursor() as c:
        for d in data.get("department", []):
            sql = """REPLACE INTO org_department
                     (id,name,parent_id,order_no,path,level,status,ext)
                     VALUES (%s,%s,%s,%s,%s,%s,1,%s)"""
            c.execute(sql, (d["id"], d.get("name"), d.get("parentid"), d.get("order"),
                            None, None, json.dumps(d, ensure_ascii=False)))
            upserted += 1
    return {"upserted": upserted}

def sync_employees(full=False, root_dept_id=1, fetch_child=1):
    data = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/user/list",
                          "contacts", params={"department_id": root_dept_id, "fetch_child": fetch_child})
    up = 0
    with _db().cursor() as c:
        for u in data.get("userlist", []):
            c.execute("""REPLACE INTO org_employee
                        (userid,name,mobile,email,position,gender,enable,qr_code,departments,ext)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                      (u["userid"], u.get("name"), u.get("mobile"), u.get("email"),
                       u.get("position"), u.get("gender"), u.get("enable"),
                       u.get("qr_code"), json.dumps(u.get("department", [])),
                       json.dumps(u, ensure_ascii=False)))
            # 映射表（先删后插避免残留）
            c.execute("DELETE FROM org_employee_dept WHERE userid=%s", (u["userid"],))
            for dpt in u.get("department", []):
                c.execute("INSERT IGNORE INTO org_employee_dept (userid, dept_id) VALUES (%s,%s)", (u["userid"], dpt))
            up += 1
    return {"upserted": up}

def list_departments(page=1, size=50):
    off = (page-1)*size
    with _db().cursor() as c:
        c.execute("SELECT * FROM org_department ORDER BY parent_id, order_no LIMIT %s,%s", (off,size))
        rows = c.fetchall()
        c.execute("SELECT COUNT(*) AS n FROM org_department"); total = c.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}

def list_employees(dept_id=None, page=1, size=50):
    off = (page-1)*size
    with _db().cursor() as c:
        if dept_id:
            c.execute("""
                SELECT e.* FROM org_employee e
                JOIN org_employee_dept m ON m.userid=e.userid
                WHERE m.dept_id=%s
                ORDER BY e.userid LIMIT %s,%s
            """, (dept_id, off, size))
            rows = c.fetchall()
            c.execute("SELECT COUNT(*) AS n FROM org_employee_dept WHERE dept_id=%s", (dept_id,))
            total = c.fetchone()["n"]
        else:
            c.execute("SELECT * FROM org_employee ORDER BY userid LIMIT %s,%s", (off, size))
            rows = c.fetchall()
            c.execute("SELECT COUNT(*) AS n FROM org_employee"); total = c.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
