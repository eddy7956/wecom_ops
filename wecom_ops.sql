/*
 Navicat Premium Data Transfer

 Source Server         : wecom_ops
 Source Server Type    : MySQL
 Source Server Version : 80036 (8.0.36)
 Source Host           : 192.168.0.13:3306
 Source Schema         : wecom_ops

 Target Server Type    : MySQL
 Target Server Version : 80036 (8.0.36)
 File Encoding         : 65001

 Date: 21/10/2025 22:09:23
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for audit_log
-- ----------------------------
DROP TABLE IF EXISTS `audit_log`;
CREATE TABLE `audit_log`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `actor` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `resource` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `trace_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `details` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_action`(`action` ASC, `created_at` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for crm_vip_link
-- ----------------------------
DROP TABLE IF EXISTS `crm_vip_link`;
CREATE TABLE `crm_vip_link`  (
  `union_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `user_id` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`union_id`) USING BTREE,
  UNIQUE INDEX `uq_union_id`(`union_id` ASC) USING BTREE,
  INDEX `idx_crm_vip_link_user_id`(`user_id` ASC) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `fk_crm_link_union` FOREIGN KEY (`union_id`) REFERENCES `ext_contact` (`unionid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for crm_vip_link_stage
-- ----------------------------
DROP TABLE IF EXISTS `crm_vip_link_stage`;
CREATE TABLE `crm_vip_link_stage`  (
  `user_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `user_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `union_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `src` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `loaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ec_contact_way
-- ----------------------------
DROP TABLE IF EXISTS `ec_contact_way`;
CREATE TABLE `ec_contact_way`  (
  `config_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `type` tinyint NULL DEFAULT NULL,
  `scene` tinyint NULL DEFAULT NULL,
  `remark` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `state_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_temp` tinyint NULL DEFAULT NULL,
  `users_json` json NULL,
  `parties_json` json NULL,
  `tags_json` json NULL,
  `ext` json NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`config_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ec_groupchat
-- ----------------------------
DROP TABLE IF EXISTS `ec_groupchat`;
CREATE TABLE `ec_groupchat`  (
  `chat_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `owner` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `notice` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `status` tinyint NULL DEFAULT NULL,
  `ext` json NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`chat_id`) USING BTREE,
  INDEX `idx_owner`(`owner` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ec_groupchat_member
-- ----------------------------
DROP TABLE IF EXISTS `ec_groupchat_member`;
CREATE TABLE `ec_groupchat_member`  (
  `chat_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `member_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `member_type` enum('employee','external') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `join_time` datetime NULL DEFAULT NULL,
  `unionid` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`chat_id`, `member_id`, `member_type`) USING BTREE,
  INDEX `idx_chat`(`chat_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_contact
-- ----------------------------
DROP TABLE IF EXISTS `ext_contact`;
CREATE TABLE `ext_contact`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `corp_full_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `position` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `gender` tinyint NULL DEFAULT NULL,
  `unionid` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `ext` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `type` tinyint NULL DEFAULT NULL,
  `avatar` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `corp_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `ext_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `follow_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `follow_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `detail_json` json NULL COMMENT 'ä¼ä¸šå¾®ä¿¡å¤–éƒ¨è”ç³»äººè¯¦æƒ…-åŽŸå§‹ä½“',
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '0=æ­£å¸¸,1=å·²åˆ ',
  `owner_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'è·Ÿè¿›äººuseridï¼ˆä»Ždetail_jsonæ˜ å°„ï¼‰',
  `is_unassigned` tinyint(1) NOT NULL DEFAULT 0 COMMENT '0=正常,1=企业侧处于待分配',
  PRIMARY KEY (`external_userid`) USING BTREE,
  UNIQUE INDEX `uk_ext_contact_eu`(`external_userid` ASC) USING BTREE,
  UNIQUE INDEX `uk_unionid`(`unionid` ASC) USING BTREE,
  INDEX `idx_updated`(`updated_at` ASC) USING BTREE,
  INDEX `idx_name`(`name` ASC) USING BTREE,
  INDEX `idx_ext_contact_owner`(`owner_userid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_contact_follow
-- ----------------------------
DROP TABLE IF EXISTS `ext_contact_follow`;
CREATE TABLE `ext_contact_follow`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `first_follow_at` datetime NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL COMMENT '建立关系时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `state` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `add_way` int NULL DEFAULT NULL,
  `createtime` int NULL DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`external_userid`, `userid`) USING BTREE,
  UNIQUE INDEX `uk_follow`(`external_userid` ASC, `userid` ASC) USING BTREE,
  UNIQUE INDEX `uk_ext_user_follow`(`external_userid` ASC, `userid` ASC) USING BTREE,
  INDEX `idx_follow_userid`(`userid` ASC) USING BTREE,
  INDEX `idx_follow_ext`(`external_userid` ASC) USING BTREE,
  INDEX `idx_follow_ext_user`(`external_userid` ASC, `userid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_contact_tag
-- ----------------------------
DROP TABLE IF EXISTS `ext_contact_tag`;
CREATE TABLE `ext_contact_tag`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `tag_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `tag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `group_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `owner_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`external_userid`, `tag_id`, `owner_userid`) USING BTREE,
  UNIQUE INDEX `uniq_eid_tag_owner`(`external_userid` ASC, `tag_id` ASC, `owner_userid` ASC) USING BTREE,
  UNIQUE INDEX `uk_ext_tag_eu_tid`(`external_userid` ASC, `tag_id` ASC) USING BTREE,
  UNIQUE INDEX `uk_ext_contact_tag_eu_owner_tid`(`external_userid` ASC, `owner_userid` ASC, `tag_id` ASC) USING BTREE,
  INDEX `idx_tag`(`tag_id` ASC) USING BTREE,
  INDEX `idx_user`(`external_userid` ASC) USING BTREE,
  INDEX `idx_owner`(`owner_userid` ASC) USING BTREE,
  INDEX `idx_ect_owner`(`owner_userid` ASC) USING BTREE,
  INDEX `idx_ect_tag`(`tag_id` ASC) USING BTREE,
  INDEX `idx_ext_tag_eu`(`external_userid` ASC) USING BTREE,
  INDEX `idx_ext_tag_tid`(`tag_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_follow
-- ----------------------------
DROP TABLE IF EXISTS `ext_follow`;
CREATE TABLE `ext_follow`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `owner_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `createtime` bigint NULL DEFAULT NULL,
  `add_way` int NULL DEFAULT NULL,
  `state` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `wechat_channels` json NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`external_userid`, `owner_userid`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_follow_user
-- ----------------------------
DROP TABLE IF EXISTS `ext_follow_user`;
CREATE TABLE `ext_follow_user`  (
  `userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `status` tinyint NULL DEFAULT NULL,
  `departments` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`userid`) USING BTREE,
  INDEX `idx_userid`(`userid` ASC) USING BTREE,
  INDEX `idx_ext_follow_user_status`(`status` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_tag
-- ----------------------------
DROP TABLE IF EXISTS `ext_tag`;
CREATE TABLE `ext_tag`  (
  `tag_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `group_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `group_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `order_no` int NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_time` datetime NULL DEFAULT NULL,
  `deleted` tinyint NULL DEFAULT 0,
  PRIMARY KEY (`tag_id`) USING BTREE,
  INDEX `idx_group`(`group_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ext_unassigned
-- ----------------------------
DROP TABLE IF EXISTS `ext_unassigned`;
CREATE TABLE `ext_unassigned`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `dimiss_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `create_time` int NULL DEFAULT NULL,
  `fetched_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `reason` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `handover_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`external_userid`) USING BTREE,
  INDEX `idx_unas_time`(`create_time` ASC) USING BTREE,
  INDEX `idx_unassigned_active`(`is_active` ASC) USING BTREE,
  INDEX `idx_unassigned_created`(`created_at` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for idempotency_key
-- ----------------------------
DROP TABLE IF EXISTS `idempotency_key`;
CREATE TABLE `idempotency_key`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `idem_key` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_idem`(`idem_key` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for kf_account
-- ----------------------------
DROP TABLE IF EXISTS `kf_account`;
CREATE TABLE `kf_account`  (
  `open_kfid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `status` tinyint NULL DEFAULT NULL,
  `ext` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`open_kfid`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for kf_customer_bind
-- ----------------------------
DROP TABLE IF EXISTS `kf_customer_bind`;
CREATE TABLE `kf_customer_bind`  (
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `open_kfid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `scene` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `latest_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`external_userid`, `open_kfid`) USING BTREE,
  INDEX `idx_kfid`(`open_kfid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for kf_servicer
-- ----------------------------
DROP TABLE IF EXISTS `kf_servicer`;
CREATE TABLE `kf_servicer`  (
  `open_kfid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status` tinyint NULL DEFAULT NULL,
  PRIMARY KEY (`open_kfid`, `userid`) USING BTREE,
  INDEX `idx_user`(`userid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mass_send_record
-- ----------------------------
DROP TABLE IF EXISTS `mass_send_record`;
CREATE TABLE `mass_send_record`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'ä¸»é”®',
  `task_id` bigint UNSIGNED NOT NULL COMMENT 'æ‰€å±žä»»åŠ¡IDï¼ˆmass_task.idï¼‰',
  `snapshot_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'ç›®æ ‡å¿«ç…§IDï¼ˆmass_target_snapshot.idï¼‰',
  `external_userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'ä¼ä¸šå¾®ä¿¡å¤–éƒ¨è”ç³»äººID',
  `unionid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'ï¼ˆå†—ä½™ï¼‰unionid åŠ é€ŸæŸ¥è¯¢/å¯¼å‡º',
  `content_type` enum('text','image','miniprogram') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'å†…å®¹ç±»åž‹',
  `content_summary` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'å†…å®¹æ‘˜è¦ï¼ˆæ–‡æ¡ˆå‰50å­—/å›¾ç‰‡å/å°ç¨‹åºæ ‡é¢˜ï¼‰',
  `content_json` json NULL COMMENT 'å®Œæ•´å‘é€å†…å®¹ç»“æž„ï¼ˆå«å›¾ç‰‡media_id/å°ç¨‹åºè·¯å¾„ä¸Žå‚æ•°ç­‰ï¼‰',
  `send_time` datetime NULL DEFAULT NULL COMMENT 'å‘é€æ—¶é—´ï¼ˆå¼€å§‹å‘é€æˆ–å®Œæˆæ—¶é—´ï¼‰',
  `status` enum('pending','sent','failed','recalled') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'pending' COMMENT 'å‘é€çŠ¶æ€',
  `fail_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'å¤±è´¥åŽŸå› ï¼ˆå®¢æˆ·å·²åˆ é™¤å¥½å‹/æŽ¥å£é™é¢‘/ç³»ç»Ÿè¶…æ—¶ç­‰ï¼‰',
  `operator` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'æ“ä½œäººï¼ˆè´¦å·ï¼‰',
  `msgid` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'ä¼ä¸šå¾®ä¿¡è¿”å›žçš„æ¶ˆæ¯IDï¼ˆç”¨äºŽæ’¤å›ž/è¿½è¸ªï¼‰',
  `trace_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'é“¾è·¯è¿½è¸ªIDï¼ˆè´¯ç©¿ä»»åŠ¡/å›žè°ƒï¼‰',
  `progress` tinyint UNSIGNED NOT NULL DEFAULT 0 COMMENT 'è¿›åº¦ç™¾åˆ†æ¯”ï¼ˆ0-100ï¼‰',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_task_send_time`(`task_id` ASC, `send_time` ASC) USING BTREE,
  INDEX `idx_extuser`(`external_userid` ASC) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  INDEX `idx_trace`(`trace_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = 'ç¾¤å‘æ˜Žç»†ï¼šæ¯æ¡åŽŸå­å†…å®¹ä¸€è¡Œ' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mass_target_snapshot
-- ----------------------------
DROP TABLE IF EXISTS `mass_target_snapshot`;
CREATE TABLE `mass_target_snapshot`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `task_id` bigint NOT NULL COMMENT '关联任务ID',
  `recipient_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '接收者ID',
  `state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'pending',
  `last_error` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `wave_no` int NOT NULL DEFAULT 1 COMMENT '波次号',
  `batch_no` int NOT NULL DEFAULT 1 COMMENT '批次号',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `shard_no` int NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_unique_task_recipient`(`task_id` ASC, `recipient_id` ASC) USING BTREE,
  INDEX `idx_task_state`(`task_id` ASC, `state` ASC) USING BTREE,
  INDEX `idx_task_wave_batch`(`task_id` ASC, `wave_no` ASC, `batch_no` ASC) USING BTREE,
  INDEX `idx_task_recipient`(`task_id` ASC, `recipient_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 322240 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '群发目标快照表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mass_task
-- ----------------------------
DROP TABLE IF EXISTS `mass_task`;
CREATE TABLE `mass_task`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `mass_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `content_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `content_json` json NULL,
  `targets_spec` json NULL,
  `status` tinyint NOT NULL DEFAULT 0,
  `scheduled_at` datetime NULL DEFAULT NULL,
  `started_at` datetime NULL DEFAULT NULL,
  `finished_at` datetime NULL DEFAULT NULL,
  `last_enqueue_at` datetime NULL DEFAULT NULL,
  `qps_limit` int NULL DEFAULT NULL,
  `concurrency_limit` int NULL DEFAULT NULL,
  `batch_size` int NULL DEFAULT NULL,
  `gray_strategy` json NULL,
  `report_stat` json NULL,
  `agent_id` int NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_task_no`(`task_no` ASC) USING BTREE,
  INDEX `idx_task_status`(`status` ASC, `scheduled_at` ASC) USING BTREE,
  INDEX `idx_task_last_enqueue`(`last_enqueue_at` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 16 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mass_task_log
-- ----------------------------
DROP TABLE IF EXISTS `mass_task_log`;
CREATE TABLE `mass_task_log`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id` bigint UNSIGNED NOT NULL,
  `level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'info',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_task_level`(`task_id` ASC, `level` ASC, `created_at` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for media_upload
-- ----------------------------
DROP TABLE IF EXISTS `media_upload`;
CREATE TABLE `media_upload`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `filename` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `total` int NULL DEFAULT 0,
  `valid` int NULL DEFAULT 0,
  `invalid` int NULL DEFAULT 0,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mobile_upload
-- ----------------------------
DROP TABLE IF EXISTS `mobile_upload`;
CREATE TABLE `mobile_upload`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `filename` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `total` int NOT NULL DEFAULT 0,
  `valid` int NOT NULL DEFAULT 0,
  `invalid` int NOT NULL DEFAULT 0,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for mobile_upload_item
-- ----------------------------
DROP TABLE IF EXISTS `mobile_upload_item`;
CREATE TABLE `mobile_upload_item`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `upload_id` bigint NOT NULL,
  `mobile_std` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_upload_mobile`(`upload_id` ASC, `mobile_std` ASC) USING BTREE,
  INDEX `idx_upload`(`upload_id` ASC) USING BTREE,
  INDEX `idx_mobile`(`mobile_std` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for num
-- ----------------------------
DROP TABLE IF EXISTS `num`;
CREATE TABLE `num`  (
  `n` int NOT NULL,
  PRIMARY KEY (`n`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for operation_log
-- ----------------------------
DROP TABLE IF EXISTS `operation_log`;
CREATE TABLE `operation_log`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `operator` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `resource_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `resource_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `result` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `detail` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_created_at`(`created_at` ASC) USING BTREE,
  INDEX `idx_operator`(`operator` ASC) USING BTREE,
  INDEX `idx_action`(`action` ASC) USING BTREE,
  INDEX `idx_resource`(`resource_type` ASC, `resource_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for org_department
-- ----------------------------
DROP TABLE IF EXISTS `org_department`;
CREATE TABLE `org_department`  (
  `id` bigint NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `parent_id` bigint NULL DEFAULT NULL,
  `order_no` int NULL DEFAULT NULL,
  `path` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `level` tinyint NULL DEFAULT NULL,
  `status` tinyint NOT NULL DEFAULT 1,
  `ext` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_parent`(`parent_id` ASC) USING BTREE,
  INDEX `idx_updated`(`updated_at` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for org_employee
-- ----------------------------
DROP TABLE IF EXISTS `org_employee`;
CREATE TABLE `org_employee`  (
  `userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `mobile` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `email` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `position` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `gender` tinyint NULL DEFAULT NULL,
  `enable` tinyint NULL DEFAULT NULL,
  `qr_code` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `departments` json NOT NULL,
  `ext` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` tinyint NULL DEFAULT NULL,
  `alias` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `avatar` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `ext_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  PRIMARY KEY (`userid`) USING BTREE,
  INDEX `idx_mobile`(`mobile` ASC) USING BTREE,
  INDEX `idx_updated`(`updated_at` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for org_employee_dept
-- ----------------------------
DROP TABLE IF EXISTS `org_employee_dept`;
CREATE TABLE `org_employee_dept`  (
  `userid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `dept_id` bigint NOT NULL,
  PRIMARY KEY (`userid`, `dept_id`) USING BTREE,
  INDEX `idx_dept`(`dept_id` ASC) USING BTREE,
  INDEX `idx_user`(`userid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for sync_state
-- ----------------------------
DROP TABLE IF EXISTS `sync_state`;
CREATE TABLE `sync_state`  (
  `domain` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `item` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `sync_cursor` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `since` datetime NULL DEFAULT NULL,
  `last_ok_at` datetime NULL DEFAULT NULL,
  `last_err` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `extra` json NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`domain`, `item`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for wecom_token
-- ----------------------------
DROP TABLE IF EXISTS `wecom_token`;
CREATE TABLE `wecom_token`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `corp_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `agent_id` int NOT NULL,
  `access_token` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_corp_agent`(`corp_id` ASC, `agent_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- View structure for v_mass_recent_touched
-- ----------------------------
DROP VIEW IF EXISTS `v_mass_recent_touched`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `v_mass_recent_touched` AS select `mass_send_record`.`external_userid` AS `external_userid`,min(`mass_send_record`.`send_time`) AS `first_touch_time`,max(`mass_send_record`.`send_time`) AS `last_touch_time`,count(0) AS `total_messages` from `mass_send_record` where (`mass_send_record`.`status` in ('sent','failed','recalled')) group by `mass_send_record`.`external_userid`;

-- ----------------------------
-- View structure for vw_contact_identity
-- ----------------------------
DROP VIEW IF EXISTS `vw_contact_identity`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `vw_contact_identity` AS select `ec`.`external_userid` AS `external_userid`,`ec`.`name` AS `ext_name`,`ef`.`userid` AS `owner_userid`,`oe`.`name` AS `owner_name`,`oe`.`mobile` AS `owner_mobile`,`ec`.`unionid` AS `unionid`,json_extract(`oe`.`departments`,'$') AS `owner_departments` from ((`ext_contact` `ec` left join `ext_follow_user` `ef` on((`ef`.`external_userid` = `ec`.`external_userid`))) left join `org_employee` `oe` on((`oe`.`userid` = `ef`.`userid`)));

-- ----------------------------
-- View structure for vw_ext_primary_owner
-- ----------------------------
DROP VIEW IF EXISTS `vw_ext_primary_owner`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `vw_ext_primary_owner` AS select `ext_contact_follow`.`external_userid` AS `external_userid`,substring_index(group_concat(`ext_contact_follow`.`userid` order by coalesce(`ext_contact_follow`.`createtime`,0) ASC,`ext_contact_follow`.`userid` ASC separator ','),',',1) AS `primary_owner_userid` from `ext_contact_follow` group by `ext_contact_follow`.`external_userid`;

-- ----------------------------
-- View structure for vw_mobile_to_external
-- ----------------------------
DROP VIEW IF EXISTS `vw_mobile_to_external`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `vw_mobile_to_external` AS select `e`.`external_userid` AS `external_userid`,`e`.`unionid` AS `unionid`,`c`.`user_id` AS `crm_user_id`,`v`.`name` AS `vip_name`,`v`.`mobile` AS `mobile_raw`,(case when regexp_like(`v`.`mobile`,'^86[1][3-9][0-9]{9}$') then `v`.`mobile` when regexp_like(`v`.`mobile`,'^[1][3-9][0-9]{9}$') then concat('86',`v`.`mobile`) else NULL end) AS `mobile_norm`,`v`.`service_store_code` AS `store_code`,`s`.`store_name` AS `store_name`,`s`.`department_brand` AS `department_brand`,`po`.`primary_owner_userid` AS `primary_owner_userid`,coalesce(`oe`.`name`,`po`.`primary_owner_userid`) AS `primary_owner_name`,`ta`.`tag_ids` AS `tag_ids`,`ta`.`tag_names` AS `tag_names`,`ta`.`tag_group_names` AS `tag_group_names`,coalesce(`e`.`is_deleted`,0) AS `is_deleted` from ((((((`ext_contact` `e` join `crm_vip_link` `c` on(((`c`.`union_id` = `e`.`unionid`) and (`c`.`user_id` is not null)))) join `bi`.`dim_vip` `v` on((`v`.`user_id` = `c`.`user_id`))) left join `bi`.`dim_store` `s` on((`s`.`store_code` = `v`.`service_store_code`))) left join (select `x`.`external_userid` AS `external_userid`,coalesce(`x`.`owner_userid`,json_unquote(json_extract((case when json_valid(`x`.`detail_json`) then `x`.`detail_json` else json_object('follow_user',json_array()) end),'$."follow_user"[0]."userid"'))) AS `primary_owner_userid` from `ext_contact` `x`) `po` on((`po`.`external_userid` = `e`.`external_userid`))) left join `org_employee` `oe` on((`oe`.`userid` = `po`.`primary_owner_userid`))) left join (select `t`.`external_userid` AS `external_userid`,group_concat(distinct `t`.`tag_id` order by `t`.`tag_id` ASC separator ',') AS `tag_ids`,group_concat(distinct coalesce(`t`.`tag_name`,`t`.`tag_id`) order by coalesce(`t`.`tag_name`,`t`.`tag_id`) ASC separator ',') AS `tag_names`,group_concat(distinct `t`.`group_name` order by `t`.`group_name` ASC separator ',') AS `tag_group_names` from `ext_contact_tag` `t` group by `t`.`external_userid`) `ta` on((`ta`.`external_userid` = `e`.`external_userid`))) where (coalesce(`e`.`is_deleted`,0) = 0);

-- ----------------------------
-- View structure for vw_vip_panorama
-- ----------------------------
DROP VIEW IF EXISTS `vw_vip_panorama`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `vw_vip_panorama` AS select `e`.`external_userid` AS `external_userid`,`e`.`unionid` AS `unionid`,`c`.`user_id` AS `crm_user_id`,`d`.`mobile` AS `vip_mobile`,`e`.`name` AS `ext_name`,`e`.`corp_name` AS `corp_name`,`e`.`avatar` AS `avatar`,`e`.`follow_userid` AS `owner_userid`,`e`.`created_at` AS `created_at`,`e`.`updated_at` AS `updated_at` from ((`ext_contact` `e` join `crm_vip_link` `c` on((`c`.`union_id` = `e`.`unionid`))) join `bi`.`dim_vip` `d` on((`d`.`user_id` = `c`.`user_id`))) where ((`c`.`user_id` is not null) and (`c`.`user_id` <> ''));

SET FOREIGN_KEY_CHECKS = 1;
