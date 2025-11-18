import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// HSBC Brand Theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#DB0011', // HSBC Red
      light: '#FF3333',
      dark: '#B8000E',
      contrastText: '#FFFFFF'
    },
    secondary: {
      main: '#000000', // HSBC Black
      light: '#333333',
      dark: '#000000',
      contrastText: '#FFFFFF'
    },
    background: {
      default: '#F8F9FA',
      paper: '#FFFFFF'
    },
    text: {
      primary: '#212121',
      secondary: '#666666'
    }
  },
  typography: {
    fontFamily: '"Open Sans", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
      color: '#212121'
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      color: '#212121'
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 500,
      color: '#212121'
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6
    }
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '8px',
          fontWeight: 500
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
        }
      }
    }
  }
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);