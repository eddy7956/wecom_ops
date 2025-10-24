/* -------------------
 * 1) 修复 sync_state 的保留字问题 + 优化字段
 * ------------------- */
DROP TABLE IF EXISTS sync_state;
CREATE TABLE IF NOT EXISTS sync_state (
  domain       VARCHAR(32)  NOT NULL,  -- org/ext/kf/group/way...
  item         VARCHAR(32)  NOT NULL,  -- departments/employees/contacts/tags/follow/kf_account/...
  sync_cursor  VARCHAR(256) NULL,      -- 原 cursor 改为 sync_cursor
  since        DATETIME     NULL,      -- 增量起点
  last_ok_at   DATETIME     NULL,      -- 最近成功时间（便于巡检）
  last_err     VARCHAR(512) NULL,      -- 最近错误摘要（便于排障）
  extra        JSON         NULL,
  updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (domain, item)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* -------------------
 * 2) 组织/人员：补充“员工-部门映射”表，提升按部门过滤性能
 * ------------------- */
CREATE TABLE IF NOT EXISTS org_employee_dept (
  userid   VARCHAR(64) NOT NULL,
  dept_id  BIGINT      NOT NULL,
  PRIMARY KEY (userid, dept_id),
  KEY idx_dept (dept_id),
  KEY idx_user (userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 首次回填（MySQL 8+ 使用 JSON_TABLE，性能/简洁最好） */
INSERT IGNORE INTO org_employee_dept (userid, dept_id)
SELECT e.userid,
       CAST(JSON_UNQUOTE(j.dept) AS UNSIGNED)
FROM org_employee e,
JSON_TABLE(e.departments, '$[*]' COLUMNS(dept VARCHAR(20) PATH '$')) AS j;

/* -------------------
 * 3) 外部联系人：补充常用索引与唯一性保护
 * ------------------- */
ALTER TABLE ext_contact
  ADD KEY idx_name (name);

ALTER TABLE ext_contact_tag
  ADD KEY idx_user (external_userid);

/* -------------------
 * 4) 预埋“客服 / 服务人员（kf）”、“客户群”、“渠道活码”结构
 *    —— 先有表后续直接落同步即可
 * ------------------- */

/* 4.1 微信客服账号 */
CREATE TABLE IF NOT EXISTS kf_account (
  open_kfid   VARCHAR(64) PRIMARY KEY,
  name        VARCHAR(128) NULL,
  status      TINYINT NULL,             -- 0停用/1启用等
  ext         JSON NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 4.2 客服服务人员（接待人员） */
CREATE TABLE IF NOT EXISTS kf_servicer (
  open_kfid   VARCHAR(64) NOT NULL,
  userid      VARCHAR(64) NOT NULL,
  status      TINYINT NULL,             -- 0移除/1正常
  PRIMARY KEY (open_kfid, userid),
  KEY idx_user (userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 4.3 客服-外部联系人 绑定（最近接待信息，可按需扩展） */
CREATE TABLE IF NOT EXISTS kf_customer_bind (
  external_userid VARCHAR(64) NOT NULL,
  open_kfid       VARCHAR(64) NOT NULL,
  scene           VARCHAR(64) NULL,     -- 业务场景/进线来源
  latest_at       DATETIME NULL,
  PRIMARY KEY (external_userid, open_kfid),
  KEY idx_kfid (open_kfid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 4.4 客户群（groupchat）及成员 */
CREATE TABLE IF NOT EXISTS ec_groupchat (
  chat_id     VARCHAR(128) PRIMARY KEY,
  name        VARCHAR(128) NULL,
  owner       VARCHAR(64)  NULL,        -- 群主（员工）
  notice      VARCHAR(1024) NULL,
  create_time DATETIME NULL,
  status      TINYINT NULL,             -- 0正常/其他状态
  ext         JSON NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_owner (owner)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ec_groupchat_member (
  chat_id     VARCHAR(128) NOT NULL,
  member_id   VARCHAR(128) NOT NULL,    -- 可能是员工userid或外部联系人external_userid
  member_type ENUM('employee','external') NOT NULL,
  join_time   DATETIME NULL,
  unionid     VARCHAR(128) NULL,        -- 外部联系人可回填
  PRIMARY KEY (chat_id, member_id, member_type),
  KEY idx_chat (chat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 4.5 渠道活码（contact_way） */
CREATE TABLE IF NOT EXISTS ec_contact_way (
  config_id   VARCHAR(64) PRIMARY KEY,
  type        TINYINT NULL,             -- 1单人/2多人
  scene       TINYINT NULL,             -- 1好友/2客户群
  remark      VARCHAR(256) NULL,
  state_code  VARCHAR(64) NULL,         -- 自定义state
  is_temp     TINYINT NULL,
  users_json  JSON NULL,                -- 关联员工列表
  parties_json JSON NULL,               -- 关联部门列表
  tags_json   JSON NULL,                -- 关联客户标签
  ext         JSON NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
