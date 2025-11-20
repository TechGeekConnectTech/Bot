import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Chip,
  Avatar,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Divider,
  ListItemButton,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import ResolutionFeedback from '../components/ResolutionFeedback';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as UserIcon,
  Refresh as RefreshIcon,
  Error as ErrorIcon,
  History as HistoryIcon,
  Add as AddIcon,
  Close as CloseIcon,
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  DeleteSweep as DeleteSweepIcon
} from '@mui/icons-material';
import { apiService } from '../services/api';
import { useAuth } from '../utils/AuthContext';
import { ChatMessage, ChatResponse } from '../types';
import ReactMarkdown from 'react-markdown';

const ChatPage: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [error, setError] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [showIncidentButton, setShowIncidentButton] = useState(false);
  const [creatingIncident, setCreatingIncident] = useState(false);
  const [showIncidentForm, setShowIncidentForm] = useState(false);
  const [conversations, setConversations] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [incidentForm, setIncidentForm] = useState({
    serverName: '',
    correlationId: '',
    jobId: '',
    affectedUsername: '',
    issueDescription: '',
    priority: 'Medium',
    category: 'API Issue'
  });
  const [showCategorySelector, setShowCategorySelector] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categoryOptions] = useState([
    {
      id: 'general',
      title: 'General Question',
      description: 'Non-HSBC specific questions, tutorials, concepts',
      icon: '📚',
      color: '#2196F3'
    },
    {
      id: 'hsbc_internal',
      title: 'HSBC Internal Issue',
      description: 'Server issues, API problems, internal systems',
      icon: '🏦',
      color: '#DB0011'
    },
    {
      id: 'monitoring',
      title: 'System Monitoring',
      description: 'Splunk logs, Ansible data, performance metrics',
      icon: '📊',
      color: '#FF9800'
    },
    {
      id: 'knowledge_base',
      title: 'Internal Knowledge',
      description: 'Confluence docs, procedures, best practices',
      icon: '📖',
      color: '#4CAF50'
    }
  ]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteAllDialogOpen, setDeleteAllDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadConversationHistory();
  }, []);

  useEffect(() => {
    // Add welcome message
    const welcomeMessage: ChatMessage = {
      id: 0,
      conversation_id: 0,
      sender_type: 'system',
      message_content: `Welcome to DC AutoAssist, ${user?.full_name}! 🤖\n\nI'm your AI assistant for API support and troubleshooting. Simply describe your issue and I'll help you resolve it.\n\nIf I can't resolve your query, you can create an incident ticket for the support team. How can I help you today?`,
      timestamp: new Date().toISOString()
    };
    setMessages([welcomeMessage]);
  }, [user]);

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Check if this is the first user message - show category selector
    const userMessages = messages.filter(m => m.sender_type === 'user');
    if (userMessages.length === 0 && !selectedCategory) {
      setShowCategorySelector(true);
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now(),
      conversation_id: currentConversationId || 0,
      sender_type: 'user',
      message_content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);
    setError('');

    try {
      const response: ChatResponse = await apiService.sendMessage({
        message: inputMessage,
        conversation_id: currentConversationId || undefined,
        category: selectedCategory || undefined
      });

      setCurrentConversationId(response.conversation_id);
      
      const botMessage: ChatMessage = {
        id: response.message_id || Date.now() + 1, // Use backend message ID for feedback tracking
        conversation_id: response.conversation_id,
        sender_type: 'bot',
        message_content: response.message,
        timestamp: new Date().toISOString(),
        message_metadata: {
          suggestions: response.suggestions,
          data_sources: response.data_sources,
          incident_required: response.incident_required
        }
      };

      setMessages(prev => [...prev, botMessage]);
      
      if (response.incident_required) {
        // Show incident creation option
        setTimeout(() => {
          const incidentMessage: ChatMessage = {
            id: Date.now() + 2,
            conversation_id: response.conversation_id,
            sender_type: 'system',
            message_content: 'This issue may require escalation to the support team. Would you like me to create an incident ticket?',
            timestamp: new Date().toISOString()
          };
          setMessages(prev => [...prev, incidentMessage]);
        }, 1000);
      }
      
    } catch (err: any) {
      setError('Failed to send message. Please try again.');
      console.error('Send message error:', err);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputMessage(suggestion);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const openIncidentForm = () => {
    // Pre-populate with conversation context
    const lastUserMessage = messages.filter(m => m.sender_type === 'user').pop()?.message_content || '';
    setIncidentForm(prev => ({
      ...prev,
      issueDescription: lastUserMessage
    }));
    setShowIncidentForm(true);
  };

  const handleIncidentFormChange = (field: string, value: string) => {
    setIncidentForm(prev => ({ ...prev, [field]: value }));
  };

  const loadConversationHistory = async () => {
    try {
      setLoadingHistory(true);
      const historyData = await apiService.getConversations();
      setConversations(historyData);
    } catch (err: any) {
      console.error('Failed to load conversation history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadConversation = async (conversationId: number) => {
    try {
      setIsLoading(true);
      const messagesData = await apiService.getConversationMessages(conversationId);
      
      const formattedMessages: ChatMessage[] = messagesData.map((msg: any) => ({
        id: msg.id,
        conversation_id: msg.conversation_id,
        sender_type: msg.sender_type,
        message_content: msg.message_content,
        timestamp: msg.timestamp,
        message_metadata: msg.message_metadata
      }));
      
      setMessages(formattedMessages);
      setCurrentConversationId(conversationId);
      setShowHistory(false);
      
    } catch (err: any) {
      setError('Failed to load conversation');
      console.error('Load conversation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewConversation = () => {
    const welcomeMessage: ChatMessage = {
      id: 0,
      conversation_id: 0,
      sender_type: 'system',
      message_content: `Welcome back to DC AutoAssist, ${user?.full_name}! 🤖\n\nI'm your AI assistant for API support and troubleshooting. Please select a category for your question to get the most relevant assistance.\n\nIf I can't resolve your query, you can create an incident ticket for the support team. How can I help you today?`,
      timestamp: new Date().toISOString()
    };
    
    setMessages([welcomeMessage]);
    setCurrentConversationId(null);
    setShowHistory(false);
    setSelectedCategory(null);
    setShowCategorySelector(false);
  };

  const handleDeleteConversation = (conversationId: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent loading the conversation
    setConversationToDelete(conversationId);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return;
    
    try {
      setDeleting(true);
      await apiService.deleteConversation(conversationToDelete);
      
      // Remove from conversations list
      setConversations(prev => prev.filter(conv => conv.id !== conversationToDelete));
      
      // If this was the current conversation, start a new one
      if (currentConversationId === conversationToDelete) {
        startNewConversation();
      }
      
      setDeleteDialogOpen(false);
      setConversationToDelete(null);
    } catch (err: any) {
      setError('Failed to delete conversation');
      console.error('Delete conversation error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteAllConversations = () => {
    setDeleteAllDialogOpen(true);
  };

  const confirmDeleteAllConversations = async () => {
    try {
      setDeleting(true);
      await apiService.deleteAllConversations();
      
      // Clear conversations and start new chat
      setConversations([]);
      startNewConversation();
      
      setDeleteAllDialogOpen(false);
    } catch (err: any) {
      setError('Failed to delete all conversations');
      console.error('Delete all conversations error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const submitIncident = async () => {
    if (!currentConversationId || !incidentForm.issueDescription.trim()) {
      setError('Issue description is required');
      return;
    }
    
    setCreatingIncident(true);
    try {
      // Call the actual API with proper field mapping
      const response = await apiService.createIncident(currentConversationId, {
        server_name: incidentForm.serverName,
        correlation_id: incidentForm.correlationId,
        job_id: incidentForm.jobId,
        affected_username: incidentForm.affectedUsername,
        issue_description: incidentForm.issueDescription,
        priority: incidentForm.priority,
        category: incidentForm.category,
        user_id: user?.id
      });
      
      const incidentMessage: ChatMessage = {
        id: Date.now() + 3,
        conversation_id: currentConversationId,
        sender_type: 'system',
        message_content: `✅ **Incident Created Successfully!**

**Incident Number:** ${response.incident_id}

**Details:**
• Server: ${incidentForm.serverName || 'Not specified'}
• Correlation ID: ${incidentForm.correlationId || 'Not specified'}
• Job ID: ${incidentForm.jobId || 'Not specified'}
• Affected User: ${incidentForm.affectedUsername || 'Not specified'}
• Priority: ${incidentForm.priority}
• Category: ${incidentForm.category}
• Status: Open

Your issue has been escalated to the support team. You will receive updates via email within 2 business hours.`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, incidentMessage]);
      setShowIncidentForm(false);
      setIncidentForm({
        serverName: '',
        correlationId: '',
        jobId: '',
        affectedUsername: '',
        issueDescription: '',
        priority: 'Medium',
        category: 'API Issue'
      });
      
    } catch (err: any) {
      setError('Failed to create incident. Please try again.');
      console.error('Create incident error:', err);
    } finally {
      setCreatingIncident(false);
    }
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.sender_type === 'user';
    const isSystem = message.sender_type === 'system';
    
    return (
      <Box
        key={message.id}
        sx={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          mb: 2,
          animation: 'fadeInUp 0.3s ease-out'
        }}
      >
        {!isUser && (
          <Avatar
            sx={{
              mr: 1,
              backgroundColor: isSystem ? '#9E9E9E' : '#DB0011',
              width: 28,
              height: 28
            }}
          >
            {isSystem ? <ErrorIcon sx={{ fontSize: 16 }} /> : <BotIcon sx={{ fontSize: 16 }} />}
          </Avatar>
        )}
        
        <Paper
          sx={{
            maxWidth: '70%',
            p: isSystem ? 1.5 : 2,
            backgroundColor: isUser ? '#DB0011' : isSystem ? '#F5F5F5' : '#FFFFFF',
            color: isUser ? 'white' : 'text.primary',
            borderRadius: isUser ? '18px 18px 6px 18px' : '18px 18px 18px 6px',
            boxShadow: isUser ? 'none' : '0 2px 8px rgba(0,0,0,0.1)',
            fontSize: isSystem ? '0.9rem' : '1rem'
          }}
        >
          <Box sx={{ fontSize: isSystem ? '0.9rem' : '1rem', lineHeight: 1.5 }}>
            <ReactMarkdown>{message.message_content}</ReactMarkdown>
          </Box>
          
          {message.message_metadata?.data_sources && (
            <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {message.message_metadata.data_sources.map((source, index) => (
                <Chip
                  key={index}
                  label={source}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: '20px' }}
                />
              ))}
            </Box>
          )}
          
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 1,
              opacity: 0.7,
              fontSize: '0.7rem'
            }}
          >
            {new Date(message.timestamp).toLocaleTimeString()}
          </Typography>
        </Paper>
        
        {/* Add Resolution Feedback for bot messages */}
        {!isUser && !isSystem && message.id && (
          <Box sx={{ width: '70%', ml: !isUser ? 5 : 0 }}>
            <ResolutionFeedback
              conversationId={message.conversation_id}
              messageId={message.id}
              onFeedbackSubmitted={(wasResolved) => {
                // Optional: Update message state or show notification
                console.log('Feedback submitted:', wasResolved);
              }}
            />
          </Box>
        )}
        
        {isUser && (
          <Avatar
            sx={{
              ml: 1,
              backgroundColor: '#666',
              width: 28,
              height: 28
            }}
          >
            <UserIcon sx={{ fontSize: 16 }} />
          </Avatar>
        )}
      </Box>
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2 }}>
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2 }}>
          {/* Header with History Toggle */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ color: '#DB0011', fontWeight: 600 }}>
            DC AutoAssist
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setShowHistory(!showHistory)}
              sx={{
                borderColor: '#DB0011',
                color: '#DB0011',
                textTransform: 'none',
                fontSize: '0.8rem'
              }}
            >
              {showHistory ? 'Hide History' : 'Chat History'}
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={startNewConversation}
              sx={{
                backgroundColor: '#DB0011',
                textTransform: 'none',
                fontSize: '0.8rem',
                '&:hover': { backgroundColor: '#B8000E' }
              }}
            >
              New Chat
            </Button>
          </Box>
        </Box>

        {/* History Panel */}
        {showHistory && (
          <Paper sx={{ mb: 2, p: 2, maxHeight: '200px', overflow: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                📚 Conversation History
              </Typography>
              {conversations.length > 0 && (
                <Button
                  size="small"
                  startIcon={<DeleteSweepIcon />}
                  onClick={handleDeleteAllConversations}
                  sx={{
                    color: '#DB0011',
                    fontSize: '0.7rem',
                    textTransform: 'none',
                    '&:hover': { backgroundColor: 'rgba(219, 0, 17, 0.05)' }
                  }}
                >
                  Delete All
                </Button>
              )}
            </Box>
            {loadingHistory ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="caption">Loading...</Typography>
              </Box>
            ) : conversations.length === 0 ? (
              <Typography variant="caption" color="text.secondary">
                No previous conversations found
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {conversations.slice(0, 10).map((conv) => (
                  <Box
                    key={conv.id}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      borderRadius: 1,
                      backgroundColor: currentConversationId === conv.id ? 'rgba(219, 0, 17, 0.1)' : 'transparent',
                      '&:hover': { backgroundColor: 'rgba(219, 0, 17, 0.05)' }
                    }}
                  >
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => loadConversation(conv.id)}
                      sx={{
                        flex: 1,
                        justifyContent: 'flex-start',
                        textAlign: 'left',
                        textTransform: 'none',
                        fontSize: '0.8rem',
                        p: 1
                      }}
                    >
                      <Box>
                        <Typography variant="caption" sx={{ fontWeight: 500, display: 'block' }}>
                          {new Date(conv.created_at).toLocaleDateString()}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {conv.title || `Conversation ${conv.id}`} • {conv.message_count} messages
                        </Typography>
                      </Box>
                    </Button>
                    <IconButton
                      size="small"
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      sx={{
                        color: '#DB0011',
                        opacity: 0.7,
                        '&:hover': { opacity: 1, backgroundColor: 'rgba(219, 0, 17, 0.1)' }
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>
        )}

        {/* Chat Messages */}
          <Paper
            sx={{
              flex: 1,
              p: 2,
              mb: 2,
              overflow: 'auto',
              backgroundColor: '#f8f9fa',
              maxHeight: showHistory ? 'calc(100vh - 500px)' : 'calc(100vh - 300px)',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
              {messages.map(renderMessage)}
              
            {isTyping && (
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ mr: 1, backgroundColor: '#DB0011', width: 28, height: 28 }}>
                  <BotIcon sx={{ fontSize: 16 }} />
                </Avatar>
                <Paper sx={{ p: 1.5, backgroundColor: 'white' }}>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {[1, 2, 3].map((dot) => (
                      <Box
                        key={dot}
                        className="typing-dot"
                        sx={{
                          width: 6,
                          height: 6,
                          backgroundColor: '#DB0011',
                          borderRadius: '50%'
                        }}
                      />
                    ))}
                  </Box>
                </Paper>
              </Box>
            )}              <div ref={messagesEndRef} />
            </Box>
          </Paper>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* Action Buttons */}
          <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              onClick={() => setShowCategorySelector(true)}
              startIcon={<AddIcon sx={{ fontSize: 16 }} />}
              sx={{
                borderColor: '#2196F3',
                color: '#2196F3',
                fontSize: '0.85rem',
                textTransform: 'none',
                py: 0.5,
                '&:hover': {
                  borderColor: '#1976D2',
                  backgroundColor: 'rgba(33, 150, 243, 0.1)'
                }
              }}
            >
              Select Category
            </Button>
            <Button
              variant="outlined"
              color="warning"
              onClick={openIncidentForm}
              disabled={!currentConversationId}
              startIcon={<ErrorIcon sx={{ fontSize: 16 }} />}
              sx={{
                borderColor: '#FF9800',
                color: '#FF9800',
                fontSize: '0.85rem',
                textTransform: 'none',
                py: 0.5,
                '&:hover': {
                  borderColor: '#F57C00',
                  backgroundColor: 'rgba(255, 152, 0, 0.1)'
                }
              }}
            >
              Create Incident
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Choose category for better responses • Escalate unresolved issues
            </Typography>
          </Box>

          {/* Category Selection Display */}
          {selectedCategory && (
            <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Category:
              </Typography>
              <Chip
                label={categoryOptions.find(opt => opt.id === selectedCategory)?.title}
                size="small"
                sx={{
                  backgroundColor: categoryOptions.find(opt => opt.id === selectedCategory)?.color,
                  color: 'white',
                  fontWeight: 500
                }}
                onDelete={() => {
                  setSelectedCategory(null);
                  setShowCategorySelector(false);
                }}
              />
            </Box>
          )}

          {/* Input Area */}
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                selectedCategory 
                  ? `Describe your ${categoryOptions.find(opt => opt.id === selectedCategory)?.title.toLowerCase()} question...`
                  : "Type your message or select a category..."
              }
              disabled={isLoading}
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '0.95rem',
                  '&.Mui-focused fieldset': {
                    borderColor: '#DB0011'
                  }
                },
                '& .MuiInputBase-input::placeholder': {
                  fontSize: '0.9rem',
                  opacity: 0.7
                }
              }}
            />
            <Button
              variant="contained"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              sx={{
                minWidth: 'auto',
                p: 1.2,
                backgroundColor: '#DB0011',
                '&:hover': {
                  backgroundColor: '#B8000E'
                }
              }}
            >
              {isLoading ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                <SendIcon sx={{ fontSize: 20 }} />
              )}
            </Button>
          </Box>
        </Box>

        {/* Category Selection Dialog */}
        <Dialog
          open={showCategorySelector}
          onClose={() => setShowCategorySelector(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ backgroundColor: '#DB0011', color: 'white', fontSize: '1.1rem' }}>
            🏷️ Select Question Category
          </DialogTitle>
          <DialogContent sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Please select the category that best matches your question to get the most relevant assistance.
            </Typography>
            
            <Grid container spacing={2}>
              {categoryOptions.map((option) => (
                <Grid item xs={12} sm={6} key={option.id}>
                  <Paper
                    onClick={() => {
                      setSelectedCategory(option.id);
                      setShowCategorySelector(false);
                      // Auto-send the message after category selection
                      setTimeout(() => {
                        if (inputMessage.trim()) {
                          sendMessage();
                        }
                      }, 100);
                    }}
                    sx={{
                      p: 2,
                      cursor: 'pointer',
                      textAlign: 'center',
                      border: '2px solid transparent',
                      transition: 'all 0.2s ease-in-out',
                      '&:hover': {
                        borderColor: option.color,
                        backgroundColor: `${option.color}10`,
                        transform: 'translateY(-2px)',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                      }
                    }}
                  >
                    <Typography
                      variant="h4"
                      sx={{ mb: 1, fontSize: '2rem' }}
                    >
                      {option.icon}
                    </Typography>
                    <Typography
                      variant="subtitle1"
                      sx={{
                        fontWeight: 600,
                        color: option.color,
                        mb: 1
                      }}
                    >
                      {option.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ fontSize: '0.85rem', lineHeight: 1.4 }}
                    >
                      {option.description}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </DialogContent>
          <DialogActions sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
            <Button 
              onClick={() => {
                setShowCategorySelector(false);
                setInputMessage('');
              }}
              color="inherit"
              sx={{ textTransform: 'none' }}
            >
              Cancel
            </Button>
          </DialogActions>
        </Dialog>

        {/* Incident Creation Dialog */}
        <Dialog 
          open={showIncidentForm} 
          onClose={() => setShowIncidentForm(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ backgroundColor: '#DB0011', color: 'white', fontSize: '1.1rem' }}>
            🎫 Create Support Incident
          </DialogTitle>
          <DialogContent sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Please provide detailed information to help our support team resolve your issue quickly.
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Server Name"
                  value={incidentForm.serverName}
                  onChange={(e) => handleIncidentFormChange('serverName', e.target.value)}
                  placeholder="e.g., api-prod-01, web-server-02"
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Correlation ID"
                  value={incidentForm.correlationId}
                  onChange={(e) => handleIncidentFormChange('correlationId', e.target.value)}
                  placeholder="e.g., abc123-def456-ghi789"
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Job ID"
                  value={incidentForm.jobId}
                  onChange={(e) => handleIncidentFormChange('jobId', e.target.value)}
                  placeholder="e.g., JOB_20241116_001"
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Affected Username"
                  value={incidentForm.affectedUsername}
                  onChange={(e) => handleIncidentFormChange('affectedUsername', e.target.value)}
                  placeholder="Username experiencing the issue"
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Priority</InputLabel>
                  <Select
                    value={incidentForm.priority}
                    label="Priority"
                    onChange={(e) => handleIncidentFormChange('priority', e.target.value)}
                  >
                    <MenuItem value="Low">Low</MenuItem>
                    <MenuItem value="Medium">Medium</MenuItem>
                    <MenuItem value="High">High</MenuItem>
                    <MenuItem value="Critical">Critical</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={incidentForm.category}
                    label="Category"
                    onChange={(e) => handleIncidentFormChange('category', e.target.value)}
                  >
                    <MenuItem value="API Issue">API Issue</MenuItem>
                    <MenuItem value="Authentication">Authentication</MenuItem>
                    <MenuItem value="Performance">Performance</MenuItem>
                    <MenuItem value="Database">Database</MenuItem>
                    <MenuItem value="Network">Network</MenuItem>
                    <MenuItem value="Other">Other</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Issue Description *"
                  value={incidentForm.issueDescription}
                  onChange={(e) => handleIncidentFormChange('issueDescription', e.target.value)}
                  placeholder="Provide detailed description of the issue, steps to reproduce, error messages, etc."
                  required
                  sx={{ mb: 2 }}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
            <Button 
              onClick={() => setShowIncidentForm(false)}
              color="inherit"
              sx={{ textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button 
              onClick={submitIncident}
              variant="contained"
              disabled={creatingIncident || !incidentForm.issueDescription.trim()}
              startIcon={creatingIncident ? <CircularProgress size={16} /> : null}
              sx={{
                backgroundColor: '#DB0011',
                textTransform: 'none',
                '&:hover': { backgroundColor: '#B8000E' }
              }}
            >
              {creatingIncident ? 'Creating Incident...' : 'Create Incident'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete Conversation Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Delete Conversation</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete this conversation? This action cannot be undone.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button 
              onClick={() => setDeleteDialogOpen(false)}
              color="inherit"
              sx={{ textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button 
              onClick={confirmDeleteConversation}
              variant="contained"
              disabled={deleting}
              startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
              sx={{
                backgroundColor: '#DB0011',
                textTransform: 'none',
                '&:hover': { backgroundColor: '#B8000E' }
              }}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete All Conversations Confirmation Dialog */}
        <Dialog open={deleteAllDialogOpen} onClose={() => setDeleteAllDialogOpen(false)}>
          <DialogTitle>Delete All Chat History</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete ALL your chat conversations? This will permanently remove all your chat history and cannot be undone.
            </Typography>
            <Typography sx={{ mt: 2, fontWeight: 'bold', color: '#DB0011' }}>
              {conversations.length} conversations will be deleted.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button 
              onClick={() => setDeleteAllDialogOpen(false)}
              color="inherit"
              sx={{ textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button 
              onClick={confirmDeleteAllConversations}
              variant="contained"
              disabled={deleting}
              startIcon={deleting ? <CircularProgress size={16} /> : <DeleteSweepIcon />}
              sx={{
                backgroundColor: '#DB0011',
                textTransform: 'none',
                '&:hover': { backgroundColor: '#B8000E' }
              }}
            >
              {deleting ? 'Deleting...' : 'Delete All'}
            </Button>
          </DialogActions>
        </Dialog>
    </Box>
  );
};

export default ChatPage;