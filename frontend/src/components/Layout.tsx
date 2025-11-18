import React, { ReactNode } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Divider,
  useMediaQuery,
  useTheme
} from '@mui/material';
import {
  Chat as ChatIcon,
  Dashboard as DashboardIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Menu as MenuIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';
import { useState } from 'react';

interface LayoutProps {
  children: ReactNode;
}

const DRAWER_WIDTH = 280;

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    {
      text: 'Chat Assistant',
      icon: <ChatIcon />,
      path: '/chat',
      description: 'Get API support and troubleshooting help',
      roles: ['admin', 'user'] // Available to all users
    },
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/dashboard',
      description: 'View analytics and reports',
      roles: ['admin'] // Admin only
    },
    {
      text: 'My Incidents',
      icon: <ErrorIcon />,
      path: '/incidents',
      description: 'View your created incidents',
      roles: ['admin', 'user'] // Available to all users
    },
    {
      text: 'Profile',
      icon: <PersonIcon />,
      path: '/profile',
      description: 'Manage your profile',
      roles: ['admin', 'user'] // Available to all users
    }
  ];

  // Filter menu items based on user role
  const filteredMenuItems = menuItems.filter(item => 
    item.roles.includes(user?.role || 'user')
  );

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* DC Logo and Brand */}
      <Box
        sx={{
          p: 3,
          background: 'linear-gradient(135deg, #DB0011 0%, #FF3333 100%)',
          color: 'white',
          textAlign: 'center'
        }}
      >
        <Typography variant="h5" fontWeight="bold">
          DC
        </Typography>
        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
          AutoAssist
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.8, display: 'block', mt: 1 }}>
          DC Automation Support
        </Typography>
      </Box>

      {/* User Info */}
      <Box sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              width: 40,
              height: 40,
              backgroundColor: '#DB0011',
              fontSize: '1rem'
            }}
          >
            {user?.full_name?.charAt(0) || 'U'}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle2" noWrap>
              {user?.full_name || 'User'}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {user?.department || 'DC Automation'}
            </Typography>
          </Box>
        </Box>
      </Box>

      <Divider />

      {/* Navigation Menu */}
      <List sx={{ flex: 1, pt: 1 }}>
        {filteredMenuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding sx={{ px: 1 }}>
              <ListItemButton
                onClick={() => {
                  navigate(item.path);
                  if (isMobile) setMobileOpen(false);
                }}
                sx={{
                  borderRadius: 2,
                  mb: 0.5,
                  backgroundColor: isActive ? 'rgba(219, 0, 17, 0.1)' : 'transparent',
                  color: isActive ? '#DB0011' : 'text.primary',
                  '&:hover': {
                    backgroundColor: isActive ? 'rgba(219, 0, 17, 0.15)' : 'rgba(0, 0, 0, 0.04)'
                  }
                }}
              >
                <ListItemIcon
                  sx={{
                    color: isActive ? '#DB0011' : 'text.secondary',
                    minWidth: 40
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  secondary={item.description}
                  primaryTypographyProps={{
                    fontWeight: isActive ? 600 : 400,
                    fontSize: '0.95rem'
                  }}
                  secondaryTypographyProps={{
                    fontSize: '0.75rem'
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      <Divider />

      {/* Logout Button */}
      <Box sx={{ p: 2 }}>
        <Button
          fullWidth
          variant="outlined"
          color="error"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
          sx={{
            borderRadius: 2,
            textTransform: 'none',
            fontWeight: 500
          }}
        >
          Sign Out
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
          backgroundColor: 'white',
          color: 'text.primary',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <Toolbar>
          {isMobile && (
            <Button
              color="inherit"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, minWidth: 'auto', p: 1 }}
            >
              <MenuIcon />
            </Button>
          )}
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {menuItems.find(item => item.path === location.pathname)?.text || 'DC AutoAssist'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#4CAF50'
              }}
            />
            <Typography variant="body2" color="text.secondary">
              Online
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Navigation Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}
      >
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true // Better open performance on mobile.
          }}
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: '1px solid rgba(0, 0, 0, 0.1)'
            }
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          minHeight: '100vh',
          backgroundColor: '#f8f9fa'
        }}
      >
        <Toolbar /> {/* Spacer for fixed AppBar */}
        <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;