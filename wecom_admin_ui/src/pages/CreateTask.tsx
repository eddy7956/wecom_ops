import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  Card, Form, Input, InputNumber, Select, DatePicker,
  Button, Space, message, Upload, Divider
} from 'antd'
import type { UploadFile } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { createTask } from '@/api/mass'

// 保留并使用原有任务号生成器（位置在 import 下方）
function genTaskNo(prefix = 'WEB') {
  const ts = Date.now().toString()
  const r3 = Math.floor(Math.random() * 1000).toString().padStart(3, '0')
  return `${prefix}-${ts}-${r3}`
}

type ContentItem = {
  type: 'text' | 'image' | 'miniprogram'
  // text
  text?: string
  // image
  title?: string
  media_id?: string
  url?: string
  // miniprogram
  appid?: string
  pagepath?: string
  thumb_media_id?: string
  thumb_url?: string
}

// FormValues 类型添加 task_no 字段（可选，用于接收用户输入）
type FormValues = {
  name: string
  task_no?: string // ★ 新增：任务号字段
  mass_type?: number | string
  content_type?: number | string
  qps_limit?: number
  concurrency_limit?: number
  batch_size?: number
  scheduled_at?: dayjs.Dayjs
  contents?: ContentItem[]
}

const uploadAction = (import.meta as any)?.env?.VITE_UPLOAD_API || '/api/v1/media/upload'
const contentTypeMap: Record<ContentItem['type'], number> = { text: 1, image: 2, miniprogram: 3 }

function clean(obj: Record<string, any>) {
  const out: Record<string, any> = {}
  Object.entries(obj).forEach(([k, v]) => {
    if (v === undefined || v === null) return
    if (typeof v === 'string' && v.trim() === '') return
    out[k] = v
  })
  return out
}

