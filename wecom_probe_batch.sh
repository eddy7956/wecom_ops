#!/usr/bin/env bash
set -euo pipefail

: "${MYSQL_HOST:=127.0.0.1}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_USER:=wecom_ops}"
: "${MYSQL_PASSWORD:=}"
: "${MYSQL_DB:=wecom_ops}"

get_token() {
  local corp="${WECOM_CORP_ID:-${WX_CORP_ID:-}}"
  local sec="${WECOM_CONTACTS_SECRET:-${WECOM_CONTACT_SECRET:-${WX_CONTACT_SECRET:-${WECOM_EXT_SECRET:-}}}}"
  curl -sS "https://qyapi.weixin.qq.com/cgi-bin/gettoken" \
    --get --data-urlencode "corpid=$corp" --data-urlencode "corpsecret=$sec" \
    | jq -r '.access_token'
}

# 取 2~3 个跟进人 userid 用来跑任务
get_follow_users() {
  local token="$1"
  curl -sS "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list?access_token=$token" \
  | jq -r '.follow_user[]' | head -n 3
}

submit_batch() {
  local token="$1"; shift
  # 优先尝试 userid_list 形态；失败再回退单个 userid 试探
  local payload
  payload="$(jq -nc --argjson arr "$(printf '%s\n' "$@" | jq -R . | jq -s .)" '{userid_list:$arr}')"
  local resp; resp="$(curl -sS -X POST \
    "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/batch/get_by_user?access_token=$token" \
    -H 'Content-Type: application/json' -d "$payload")"
  local err; err="$(jq -r '.errcode' <<<"$resp")"
  if [[ "$err" != "0" ]]; then
    # 回退单 user 形态
    payload="$(jq -nc --arg u "$1" '{userid:$u}')"  # 用第一个 userid 试探
    resp="$(curl -sS -X POST \
      "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/batch/get_by_user?access_token=$token" \
      -H 'Content-Type: application/json' -d "$payload")"
    err="$(jq -r '.errcode' <<<"$resp")"
    [[ "$err" == "0" ]] || { echo "提交失败：$resp" >&2; return 1; }
  fi
  jq -r '.jobid' <<<"$resp"
}

poll_result() {
  local token="$1" jobid="$2"
  # 轮询两条可能的结果路径，哪个先返回 ok 就用哪个
  local tries=60
  while ((tries-- > 0)); do
    # 尝试 externalcontact/batch/get_result
    for path in "externalcontact/batch/get_result" "batch/getresult"; do
      local url="https://qyapi.weixin.qq.com/cgi-bin/$path?access_token=$token&jobid=$jobid"
      local r; r="$(curl -sS "$url")"
      local err; err="$(jq -r '.errcode // .errCode // 99999' <<<"$r")"
      if [[ "$err" == "0" ]]; then
        echo "$r"
        return 0
      fi
    done
    sleep 2
  done
  echo "轮询超时 or 无法识别结果接口" >&2
  return 1
}

main() {
  local token; token="$(get_token)"; [[ -n "$token" && "$token" != "null" ]] || { echo "取 token 失败"; exit 1; }
  echo "token OK"

  mapfile -t USERS < <(get_follow_users "$token")
  echo "sample users: ${USERS[*]}"

  local jobid; jobid="$(submit_batch "$token" "${USERS[@]}")"
  echo "jobid=$jobid"

  local result; result="$(poll_result "$token" "$jobid")"
  echo "$result" | jq '. | {errcode, count:(.total or .result | length?), sample:(.external_contact_list[0] // .result[0] // {}) }'
}

main "$@"
