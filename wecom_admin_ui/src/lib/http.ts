const API_BASE = '/api/v1';

async function request<T=any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers||{}) },
    ...init,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const msg = data?.error?.message || data?.error || res.statusText;
    throw new Error(msg || 'Request failed');
  }
  return data;
}

export const api = {
  listTasks: (page=1, size=10, q='') => request(`/mass/tasks?page=${page}&size=${size}&q=${encodeURIComponent(q)}`),
  createTask: (payload:any) => request(`/mass/tasks`, { method:'POST', body: JSON.stringify(payload) }),
  getTask:   (id:number) => request(`/mass/tasks/${id}`),
  planTask:  (id:number) => request(`/mass/tasks/${id}/plan`, { method:'POST' }),
  listTargets: (id:number, state='pending', page=1, size=10) =>
    request(`/mass/tasks/${id}/targets?state=${encodeURIComponent(state)}&page=${page}&size=${size}`),
  listLogs: (id:number, page=1, size=20) =>
    request(`/mass/tasks/${id}/logs?page=${page}&size=${size}`),
}
