import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import './App.css';

// Components
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';

// Pages
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import ProfilePage from './pages/ProfilePage';
import IncidentsPage from './pages/IncidentsPage';

// Context
import { AuthProvider } from './utils/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected Routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/chat" replace />} />
                    <Route path="/chat" element={<ChatPage />} />
                    <Route 
                      path="/dashboard" 
                      element={
                        <AdminRoute>
                          <DashboardPage />
                        </AdminRoute>
                      } 
                    />
                    <Route path="/incidents" element={<IncidentsPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                    <Route path="*" element={<Navigate to="/chat" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Box>
    </AuthProvider>
  );
}

export default App;