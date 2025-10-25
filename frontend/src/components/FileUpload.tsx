import React, { useRef } from 'react'
import { message } from 'antd'

interface FileUploadProps {
  onUpload: (file: File) => void
  loading?: boolean
  accept?: string
  maxSize?: number // MB
  children: React.ReactNode
}

const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  loading = false,
  accept = 'image/*',
  maxSize = 10,
  children
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleClick = () => {
    if (loading) return
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 验证文件大小
    if (file.size > maxSize * 1024 * 1024) {
      message.error(`文件大小不能超过 ${maxSize}MB`)
      return
    }

    // 验证文件类型
    if (accept !== '*' && !file.type.match(accept.replace('*', '.*'))) {
      message.error('文件类型不支持')
      return
    }

    onUpload(file)
    
    // 清空input值，允许重复上传同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      <div onClick={handleClick} style={{ cursor: loading ? 'not-allowed' : 'pointer' }}>
        {children}
      </div>
    </>
  )
}

export default FileUpload