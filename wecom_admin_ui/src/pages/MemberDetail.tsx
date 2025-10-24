// src/pages/MemberDetail.tsx
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Descriptions, Tag, Card } from 'antd'
import dayjs from 'dayjs'
import { getMemberDetail, type MemberDetail } from '@/api/members'

export default function MemberDetail() {
  const { external_userid } = useParams<{ external_userid: string }>()
  const q = useQuery({
    queryKey: ['member-detail', external_userid],
    queryFn: () => getMemberDetail(external_userid || '', true),
    enabled: !!external_userid,
  })

  const m: MemberDetail = (q.data as any) || ({} as MemberDetail)

  return (
    <div style={{ padding: 16 }}>
      <Card title={`会员详情：${m.vip_name || m.name || m.external_userid || ''}`}>
        <Descriptions bordered column={2} size="middle">
          <Descriptions.Item label="外部联系人ID" span={2}>
            {m.external_userid || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="UnionID">{m.unionid || '-'}</Descriptions.Item>
          <Descriptions.Item label="CRM用户ID">{m.crm_user_id ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="VIP姓名">{m.vip_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="企微名">{m.name || '-'}</Descriptions.Item>
          <Descriptions.Item label="手机号">{m.mobile || '-'}</Descriptions.Item>
          <Descriptions.Item label="品牌">{m.department_brand || '-'}</Descriptions.Item>
          <Descriptions.Item label="门店">{m.store_name || m.store_code || '-'}</Descriptions.Item>
          <Descriptions.Item label="跟进人">{m.owner_name || m.owner_userid || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {m.created_at ? dayjs(m.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {m.updated_at ? dayjs(m.updated_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>

          <Descriptions.Item label="标签" span={2}>
            {Array.isArray(m.tags) && m.tags.length ? (
              (m.tags as any[]).map((t, i) => <Tag key={i}>{t.tag_name || t.tag_id || t}</Tag>)
            ) : (
              <>-</>
            )}
          </Descriptions.Item>

          <Descriptions.Item label="原始企微明细（ext_detail）" span={2}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {m.ext_detail ? JSON.stringify(m.ext_detail, null, 2) : '-'}
            </pre>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}
