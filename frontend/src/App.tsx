import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import { useAuthStore } from '@/stores/authStore'
import LoginPage from '@/pages/LoginPage'
import ChatPage from '@/pages/ChatPage'
import ProtectedRoute from '@/components/ProtectedRoute'

const { Content } = Layout

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content>
        <Routes>
          <Route 
            path="/login" 
            element={
              isAuthenticated ? <Navigate to="/chat" replace /> : <LoginPage />
            } 
          />
          <Route 
            path="/chat" 
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/" 
            element={<Navigate to={isAuthenticated ? "/chat" : "/login"} replace />} 
          />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App