export default function CreateTask() {
  const nav = useNavigate()
  const [form] = Form.useForm<FormValues>()

  const mCreate = useMutation({
    mutationFn: async (values: FormValues) => {
      const contents = (values.contents || []).map((it) => {
        if (it.type === 'text') {
          return clean({ type: 'text', text: it.text })
        }
        if (it.type === 'image') {
          return clean({
            type: 'image',
            title: it.title,
            media_id: it.media_id,
            url: it.url,
          })
        }
        // miniprogram
        return clean({
          type: 'miniprogram',
          title: it.title,
          appid: it.appid,
          pagepath: it.pagepath,
          thumb_media_id: it.thumb_media_id,
          thumb_url: it.thumb_url,
        })
      })

      // ★ 新增：处理任务号（优先用户输入，无输入则自动生成）
      const taskNoFromUser = values.task_no?.trim()
      const task_no = taskNoFromUser || genTaskNo('WEB')

      // ★ 新增：处理计划时间的多格式输出（兼容后端需求）
      const scheduledAt = values.scheduled_at
      const schedStr = scheduledAt?.format('YYYY-MM-DD HH:mm:ss') // 原格式
      const schedIso = scheduledAt?.toISOString() // ISO 格式
      const schedTs = scheduledAt?.valueOf() // 时间戳（毫秒）

      // ★ 新增：处理单文本兼容字段（向后兼容老后端）
      const singleText = contents.length === 1 && contents[0].type === 'text' 
        ? contents[0].text?.trim() 
        : undefined

      // 构造 payload（新增 task_no、scheduled_at_iso、scheduled_time、content_text）
      const payload = clean({
        task_no, // ★ 新增：任务号（自动生成/用户输入）
        name: values.name,
        mass_type: values.mass_type,                 // 1=企业群发 2=客户群群发（按你后端）
        content_type: values.content_type
          ?? (contents[0] ? contentTypeMap[contents[0].type as ContentItem['type']] : undefined),
        qps_limit: values.qps_limit,
        concurrency_limit: values.concurrency_limit,
        batch_size: values.batch_size,
        scheduled_at: schedStr,          // 原计划时间格式
        scheduled_at_iso: schedIso,      // ★ 新增：ISO 格式时间
        scheduled_time: schedTs,         // ★ 新增：时间戳
        contents: contents.length ? contents : undefined,
        content_text: singleText,        // ★ 新增：单文本兼容字段
      })

      return createTask(payload)
    },
    onSuccess: (data: any) => {
      message.success('创建成功')
      nav('/tasks')
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.message || e?.message || '创建失败'
      message.error(msg)
    },
  })

  return (
    <Card title="创建任务" style={{ maxWidth: 1000 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={(v) => mCreate.mutate(v as FormValues)}
        initialValues={{
          qps_limit: 300, concurrency_limit: 20, batch_size: 300,
          contents: [{ type: 'text' }],   // 默认一条文本
        }}
      >
        {/* 任务名称 */}
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
          <Input placeholder="例如：国庆节活动群发 A1" />
        </Form.Item>

        {/* ★ 新增：任务号输入项（可选，位于任务名称下方） */}
        <Form.Item 
          name="task_no" 
          label="任务号（可留空，自动生成）" 
          tooltip="不填将自动生成，后端也可二次覆盖"
        >
          <Input placeholder="例如：WEB-1759024414849-123" />
        </Form.Item>

        <Space size={16} wrap>
          <Form.Item name="mass_type" label="任务类型" style={{ minWidth: 220 }}>
            <Select
              allowClear
              options={[
                { value: 1, label: '企业群发' },
                { value: 2, label: '客户群群发' },
              ]}
            />
          </Form.Item>
          <Form.Item name="content_type" label="内容类型（可留空，随首条内容推断）" style={{ minWidth: 320 }}>
            <Select
              allowClear
              options={[
                { value: 1, label: '文本' },
                { value: 2, label: '图文' },
                { value: 3, label: '小程序' },
              ]}
            />
          </Form.Item>
          <Form.Item name="scheduled_at" label="计划时间" tooltip="不选则立即任务">
            <DatePicker showTime />
          </Form.Item>
        </Space>

        <Space size={16} wrap>
          <Form.Item name="qps_limit" label="QPS 限速"><InputNumber min={1} max={2000} /></Form.Item>
          <Form.Item name="concurrency_limit" label="并发数"><InputNumber min={1} max={200} /></Form.Item>
          <Form.Item name="batch_size" label="批大小"><InputNumber min={1} max={5000} /></Form.Item>
        </Space>

        <Divider>内容列表（可添加多条）</Divider>

        <Form.List name="contents">
          {(fields, { add, remove }) => (
            <>
              {fields.map((field, idx) => (
                <Card
                  key={field.key}
                  size="small"
                  style={{ marginBottom: 12 }}
                  title={`内容 #${idx + 1}`}
                  extra={
                    <Button
                      danger size="small" icon={<DeleteOutlined />}
                      onClick={() => remove(field.name)}
                    >删除</Button>
                  }
                >
                  <Form.Item
                    name={[field.name, 'type']}
                    label="类型"
                    rules={[{ required: true, message: '请选择类型' }]}
                  >
                    <Select
                      options={[
                        { value: 'text', label: '文本' },
                        { value: 'image', label: '图文' },
                        { value: 'miniprogram', label: '小程序' },
                      ]}
                      style={{ width: 200 }}
                    />
                  </Form.Item>

                  {/* 按类型动态渲染字段 */}
                  <Form.Item noStyle shouldUpdate>
                    {() => {
                      const t: ContentItem['type'] = form.getFieldValue(['contents', field.name, 'type'])
                      if (t === 'text') {
                        return (
                          <Form.Item
                            name={[field.name, 'text']}
                            label="文本内容"
                            rules={[{ required: true, message: '请输入文本内容' }]}
                          >
                            <Input.TextArea rows={4} placeholder="示例：亲爱的客户，国庆活动已上线..." />
                          </Form.Item>
                        )
                      }
                      if (t === 'image') {
                        return (
                          <>
                            <Form.Item name={[field.name, 'title']} label="标题">
                              <Input placeholder="图文消息标题（可选）" />
                            </Form.Item>

                            <Space size={16} wrap>
                              <Form.Item name={[field.name, 'media_id']} label="图片 media_id">
                                <Input placeholder="已有 media_id 可直接填" style={{ width: 260 }} />
                              </Form.Item>
                              <Form.Item name={[field.name, 'url']} label="图片 URL">
                                <Input placeholder="或填写图片直链 URL" style={{ width: 360 }} />
                              </Form.Item>
                            </Space>

                            <Form.Item
                              label="上传图片（可选）"
                              valuePropName="fileList"
                              getValueFromEvent={(e) => e?.fileList as UploadFile[]}
                            >
                              <Upload.Dragger
                                name="file"
                                action={uploadAction}
                                maxCount={1}
                                onChange={(info) => {
                                  const f = info.file
                                  if (f.status === 'done') {
                                    const resp: any = f.response || {}
                                    const d = resp.data ?? resp
                                    const mediaId = d?.media_id || d?.mediaId
                                    const url = d?.url || d?.pic_url || d?.download_url
                                    const patch: any = {}
                                    if (mediaId) patch.media_id = mediaId
                                    if (url) patch.url = url
                                    if (Object.keys(patch).length) {
                                      const cur = form.getFieldValue('contents') || []
                                      cur[field.name] = { ...cur[field.name], ...patch }
                                      form.setFieldsValue({ contents: cur })
                                    }
                                    message.success('上传成功')
                                  } else if (f.status === 'error') {
                                    message.error('上传失败')
                                  }
                                }}
                              >
                                <p>点击或拖拽上传（成功后自动填写 media_id / URL）</p>
                              </Upload.Dragger>
                            </Form.Item>
                          </>
                        )
                      }
                      if (t === 'miniprogram') {
                        return (
                          <>
                            <Form.Item name={[field.name, 'title']} label="标题">
                              <Input placeholder="小程序卡片标题（可选）" />
                            </Form.Item>

                            <Space size={16} wrap>
                              <Form.Item
                                name={[field.name, 'appid']}
                                label="AppID"
                                rules={[{ required: true, message: '请输入 AppID' }]}
                              >
                                <Input style={{ width: 260 }} />
                              </Form.Item>
                              <Form.Item
                                name={[field.name, 'pagepath']}
                                label="路径"
                                rules={[{ required: true, message: '请输入路径' }]}
                              >
                                <Input placeholder="pages/home/index?foo=bar" style={{ width: 360 }} />
                              </Form.Item>
                            </Space>

                            <Space size={16} wrap>
                              <Form.Item name={[field.name, 'thumb_media_id']} label="封面 media_id">
                                <Input style={{ width: 260 }} />
                              </Form.Item>
                              <Form.Item name={[field.name, 'thumb_url']} label="封面 URL">
                                <Input style={{ width: 360 }} />
                              </Form.Item>
                            </Space>
                          </>
                        )
                      }
                      return null
                    }}
                  </Form.Item>
                </Card>
              ))}

              <Button type="dashed" icon={<PlusOutlined />} onClick={() => {
                const cur = form.getFieldValue('contents') || []
                form.setFieldsValue({ contents: [...cur, { type: 'text' }] })
              }}>
                添加内容
              </Button>
            </>
          )}
        </Form.List>

        <Divider />
        <Space>
          <Button type="primary" htmlType="submit" loading={mCreate.isPending}>创建</Button>
          <Button onClick={() => nav('/tasks')}>取消</Button>
        </Space>
      </Form>
    </Card>
  )
}