# 数据表索引

以下列表依据仓库中的 SQL 语句归纳出当前应用依赖的数据库表与视图，并列出各表在代码中使用到的主要字段，便于快速定位数据来源。

## 默认 schema（无显式前缀）

### org_department
- 相关代码：`app/org/service.py::sync_departments`、`list_departments`
- 字段：`id`、`name`、`parent_id`、`order_no`、`path`、`level`、`status`、`ext`

### org_employee
- 相关代码：`app/org/service.py::sync_employees`、`list_employees`
- 字段：`userid`、`name`、`mobile`、`email`、`position`、`gender`、`enable`、`qr_code`、`departments`、`ext`

### org_employee_dept
- 相关代码：`app/org/service.py::sync_employees`、`list_employees`
- 字段：`userid`、`dept_id`

### ext_contact
- 相关代码：`app/ext/service.py::sync_contacts`、`list_contacts`，`app/org/routes_v1.py::list_employees`
- 字段：`external_userid`、`name`、`corp_full_name`、`position`、`gender`、`unionid`、`ext`、`follow_userid`

### ext_follow_user
- 相关代码：`app/ext/service.py::sync_contacts`、`app/identity/service.py::get_union_mapping`、`app/org/routes_v1.py::list_employees`
- 字段：`external_userid`、`userid`、`remark`、`state`、`add_way`、`create_time`

### ext_contact_tag
- 相关代码：`app/ext/service.py::sync_contacts`、`list_contacts`
- 字段：`external_userid`、`tag_id`

### ext_tag
- 相关代码：`app/ext/service.py::sync_tags`
- 字段：`tag_id`、`group_id`、`group_name`、`name`、`order_no`

### ec_groupchat
- 相关代码：`app/group/service.py::sync_groupchats`
- 字段：`chat_id`、`name`、`owner`、`notice`、`create_time`、`status`、`ext`

### ec_groupchat_member
- 相关代码：`app/group/service.py::sync_groupchats`
- 字段：`chat_id`、`member_id`、`member_type`、`join_time`、`unionid`

### kf_account
- 相关代码：`app/kf/service.py::sync_kf_accounts`
- 字段：`open_kfid`、`name`、`status`、`ext`

### kf_servicer
- 相关代码：`app/kf/service.py::sync_kf_servicers`
- 字段：`open_kfid`、`userid`、`status`

### operation_log
- 相关代码：`app/common/audit.py::log`
- 字段：`operator`、`action`、`resource_type`、`resource_id`、`result`、`detail`

### mass_task
- 相关代码：`app/mass/repo.py` 的建单、查询与更新函数
- 字段：`id`、`task_no`、`name`、`mass_type`、`content_type`、`content_json`、`targets_spec`、`status`、`scheduled_at`、`qps_limit`、`concurrency_limit`、`batch_size`、`gray_strategy`、`report_stat`、`agent_id`、`created_at`、`updated_at`

### mass_target_snapshot
- 相关代码：`app/mass/repo.py`、`app/mass/routes_v1.py`
- 字段：`id`、`task_id`、`recipient_id`、`shard_no`、`wave_no`、`batch_no`、`state`、`last_error`、`created_at`、`updated_at`

### mass_task_log
- 相关代码：`app/mass/repo.py::list_logs`
- 字段：`task_id`、`created_at`、`level`、`message`

## `wecom_ops` schema

### wecom_ops.ext_contact
- 相关代码：`app/wecom/service.py::upsert_external_contact`、`app/wecom/routes_v1.py`、`app/members/routes_v1.py`
- 字段：`external_userid`、`name`、`avatar`、`unionid`、`corp_name`、`detail_json`、`is_deleted`、`is_unassigned`、`created_at`、`updated_at`

### wecom_ops.ext_contact_follow
- 相关代码：`app/wecom/routes_v1.py` 的回调、待分配处理
- 字段：`external_userid`、`userid`

### wecom_ops.ext_unassigned
- 相关代码：`app/wecom/routes_v1.py` 的待分配查询与分配逻辑
- 字段：`external_userid`、`is_active`、`reason`、`handover_userid`、`created_at`、`updated_at`

### wecom_ops.ext_contact_tag
- 相关代码：`app/wecom/routes_v1.py`、`app/members/routes_v1.py`
- 字段：`external_userid`、`tag_id`、`tag_name`、`group_name`

### wecom_ops.mobile_upload
- 相关代码：`app/media/routes_v1.py::upload`
- 字段：`id`、`type`、`filename`、`total`、`valid`、`invalid`

### wecom_ops.mobile_upload_item
- 相关代码：`app/media/routes_v1.py::upload`
- 字段：`upload_id`、`mobile_std`

### wecom_ops.mass_task
- 相关代码：`app/mass/routes_v1.py` 的任务创建、查询、状态流转
- 字段：`id`、`task_no`、`name`、`content_type`、`content_json`、`targets_spec`、`status`、`qps_limit`、`concurrency_limit`、`batch_size`、`agent_id`、`scheduled_at`、`created_at`、`updated_at`

### wecom_ops.mass_target_snapshot
- 相关代码：`app/mass/routes_v1.py` 的任务规划、分页、状态更新
- 字段：`task_id`、`recipient_id`、`state`、`wave_no`、`batch_no`、`created_at`、`updated_at`

### wecom_ops.vw_mobile_to_external（视图）
- 相关代码：`app/media/routes_v1.py`、`app/identity/routes.py`、`app/members/routes_v1.py`
- 字段：`mobile_std`、`external_userid`、`vip_name`、`mobile_raw`、`primary_owner_userid`、`primary_owner_name`、`store_code`、`store_name`、`department_brand`、`tag_names`、`is_deleted`

### wecom_ops.vw_vip_panorama（视图）
- 相关代码：`app/identity/routes.py::mapping`
- 字段：`external_userid`、`ext_name`、`unionid`
