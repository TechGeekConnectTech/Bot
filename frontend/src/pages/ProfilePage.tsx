import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Avatar,
  Button,
  TextField,
  Grid,
  Divider,
  Chip,
  Alert,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Person as PersonIcon
} from '@mui/icons-material';
import { useAuth } from '../utils/AuthContext';

const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    department: user?.department || ''
  });
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      full_name: user?.full_name || '',
      email: user?.email || '',
      department: user?.department || ''
    });
  };

  const handleCancel = () => {
    setIsEditing(false);
    setFormData({
      full_name: user?.full_name || '',
      email: user?.email || '',
      department: user?.department || ''
    });
  };

  const handleSave = async () => {
    try {
      // In a real app, you would call an API to update the user
      // await apiService.updateUser(formData);
      setSuccess('Profile updated successfully!');
      setIsEditing(false);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to update profile');
      setTimeout(() => setError(''), 3000);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        Profile
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Manage your account settings and preferences
      </Typography>

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Profile Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">
                  Personal Information
                </Typography>
                {!isEditing ? (
                  <Button
                    variant="outlined"
                    startIcon={<EditIcon />}
                    onClick={handleEdit}
                    sx={{
                      borderColor: '#DB0011',
                      color: '#DB0011',
                      '&:hover': {
                        borderColor: '#B8000E',
                        backgroundColor: 'rgba(219, 0, 17, 0.04)'
                      }
                    }}
                  >
                    Edit Profile
                  </Button>
                ) : (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      variant="outlined"
                      startIcon={<CancelIcon />}
                      onClick={handleCancel}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon />}
                      onClick={handleSave}
                      sx={{
                        backgroundColor: '#DB0011',
                        '&:hover': {
                          backgroundColor: '#B8000E'
                        }
                      }}
                    >
                      Save
                    </Button>
                  </Box>
                )}
              </Box>

              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
                    <Avatar
                      sx={{
                        width: 80,
                        height: 80,
                        backgroundColor: '#DB0011',
                        fontSize: '2rem',
                        fontWeight: 'bold'
                      }}
                    >
                      {user?.full_name?.charAt(0) || 'U'}
                    </Avatar>
                    <Box>
                      <Typography variant="h5" fontWeight="bold">
                        {user?.full_name || 'User Name'}
                      </Typography>
                      <Typography variant="body1" color="text.secondary">
                        @{user?.username}
                      </Typography>
                      <Chip
                        label={user?.role?.toUpperCase() || 'USER'}
                        size="small"
                        sx={{
                          mt: 1,
                          backgroundColor: '#DB0011',
                          color: 'white'
                        }}
                      />
                    </Box>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Full Name"
                    value={isEditing ? formData.full_name : user?.full_name || ''}
                    onChange={(e) => handleInputChange('full_name', e.target.value)}
                    disabled={!isEditing}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        '&.Mui-focused fieldset': {
                          borderColor: '#DB0011'
                        }
                      },
                      '& .MuiInputLabel-root.Mui-focused': {
                        color: '#DB0011'
                      }
                    }}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Email"
                    value={isEditing ? formData.email : user?.email || ''}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    disabled={!isEditing}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        '&.Mui-focused fieldset': {
                          borderColor: '#DB0011'
                        }
                      },
                      '& .MuiInputLabel-root.Mui-focused': {
                        color: '#DB0011'
                      }
                    }}
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Department"
                    value={isEditing ? formData.department : user?.department || ''}
                    onChange={(e) => handleInputChange('department', e.target.value)}
                    disabled={!isEditing}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        '&.Mui-focused fieldset': {
                          borderColor: '#DB0011'
                        }
                      },
                      '& .MuiInputLabel-root.Mui-focused': {
                        color: '#DB0011'
                      }
                    }}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>


      </Grid>
    </Box>
  );
};

export default ProfilePage;