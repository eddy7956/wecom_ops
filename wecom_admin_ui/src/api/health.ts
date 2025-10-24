import { http } from '@/api/http'

export type HealthResp = {
  ok: boolean
  status?: string
  version?: string
  now?: string
  trace_id?: string
  error?: string
}

/** 健康检查：仅用 /mass/tasks 探针，避免 /health 404 */
export async function getHealth(): Promise<HealthResp> {
  try {
    await http.get('/mass/tasks', { params: { page: 1, size: 1 } })
    return { ok: true, status: 'OK', now: new Date().toISOString() }
  } catch (e: any) {
    return { ok: false, status: 'DOWN', now: new Date().toISOString(), error: e?.message || 'unreachable' }
  }
}
