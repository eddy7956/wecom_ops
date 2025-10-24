#!/usr/bin/env bash
set -euo pipefail

# 载入 .env（含 WECOM_ 与 MYSQL_ 变量）
set -a; . /www/wwwroot/wecom_ops/.env 2>/dev/null || true; set +a

# 1) 取 token（优先 EXT_SECRET，其次 AGENT_SECRET）
SKEY="${WECOM_EXT_SECRET:-${WECOM_AGENT_SECRET:-}}"
[ -n "${WECOM_CORP_ID:-}" ] || { echo "missing WECOM_CORP_ID"; exit 1; }
[ -n "$SKEY" ] || { echo "missing WECOM_EXT_SECRET or WECOM_AGENT_SECRET"; exit 1; }

AT=$(curl -sS "https://qyapi.weixin.qq.com/cgi-bin/gettoken" \
      --get --data-urlencode "corpid=${WECOM_CORP_ID}" \
             --data-urlencode "corpsecret=${SKEY}" | jq -r '.access_token // empty')
[ -n "$AT" ] || { echo "gettoken failed"; exit 1; }

# 2) 拉服务人员列表
RESP=$(curl -sS "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list?access_token=$AT")
errcode=$(echo "$RESP" | jq -r '.errcode // 0')
[ "$errcode" = "0" ] || { echo "API error: $RESP"; exit 1; }

# 提取 userid 列表（可能为空）
mapfile -t USERS < <(echo "$RESP" | jq -r '.follow_user[]?')

# 3) DB 连接
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:?missing MYSQL_USER}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:?missing MYSQL_PASSWORD}"
MYSQL_DB="${MYSQL_DB:?missing MYSQL_DB}"
mysql_cli=(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N "$MYSQL_DB")

# 4) 表结构（幂等）
"${mysql_cli[@]}" <<'SQL'
CREATE TABLE IF NOT EXISTS ext_follow_user (
  userid      VARCHAR(64) PRIMARY KEY,
  name        VARCHAR(128) NULL,
  status      TINYINT NULL,
  departments JSON NULL,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
              ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL

# 5) upsert/清理
if [ "${#USERS[@]}" -gt 0 ]; then
  # upsert
  VALUES=$(printf "('%s')," "${USERS[@]}"); VALUES="${VALUES%,}"
  "${mysql_cli[@]}" -e "INSERT INTO ext_follow_user (userid) VALUES ${VALUES} ON DUPLICATE KEY UPDATE userid=VALUES(userid);"
  # 删除已不在服务人员列表的
  INLIST=$(printf "'%s'," "${USERS[@]}"); INLIST="${INLIST%,}"
  "${mysql_cli[@]}" -e "DELETE FROM ext_follow_user WHERE userid NOT IN (${INLIST});"
fi

# 6) 用 org_employee 回填（如果有 org_employee 就填，没有也不报错）
"${mysql_cli[@]}" <<'SQL' || true
UPDATE ext_follow_user f
LEFT JOIN org_employee e ON e.userid=f.userid
SET f.name=e.name, f.status=e.status, f.departments=e.departments;
SQL

# 7) 输出统计
"${mysql_cli[@]}" -e "SELECT COUNT(*) AS follow_users FROM ext_follow_user;"

