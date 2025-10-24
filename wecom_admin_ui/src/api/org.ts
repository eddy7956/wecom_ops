// src/api/org.ts
import { http } from '@/api/http'
const pickData = (x: any) => (x && typeof x === 'object' && 'data' in x ? x.data : x)

export async function listEmployees(params: { q?: string; page?: number; size?: number } = {}) {
  const path = import.meta.env.VITE_ORG_EMPLOYEES || '/org/employees'
  const r = await http.get(path, { params: { page: 1, size: 200, ...params } })
  const d = pickData(r.data) || {}
  const items = Array.isArray(d) ? d : (d.items || [])
  return items.map((u: any) => ({
    userid: u.userid ?? u.id,
    name: u.name ?? u.userid ?? '',
  }))
}
