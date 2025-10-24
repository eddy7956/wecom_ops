# -*- coding: utf-8 -*-
import os, pymysql

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

def get_union_mapping(employee_id=None, external_userid=None):
    with _db().cursor() as c:
        if employee_id:
            c.execute("""SELECT ec.external_userid, ec.name AS ext_name
                         FROM ext_follow_user ef JOIN ext_contact ec
                         ON ec.external_userid=ef.external_userid
                         WHERE ef.userid=%s""", (employee_id,))
            return {"employee_id": employee_id, "contacts": c.fetchall()}
        if external_userid:
            c.execute("""SELECT ef.userid AS owner_userid, oe.name AS owner_name
                         FROM ext_follow_user ef
                         LEFT JOIN org_employee oe ON oe.userid=ef.userid
                         WHERE ef.external_userid=%s""", (external_userid,))
            return {"external_userid": external_userid, "owners": c.fetchall()}
    return {}

def list_bi_views(view="vw_contact_identity", page=1, size=50):
    off = (page-1)*size
    with _db().cursor() as c:
        c.execute(f"SELECT SQL_CALC_FOUND_ROWS * FROM {view} LIMIT %s,%s", (off,size))
        rows = c.fetchall()
        c.execute("SELECT FOUND_ROWS() AS n"); total = c.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
