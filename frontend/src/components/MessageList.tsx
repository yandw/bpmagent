import React, { useEffect, useRef } from 'react'
import { Avatar, Typography, Tag, Spin, Card } from 'antd'
import { UserOutlined, RobotOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import dayjs from 'dayjs'
import type { ChatMessage } from '@/stores/chatStore'

const { Text } = Typography

interface MessageListProps {
  messages: ChatMessage[]
  loading?: boolean
}

const MessageList: React.FC<MessageListProps> = ({ messages, loading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const renderMessageContent = (message: ChatMessage) => {
    if (message.type === 'system') {
      return (
        <Card size="small" style={{ backgroundColor: '#fff7e6', border: '1px solid #ffd591' }}>
          <Text type="warning">{message.content}</Text>
        </Card>
      )
    }

    return (
      <div className={`message-content ${message.type}`}>
        <ReactMarkdown>{message.content}</ReactMarkdown>
        
        {/* 显示意图标签 */}
        {message.intent && (
          <div style={{ marginTop: 8 }}>
            <Tag color="blue">{getIntentLabel(message.intent)}</Tag>
          </div>
        )}
        
        {/* 显示操作按钮 */}
        {message.actions && message.actions.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {message.actions.map((action, index) => (
              <Tag key={index} color="green">
                {action.type}: {action.description || '执行中...'}
              </Tag>
            ))}
          </div>
        )}
        
        {/* 显示验证结果 */}
        {message.validation && (
          <div style={{ marginTop: 8 }}>
            <Card size="small" title="表单验证结果">
              <Text>{message.validation.summary}</Text>
              {message.validation.results && message.validation.results.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  {message.validation.results.map((result: any, index: number) => (
                    <div key={index}>
                      <Tag color={result.severity === 'error' ? 'red' : 'orange'}>
                        {result.field}: {result.message}
                      </Tag>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    )
  }

  const getIntentLabel = (intent: string) => {
    const intentLabels: Record<string, string> = {
      'form_filling': '表单填写',
      'ocr_processing': 'OCR识别',
      'question_answering': '问答',
      'data_extraction': '数据提取',
      'general': '一般对话'
    }
    return intentLabels[intent] || intent
  }

  const getAvatar = (type: string) => {
    if (type === 'user') {
      return <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
    } else if (type === 'assistant') {
      return <Avatar size="small" icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
    } else {
      return <Avatar size="small" style={{ backgroundColor: '#faad14' }}>系统</Avatar>
    }
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '16px 0' }}>
      {messages.length === 0 && !loading && (
        <div style={{ 
          textAlign: 'center', 
          padding: '60px 20px',
          color: 'rgba(0, 0, 0, 0.45)'
        }}>
          <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <div>
            <Text type="secondary" style={{ fontSize: 16 }}>
              您好！我是您的BPM助手
            </Text>
          </div>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              我可以帮助您自动填写表单、识别文档信息和处理业务流程
            </Text>
          </div>
        </div>
      )}

      {messages.map((message) => (
        <div key={message.id} className={`message-item ${message.type}`}>
          <div className="message-avatar">
            {getAvatar(message.type)}
          </div>
          
          <div style={{ flex: 1, maxWidth: '70%' }}>
            {renderMessageContent(message)}
            <div className="message-time">
              {dayjs(message.timestamp).format('HH:mm:ss')}
            </div>
          </div>
        </div>
      ))}

      {loading && (
        <div className="message-item assistant">
          <div className="message-avatar">
            {getAvatar('assistant')}
          </div>
          <div className="message-content assistant">
            <Spin size="small" /> 正在思考中...
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}

export default MessageList