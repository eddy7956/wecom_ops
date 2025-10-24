// src/pages/Planning.tsx
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Card, Space, Select, Switch, Button, Upload, message, Alert, Statistic, Divider, Typography } from 'antd'
import { UploadOutlined, CalculatorOutlined, CheckCircleOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { getPlanningMeta, estimateTargets, type TargetsSpec } from '@/api/planning'
import { uploadMobileList } from '@/api/media'

const { Text } = Typography

export default function Planning() {
  const nav = useNavigate()
  const [tagIds, setTagIds] = useState<string[]>([])
  const [owners, setOwners] = useState<string[]>([])
  const [hasU, setHasU] = useState(false)
  const [uploadId, setUploadId] = useState<number | undefined>(undefined)
  const [uploadSummary, setUploadSummary] = useState<{total?:number; valid?:number; invalid?:number}>({})
  const [mode, setMode] = useState<'FILTER' | 'UPLOAD' | 'MIXED'>('FILTER')
  const [est, setEst] = useState<{ total?: number; by?: Record<string, number> }>({})

  const qMeta = useQuery({
    queryKey: ['planning-meta'],
    queryFn: () => getPlanningMeta(),
    staleTime: 5 * 60 * 1000,
  })

  // 组装 targets_spec
  const targetsSpec: TargetsSpec = useMemo(() => {
    const filters = {
      tag_ids: tagIds.length ? tagIds : undefined,
      owner_userids: owners.length ? owners : undefined,
      has_unionid: hasU ? (1 as 1) : undefined,
    }
    if (mode === 'FILTER') return { mode, filters }
    if (mode === 'UPLOAD') return { mode, upload_id: uploadId }
    return { mode: 'MIXED', filters, upload_id: uploadId }
  }, [tagIds, owners, hasU, uploadId, mode])

  // 上传文件
  const mUpload = useMutation({
    mutationFn: async (file: File) => uploadMobileList(file),
    onSuccess: (d) => {
      setUploadId(d?.upload_id)
      setUploadSummary({ total: d?.total, valid: d?.valid, invalid: d?.invalid })
      message.success(`上传成功：共 ${d?.total || 0}，有效 ${d?.valid || 0}`)
      if (mode === 'FILTER') setMode('MIXED')
    },
  })

  const uploadProps: UploadProps = {
    accept: '.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    showUploadList: false,
    beforeUpload: (file) => {
      mUpload.mutate(file)
      return false // 阻止 antd 自己上传，改为我们走接口
    },
  }

  // 覆盖预估
  const mEstimate = useMutation({
    mutationFn: async () => estimateTargets(targetsSpec),
    onSuccess: (d) => setEst(d || {}),
  })

  useEffect(() => { setEst({}) }, [targetsSpec.mode, tagIds, owners, hasU, uploadId])

  return (
    <div>
      <Card title="规划：选择目标人群" extra={<Space>
        <Button onClick={()=>setMode('FILTER')} type={mode==='FILTER'?'primary':'default'}>仅筛选</Button>
        <Button onClick={()=>setMode('UPLOAD')} type={mode==='UPLOAD'?'primary':'default'} disabled={!uploadId}>仅名单</Button>
        <Button onClick={()=>setMode('MIXED')} type={mode==='MIXED'?'primary':'default'} disabled={!uploadId && !tagIds.length && !owners.length && !hasU}>混合模式</Button>
      </Space>}>
        {qMeta.isError && <Alert type="error" message="加载筛选项失败" style={{marginBottom:12}} />}
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Space wrap>
            <Select
              mode="multiple" allowClear placeholder="标签（可多选）" style={{ minWidth: 320 }}
              options={(qMeta.data?.tags || []).map((t:any)=>({ value: t.id || t.tag_id, label: t.name }))}
              value={tagIds} onChange={setTagIds}
            />
            <Select
              mode="multiple" allowClear placeholder="跟进人（可多选）" style={{ minWidth: 280 }}
              options={(qMeta.data?.owners || []).map((o:any)=>({ value: o.userid, label: o.name || o.userid }))}
              value={owners} onChange={setOwners}
            />
            <Space>
              <Text type="secondary">仅含 unionid</Text>
              <Switch checked={hasU} onChange={setHasU} />
            </Space>
          </Space>

          <Divider style={{ margin: '8px 0' }} />

          <Space wrap>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />} loading={mUpload.isPending}>上传手机号名单（CSV/XLSX）</Button>
            </Upload>
            {uploadId && <Text>upload_id: <Text code>{uploadId}</Text></Text>}
            {uploadSummary?.total !== undefined && (
              <Space>
                <Text type="secondary">导入统计：</Text>
                <Text>共 <b>{uploadSummary.total}</b></Text>
                <Text>有效 <b>{uploadSummary.valid}</b></Text>
                <Text>无效 <b>{uploadSummary.invalid}</b></Text>
              </Space>
            )}
          </Space>

          <Divider style={{ margin: '8px 0' }} />

          <Space>
            <Button type="primary" icon={<CalculatorOutlined />} onClick={()=>mEstimate.mutate()} loading={mEstimate.isPending}>
              预估覆盖人数
            </Button>
            <Button icon={<CheckCircleOutlined />} disabled={!est?.total} onClick={()=>{
              // Part 2 会在“创建任务”页读取这个草案，这里先临时存一下
              sessionStorage.setItem('targets_spec_draft', JSON.stringify(targetsSpec))
              message.success('已保存人群草案，下一步前往“创建任务”页')
              nav('/tasks/new')
            }}>
              下一步：去创建任务
            </Button>
          </Space>

          {mEstimate.isError && <Alert type="error" message="预估失败" />}

          {!!est?.total && (
            <Card size="small" title="预估结果" style={{ maxWidth: 520 }}>
              <Statistic title="覆盖总数" value={est.total} />
              {est.by && <div style={{marginTop:8}}>
                {Object.entries(est.by).map(([k,v])=>(
                  <div key={k} style={{display:'flex', justifyContent:'space-between'}}><Text type="secondary">{k}</Text><Text>{v as number}</Text></div>
                ))}
              </div>}
            </Card>
          )}
        </Space>
      </Card>
    </div>
  )
}
