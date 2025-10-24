/*
 Navicat Premium Data Transfer

 Source Server         : wecom_ops
 Source Server Type    : MySQL
 Source Server Version : 80036 (8.0.36)
 Source Host           : 192.168.0.13:3306
 Source Schema         : bi

 Target Server Type    : MySQL
 Target Server Version : 80036 (8.0.36)
 File Encoding         : 65001

 Date: 21/10/2025 22:09:41
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for dim_store
-- ----------------------------
DROP TABLE IF EXISTS `dim_store`;
CREATE TABLE `dim_store`  (
  `store_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '店铺编码',
  `store_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `province` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `retail_brand` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `department_brand` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `first_order_date` date NULL DEFAULT NULL,
  `employee_count` int NULL DEFAULT NULL,
  `store_area_sqm` decimal(10, 2) NULL DEFAULT NULL,
  `mall_commission_rate` decimal(5, 4) NULL DEFAULT NULL,
  PRIMARY KEY (`store_code`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dim_vip
-- ----------------------------
DROP TABLE IF EXISTS `dim_vip`;
CREATE TABLE `dim_vip`  (
  `vip_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `vip_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `age` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `mobile` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `birthday` date NULL DEFAULT NULL,
  `join_date` date NULL DEFAULT NULL,
  `card_issuing_employee_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `service_employee_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `service_employee_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `card_issuing_store_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `card_issuing_store_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `vip_source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `first_purchase_date` date NULL DEFAULT NULL,
  `last_purchase_date` date NULL DEFAULT NULL,
  `last_purchase_amount` decimal(10, 2) NULL DEFAULT NULL,
  `total_points` int NULL DEFAULT NULL,
  `available_balance` decimal(10, 2) NULL DEFAULT NULL,
  `avg_item_amount` decimal(10, 2) NULL DEFAULT NULL,
  `avg_order_amount` decimal(10, 2) NULL DEFAULT NULL,
  `total_orders` int NULL DEFAULT NULL,
  `total_items` int NULL DEFAULT NULL,
  `total_sales_amount` decimal(10, 2) NULL DEFAULT NULL,
  `total_original_price` decimal(10, 2) NULL DEFAULT NULL,
  `avg_discount` decimal(5, 2) NULL DEFAULT NULL,
  `service_store_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `user_id` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`vip_code`) USING BTREE,
  UNIQUE INDEX `uq_user_id`(`user_id` ASC) USING BTREE,
  INDEX `dim_vip_ibfk_1`(`card_issuing_store_code` ASC) USING BTREE,
  INDEX `idx_mobile`(`mobile` ASC) USING BTREE,
  INDEX `idx_dim_vip_user_id`(`user_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
