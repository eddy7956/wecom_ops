// src/api/ext.ts
import { http } from '@/api/http'
const pickData = (x: any) => (x && typeof x === 'object' && 'data' in x ? x.data : x)

/** 外部联系人标签列表（不分页或由后端自行返回全量） */
export async function listExtTags() {
  const path = import.meta.env.VITE_EXT_TAGS || '/ext/tags'
  const r = await http.get(path)
  const d = pickData(r.data) || []
  // 兼容后端返回 {tag_id,name} 或 {id,name}
  return (Array.isArray(d) ? d : d.items || []).map((t: any) => ({
    id: t.id ?? t.tag_id,
    name: t.name ?? String(t.id ?? t.tag_id ?? ''),
  }))
}
