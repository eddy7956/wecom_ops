## 发布与回滚（概要）
- 分支：develop→测试（5002）、main→生产（5001）
- 自动化：deploy-dev.yml / deploy-prod.yml / rollback-prod.yml
- 公网冒烟：  
  - DEV：`https://wework.yfsports.com.cn/dev-api/v1/health`  
  - PROD：`https://wework.yfsports.com.cn/api/v1/health`

完整流程见《标准上线清单.md》。

