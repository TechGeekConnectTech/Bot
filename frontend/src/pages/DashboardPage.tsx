import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import {
  TrendingUp,
  People,
  Chat,
  CheckCircle,
  Warning,
  Schedule
} from '@mui/icons-material';
import { apiService } from '../services/api';
import { DashboardStats, UserStats } from '../types';
import { useAuth } from '../utils/AuthContext';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [userStats, setUserStats] = useState<UserStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [dashboardData, usersData] = await Promise.all([
        apiService.getDashboardStats(),
        apiService.getUserStatistics()
      ]);
      
      setStats(dashboardData);
      setUserStats(usersData);
    } catch (err: any) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress size={60} sx={{ color: '#DB0011' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const StatCard = ({ title, value, icon, color, subtitle }: any) => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h4" fontWeight="bold" color={color}>
              {value}
            </Typography>
            <Typography variant="h6" color="text.primary">
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              backgroundColor: `${color}20`,
              color: color
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h4" fontWeight="bold">
          Administrator Dashboard
        </Typography>
        <Chip 
          label="Admin Only" 
          size="small" 
          color="primary"
          sx={{ 
            backgroundColor: '#DB0011',
            color: 'white',
            fontWeight: 'bold'
          }}
        />
      </Box>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        DC AutoAssist System Analytics & Performance Insights
      </Typography>

      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Users"
            value={stats?.total_users || 0}
            icon={<People />}
            color="#2196F3"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Conversations"
            value={stats?.total_conversations || 0}
            icon={<Chat />}
            color="#4CAF50"
            subtitle="All time"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Queries Resolved"
            value={stats?.total_queries_resolved || 0}
            icon={<CheckCircle />}
            color="#DB0011"
            subtitle="Automatically"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Today's Queries"
            value={stats?.queries_today || 0}
            icon={<Schedule />}
            color="#FF9800"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Resolution Rate */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Resolution Rate
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h3" fontWeight="bold" color="#DB0011">
                  {stats?.resolution_rate || 0}%
                </Typography>
                <TrendingUp sx={{ ml: 1, color: '#4CAF50' }} />
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats?.resolution_rate || 0}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: '#f5f5f5',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: '#DB0011'
                  }
                }}
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Queries resolved without human intervention
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Conversations */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Conversations
              </Typography>
              <Typography variant="h3" fontWeight="bold" color="#2196F3">
                {stats?.active_conversations || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Currently ongoing support sessions
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Common Issues */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Common Issues
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {stats?.common_issues?.map((issue, index) => (
                  <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">
                      {issue.issue_type.replace('_', ' ').toUpperCase()}
                    </Typography>
                    <Chip
                      label={issue.count}
                      size="small"
                      sx={{ backgroundColor: '#DB0011', color: 'white' }}
                    />
                  </Box>
                )) || []}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* User Activity */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top Active Users
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell align="right">Conversations</TableCell>
                      <TableCell align="right">Resolved</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {userStats.slice(0, 5).map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight={user.id === (user as any).id ? 'bold' : 'normal'}>
                            {user.full_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {user.department}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{user.total_conversations}</TableCell>
                        <TableCell align="right">{user.queries_resolved}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;