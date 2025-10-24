import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Card, Descriptions, Table, Space, Tag, Select, Button, Alert, Modal, message, Statistic, Row, Col, Switch, Tooltip } from 'antd'
import { getTask, listTargets, planTask, executeTask, retryTarget, retryTargets, getTaskProgress, type Page } from '@/api/mass'

type Task = {
  id: number | string
  name?: string | null
  task_no?: string
  status?: string | number
  created_at?: string
  scheduled_at?: string | null
  report_stat?: Record<string, any>
}

const STATUS_META: Record<string, { text: string; color: any }> = {
  INIT:    { text: '初始化', color: 'default' },
  READY:   { text: '就绪',   color: 'processing' },
  PLANNED: { text: '已规划', color: 'cyan' },
  RUNNING: { text: '执行中', color: 'blue' },
  DONE:    { text: '已完成', color: 'success' },
  FAILED:  { text: '失败',   color: 'error' },
}
const CODE_TO_KEY: Record<string, string> = {
  '0': 'INIT', '1': 'READY', '2': 'PLANNED', '3': 'RUNNING', '4': 'DONE', '5': 'FAILED',
}
const statusTag = (s: any) => {
  const raw = String(s ?? '')
  const key = (CODE_TO_KEY[raw] || raw).toUpperCase()
  const meta = STATUS_META[key] || { text: String(s ?? '未知'), color: 'default' }
  return <Tag color={meta.color}>{meta.text}</Tag>
}

const fmt = (v?: any) => (v === undefined || v === null || v === '' ? '-' : String(v))

// 行唯一键：优先 id/target_id，否则退化为组合键
const getRowKey = (r: any) =>
  r?.id ?? r?.target_id ?? (r?.recipient_id != null && r?.wave_no != null && r?.batch_no != null
    ? `${r.recipient_id}_${r.wave_no}_${r.batch_no}`
    : JSON.stringify(r))

const extractTargetId = (r: any): string | number | null =>
  r?.id ?? r?.target_id ?? null

