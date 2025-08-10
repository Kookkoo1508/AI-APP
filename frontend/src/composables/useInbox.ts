import { ref } from 'vue'
import { api } from '@/services/api'

export type Task = {
  id: number
  owner_id: number
  title: string
  notes?: string
  is_done: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

const tasks = ref<Task[]>([])
const archive = ref<Task[]>([])
const loading = ref(false)

export function useInbox() {
  async function fetchTasks() {
    loading.value = true
    try {
      const { data } = await api.get('/inbox/tasks')
      tasks.value = data.items
    } finally { loading.value = false }
  }

  async function fetchArchive() {
    const { data } = await api.get('/inbox/archive')
    archive.value = data.items
  }

  async function createTask(title: string, notes?: string) {
    const { data } = await api.post('/inbox/tasks', { title, notes })
    tasks.value.unshift(data.item)
  }

  async function updateTask(id: number, patch: Partial<Pick<Task,'title'|'notes'|'is_done'>>) {
    const { data } = await api.patch(`/inbox/tasks/${id}`, patch)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) tasks.value[idx] = data.item
  }

  async function archiveTask(id: number) {
    const { data } = await api.post(`/inbox/tasks/${id}/archive`)
    tasks.value = tasks.value.filter(t => t.id !== id)
    archive.value.unshift(data.item)
  }

  return { tasks, archive, loading, fetchTasks, fetchArchive, createTask, updateTask, archiveTask }
}
