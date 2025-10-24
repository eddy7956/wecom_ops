import { useQuery } from '@tanstack/react-query'
import { Card, Descriptions, Alert, Spin, Button } from 'antd'
import { getHealth, type HealthResp } from '@/api/health'

export default function HealthPage() {
  const q = useQuery<HealthResp>({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 10000 })
  if (q.isLoading) return <Spin tip="健康检查：加载中..." />
  if (q.isError) {
    return <Alert type="error" message="健康检查失败" description={(q.error as Error)?.message || '未知错误'}
      action={<Button onClick={() => q.refetch()}>重试</Button>} />
  }
  const d = q.data ?? ({} as HealthResp)
  return (
    <Card title="后端健康">
      <Descriptions column={1} size="small">
        <Descriptions.Item label="状态">{d.status ?? (d.ok ? 'OK' : 'UNKNOWN')}</Descriptions.Item>
        <Descriptions.Item label="TraceID">{d.trace_id ?? '-'}</Descriptions.Item>
        {d.version && <Descriptions.Item label="版本">{d.version}</Descriptions.Item>}
        {d.now && <Descriptions.Item label="时间">{d.now}</Descriptions.Item>}
      </Descriptions>
      <Button style={{ marginTop: 12 }} onClick={() => q.refetch()}>立即刷新</Button>
    </Card>
  )
}
