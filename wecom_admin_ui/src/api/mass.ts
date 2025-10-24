import { http } from '@/api/http'

export type Page<T = any> = { items: T[]; total: number; page: number; size: number }

type ListParams = {
  page?: number
  size?: number
  q?: string
  status?: string // enum name e.g. 'READY'
  from?: string
  to?: string
  status_code?: number // backend alt
}

type TargetsParams = {
  page?: number
  size?: number
  state?: string
  state_code?: number
}

const KEY_TO_CODE: Record<string, number> = { INIT:0, READY:1, PLANNED:2, RUNNING:3, DONE:4, FAILED:5 }

const clean = (obj: Record<string, any>) =>
  Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined && v !== null && v !== ''))

export function unwrap<T = any>(x: any): T {
  if (x && typeof x === 'object' && 'data' in x) return (x as any).data as T
  return x as T
}

// listTasks
export async function listTasks(params: ListParams) {
  const p: any = { ...params }
  if (p.status) {
    const code = KEY_TO_CODE[String(p.status).toUpperCase()]
    if (code !== undefined) p.status_code = code
  }
  const res = await http.get('/mass/tasks', { params: clean(p) })
  return unwrap<Page<any>>(res.data)
}

// getTask with fallback
export async function getTask(id: string | number) {
  try {
    const r = await http.get(`/mass/tasks/${id}`)
    return unwrap<any>(r.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  const r2 = await http.get(`/mass/task/${id}`)
  return unwrap<any>(r2.data)
}

// createTask
export async function createTask(body: any) {
  const r = await http.post('/mass/tasks', body)
  return unwrap<any>(r.data)
}

// planTask/executeTask
export async function planTask(id: string | number) {
  const r = await http.post(`/mass/tasks/${id}/plan`)
  return unwrap<any>(r.data)
}

export async function executeTask(id: string | number) {
  const r = await http.post(`/mass/tasks/${id}/execute`)
  return unwrap<any>(r.data)
}

// listTargets multipath
export async function listTargets(id: string | number, params: TargetsParams = {}) {
  const p: any = { ...params }
  if (p.state) {
    const code = KEY_TO_CODE[String(p.state).toUpperCase()]
    if (code !== undefined) p.state_code = code
  }
  try {
    const r = await http.get(`/mass/tasks/${id}/targets`, { params: clean(p) })
    return unwrap<Page<any>>(r.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  try {
    const r2 = await http.get(`/mass/tasks/${id}/snapshot`, { params: clean(p) })
    return unwrap<Page<any>>(r2.data)
  } catch (e2: any) {
    if (e2?.response?.status !== 404) throw e2
  }
  const r3 = await http.get('/mass/targets', { params: clean({ ...p, task_id: id }) })
  return unwrap<Page<any>>(r3.data)
}

// retryFailed task-level
export async function retryFailed(id: string | number) {
  try {
    const r = await http.post(`/mass/tasks/${id}/retry_failed`)
    return unwrap<any>(r.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  const r2 = await http.post(`/mass/tasks/${id}/retry`)
  return unwrap<any>(r2.data)
}

// helper types
type PageMeta = { items?: any[]; total?: number; page?: number; size?: number }

// internal
async function fetchTargetsTotal(id: string | number, state?: string) {
  const params: any = { page: 1, size: 1 }
  if (state) params.state = state
  const code = state ? KEY_TO_CODE[String(state).toUpperCase()] : undefined
  if (code !== undefined) params.state_code = code

  try {
    const r1 = await http.get(`/mass/tasks/${id}/targets`, { params })
    const d1 = unwrap<PageMeta>(r1.data)
    return d1?.total ?? 0
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  try {
    const r2 = await http.get(`/mass/tasks/${id}/snapshot`, { params })
    const d2 = unwrap<PageMeta>(r2.data)
    return d2?.total ?? 0
  } catch (e2: any) {
    if (e2?.response?.status !== 404) throw e2
  }
  const r3 = await http.get('/mass/targets', { params: { ...params, task_id: id } })
  const d3 = unwrap<PageMeta>(r3.data)
  return d3?.total ?? 0
}

export async function getTaskProgress(id: string | number) {
  const [total, done, failed, running, planned] = await Promise.all([
    fetchTargetsTotal(id, undefined),
    fetchTargetsTotal(id, 'DONE'),
    fetchTargetsTotal(id, 'FAILED'),
    fetchTargetsTotal(id, 'RUNNING'),
    fetchTargetsTotal(id, 'PLANNED'),
  ])
  const pending = Math.max(0, (total || 0) - ((done || 0) + (failed || 0) + (running || 0) + (planned || 0)))
  return { total, done, failed, running, planned, pending }
}

// single target retry
export async function retryTarget(id: string | number) {
  try {
    const r = await http.post(`/mass/targets/${id}/retry`)
    return unwrap<any>(r.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  const r2 = await http.post('/mass/targets/retry', { target_ids: [id] })
  return unwrap<any>(r2.data)
}

// batch targets retry
export async function retryTargets(taskId: string | number, targetIds: Array<string | number>) {
  try {
    const r = await http.post(`/mass/tasks/${taskId}/retry_targets`, { target_ids: targetIds })
    return unwrap<any>(r.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
  }
  try {
    const r2 = await http.post('/mass/targets/retry', { task_id: taskId, target_ids: targetIds })
    return unwrap<any>(r2.data)
  } catch (e2: any) {
    const items: any[] = []
    for (const id of targetIds) {
      try {
        const d = await retryTarget(id)
        items.push({ id, ok: true, data: d })
      } catch (err: any) {
        items.push({ id, ok: false, error: err?.message || 'retry failed' })
      }
    }
    return { items }
  }
}
