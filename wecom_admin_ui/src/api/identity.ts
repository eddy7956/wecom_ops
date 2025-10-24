// src/api/identity.ts
import { http } from '@/api/http'
const pickData = (x: any) => (x && typeof x === 'object' && 'data' in x ? x.data : x)

export async function resolveMobiles(mobiles: string[]) {
  const path = import.meta.env.VITE_IDENTITY_RESOLVE_MOB || '/identity/resolve-mobiles'
  const r = await http.post(path, { mobiles })
  return pickData(r.data) // { mapped: [...], unmatched: [...] }
}
