-- M2 migration · wecom_ops

-- 1) access token 表（预埋）
CREATE TABLE IF NOT EXISTS wecom_token (
  id INT PRIMARY KEY AUTO_INCREMENT,
  corp_id VARCHAR(64) NOT NULL,
  agent_id INT NOT NULL,
  access_token VARCHAR(1024) NOT NULL,
  expires_at DATETIME NOT NULL,
  UNIQUE KEY uk_corp_agent (corp_id, agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) 幂等键（预埋）
CREATE TABLE IF NOT EXISTS idempotency_key (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  idem_key VARCHAR(191) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_idem (idem_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) 群发任务主表（将 M1 的 mass_task 提升为 v3 结构，保留兼容）
CREATE TABLE IF NOT EXISTS mass_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3.1 兼容旧列（若存在 biz_no/payload/target 保留），新增/扩展新列
ALTER TABLE mass_task
  ADD COLUMN IF NOT EXISTS task_no VARCHAR(64) NULL,
  ADD COLUMN IF NOT EXISTS mass_type VARCHAR(32) NULL,
  ADD COLUMN IF NOT EXISTS content_type VARCHAR(32) NULL,
  ADD COLUMN IF NOT EXISTS content_json JSON NULL,
  ADD COLUMN IF NOT EXISTS targets_spec JSON NULL,
  ADD COLUMN IF NOT EXISTS status TINYINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS scheduled_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS last_enqueue_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS qps_limit INT NULL,
  ADD COLUMN IF NOT EXISTS concurrency_limit INT NULL,
  ADD COLUMN IF NOT EXISTS batch_size INT NULL,
  ADD COLUMN IF NOT EXISTS gray_strategy JSON NULL,
  ADD COLUMN IF NOT EXISTS report_stat JSON NULL,
  ADD COLUMN IF NOT EXISTS agent_id INT NULL,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- 3.2 兼容迁移：如果旧列 biz_no 存在且 task_no 为空，则迁移一次
UPDATE mass_task SET task_no = COALESCE(task_no, biz_no) WHERE task_no IS NULL AND COLUMN_EXISTS(mass_task,'biz_no');

-- 3.3 索引
CREATE INDEX IF NOT EXISTS idx_task_status ON mass_task (status, scheduled_at);
CREATE UNIQUE INDEX IF NOT EXISTS uk_task_no ON mass_task (task_no);
CREATE INDEX IF NOT EXISTS idx_task_last_enqueue ON mass_task (last_enqueue_at);

-- 4) 任务明细快照（按 v3 设计）
CREATE TABLE IF NOT EXISTS mass_target_snapshot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  recipient_id VARCHAR(64) NOT NULL,
  shard_no INT NOT NULL DEFAULT 0,
  wave_no INT NOT NULL DEFAULT 1,
  batch_no INT NOT NULL DEFAULT 1,
  state ENUM('pending','sent','failed','recalled') NOT NULL DEFAULT 'pending',
  last_error VARCHAR(255) NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_task_state (task_id, state),
  KEY idx_task_wave_batch (task_id, wave_no, batch_no),
  KEY idx_task_recipient (task_id, recipient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5) 任务日志（若未建）
CREATE TABLE IF NOT EXISTS mass_task_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  level VARCHAR(10) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
