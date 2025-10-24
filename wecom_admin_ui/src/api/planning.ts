// src/api/planning.ts
import { http } from '@/api/http'
import { listExtTags } from '@/api/ext'
import { listEmployees } from '@/api/org'

export type TargetsSpec = {
  mode: 'FILTER' | 'UPLOAD' | 'MIXED'
  filters?: {
    tag_ids?: string[]
    owner_userids?: string[]
    has_unionid?: 0 | 1
  }
  upload_id?: number
}

const pickData = (x: any) => (x && typeof x === 'object' && 'data' in x ? x.data : x)

export async function getPlanningMeta() {
  const [tags, owners] = await Promise.all([
    listExtTags(),
    listEmployees({ page: 1, size: 200 }),
  ])
  return { tags, owners, groups: [] }
}

export async function estimateTargets(spec: TargetsSpec) {
  const path = import.meta.env.VITE_TARGETS_ESTIMATE || '/mass/targets/estimate'
  const r = await http.post(path, spec)
  return pickData(r.data) // { total, by? }
}