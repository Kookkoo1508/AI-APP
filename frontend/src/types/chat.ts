// src/types/chat.ts

// role ที่ UI รองรับ
export type Role = 'user' | 'assistant' | 'system'

// รูปแบบที่ API ส่งมา (DTO)
export interface ApiMsgDTO {
  id: number
  role: string           // จาก backend เป็น string
  content: string
  created_at: string
}

// รูปแบบที่ UI ใช้จริง (View model)
export interface ChatMsg {
  id: number
  role: Role             // ให้เป็น Role ที่เรากำหนดเอง
  content: string
  ts: number             // แปลงเวลาเป็น timestamp ไว้ใช้ง่าย
}
