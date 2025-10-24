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

 Date: 23/10/2025 13:03:45
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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

SET FOREIGN_KEY_CHECKS = 1;
