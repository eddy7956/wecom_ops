from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import JSON  # 支持MySQL的JSON类型

# 初始化SQLAlchemy（数据库操作对象）
db = SQLAlchemy()

class MassTask(db.Model):
    """群发任务表（对应设计文档中的mass_task）"""
    __tablename__ = 'mass_task'
    
    id = db.Column(db.Integer, primary_key=True)  # 自增主键
    task_no = db.Column(db.String(64), unique=True, nullable=False)  # 任务编号（唯一）
    mass_type = db.Column(db.String(32), nullable=False)  # 群发类型
    content_type = db.Column(db.String(32), nullable=False)  # 内容类型
    content_json = db.Column(JSON, nullable=False)  # 内容（JSON格式）
    targets_spec = db.Column(JSON, nullable=False)  # 目标人群规则（JSON格式）
    status = db.Column(db.String(32), nullable=False, default='draft')  # 任务状态
    scheduled_at = db.Column(db.DateTime)  # 计划执行时间
    last_enqueue_at = db.Column(db.DateTime)  # 最后入队时间
    qps_limit = db.Column(db.Integer, default=100)  # QPS限制
    concurrency_limit = db.Column(db.Integer, default=50)  # 任务并发限制
    batch_size = db.Column(db.Integer, default=300)  # 批次大小
    gray_strategy = db.Column(JSON)  # 灰度策略（JSON格式）
    report_stat = db.Column(JSON, default={})  # 统计报告（JSON格式）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 索引（对应设计文档）
    __table_args__ = (
        db.Index('idx_status_scheduled', 'status', 'scheduled_at'),
        db.Index('idx_last_enqueue', 'last_enqueue_at'),
    )

class MassTargetSnapshot(db.Model):
    """群发目标快照表（对应设计文档中的mass_target_snapshot）"""
    __tablename__ = 'mass_target_snapshot'
    
    id = db.Column(db.Integer, primary_key=True)  # 自增主键
    task_id = db.Column(db.Integer, db.ForeignKey('mass_task.id'), nullable=False)  # 关联任务ID
    recipient_id = db.Column(db.String(64), nullable=False)  # 接收者ID
    shard_no = db.Column(db.Integer, nullable=False)  # 分片编号
    wave_no = db.Column(db.Integer, nullable=False)  # 波次编号
    batch_no = db.Column(db.Integer, nullable=False)  # 批次编号
    state = db.Column(db.String(32), default='pending')  # 状态（pending/sent/failed/recalled）
    last_error = db.Column(db.String(256))  # 最后错误信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 索引（对应设计文档）
    __table_args__ = (
        db.Index('idx_task_state', 'task_id', 'state'),
        db.Index('idx_task_wave_batch', 'task_id', 'wave_no', 'batch_no'),
        db.Index('idx_task_recipient', 'task_id', 'recipient_id'),
    )