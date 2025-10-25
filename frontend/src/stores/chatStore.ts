import { create } from 'zustand'
import axios from '@/utils/axios'

export interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  intent?: string
  actions?: any[]
  validation?: any
  isStreaming?: boolean  // 标识是否为流式消息
}

export interface ChatSession {
  session_id: string
  name: string
  created_at: string
  target_url?: string
}

interface ChatState {
  messages: ChatMessage[]
  currentSession: ChatSession | null
  isConnected: boolean
  isLoading: boolean
  websocket: WebSocket | null
  streamingMessageId: string | null  // 当前流式消息的ID
  
  // Actions
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  appendToMessage: (id: string, content: string) => void
  setCurrentSession: (session: ChatSession | null) => void
  setConnected: (connected: boolean) => void
  setLoading: (loading: boolean) => void
  setWebSocket: (ws: WebSocket | null) => void
  setStreamingMessageId: (id: string | null) => void
  
  // API Actions
  createSession: () => Promise<ChatSession | null>
  loadSessions: () => Promise<ChatSession[]>
  sendMessage: (content: string, type?: string) => Promise<void>
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  currentSession: null,
  isConnected: false,
  isLoading: false,
  websocket: null,
  streamingMessageId: null,

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    )
  })),

  appendToMessage: (id, content) => set((state) => ({
    messages: state.messages.map(msg => 
      msg.id === id ? { ...msg, content: msg.content + content } : msg
    )
  })),

  setCurrentSession: (session) => set({ currentSession: session }),

  setConnected: (connected) => set({ isConnected: connected }),

  setLoading: (loading) => set({ isLoading: loading }),

  setWebSocket: (ws) => set({ websocket: ws }),

  setStreamingMessageId: (id) => set({ streamingMessageId: id }),

  createSession: async () => {
    try {
      const response = await axios.post('/api/chat/sessions', {
        name: `会话 ${new Date().toLocaleString()}`
      })
      
      const session = response.data
      set({ currentSession: session })
      return session
    } catch (error) {
      console.error('创建会话失败:', error)
      return null
    }
  },

  loadSessions: async () => {
    try {
      const response = await axios.get('/api/chat/sessions')
      return response.data
    } catch (error) {
      console.error('加载会话失败:', error)
      return []
    }
  },

  sendMessage: async (content: string, type: string = 'text') => {
    const { websocket, currentSession } = get()
    
    if (!websocket || !currentSession) {
      console.error('WebSocket未连接或会话不存在')
      return
    }

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    
    get().addMessage(userMessage)
    set({ isLoading: true })

    // 发送消息到WebSocket
    try {
      websocket.send(JSON.stringify({
        message: content,
        type,
        timestamp: new Date().toISOString()
      }))
    } catch (error) {
      console.error('发送消息失败:', error)
      set({ isLoading: false })
    }
  },

  clearMessages: () => set({ messages: [] })
}))