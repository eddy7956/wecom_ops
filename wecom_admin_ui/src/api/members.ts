// src/api/members.ts
import { http } from '@/api/http'

export type ListParams = {
  page?: number
  size?: number
  q?: string
  owner_userids?: string[]        // 多选 -> 逗号分隔
  store_codes?: string[]
  brands?: string[]
  tag_ids?: string[]
}

export type Member = {
  external_userid: string
  unionid?: string | null
  crm_user_id?: number | string | null
  vip_name?: string | null
  mobile?: string | null
  store_code?: string | null
  store_name?: string | null
  department_brand?: string | null
  owner_userid?: string | null
  owner_name?: string | null
  tags?: string[]                 // 列表里就是“标签名”数组
  is_deleted?: 0 | 1
  name?: string | null            // 企微展示名
  avatar?: string | null
  corp_name?: string | null
  created_at?: string
  updated_at?: string
}

export type MemberDetail = Omit<Member, 'tags'> & {
  // 详情页：tag 是对象（含 tag_id / tag_name / group_name）
  tags?: { tag_id: string; tag_name: string; group_name?: string }[]
  ext_detail?: Record<string, any> | null
}

// 通用解包
const unwrap = <T,>(x: any): T => (x && typeof x === 'object' && 'data' in x ? x : { ok: true, data: x }) as T

// 构建查询串（数组转逗号分隔）
const toQS = (obj: Record<string, any>) => {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    if (Array.isArray(v)) {
      if (v.length) p.set(k, v.join(','))
    } else {
      p.set(k, String(v))
    }
  })
  const s = p.toString()
  return s ? `?${s}` : ''
}

type Paged<T> = { ok: boolean; data: { items: T[]; page: number; size: number; total: number } }

export async function listMembers(params: ListParams) {
  const qs = toQS({
    ...params,
    owner_userids: params.owner_userids,
    store_codes: params.store_codes,
    brands: params.brands,
    tag_ids: params.tag_ids,
  })
  const res = await http.get(`/members/list${qs}`)
  return unwrap<Paged<Member>>(res.data).data
}

export async function getMembersMeta(opts?: { only?: ('tags' | 'owners' | 'stores')[]; q?: string; page?: number; size?: number }) {
  const qs = toQS({ ...opts, only: opts?.only?.join(',') })
  const res = await http.get(`/members/meta${qs}`)
  // 结构：{ tags?: {items,page,size,total}, owners?: {...}, stores?: {...} }
  return unwrap<{ ok: boolean; data: any }>(res.data).data
}

export async function estimateMembers(params: Omit<ListParams, 'page' | 'size'>) {
  const qs = toQS({
    ...params,
    owner_userids: params.owner_userids,
    store_codes: params.store_codes,
    brands: params.brands,
    tag_ids: params.tag_ids,
  })
  const res = await http.get(`/members/estimate${qs}`)
  return unwrap<{ ok: boolean; data: { total: number } }>(res.data).data.total ?? 0
}

export async function getMemberDetail(external_userid: string, includeExt = true) {
  const qs = toQS({ external_userid, include: includeExt ? 'ext_detail' : undefined })
  const res = await http.get(`/members/detail${qs}`)
  return unwrap<{ ok: boolean; data: MemberDetail }>(res.data).data
}
