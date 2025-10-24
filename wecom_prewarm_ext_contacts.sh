#!/usr/bin/env bash
set -euo pipefail
set -a; . /www/wwwroot/wecom_ops/.env 2>/dev/null || true; set +a

SKEY="${WECOM_EXT_SECRET:-${WECOM_AGENT_SECRET:-}}"
[ -n "${WECOM_CORP_ID:-}" ] || { echo "missing WECOM_CORP_ID"; exit 1; }
[ -n "$SKEY" ] || { echo "missing WECOM_EXT_SECRET or WECOM_AGENT_SECRET"; exit 1; }

# get token
AT=$(curl -sS "https://qyapi.weixin.qq.com/cgi-bin/gettoken" \
      --get --data-urlencode "corpid=${WECOM_CORP_ID}" \
             --data-urlencode "corpsecret=${SKEY}" | jq -r '.access_token // empty')
[ -n "$AT" ] || { echo "gettoken failed"; exit 1; }

# mysql cli（注意 -p 贴紧）
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:?missing MYSQL_USER}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:?missing MYSQL_PASSWORD}"
MYSQL_DB="${MYSQL_DB:?missing MYSQL_DB}"
mysql_cli=(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N "$MYSQL_DB")

# 确保 ext_contact 存在（先建主键列）
"${mysql_cli[@]}" <<'SQL'
CREATE TABLE IF NOT EXISTS ext_contact (
  external_userid VARCHAR(64) PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL

# 拉服务人员
FL=$(curl -sS "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list?access_token=$AT")
[ "$(echo "$FL" | jq -r '.errcode')" = "0" ] || { echo "get_follow_user_list error: $FL"; exit 1; }
mapfile -t FUSERS < <(echo "$FL" | jq -r '.follow_user[]?')
echo "[info] follow_user count: ${#FUSERS[@]}"

batch=500   # 每批 500 个 external_userid，避免 SQL 过长/argv 过长

for u in "${FUSERS[@]}"; do
  L=$(curl -sS "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/list?access_token=$AT&userid=$u")
  [ "$(echo "$L" | jq -r '.errcode')" = "0" ] || { echo "list error($u): $L"; continue; }
  mapfile -t EUS < <(echo "$L" | jq -r '.external_userid[]?')
  total=${#EUS[@]}
  (( total )) || { echo "[warn] $u has 0 customers"; continue; }

  idx=0
  while [ $idx -lt $total ]; do
    end=$(( idx + batch ))
    [ $end -gt $total ] && end=$total

    # 通过 stdin 喂给 mysql，避免把超长 SQL 放入 -e 参数
    {
      printf "INSERT IGNORE INTO ext_contact (external_userid) VALUES "
      for ((i=idx;i<end;i++)); do
        id="${EUS[i]//\'/\\\'}"   # 以防万一转义单引号
        if [ $i -eq $((end-1)) ]; then
          printf "('%s');\n" "$id"
        else
          printf "('%s')," "$id"
        fi
      done
    } | "${mysql_cli[@]}"

    idx=$end
  done

  echo "[ok] $u -> inserted $total"
  sleep 0.2   # 轻微限速，防止接口被判频
done

# 汇总统计
"${mysql_cli[@]}" -e "SELECT COUNT(*) AS ext_contact_rows FROM ext_contact;"

