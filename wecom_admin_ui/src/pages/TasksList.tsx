import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Table, Input, Button, Space, Tag, Select, DatePicker, message } from 'antd'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { listTasks, planTask, executeTask } from '@/api/mass'
import { useNavigate } from 'react-router-dom'

type Task = {
  id: number | string
  name?: string | null
  task_no?: string
  status?: number | string  // 支持数字或字符串状态
  created_at?: string
  scheduled_at?: string | null
  report_stat?: Record<string, any>
}

type Page<T> = { items: T[]; total: number; page: number; size: number }

// ---------- 小工具 ----------
const fmt = (s?: string | null) => (s ? s : '-')

// 放在文件顶部 utils 区域
const STATUS_META: Record<string, { text: string; color: any }> = {
  INIT:    { text: '初始化', color: 'default' },
  READY:   { text: '就绪',   color: 'processing' },
  PLANNED: { text: '已规划', color: 'cyan' },
  RUNNING: { text: '执行中', color: 'blue' },
  DONE:    { text: '已完成', color: 'success' },
  FAILED:  { text: '失败',   color: 'error' },
}

const CODE_TO_KEY: Record<string, string> = {
  '0': 'INIT',
  '1': 'READY',
  '2': 'PLANNED',
  '3': 'RUNNING',
  '4': 'DONE',
  '5': 'FAILED',
}

const statusLabel = (s: any) => {
  const raw = String(s ?? '')
  const key = (CODE_TO_KEY[raw] || raw).toUpperCase()
  const meta = STATUS_META[key] || { text: String(s ?? '未知'), color: 'default' }
  return <Tag color={meta.color}>{meta.text}</Tag>
}

function toCSV(rows: any[], headers: { key: string; title: string }[]) {
  const esc = (v: any) => {
    const s = v === undefined || v === null ? '' : String(v)
    // 包含逗号/引号/换行时，用双引号包裹，并把内部 " 变成 ""
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const head = headers.map(h => esc(h.title)).join(',')
  const body = rows.map(r => headers.map(h => esc((r as any)[h.key])).join(',')).join('\n')
  return head + '\n' + body
}

function downloadCSV(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------- 组件 ----------
export default function TasksList() {
  const nav = useNavigate()
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)
  const [q, setQ] = useState<string>('')
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)

  const from = range ? range[0].format('YYYY-MM-DD HH:mm:ss') : undefined
  const to = range ? range[1].format('YYYY-MM-DD HH:mm:ss') : undefined

  const qy = useQuery<Page<Task>>({
    queryKey: ['tasks', page, size, q, status, from, to],
    queryFn: () => listTasks({ page, size, q: q || undefined, status, from, to }),
    placeholderData: (prev) => prev, // 相当于 keepPreviousData
    refetchInterval: 10000,          // 10 秒自动刷新
  })

  useEffect(() => {
    setPage(1) // 任一筛选变化回到第 1 页
  }, [q, status, from, to])

  // 规划 / 执行（已存在则沿用）
  const mPlan = useMutation({
    mutationFn: (id: string | number) => planTask(id),
    onSuccess: () => { message.success('已发起规划'); qy.refetch() },
    onError: (e:any) => message.error(e?.message || '规划失败'),
  })
  const mExec = useMutation({
    mutationFn: (id: string | number) => executeTask(id),
    onSuccess: () => { message.success('已发起执行'); qy.refetch() },
    onError: (e:any) => message.error(e?.message || '执行失败'),
  })

  const columns = useMemo(() => {
    return [
      { title: 'ID', dataIndex: 'id', width: 100, fixed: 'left' as const },
      { title: '任务号', dataIndex: 'task_no', width: 220, render: (v: any) => fmt(v) },
      { title: '名称', dataIndex: 'name', width: 240, render: (v: any) => fmt(v) },
      { title: '状态', dataIndex: 'status', width: 120, render: (s: any) => statusLabel(s) },
      { title: '创建时间', dataIndex: 'created_at', width: 200, render: (v: any) => fmt(v) },
      { title: '计划时间', dataIndex: 'scheduled_at', width: 200, render: (v: any) => fmt(v) },
      {
        title: '操作',
        key: 'op',
        width: 220,
        fixed: 'right' as const,
        render: (_: any, r: Task) => (
          <Space>
            <Button size="small" onClick={() => nav(`/tasks/${r.id}`)}>详情</Button>
            <Button size="small" loading={mPlan.isPending} onClick={() => mPlan.mutate(r.id)}>规划</Button>
            <Button size="small" type="primary" loading={mExec.isPending} onClick={() => mExec.mutate(r.id)}>执行</Button>
          </Space>
        ),
      },
    ]
  }, [mPlan.isPending, mExec.isPending, nav])

  async function exportAll() {
    // 拉取当前筛选条件下的“大页”数据（根据你的规模可调大/分批导出）
    const big = await listTasks({ page: 1, size: 10000, q: q || undefined, status, from, to })
    const items: Task[] = (big as any)?.items || []
    const headers = [
      { key: 'id', title: 'ID' },
      { key: 'task_no', title: '任务号' },
      { key: 'name', title: '名称' },
      { key: 'status', title: '状态' },
      { key: 'created_at', title: '创建时间' },
      { key: 'scheduled_at', title: '计划时间' },
    ]
    const rows = items.map(it => {
      // 同步状态渲染逻辑：数字→英文→中文
      const raw = String((it as any).status ?? '')
      const key = (CODE_TO_KEY[raw] || raw).toUpperCase()
      const text = STATUS_META[key]?.text || String((it as any).status ?? '未知')
      return { ...it, status: text }
    })
    const csv = toCSV(rows, headers)
    downloadCSV(csv, `tasks_${Date.now()}.csv`)
  }

  return (
    <div>
      <Space size={8} style={{ marginBottom: 12 }} wrap>
        <Input.Search
          allowClear
          placeholder="按名称/任务号搜索"
          enterButton
          onSearch={(v) => setQ(v)}
          style={{ width: 280 }}
        />
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 160 }}
          value={status as any}
          onChange={(v) => setStatus(v)}
          options={[
            { value: 'INIT',    label: '初始化' },
            { value: 'READY',   label: '就绪' },
            { value: 'PLANNED', label: '已规划' },
            { value: 'RUNNING', label: '执行中' },
            { value: 'DONE',    label: '已完成' },
            { value: 'FAILED',  label: '失败' },
          ]}
        />
        <DatePicker.RangePicker
          showTime
          value={range as any}
          onChange={(v) => setRange(v as any)}
          placeholder={['开始时间', '结束时间']}
        />
        <Button icon={<ReloadOutlined />} onClick={() => qy.refetch()}>刷新</Button>
        <Button icon={<DownloadOutlined />} onClick={exportAll}>导出CSV</Button>
      </Space>

      <Table<Task>
        rowKey="id"
        dataSource={qy.data?.items || []}
        columns={columns as any}
        loading={qy.isLoading}
        pagination={{
          current: page,
          pageSize: size,
          total: qy.data?.total || 0,
          showSizeChanger: true,
          onChange: (p, s) => { setPage(p); setSize(s || 20) },
        }}
        scroll={{ x: 1200 }}
      />
    </div>
  )
}