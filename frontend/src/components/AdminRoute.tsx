import React, { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';
import { Box, Alert, Paper, Typography } from '@mui/material';
import { Shield as ShieldIcon } from '@mui/icons-material';

interface AdminRouteProps {
  children: ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          p: 3
        }}
      >
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check if user has admin role
  if (user?.role !== 'admin') {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          p: 3
        }}
      >
        <Paper
          sx={{
            p: 4,
            textAlign: 'center',
            maxWidth: 400,
            backgroundColor: '#fff3cd',
            border: '1px solid #ffeaa7'
          }}
        >
          <ShieldIcon
            sx={{
              fontSize: 64,
              color: '#856404',
              mb: 2
            }}
          />
          <Typography variant="h5" gutterBottom sx={{ color: '#856404', fontWeight: 600 }}>
            Access Restricted
          </Typography>
          <Typography variant="body1" sx={{ color: '#856404', mb: 2 }}>
            This section is only available to administrators.
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Current Role:</strong> {user?.role || 'User'}
              <br />
              <strong>Required Role:</strong> Admin
            </Typography>
          </Alert>
          <Typography variant="body2" sx={{ mt: 2, color: '#6c757d' }}>
            Please contact your system administrator if you need access to this feature.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return <>{children}</>;
};

export default AdminRoute;