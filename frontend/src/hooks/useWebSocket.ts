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
  
  // 使用useRef来保持streamingMessageId的实时状态
  const streamingMessageIdRef = useRef<string | null>(null)

  const { addMessage, setConnected, setLoading, setWebSocket, appendToMessage, updateMessage, setStreamingMessageId } = useChatStore()
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
    const wsUrl = `${wsProtocol}//localhost:8888/api/chat/ws/${sessionId}`
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
        console.log('收到WebSocket消息:', data.type, '当前streamingMessageId:', streamingMessageIdRef.current)
        
        // 处理不同类型的消息
        if (data.type === 'message_chunk') {
          // 流式消息块
          if (streamingMessageIdRef.current) {
            // 追加内容到现有流式消息
            console.log('追加内容到现有消息:', streamingMessageIdRef.current)
            appendToMessage(streamingMessageIdRef.current, data.content)
          } else {
            // 创建新的流式消息，使用更稳定的ID生成方式
            const messageId = `streaming_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            const message: ChatMessage = {
              id: messageId,
              type: 'assistant',
              content: data.content,
              timestamp: data.timestamp || new Date().toISOString(),
              isStreaming: true
            }
            addMessage(message)
            setStreamingMessageId(messageId)
            streamingMessageIdRef.current = messageId
            console.log('创建新的流式消息:', messageId)
          }
        } else if (data.type === 'message_complete') {
          // 流式消息完成
          if (streamingMessageIdRef.current) {
            console.log('完成流式消息:', streamingMessageIdRef.current)
            // 更新现有的流式消息，标记为完成
            updateMessage(streamingMessageIdRef.current, {
              content: data.content, // 使用完整内容替换
              intent: data.intent,
              actions: data.actions,
              validation: data.validation,
              isStreaming: false
            })
            setStreamingMessageId(null)
            streamingMessageIdRef.current = null
          } else {
            console.log('没有找到流式消息ID，创建新消息')
            // 如果没有流式消息ID，可能是直接收到完整消息，创建新消息
            const message: ChatMessage = {
              id: `complete_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
              type: 'assistant',
              content: data.content,
              timestamp: data.timestamp || new Date().toISOString(),
              intent: data.intent,
              actions: data.actions,
              validation: data.validation,
              isStreaming: false
            }
            addMessage(message)
          }
        } else if (data.type === 'message') {
          // 兼容旧版本的完整消息
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
          // 错误消息
          const errorMessage: ChatMessage = {
            id: Date.now().toString(),
            type: 'system',
            content: `错误: ${data.content}`,
            timestamp: data.timestamp || new Date().toISOString()
          }
          addMessage(errorMessage)
          // 如果有流式消息正在进行，停止流式输出
          if (streamingMessageIdRef.current) {
            updateMessage(streamingMessageIdRef.current, { isStreaming: false })
            setStreamingMessageId(null)
            streamingMessageIdRef.current = null
          }
        }
        
        setLoading(false)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error)
        setLoading(false)
        // 如果有流式消息正在进行，停止流式输出
        if (streamingMessageIdRef.current) {
          updateMessage(streamingMessageIdRef.current, { isStreaming: false })
          setStreamingMessageId(null)
          streamingMessageIdRef.current = null
        }
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