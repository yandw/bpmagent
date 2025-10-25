import React, { useState, useEffect, useRef } from 'react'
import { Layout, Input, Button, Avatar, Typography, message } from 'antd'
import { SendOutlined, PaperClipOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import MessageList from '@/components/MessageList'
import FileUpload from '@/components/FileUpload'

const { Header, Content, Footer } = Layout
const { TextArea } = Input
const { Title, Text } = Typography

const ChatPage: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const inputRef = useRef<any>(null)
  
  const { user, logout } = useAuthStore()
  const { 
    messages, 
    currentSession, 
    isLoading,
    createSession,
    sendMessage 
  } = useChatStore()

  const { connect, disconnect, connectionStatus } = useWebSocket()
  
  // 使用useWebSocket的连接状态
  const isConnected = connectionStatus === 'connected'

  useEffect(() => {
    // 初始化聊天会话 - 只在组件挂载时执行一次
    const initChat = async () => {
      if (!currentSession) {
        await createSession()
      }
    }
    
    initChat()
  }, []) // 移除依赖数组中的currentSession和createSession

  useEffect(() => {
    // 连接WebSocket - 只有在有会话且未连接时才连接
    if (currentSession?.session_id && !isConnected && connectionStatus === 'disconnected') {
      console.log('尝试连接WebSocket:', {
        sessionId: currentSession.session_id,
        isConnected,
        connectionStatus
      })
      connect(currentSession.session_id)
    }
  }, [currentSession?.session_id, isConnected, connectionStatus]) // 移除disconnect依赖

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const message = inputValue.trim()
    setInputValue('')
    
    await sendMessage(message, 'text')
    
    // 聚焦输入框
    setTimeout(() => {
      inputRef.current?.focus()
    }, 100)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleFileUpload = async (file: File) => {
    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('ocr', 'true')

      const response = await fetch('/api/upload/image', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`
        }
      })

      if (response.ok) {
        const result = await response.json()
        message.success('文件上传成功')
        
        // 发送OCR结果消息
        if (result.ocr_result) {
          await sendMessage(`我上传了一个文件，OCR识别结果：${JSON.stringify(result.ocr_result)}`, 'ocr')
        }
      } else {
        message.error('文件上传失败')
      }
    } catch (error) {
      console.error('上传错误:', error)
      message.error('文件上传失败')
    } finally {
      setIsUploading(false)
    }
  }

  const handleLogout = () => {
    disconnect()
    logout()
  }

  return (
    <Layout className="chat-container">
      <Header className="chat-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={4} style={{ margin: 0, color: '#1677ff' }}>
              BPM Agent
            </Title>
            <Text type="secondary">智能业务流程助手</Text>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div 
                className={`status-dot ${connectionStatus === 'connected' ? '' : 'error'}`}
              />
              <Text type="secondary">
                {connectionStatus === 'connected' ? '已连接' : '连接中...'}
              </Text>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar size="small" icon={<UserOutlined />} />
              <Text>{user?.username}</Text>
              <Button 
                type="text" 
                icon={<LogoutOutlined />} 
                onClick={handleLogout}
                title="退出登录"
              />
            </div>
          </div>
        </div>
      </Header>

      <Content className="chat-messages">
        <MessageList messages={messages} loading={isLoading} />
      </Content>

      <Footer className="chat-input-area">
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <TextArea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                !isConnected 
                  ? "正在连接WebSocket..." 
                  : isLoading 
                    ? "正在处理消息..." 
                    : "输入消息... (Shift+Enter 换行，Enter 发送)"
              }
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={isLoading || !isConnected}
            />
          </div>
          
          <div style={{ display: 'flex', gap: 8 }}>
            <FileUpload
              onUpload={handleFileUpload}
              loading={isUploading}
            >
              <Button 
                icon={<PaperClipOutlined />}
                loading={isUploading}
                disabled={isLoading || !isConnected}
                title="上传文件"
              />
            </FileUpload>
            
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading || !isConnected}
              loading={isLoading}
            >
              发送
            </Button>
          </div>
        </div>
      </Footer>
    </Layout>
  )
}

export default ChatPage