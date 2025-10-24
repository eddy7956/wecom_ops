# WeCom Unified Ops Platform — README (M1)

> **目标（M1）**：完成 `core（配置/日志/TraceID/DB/Redis）`、`common（semaphore/ratelimit/idempotency/cache）` 基础工具（含单测），以及 `api/v1` 框架与统一错误包装 + `健康检查`。  
> **环境**：Debian + 宝塔面板（Nginx）+ 单机后端（Flask/Gunicorn）

---

## 目录
1. [项目概览与记忆点](#项目概览与记忆点)
2. [快速上手（TL;DR）](#快速上手tldr)
3. [依赖与目录结构](#依赖与目录结构)
4. [环境变量（.env 示例）](#环境变量env-示例)
5. [核心代码模块说明](#核心代码模块说明)
6. [本地运行与生产部署](#本地运行与生产部署)
7. [宝塔 Nginx 配置（反代与全局 map）](#宝塔-nginx-配置反代与全局-map)
8. [健康检查与验证用例](#健康检查与验证用例)
9. [单元测试与路径问题修复](#单元测试与路径问题修复)
10. [JSON 日志与可观测](#json-日志与可观测)
11. [常见故障排查（Troubleshooting）](#常见故障排查troubleshooting)
12. [Systemd 常驻（可选）](#systemd-常驻可选)
13. [M1 验收清单](#m1-验收清单)
14. [预埋 M2（供后续使用）](#预埋-m2供后续使用)

---

## 项目概览与记忆点

- **域名**：`wework.yfsports.com.cn`
- **后端监听**：`127.0.0.1:5001`（Gunicorn）
- **宝塔/Nginx**：反代 `/api/` → `http://127.0.0.1:5001`
- **健康检查**：`GET /api/v1/health`（返回 JSON，含 `trace_id`；响应头有 `X-Request-Id`）
- **调试标记（临时）**：`X-Site: wework-yfsports`（用于确认命中正确站点，验收通过后可删除）
- **Python**：3.11.x（项目使用虚拟环境 `.venv`）
- **单测**：`pytest -q`（当前通过 `21 passed`）
- **重要全局 map（Nginx http{}）**：`map $http_x_request_id $xrid { default $request_id; }`

> **牢记**：所有 Nginx、站点与反代均在 **宝塔面板**内配置，不走系统文件直改。

---

## 快速上手（TL;DR）

```bash
# 1) 初始化（项目根 /www/wwwroot/wecom_ops）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) 写 .env（见下文示例）

# 3) 启动后端（生产推荐）
./.venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 app.app:app --timeout 60

# 4) 宝塔：
#    - Nginx 全局 http{} 加：map $http_x_request_id $xrid { default $request_id; }
#    - 站点 server{}（域名 wework.yfsports.com.cn）加 /api/ 反代（见下文）

# 5) 验证（本机，不依赖公网）
curl -i -H 'Host: wework.yfsports.com.cn' http://127.0.0.1/api/v1/health
curl -i -H 'Host: wework.yfsports.com.cn' -H 'X-Request-Id: via-nginx-001' http://127.0.0.1/api/v1/health

# 6) 单测
pytest -q
```

---

## 依赖与目录结构

**依赖（requirements.txt）**：
```
flask==3.0.3
pydantic==2.7.4
python-dotenv==1.0.1
redis==5.0.7
pymysql==1.1.1
mysqlclient==2.2.4
rq==1.15.1
uvicorn==0.30.6
gunicorn==22.0.0
structlog==24.1.0
fakeredis==2.23.2
pytest==8.3.3
```

**目录结构**：
```
/www/wwwroot/wecom_ops
├── app
│   ├── app.py
│   ├── core/         # config, logging(JSON), tracing, db, redis
│   ├── common/       # retry, idempotency, ratelimit, semaphore, cache
│   └── api
│       └── v1/       # blueprint, errors, routes(/health)
├── tests/            # pytest 用例（21+）
├── logs/
├── .venv/
└── requirements.txt
```

---

## 环境变量（.env 示例）

```dotenv
# —— API 与日志 ——
API_VERSION_PREFIX=v1
LOG_WITH_TRACE_ID=1

# —— 并发与缓存（默认值可后续调）——
GLOBAL_CONCURRENCY=20
DISPATCH_BATCH_SIZE=300
DISPATCH_QPS_LIMIT=600
RETRY_MAX=5
RETRY_BACKOFF_BASE=2.0
CACHE_SOFT_TTL_SEC=300
CACHE_HARD_TTL_SEC=900
CACHE_JITTER_MIN=0.9
CACHE_JITTER_MAX=1.2

# —— MySQL ——
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=wecom
MYSQL_PASSWORD=REPLACE_WITH_REAL_PASSWORD
MYSQL_DB=wecom_ops
MYSQL_CHARSET=utf8mb4

# —— Redis ——
REDIS_URL=redis://:REPLACE_WITH_REAL_PASSWORD@127.0.0.1:6379/0
```

---

## 核心代码模块说明

- **core/config.py**：读取 `.env`，集中配置（版本前缀/并发/缓存/DB/Redis）。  
- **core/logging.py**：JSON 日志格式器 + 根 logger 初始化（输出 `ts, level, msg, trace_id ...`）。  
- **core/tracing.py**：从请求头取 `X-Request-Id`/`X-Trace-Id`，若无则生成 UUID 并贯穿到 g 上下文。  
- **core/db.py**：MySQL 连接助手（pymysql）。  
- **core/redis.py**：Redis 连接助手（from_url，decode_responses=True）。  
- **common/**：
  - `retry.expo_backoff()`：指数退避（单测覆盖 20+ 条用例）。
  - `idempotency.try_mark_once()`：幂等 Key（SET NX EX）。
  - `ratelimit.take_token()`：简化令牌桶（HSET 存状态）。
  - `semaphore.acquire_sem()/release_sem()`：简化信号量（M2 计划升级 Lua + owners）。
  - `cache.get_with_singleflight()`：软/硬 TTL，空值占位；M2 接互斥与异步刷新。  
- **api/v1/**：
  - `errors.py`：统一错误包装（ApiError + 404/Exception handler）。
  - `routes.py`：`GET /health` 返回 `{ok, trace_id, version}`。
- **app/app.py**：Flask 应用工厂，before/after 中间件注入/回写 `X-Request-Id`，蓝图注册。

---

## 本地运行与生产部署

**开发运行**：
```bash
source .venv/bin/activate
export FLASK_APP=app.app:app
python -m flask run --host=0.0.0.0 --port=5001
```

**生产（Gunicorn）**：务必使用 **venv** 内的可执行文件
```bash
cd /www/wwwroot/wecom_ops
./.venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 app.app:app --timeout 60 --access-logfile - --error-logfile -
```

> 若端口被占用：`lsof -iTCP:5001 -sTCP:LISTEN -Pn` → `kill -TERM <PID>` / `kill -9 <PID>` 或 `fuser -k 5001/tcp`。

---

## 宝塔 Nginx 配置（反代与全局 map）

**全局 http{}（一次性）**：宝塔 → Nginx → 设置 → 配置修改（nginx.conf）
```nginx
map $http_x_request_id $xrid { default $request_id; }
log_format wecom '$remote_addr "$request" $status reqid=$http_x_request_id upstream=$upstream_addr $upstream_status';
```

**站点 server{}（wework.yfsports.com.cn）**：宝塔 → 网站 → 配置文件
```nginx
server
{
    listen 80;
    server_name wework.yfsports.com.cn;
    root /www/wwwroot/wecom_ops_site;
    index index.php index.html index.htm default.php default.htm default.html;

    # 证书申请校验（保留）
    include /www/server/panel/vhost/nginx/well-known/wework.yfsports.com.cn.conf;
    include /www/server/panel/vhost/nginx/extension/wework.yfsports.com.cn/*.conf;

    # === WeCom Ops API 反代 ===
    location /api/ {
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Request-Id      $xrid;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_send_timeout    60s;
        proxy_read_timeout    60s;
        proxy_pass http://127.0.0.1:5001;
    }

    access_log  /www/wwwlogs/wecom_ops.access.log  wecom;
    error_log   /www/wwwlogs/wecom_ops.error.log;

    location / { try_files $uri $uri/ =404; }
}
```

**HTTPS（两种方式）**：
- **自动部署**（修复宝塔标记即可）：站点配置内保留**原样标记**：
  ```nginx
  #SSL-START
  #error_page 404/404.html;
  #SSL-END
  ```
  然后在宝塔“SSL”页点击“**自动部署证书**”。  
- **手动部署**（即刻可用，证书路径以宝塔默认为例）：
  ```nginx
  server { listen 80; server_name wework.yfsports.com.cn; return 301 https://$host$request_uri; }
  server {
      listen 443 ssl http2;
      server_name wework.yfsports.com.cn;
      root /www/wwwroot/wecom_ops_site;
      index index.php index.html index.htm default.php default.htm default.html;

      ssl_certificate     /www/server/panel/vhost/cert/wework.yfsports.com.cn/fullchain.pem;
      ssl_certificate_key /www/server/panel/vhost/cert/wework.yfsports.com.cn/privkey.pem;
      ssl_protocols       TLSv1.2 TLSv1.3;
      ssl_ciphers         HIGH:!aNULL:!MD5;
      add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

      location /api/ {
          proxy_http_version 1.1;
          proxy_set_header Host $host;
          proxy_set_header X-Request-Id $xrid;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_pass http://127.0.0.1:5001;
      }
      access_log  /www/wwwlogs/wecom_ops.access.log  wecom;
      error_log   /www/wwwlogs/wecom_ops.error.log;
      location / { try_files $uri $uri/ =404; }
  }
  ```

> **外网访问前提**：若机器在内网 `192.168.0.13`，需路由/NAT 将 `59.49.99.226:80/443` 转发至本机 `:80/443`。本机验证用 `Host` 头打 `127.0.0.1` 不依赖 DNS/NAT。

---

## 健康检查与验证用例

**Gunicorn 直连**：
```bash
curl -i http://127.0.0.1:5001/api/v1/health
curl -i -H 'X-Request-Id: demo-abc-123' http://127.0.0.1:5001/api/v1/health
```

**Nginx 侧（站点命中验证）**：
```bash
curl -i -H 'Host: wework.yfsports.com.cn' http://127.0.0.1/api/v1/health
curl -i -H 'Host: wework.yfsports.com.cn' -H 'X-Request-Id: via-nginx-001' http://127.0.0.1/api/v1/health
```

期望：
- `HTTP/1.1 200 OK`
- Body：`{"ok": true, "trace_id": "...", "version": "v1"}`
- 响应头：`X-Request-Id: ...`（第二条应为 `via-nginx-001`）

---

## 单元测试与路径问题修复

**测试入口**：`tests/test_health_and_utils.py`（含 20+ 参数化用例）

**固定 PythonPath（避免 `ModuleNotFoundError: app`）**：
- `pytest.ini`
  ```ini
  [pytest]
  pythonpath = .
  addopts = -q
  ```
- `tests/conftest.py`
  ```python
  import os, sys, pathlib
  ROOT = pathlib.Path(__file__).resolve().parent.parent
  if str(ROOT) not in sys.path:
      sys.path.insert(0, str(ROOT))
  ```

**执行**：
```bash
cd /www/wwwroot/wecom_ops
source .venv/bin/activate
pytest
```

---

## JSON 日志与可观测

**快速验证 JSON 输出**：
```bash
python - <<'PY'
from app.core.logging import init_json_logger
import logging
init_json_logger()
logging.getLogger().info("hello-json", extra={"trace_id":"demo-123","route":"/api/v1/health","latency_ms":3})
PY
```
期望输出（示例）：
```json
{"ts":"2025-09-23T10:xx:xx","level":"INFO","msg":"hello-json","trace_id":"demo-123","route":"/api/v1/health","latency_ms":3}
```

**Nginx 访问日志**：`/www/wwwlogs/wecom_ops.access.log`（使用 `wecom` 格式，包含 `reqid` 与 upstream）

---

## 常见故障排查（Troubleshooting）

| 现象/报错 | 可能原因 | 解决方案 |
|---|---|---|
| `Error: Could not import 'app.app'` | 包结构缺 `__init__.py`、当前目录不对 | 确保 `app/__init__.py`、在项目根执行；或按上文 `pytest.ini` 固定 pythonpath |
| `IndentationError` | 将 Python 代码直接粘到 Bash 执行，缩进丢失 | 用 **Here-Doc** 写入 `.py` 文件（`<<'PY'`），不要在 Bash 里直接跑 Python 代码片段 |
| `ModuleNotFoundError: app` | PythonPath 未包含项目根 | 新增 `pytest.ini` / `tests/conftest.py`，或 `sys.path.insert(0, os.getcwd())` |
| `Connection in use: 127.0.0.1:5001` | 端口被旧进程占用 | `lsof -iTCP:5001 -sTCP:LISTEN -Pn` → `kill -TERM/-9 <PID>` 或 `fuser -k 5001/tcp` |
| `curl 404`（Nginx） | 未命中正确 server 或 `/api/` 未配置 | 站点 `server_name` 设为 **wework.yfsports.com.cn**，并添加 `/api/` 反代；用 `Host:` 验证 |
| 宝塔 SSL 自动部署提示未找到标识 | 站点配置中缺少原始标记 `#SSL-START/#SSL-END` + `#error_page 404/404.html;` | 恢复标记（参见上文“HTTPS 自动部署”），或手动加 443 server 并指向证书路径 |
| 外网访问不通 | NAT/端口未转发、80/443 未放行 | 将公网 `59.49.99.226:80/443` 转发到服务器 `:80/443`；防火墙开放端口 |

---

## Systemd 常驻（可选）

`/etc/systemd/system/wecom_ops.service`：
```ini
[Unit]
Description=WeCom Ops (Gunicorn)
After=network.target

[Service]
WorkingDirectory=/www/wwwroot/wecom_ops
Environment="PATH=/www/wwwroot/wecom_ops/.venv/bin"
ExecStart=/www/wwwroot/wecom_ops/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 app.app:app --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

启用：
```bash
systemctl daemon-reload
systemctl enable --now wecom_ops
systemctl status wecom_ops --no-pager
```

---

## M1 验收清单

- [x] `GET /api/v1/health` 返回 `200`，Body 含 `trace_id`，响应头含 `X-Request-Id`
- [x] JSON 日志格式器工作正常（可看到 `trace_id` 等字段）
- [x] `pytest` 用例数 ≥ 20 且全部通过（当前 21 passed）
- [x] 宝塔 Nginx 站点 `/api/` 反代生效，`Host:` 命中站点验证通过

---

## 预埋 M2（供后续使用）

**建议表结构（MySQL）**：
```sql
CREATE TABLE IF NOT EXISTS wecom_token (
  id INT PRIMARY KEY AUTO_INCREMENT,
  corp_id VARCHAR(64) NOT NULL,
  agent_id INT NOT NULL,
  access_token VARCHAR(1024) NOT NULL,
  expires_at DATETIME NOT NULL,
  UNIQUE KEY uk_corp_agent (corp_id, agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS idempotency_key (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  idem_key VARCHAR(191) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_idem (idem_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mass_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  biz_no VARCHAR(64) NOT NULL,
  agent_id INT NOT NULL,
  msg_type VARCHAR(32) NOT NULL,
  payload JSON NOT NULL,
  target JSON NOT NULL,
  status TINYINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_biz_no (biz_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mass_task_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  level VARCHAR(10) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**WeCom 相关 `.env`（占位）**：
```dotenv
WECOM_CORP_ID=你的企业ID
WECOM_AGENT_ID=1000002
WECOM_AGENT_SECRET=你的应用密钥
WECOM_CALLBACK_TOKEN=回调Token
WECOM_CALLBACK_AESKEY=43位EncodingAESKey
```

**联通性探针（计划在 M2 增加）**：
- `GET /api/v1/pingdb`：MySQL 直连成功 → `{ok:true}`
- `GET /api/v1/pingredis`：Redis 直连成功 → `{ok:true}`

---

> 本 README 收录了 M1 期间的所有关键配置、验证命令与故障排查结论，后续 M2 将在此基础上扩展（数据库 Schema、WeCom Token 缓存、签名校验、群发并发/灰度等）。
