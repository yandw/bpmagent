import { useEffect, useRef, useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { useAuthStore } from '@/stores/authStore'
import type { ChatMessage } from '@/stores/chatStore'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export const useWebSocket = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const { addMessage, setConnected, setLoading, setWebSocket } = useChatStore()
  const { token } = useAuthStore()

  const connect = (sessionId: string) => {
    // 检查是否已经连接或正在连接
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING ||
        connectionStatus === 'connecting' ||
        connectionStatus === 'connected') {
      console.log('WebSocket已连接或正在连接，跳过重复连接')
      return
    }

    // 清理现有连接
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setConnectionStatus('connecting')
    
    // 使用相对路径，让浏览器自动处理主机名和端口
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//localhost:8001/api/chat/ws/${sessionId}`
    // 添加JWT token到WebSocket连接
    const wsUrlWithAuth = token ? `${wsUrl}?token=${encodeURIComponent(token)}` : wsUrl
    
    console.log('WebSocket连接信息:', {
      sessionId,
      hasToken: !!token,
      tokenLength: token?.length || 0,
      wsUrl: wsUrlWithAuth
    })
    
    const ws = new WebSocket(wsUrlWithAuth)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket连接已建立')
      setConnectionStatus('connected')
      setConnected(true)
      setWebSocket(ws)
      setLoading(false)
      reconnectAttempts.current = 0
      
      // 清除重连定时器
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // 处理不同类型的消息
        if (data.type === 'message') {
          const message: ChatMessage = {
            id: Date.now().toString(),
            type: 'assistant',
            content: data.content,
            timestamp: data.timestamp || new Date().toISOString(),
            intent: data.intent,
            actions: data.actions,
            validation: data.validation
          }
          addMessage(message)
        } else if (data.type === 'status') {
          // 处理状态消息
          console.log('状态更新:', data.content)
        } else if (data.type === 'error') {
          const errorMessage: ChatMessage = {
            id: Date.now().toString(),
            type: 'system',
            content: `错误: ${data.content}`,
            timestamp: data.timestamp || new Date().toISOString()
          }
          addMessage(errorMessage)
        }
        
        setLoading(false)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error)
        setLoading(false)
      }
    }

    ws.onclose = (event) => {
      console.log('WebSocket连接已关闭', event.code, event.reason)
      console.log('关闭事件详情:', event)
      setConnectionStatus('disconnected')
      setConnected(false)
      setWebSocket(null)
      setLoading(false)

      // 自动重连
      if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts.current) * 1000 // 指数退避
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++
          console.log(`尝试重连 (${reconnectAttempts.current}/${maxReconnectAttempts})`)
          connect(sessionId)
        }, delay)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      console.error('错误详情:', {
        readyState: ws.readyState,
        url: ws.url,
        protocol: ws.protocol,
        sessionId: sessionId,
        hasToken: !!token
      })
      setConnectionStatus('error')
      setConnected(false)
      setWebSocket(null)
      setLoading(false)
    }

    wsRef.current = ws
  }

  const disconnect = () => {
    console.log('断开WebSocket连接')
    
    // 清除重连定时器
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, '用户主动断开')
      wsRef.current = null
    }
    
    setConnectionStatus('disconnected')
    setConnected(false)
    setWebSocket(null)
    reconnectAttempts.current = 0
  }

  const sendMessage = (message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    return false
  }

  // 清理函数
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [])

  return {
    connect,
    disconnect,
    sendMessage,
    connectionStatus,
    isConnected: connectionStatus === 'connected'
  }
}