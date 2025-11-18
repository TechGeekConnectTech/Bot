import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Container,
  Card,
  CardContent,
  Grid,
  TextField,
  InputAdornment,
  Pagination,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Person as PersonIcon,
  Storage as ServerIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { apiService } from '../services/api';
import { useAuth } from '../utils/AuthContext';

interface IncidentDetails {
  incident_id: string;
  conversation_id: number;
  created_by_username?: string;
  created_by_full_name?: string;
  created_by_department?: string;
  server_name?: string;
  correlation_id?: string;
  query_type: string;
  created_at: string;
  status?: string;
  priority?: string;
}

interface SelectedIncident extends IncidentDetails {
  resolution_steps?: string;
  issue_description?: string;
  affected_username?: string;
  job_id?: string;
  category?: string;
}

interface Filters {
  server_name: string;
  query_type: string;
  incident_status: string;
}

const IncidentsPage: React.FC = () => {
  const { user } = useAuth();
  const [incidents, setIncidents] = useState<IncidentDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalIncidents, setTotalIncidents] = useState(0);
  const [selectedIncident, setSelectedIncident] = useState<SelectedIncident | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [isAdminView, setIsAdminView] = useState(false);
  const itemsPerPage = 10;

  const [filters, setFilters] = useState<Filters>({
    server_name: '',
    query_type: '',
    incident_status: ''
  });

  useEffect(() => {
    loadIncidents();
  }, [currentPage, filters]);

  const loadIncidents = async () => {
    try {
      setLoading(true);
      const filterParams = {
        page: currentPage,
        limit: itemsPerPage,
        ...(filters.server_name && { server_name: filters.server_name }),
        ...(filters.query_type && { query_type: filters.query_type }),
        ...(filters.incident_status && { incident_status: filters.incident_status })
      };

      // Try to get user incidents first
      let response;
      try {
        response = await apiService.getUserIncidents(filterParams);
        setIsAdminView(false);
      } catch (userErr: any) {
        // If user incidents fail, try admin incidents (for admin users)
        if (userErr.message.includes('Admin access required')) {
          response = await apiService.getAdminIncidents(filterParams);
          setIsAdminView(true);
        } else {
          throw userErr;
        }
      }
      
      setIncidents(response.incidents || []);
      setTotalPages(response.total_pages || 0);
      setTotalIncidents(response.total_incidents || 0);
      setError('');
    } catch (err: any) {
      if (err.message.includes('Admin access required')) {
        setError('You need administrator privileges to view all incidents. Showing your personal incidents only.');
      } else {
        setError('Failed to load incidents. Please try again later.');
      }
      console.error('Error loading incidents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (incidentId: string) => {
    try {
      const details = await apiService.getIncidentDetails(incidentId);
      setSelectedIncident(details);
      setDetailsOpen(true);
    } catch (err) {
      console.error('Error loading incident details:', err);
      setError('Failed to load incident details');
    }
  };

  const handleFilterChange = (filterName: keyof Filters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({
      server_name: '',
      query_type: '',
      incident_status: ''
    });
    setCurrentPage(1);
  };

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    // For now, search functionality will be client-side
    // In the future, this could be enhanced to be server-side
  };

  const getFilteredIncidents = () => {
    if (!searchTerm.trim()) return incidents;
    
    return incidents.filter(incident =>
      incident.incident_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      incident.server_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      getQueryTypeDisplay(incident.query_type).toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPriorityColor = (priority?: string) => {
    if (!priority) return 'default';
    switch (priority.toLowerCase()) {
      case 'high':
      case 'critical': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getQueryTypeDisplay = (queryType: string) => {
    const typeMap: { [key: string]: string } = {
      'auth_issue': 'Authentication Issue',
      'payload_issue': 'Payload Issue',
      'resource_lock': 'Resource Lock',
      'performance_issue': 'Performance Issue',
      'configuration_issue': 'Configuration Issue',
      'api_issue': 'API Issue',
      'other': 'Other'
    };
    return typeMap[queryType] || queryType;
  };

  // Get filtered incidents for display (client-side search)
  const displayedIncidents = getFilteredIncidents();
  
  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    setCurrentPage(page);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ ml: 2 }}>
            Loading incidents...
          </Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4" component="h1" sx={{ color: '#DB0011', fontWeight: 600 }}>
          <ErrorIcon sx={{ mr: 2, verticalAlign: 'middle' }} />
          {isAdminView ? 'All Incidents (Admin View)' : 'My Incidents'}
        </Typography>
        {user && (
          <Chip 
            label={isAdminView ? `Admin: ${user.full_name}` : `User: ${user.full_name}`}
            color={isAdminView ? 'error' : 'primary'}
            variant="outlined"
          />
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Incidents
              </Typography>
              <Typography variant="h4" component="div">
                {totalIncidents}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                High Priority
              </Typography>
              <Typography variant="h4" component="div" color="error">
                {incidents.filter(inc => inc.priority === 'High' || inc.priority === 'Critical' || inc.priority === 'high' || inc.priority === 'critical').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Current Page
              </Typography>
              <Typography variant="h4" component="div">
                {incidents.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Search Results
              </Typography>
              <Typography variant="h4" component="div">
                {searchTerm ? displayedIncidents.length : incidents.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <FilterIcon sx={{ mr: 1, color: '#DB0011' }} />
          <Typography variant="h6" sx={{ color: '#DB0011', fontWeight: 600 }}>
            Filters
          </Typography>
          <Box sx={{ ml: 'auto' }}>
            <Button 
              onClick={clearFilters}
              size="small"
              sx={{ mr: 2 }}
            >
              Clear Filters
            </Button>
            <Button 
              onClick={loadIncidents}
              size="small"
              startIcon={<RefreshIcon />}
              variant="outlined"
            >
              Refresh
            </Button>
          </Box>
        </Box>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Server Name</InputLabel>
              <Select
                value={filters.server_name}
                label="Server Name"
                onChange={(e) => handleFilterChange('server_name', e.target.value)}
              >
                <MenuItem value="">All Servers</MenuItem>
                <MenuItem value="srv-web-01">srv-web-01</MenuItem>
                <MenuItem value="srv-web-02">srv-web-02</MenuItem>
                <MenuItem value="srv-db-01">srv-db-01</MenuItem>
                <MenuItem value="srv-db-02">srv-db-02</MenuItem>
                <MenuItem value="srv-lb-01">srv-lb-01</MenuItem>
                <MenuItem value="srv-app-01">srv-app-01</MenuItem>
                <MenuItem value="srv-cache-01">srv-cache-01</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Query Type</InputLabel>
              <Select
                value={filters.query_type}
                label="Query Type"
                onChange={(e) => handleFilterChange('query_type', e.target.value)}
              >
                <MenuItem value="">All Types</MenuItem>
                <MenuItem value="auth_issue">Authentication Issue</MenuItem>
                <MenuItem value="payload_issue">Payload Issue</MenuItem>
                <MenuItem value="resource_lock">Resource Lock</MenuItem>
                <MenuItem value="performance_issue">Performance Issue</MenuItem>
                <MenuItem value="configuration_issue">Configuration Issue</MenuItem>
                <MenuItem value="api_issue">API Issue</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={filters.incident_status}
                label="Status"
                onChange={(e) => handleFilterChange('incident_status', e.target.value)}
              >
                <MenuItem value="">All Statuses</MenuItem>
                <MenuItem value="Open">Open</MenuItem>
                <MenuItem value="In Progress">In Progress</MenuItem>
                <MenuItem value="Resolved">Resolved</MenuItem>
                <MenuItem value="Closed">Closed</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Search Bar */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search incidents by ID, user, or type..."
          value={searchTerm}
          onChange={(e) => handleSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ maxWidth: 500 }}
        />
      </Box>

      {/* Incidents Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell><strong>Incident ID</strong></TableCell>
                {isAdminView && <TableCell><strong>Created By</strong></TableCell>}
                <TableCell><strong>Type</strong></TableCell>
                <TableCell><strong>Server</strong></TableCell>
                <TableCell><strong>Priority</strong></TableCell>
                <TableCell><strong>Created At</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displayedIncidents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={isAdminView ? 6 : 5} align="center">
                    <Box py={4}>
                      <Typography variant="body1" color="textSecondary">
                        {searchTerm ? 'No incidents match your search' : 'No incidents found'}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : (
                displayedIncidents.map((incident) => (
                  <TableRow 
                    key={incident.incident_id} 
                    hover 
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleViewDetails(incident.incident_id)}
                  >
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <Tooltip title="Click to view details">
                          <InfoIcon sx={{ mr: 1, color: 'action.active', fontSize: 16 }} />
                        </Tooltip>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', color: '#DB0011', fontWeight: 600 }}>
                          {incident.incident_id}
                        </Typography>
                      </Box>
                    </TableCell>
                    {isAdminView && (
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          <PersonIcon sx={{ mr: 1, color: 'action.active', fontSize: 16 }} />
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {incident.created_by_full_name || 'Unknown User'}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              @{incident.created_by_username || 'unknown'}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                    )}
                    <TableCell>
                      <Chip
                        label={getQueryTypeDisplay(incident.query_type)}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <ServerIcon sx={{ mr: 1, color: 'action.active', fontSize: 16 }} />
                        <Typography variant="body2">
                          {incident.server_name || 'Not specified'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={incident.priority || 'Medium'}
                        size="small"
                        color={getPriorityColor(incident.priority) as any}
                        sx={{ fontWeight: incident.priority === 'High' || incident.priority === 'Critical' ? 'bold' : 'normal' }}
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <ScheduleIcon sx={{ mr: 1, color: 'action.active', fontSize: 16 }} />
                        <Typography variant="body2">
                          {formatDate(incident.created_at)}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Stack spacing={2}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={handlePageChange}
              color="primary"
              size="large"
              showFirstButton
              showLastButton
            />
            <Typography variant="body2" color="textSecondary" textAlign="center">
              Page {currentPage} of {totalPages} ({totalIncidents} total incidents)
            </Typography>
          </Stack>
        </Box>
      )}
      </Paper>

      {/* Incident Details Dialog */}
      <Dialog 
        open={detailsOpen} 
        onClose={() => setDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <ErrorIcon sx={{ mr: 1, color: '#DB0011' }} />
            <Typography variant="h6" sx={{ color: '#DB0011', fontWeight: 600 }}>
              Incident Details
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedIncident && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Incident ID
                </Typography>
                <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 600, mb: 2 }}>
                  {selectedIncident.incident_id}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Created By
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedIncident.created_by_full_name} (@{selectedIncident.created_by_username})
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Server Name
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedIncident.server_name || 'Not specified'}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Query Type
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {getQueryTypeDisplay(selectedIncident.query_type)}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Priority
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Chip
                    label={selectedIncident.priority || 'Medium'}
                    size="small"
                    color={getPriorityColor(selectedIncident.priority) as any}
                  />
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Status
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedIncident.status}
                </Typography>
              </Grid>
              
              {selectedIncident.correlation_id && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Correlation ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {selectedIncident.correlation_id}
                  </Typography>
                </Grid>
              )}
              
              {selectedIncident.job_id && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Job ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {selectedIncident.job_id}
                  </Typography>
                </Grid>
              )}
              
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="textSecondary">
                  Created At
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {formatDate(selectedIncident.created_at)}
                </Typography>
              </Grid>
              
              {selectedIncident.issue_description && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Issue Description
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {selectedIncident.issue_description}
                  </Typography>
                </Grid>
              )}
              
              {selectedIncident.resolution_steps && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Resolution Steps
                  </Typography>
                  <Paper sx={{ p: 2, backgroundColor: '#f5f5f5', mt: 1 }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {selectedIncident.resolution_steps}
                    </Typography>
                  </Paper>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default IncidentsPage;