// src/api/media.ts
import { http } from '@/api/http'

const pickData = (x: any) => (x && typeof x === 'object' && 'data' in x ? x.data : x)

export async function uploadMobileList(file: File) {
  const path = import.meta.env.VITE_MEDIA_UPLOAD || '/media/upload'
  const form = new FormData()
  form.append('type', 'mobile_list')
  form.append('file', file)
  const r = await http.post(path, form, { headers: { 'Content-Type': 'multipart/form-data' } })
  // 返回 { upload_id, total, valid, invalid }
  return pickData(r.data)
}
