import React, { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useAuth } from '../utils/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          backgroundColor: '#f8f9fa'
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h4" fontWeight="bold" color="#DB0011" sx={{ mb: 3 }}>
            DC AutoAssist
          </Typography>
          <CircularProgress
            size={40}
            thickness={4}
            sx={{
              color: '#DB0011',
              mb: 2
            }}
          />
          <Typography variant="h6" color="text.secondary">
            Loading DC AutoAssist...
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Please wait while we verify your session
          </Typography>
        </Box>
      </Box>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page with return url
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;