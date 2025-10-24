// src/pages/MembersList.tsx
import { useQuery } from '@tanstack/react-query'
import { listMembers, estimateMembers, getMembersMeta, type Member, type ListParams } from '@/api/members'
import { Table, Input, Button, Space, Tag, Select, Row, Col, Statistic, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const { Search } = Input

export default function MembersList() {
  const nav = useNavigate()

  // 过滤器：契约字段
  const [filters, setFilters] = useState<Partial<ListParams>>({
    q: '',
    owner_userids: [],
    tag_ids: [],
    store_codes: [],
    brands: [],
  })
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)
  const [estTotal, setEstTotal] = useState<number | null>(null)

  // 元数据（筛选项）
  const qMeta = useQuery({
    queryKey: ['members-meta'],
    queryFn: () => getMembersMeta({ only: ['owners', 'tags'], page: 1, size: 200 }),
    staleTime: 5 * 60 * 1000,
  })

  // 列表
  const qList = useQuery({
    queryKey: ['members', page, size, JSON.stringify(filters)],
    queryFn: () => listMembers({ page, size, ...filters }),
  })

  // 估算（和 list 同过滤项，GET）
  const doEstimate = async () => {
    try {
      const total = await estimateMembers({
        q: filters.q,
        owner_userids: filters.owner_userids,
        tag_ids: filters.tag_ids,
        store_codes: filters.store_codes,
        brands: filters.brands,
      })
      setEstTotal(total)
    } catch (e: any) {
      message.error(e?.message || '估算失败')
    }
  }

  useEffect(() => {
    // 过滤变化时自动估计一次
    doEstimate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)])

  const columns = useMemo(
    () => [
      { title: '外部联系人ID', dataIndex: 'external_userid', width: 280, ellipsis: true },
      { title: 'VIP姓名', dataIndex: 'vip_name', width: 120 },
      { title: '企微名', dataIndex: 'name', width: 120 },
      { title: '手机号', dataIndex: 'mobile', width: 140 },
      { title: '品牌', dataIndex: 'department_brand', width: 120 },
      { title: '门店', dataIndex: 'store_name', width: 160 },
      { title: '跟进人', dataIndex: 'owner_name', width: 120 },
      {
        title: '标签',
        dataIndex: 'tags',
        render: (arr: any) =>
          Array.isArray(arr) && arr.length ? (
            <Space wrap>
              {arr.map((name: string, i: number) => (
                <Tag key={i}>{name}</Tag>
              ))}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        title: '操作',
        width: 120,
        render: (_: any, r: Member) => (
          <Space>
            <Button size="small" onClick={() => nav(`/members/${r.external_userid}`)}>
              详情
            </Button>
          </Space>
        ),
      },
    ],
    [nav]
  )

  const owners = (qMeta.data?.owners?.items ?? []).map((o: any) => ({
    label: `${o.owner_userid}（${o.count}）`,
    value: o.owner_userid,
  }))
  const tags = (qMeta.data?.tags?.items ?? []).map((t: any) => ({
    label: `${t.tag_name || t.tag_id}（${t.members ?? 0}）`,
    value: t.tag_id || t.tag_name,
  }))

  return (
    <div style={{ padding: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 筛选行 */}
        <Row gutter={[12, 12]}>
          <Col flex="280px">
            <Search
              placeholder="姓名/手机号/跟进人/门店/品牌（模糊）"
              allowClear
              onSearch={(v) => {
                setPage(1)
                setFilters((s) => ({ ...s, q: v || '' }))
              }}
            />
          </Col>
          <Col flex="320px">
            <Select
              mode="multiple"
              allowClear
              placeholder="选择跟进人"
              style={{ width: '100%' }}
              options={owners}
              value={filters.owner_userids as string[]}
              onChange={(v) => {
                setPage(1)
                setFilters((s) => ({ ...s, owner_userids: v }))
              }}
            />
          </Col>
          <Col flex="380px">
            <Select
              mode="multiple"
              allowClear
              placeholder="选择标签"
              style={{ width: '100%' }}
              options={tags}
              value={filters.tag_ids as string[]}
              onChange={(v) => {
                setPage(1)
                setFilters((s) => ({ ...s, tag_ids: v }))
              }}
            />
          </Col>
          <Col flex="auto">
            <Space>
              <Button onClick={() => setFilters({ q: '', owner_userids: [], tag_ids: [], store_codes: [], brands: [] })}>
                清空
              </Button>
              <Statistic title="覆盖人数（估算）" value={estTotal ?? '-'} />
            </Space>
          </Col>
        </Row>

        {/* 列表 */}
        <Table<Member>
          rowKey="external_userid"
          loading={qList.isLoading}
          dataSource={qList.data?.items ?? []}
          columns={columns as any}
          pagination={{
            current: page,
            pageSize: size,
            total: qList.data?.total ?? 0,
            onChange: (p, s) => {
              setPage(p)
              setSize(s || 20)
            },
          }}
          size="middle"
        />
      </Space>
    </div>
  )
}
