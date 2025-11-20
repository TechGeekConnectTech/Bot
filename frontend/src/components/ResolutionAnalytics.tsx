import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Rating
} from '@mui/material';
import {
  TrendingUp,
  CheckCircle,
  Cancel,
  Analytics,
  Star
} from '@mui/icons-material';
import { apiService } from '../services/api';

interface ResolutionStats {
  total_queries: number;
  resolved_queries: number;
  resolution_rate: number;
  average_rating?: number;
  resolution_by_category: Record<string, {
    total: number;
    resolved: number;
    rate: number;
  }>;
  resolution_by_ai_service: Record<string, {
    total: number;
    resolved: number;
    rate: number;
  }>;
  recent_feedback: Array<{
    id: number;
    conversation_id: number;
    message_id: number;
    was_resolved: boolean;
    resolution_rating?: number;
    feedback_comment?: string;
    category?: string;
    ai_service_used?: string;
    created_at: string;
  }>;
}

const ResolutionAnalytics: React.FC = () => {
  const [stats, setStats] = useState<ResolutionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadResolutionStats();
  }, []);

  const loadResolutionStats = async () => {
    try {
      setLoading(true);
      const response = await apiService.getResolutionStats();
      setStats(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load resolution statistics');
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      'general': '#2196F3',
      'hsbc_internal': '#DB0011',
      'monitoring': '#FF9800',
      'knowledge_base': '#4CAF50'
    };
    return colors[category] || '#666';
  };

  const getServiceColor = (service: string) => {
    const colors: Record<string, string> = {
      'openai_technical_analysis': '#10A37F',
      'openai_educational': '#10A37F',
      'ollama_fallback': '#FF6B35',
      'fallback': '#9E9E9E'
    };
    return colors[service] || '#666';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!stats) {
    return <Alert severity="info">No resolution data available yet</Alert>;
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Analytics sx={{ mr: 1, color: '#DB0011' }} />
        Resolution Analytics Dashboard
      </Typography>

      {/* Overall Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Queries
                  </Typography>
                  <Typography variant="h4" component="div">
                    {stats.total_queries}
                  </Typography>
                </Box>
                <TrendingUp sx={{ fontSize: 40, color: '#2196F3' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Resolved Queries
                  </Typography>
                  <Typography variant="h4" component="div">
                    {stats.resolved_queries}
                  </Typography>
                </Box>
                <CheckCircle sx={{ fontSize: 40, color: '#4CAF50' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Resolution Rate
                  </Typography>
                  <Typography variant="h4" component="div" color={stats.resolution_rate >= 80 ? 'success.main' : stats.resolution_rate >= 60 ? 'warning.main' : 'error.main'}>
                    {stats.resolution_rate}%
                  </Typography>
                </Box>
                <Box sx={{ width: 60, height: 60, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress
                    variant="determinate"
                    value={stats.resolution_rate}
                    size={50}
                    sx={{
                      color: stats.resolution_rate >= 80 ? '#4CAF50' : stats.resolution_rate >= 60 ? '#FF9800' : '#f44336'
                    }}
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Average Rating
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography variant="h4" component="div" sx={{ mr: 1 }}>
                      {stats.average_rating ? stats.average_rating.toFixed(1) : 'N/A'}
                    </Typography>
                    {stats.average_rating && (
                      <Rating value={stats.average_rating} precision={0.1} readOnly size="small" />
                    )}
                  </Box>
                </Box>
                <Star sx={{ fontSize: 40, color: '#FFD700' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Resolution by Category */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Resolution Rate by Category
            </Typography>
            {Object.entries(stats.resolution_by_category).map(([category, data]) => (
              <Box key={category} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Chip
                    label={category.replace('_', ' ').toUpperCase()}
                    size="small"
                    sx={{ 
                      backgroundColor: getCategoryColor(category),
                      color: 'white',
                      fontWeight: 'bold'
                    }}
                  />
                  <Typography variant="body2">
                    {data.resolved}/{data.total} ({data.rate.toFixed(1)}%)
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={data.rate}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#f0f0f0',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: getCategoryColor(category)
                    }
                  }}
                />
              </Box>
            ))}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Resolution Rate by AI Service
            </Typography>
            {Object.entries(stats.resolution_by_ai_service).map(([service, data]) => (
              <Box key={service} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Chip
                    label={service.replace('_', ' ').toUpperCase()}
                    size="small"
                    sx={{ 
                      backgroundColor: getServiceColor(service),
                      color: 'white',
                      fontWeight: 'bold'
                    }}
                  />
                  <Typography variant="body2">
                    {data.resolved}/{data.total} ({data.rate.toFixed(1)}%)
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={data.rate}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#f0f0f0',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: getServiceColor(service)
                    }
                  }}
                />
              </Box>
            ))}
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Feedback */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recent User Feedback
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>AI Service</TableCell>
                <TableCell>Resolved</TableCell>
                <TableCell>Rating</TableCell>
                <TableCell>Comment</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {stats.recent_feedback.map((feedback) => (
                <TableRow key={feedback.id}>
                  <TableCell>
                    {new Date(feedback.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {feedback.category && (
                      <Chip
                        label={feedback.category.replace('_', ' ')}
                        size="small"
                        sx={{ 
                          backgroundColor: getCategoryColor(feedback.category),
                          color: 'white'
                        }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                      {feedback.ai_service_used || 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {feedback.was_resolved ? (
                      <CheckCircle sx={{ color: '#4CAF50', fontSize: 20 }} />
                    ) : (
                      <Cancel sx={{ color: '#f44336', fontSize: 20 }} />
                    )}
                  </TableCell>
                  <TableCell>
                    {feedback.resolution_rating ? (
                      <Rating value={feedback.resolution_rating} readOnly size="small" />
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>
                    <Typography variant="body2" sx={{ 
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {feedback.feedback_comment || '-'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default ResolutionAnalytics;