export default function TaskDetail() {
  const params = useParams<{ id: string }>()
  const taskId = params.id!
  const nav = useNavigate()

  // 顶部统计
  const qProg = useQuery({
    queryKey: ['task-progress', taskId],
    queryFn: () => getTaskProgress(taskId),
    enabled: !!taskId,
    refetchInterval: 10000,
    placeholderData: (prev)=>prev
  })

  // 任务详情
  const qTask = useQuery<Task>({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId),
    enabled: !!taskId,
    placeholderData: (prev)=>prev
  })

  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)
  const [tState, setTState] = useState<string | undefined>(undefined)
  const [onlyFailed, setOnlyFailed] = useState(false)
  const qTargets = useQuery<Page<any>>({
    queryKey: ['targets', taskId, page, size, tState, onlyFailed],
    queryFn: () => listTargets(taskId, { page, size, state: onlyFailed ? 'FAILED' : tState }),
    enabled: !!taskId,
    placeholderData: (prev)=>prev,
    refetchInterval: 10000,
  })
  useEffect(()=>{ setPage(1) }, [tState, onlyFailed])

  // 动作
  const mPlan = useMutation({
    mutationFn: () => planTask(taskId),
    onSuccess: () => { message.success('已发起规划'); qTargets.refetch(); qProg.refetch() },
    onError: (e:any) => message.error(e?.message || '规划失败'),
  })
  const mExec = useMutation({
    mutationFn: () => executeTask(taskId),
    onSuccess: () => { message.success('已发起执行'); qTargets.refetch(); qProg.refetch() },
    onError: (e:any) => message.error(e?.message || '执行失败'),
  })
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [selectedRows, setSelectedRows] = useState<any[]>([])
  const mRetryOne = useMutation({
    mutationFn: (id: string | number) => retryTarget(id),
    onSuccess: () => { message.success('已触发重试'); qTargets.refetch(); qProg.refetch() },
    onError: (e:any) => message.error(e?.message || '重试失败'),
  })
  const mRetrySelected = useMutation({
    mutationFn: async () => {
      const ids = selectedRows.map(extractTargetId).filter(Boolean) as Array<string | number>
      if (!ids.length) throw new Error('未选中有效记录')
      return retryTargets(taskId, ids)
    },
    onSuccess: () => {
      message.success('已触发重试选中')
      setSelectedRowKeys([]); setSelectedRows([])
      qTargets.refetch(); qProg.refetch()
    },
    onError: (e:any) => message.error(e?.message || '重试选中失败'),
  })

  const columns = useMemo(() => {
    return [
      { title: '目标ID', dataIndex: 'id', width: 160, render: (_:any, r:any)=>fmt(r?.id ?? r?.target_id) },
      { title: '收件人', dataIndex: 'recipient_id', width: 180, render: (_:any, r:any)=>fmt(r?.recipient_id ?? r?.external_userid ?? r?.userid) },
      { title: '状态', dataIndex: 'state', width: 120, render: (s:any)=>statusTag(s) },
      { title: '波次', dataIndex: 'wave_no', width: 100, render: (v:any)=>fmt(v) },
      { title: '批次', dataIndex: 'batch_no', width: 100, render: (v:any)=>fmt(v) },
      {
        title: '操作',
        key: 'op',
        width: 120,
        fixed: 'right' as const,
        render: (_: any, r: any) => {
          const tid = extractTargetId(r)
          const disabled = !tid
          return (
            <Tooltip title={disabled ? '缺少目标ID，无法单条重试' : ''}>
              <Button size="small" disabled={disabled} loading={mRetryOne.isPending}
                onClick={() => Modal.confirm({ title: '确认重试该目标？', onOk: () => tid && mRetryOne.mutate(tid) })}>
                重试
              </Button>
            </Tooltip>
          )
        },
      },
    ]
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mRetryOne.isPending])

  return (
    <div>
      {/* 抬头牌 */}
      <Card style={{ marginBottom: 12 }}>
        <Row gutter={16}>
          <Col span={4}><Statistic title="总目标" value={qProg.data?.total ?? '-'} /></Col>
          <Col span={4}><Statistic title="已完成" value={qProg.data?.done ?? 0} /></Col>
          <Col span={4}><Statistic title="失败" value={qProg.data?.failed ?? 0} /></Col>
          <Col span={4}><Statistic title="执行中" value={qProg.data?.running ?? 0} /></Col>
          <Col span={4}><Statistic title="已规划" value={qProg.data?.planned ?? 0} /></Col>
          <Col span={4}><Statistic title="待处理" value={qProg.data?.pending ?? 0} /></Col>
        </Row>
      </Card>

      {/* 任务详情 */}
      <Card
        title="任务概览"
        style={{ marginBottom: 12 }}
        extra={
          <Space>
            <Button onClick={() => qTask.refetch()}>刷新详情</Button>
            <Button onClick={() => qTargets.refetch()}>刷新目标</Button>
            <Button loading={mPlan.isPending} onClick={() => Modal.confirm({ title: '确认规划任务？', onOk: () => mPlan.mutate() })}>规划</Button>
            <Button type="primary" loading={mExec.isPending} onClick={() => Modal.confirm({ title: '确认执行任务？', onOk: () => mExec.mutate() })}>执行</Button>
            <Button disabled={!selectedRowKeys.length} loading={mRetrySelected.isPending}
              onClick={() => Modal.confirm({ title: `确认对选中 ${selectedRowKeys.length} 条重试？`, onOk: () => mRetrySelected.mutate() })}>
              重试选中
            </Button>
            <Button onClick={() => nav('/tasks')}>返回列表</Button>
          </Space>
        }
      >
        {qTask.isError && <Alert type="error" message="加载任务失败" style={{ marginBottom: 12 }} />}
        <Descriptions column={2} size="small">
          <Descriptions.Item label="任务ID">{fmt(qTask.data?.id)}</Descriptions.Item>
          <Descriptions.Item label="任务号">{fmt(qTask.data?.task_no)}</Descriptions.Item>
          <Descriptions.Item label="名称">{fmt(qTask.data?.name)}</Descriptions.Item>
          <Descriptions.Item label="状态">{statusTag(qTask.data?.status)}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{fmt(qTask.data?.created_at)}</Descriptions.Item>
          <Descriptions.Item label="计划时间">{fmt(qTask.data?.scheduled_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 目标列表 */}
      <Card
        title="目标 / 快照"
        extra={
          <Space size={8}>
            <Select
              allowClear
              value={onlyFailed ? undefined : tState}
              disabled={onlyFailed}
              placeholder="按状态过滤"
              style={{ width: 160 }}
              onChange={(v) => { setTState(v); setOnlyFailed(false); setPage(1) }}
              options={[
                { value: 'INIT', label: '初始化' },
                { value: 'READY', label: '就绪' },
                { value: 'PLANNED', label: '已规划' },
                { value: 'RUNNING', label: '执行中' },
                { value: 'DONE', label: '已完成' },
                { value: 'FAILED', label: '失败' },
              ]}
            />
            <Space size={4}>
              <span style={{ color:'#999' }}>只看失败</span>
              <Switch checked={onlyFailed} onChange={(v)=>{ setOnlyFailed(v); setPage(1) }} />
            </Space>
            <Button onClick={() => { setTState(undefined); setOnlyFailed(false); setPage(1) }}>清筛</Button>
          </Space>
        }
      >
        {qTargets.isError && <Alert type="error" message="加载目标失败" style={{ marginBottom: 12 }} />}
        <Table
          rowKey={getRowKey}
          dataSource={qTargets.data?.items || []}
          columns={columns as any}
          loading={qTargets.isLoading}
          pagination={{
            current: page,
            pageSize: size,
            total: qTargets.data?.total || 0,
            showSizeChanger: true,
            onChange: (p, s) => { setPage(p); setSize(s || 20) },
          }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys, rows) => { setSelectedRowKeys(keys); setSelectedRows(rows) },
          }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}
