/* ---------- M3 schema (fixed & extended) ---------- */

-- 组织
CREATE TABLE IF NOT EXISTS org_department (
  id BIGINT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  parent_id BIGINT NULL,
  order_no INT NULL,
  path VARCHAR(512) NULL,
  level TINYINT NULL,
  status TINYINT NOT NULL DEFAULT 1,
  ext JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_parent (parent_id),
  KEY idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS org_employee (
  userid VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NULL,
  mobile VARCHAR(32) NULL,
  email VARCHAR(128) NULL,
  position VARCHAR(128) NULL,
  gender TINYINT NULL,
  enable TINYINT NULL,
  qr_code VARCHAR(512) NULL,
  departments JSON NOT NULL,
  ext JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_mobile (mobile),
  KEY idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 为高效按部门筛人：员工-部门映射表
CREATE TABLE IF NOT EXISTS org_employee_dept (
  userid  VARCHAR(64) NOT NULL,
  dept_id BIGINT      NOT NULL,
  PRIMARY KEY (userid, dept_id),
  KEY idx_dept (dept_id),
  KEY idx_user (userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 外部联系人/标签/跟进人
CREATE TABLE IF NOT EXISTS ext_contact (
  external_userid VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NULL,
  corp_full_name VARCHAR(256) NULL,
  position VARCHAR(128) NULL,
  gender TINYINT NULL,
  unionid VARCHAR(128) NULL,
  ext JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_unionid (unionid),
  KEY idx_updated (updated_at),
  KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ext_follow_user (
  external_userid VARCHAR(64) NOT NULL,
  userid VARCHAR(64) NOT NULL,
  remark VARCHAR(256) NULL,
  state  VARCHAR(64) NULL,
  add_way TINYINT NULL,
  create_time DATETIME NULL,
  PRIMARY KEY (external_userid, userid),
  KEY idx_userid (userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ext_tag (
  tag_id VARCHAR(64) PRIMARY KEY,
  group_id VARCHAR(64) NULL,
  group_name VARCHAR(128) NULL,
  name VARCHAR(128) NOT NULL,
  order_no INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_group (group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ext_contact_tag (
  external_userid VARCHAR(64) NOT NULL,
  tag_id VARCHAR(64) NOT NULL,
  PRIMARY KEY (external_userid, tag_id),
  KEY idx_tag (tag_id),
  KEY idx_user (external_userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 同步状态（修复：cursor -> sync_cursor）
DROP TABLE IF EXISTS sync_state;
CREATE TABLE IF NOT EXISTS sync_state (
  domain       VARCHAR(32)  NOT NULL,
  item         VARCHAR(32)  NOT NULL,
  sync_cursor  VARCHAR(256) NULL,
  since        DATETIME     NULL,
  last_ok_at   DATETIME     NULL,
  last_err     VARCHAR(512) NULL,
  extra        JSON         NULL,
  updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (domain, item)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 审计
CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  action VARCHAR(64) NOT NULL,
  actor  VARCHAR(64) NULL,
  resource VARCHAR(64) NULL,
  trace_id VARCHAR(64) NULL,
  details JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_action (action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 身份映射视图
CREATE OR REPLACE VIEW vw_contact_identity AS
SELECT
  ec.external_userid,
  ec.name            AS ext_name,
  ef.userid          AS owner_userid,
  oe.name            AS owner_name,
  oe.mobile          AS owner_mobile,
  ec.unionid,
  JSON_EXTRACT(oe.departments, '$') AS owner_departments
FROM ext_contact ec
LEFT JOIN ext_follow_user ef ON ef.external_userid = ec.external_userid
LEFT JOIN org_employee oe     ON oe.userid        = ef.userid;

-- 预埋：微信客服 / 客户群 / 渠道活码
CREATE TABLE IF NOT EXISTS kf_account (
  open_kfid   VARCHAR(64) PRIMARY KEY,
  name        VARCHAR(128) NULL,
  status      TINYINT NULL,
  ext         JSON NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS kf_servicer (
  open_kfid   VARCHAR(64) NOT NULL,
  userid      VARCHAR(64) NOT NULL,
  status      TINYINT NULL,
  PRIMARY KEY (open_kfid, userid),
  KEY idx_user (userid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS kf_customer_bind (
  external_userid VARCHAR(64) NOT NULL,
  open_kfid       VARCHAR(64) NOT NULL,
  scene           VARCHAR(64) NULL,
  latest_at       DATETIME NULL,
  PRIMARY KEY (external_userid, open_kfid),
  KEY idx_kfid (open_kfid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ec_groupchat (
  chat_id     VARCHAR(128) PRIMARY KEY,
  name        VARCHAR(128) NULL,
  owner       VARCHAR(64)  NULL,
  notice      VARCHAR(1024) NULL,
  create_time DATETIME NULL,
  status      TINYINT NULL,
  ext         JSON NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_owner (owner)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ec_groupchat_member (
  chat_id     VARCHAR(128) NOT NULL,
  member_id   VARCHAR(128) NOT NULL,
  member_type ENUM('employee','external') NOT NULL,
  join_time   DATETIME NULL,
  unionid     VARCHAR(128) NULL,
  PRIMARY KEY (chat_id, member_id, member_type),
  KEY idx_chat (chat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ec_contact_way (
  config_id   VARCHAR(64) PRIMARY KEY,
  type        TINYINT NULL,
  scene       TINYINT NULL,
  remark      VARCHAR(256) NULL,
  state_code  VARCHAR(64) NULL,
  is_temp     TINYINT NULL,
  users_json   JSON NULL,
  parties_json JSON NULL,
  tags_json    JSON NULL,
  ext         JSON NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 首次回填 org_employee_dept（MySQL 8）
INSERT IGNORE INTO org_employee_dept (userid, dept_id)
SELECT e.userid, CAST(JSON_UNQUOTE(j.dept) AS UNSIGNED)
FROM org_employee e,
JSON_TABLE(e.departments, '$[*]' COLUMNS(dept VARCHAR(20) PATH '$')) AS j;
