# -*- coding: utf-8 -*-
import os, json, pymysql, time
from app.wecom.client import wecom_get_json, wecom_post_json

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

def _employees():
    with _db().cursor() as c:
        c.execute("SELECT userid FROM org_employee WHERE enable=1 OR enable IS NULL")
        return [r["userid"] for r in c.fetchall()]

def sync_contacts(full=False, throttle_ms=200):
    up_contact = up_follow = up_tagrel = 0
    with _db().cursor() as c:
        for uid in _employees():
            lst = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/list","ext",
                                 params={"userid": uid})
            for exid in lst.get("external_userid", []):
                dt = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get","ext",
                                    params={"external_userid": exid})
                info = dt.get("external_contact", {})
                follow = dt.get("follow_user", [])
                c.execute("""REPLACE INTO ext_contact
                            (external_userid,name,corp_full_name,position,gender,unionid,ext)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                          (info.get("external_userid") or exid, info.get("name"), info.get("corp_full_name"),
                           info.get("position"), info.get("gender"), info.get("unionid"),
                           json.dumps(info, ensure_ascii=False)))
                up_contact += 1
                for f in follow:
                    c.execute("""REPLACE INTO ext_follow_user
                                (external_userid, userid, remark, state, add_way, create_time)
                                VALUES (%s,%s,%s,%s,%s,FROM_UNIXTIME(%s))""",
                              (exid, f.get("userid"), f.get("remark"), f.get("state"),
                               f.get("add_way"), f.get("createtime") or 0))
                    # 客户标签关系（若返回）
                    for tid in f.get("tags") or []:
                        c.execute("""REPLACE INTO ext_contact_tag (external_userid, tag_id)
                                     VALUES (%s,%s)""", (exid, tid))
                        up_tagrel += 1
                    up_follow += 1
            time.sleep(throttle_ms/1000.0)
    return {"contacts_upserted": up_contact, "follow_upserted": up_follow, "tag_relations": up_tagrel}

def sync_tags():
    # 官方为 POST
    data = wecom_post_json("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_corp_tag_list",
                           "ext", body={})
    up = 0
    with _db().cursor() as c:
        for grp in data.get("tag_group", []):
            for t in grp.get("tag", []):
                c.execute("""REPLACE INTO ext_tag (tag_id,group_id,group_name,name,order_no)
                            VALUES (%s,%s,%s,%s,%s)""",
                          (t["id"], grp.get("group_id"), grp.get("group_name"), t.get("name"), t.get("order")))
                up += 1
    return {"tags_upserted": up}

def list_contacts(tag=None, owner=None, page=1, size=50):
    off = (page-1)*size
    with _db().cursor() as c:
        if tag and owner:
            sql = """SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                     JOIN ext_follow_user ef ON ef.external_userid=ec.external_userid
                     JOIN ext_contact_tag et ON et.external_userid=ec.external_userid
                     WHERE ef.userid=%s AND et.tag_id=%s
                     ORDER BY ec.external_userid LIMIT %s,%s"""
            c.execute(sql, (owner, tag, off, size))
        elif tag:
            sql = """SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                     JOIN ext_contact_tag et ON et.external_userid=ec.external_userid
                     WHERE et.tag_id=%s ORDER BY ec.external_userid LIMIT %s,%s"""
            c.execute(sql, (tag, off, size))
        elif owner:
            sql = """SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                     JOIN ext_follow_user ef ON ef.external_userid=ec.external_userid
                     WHERE ef.userid=%s ORDER BY ec.external_userid LIMIT %s,%s"""
            c.execute(sql, (owner, off, size))
        else:
            c.execute("""SELECT SQL_CALC_FOUND_ROWS * FROM ext_contact
                         ORDER BY external_userid LIMIT %s,%s""", (off,size))
        rows = c.fetchall()
        c.execute("SELECT FOUND_ROWS() AS n"); total = c.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
