import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  ButtonGroup,
  Rating,
  TextField,
  Box,
  Alert,
  Collapse
} from '@mui/material';
import {
  ThumbUp,
  ThumbDown,
  CheckCircle,
  HelpOutline
} from '@mui/icons-material';
import { apiService } from '../services/api';

interface ResolutionFeedbackProps {
  conversationId: number;
  messageId: number;
  onFeedbackSubmitted?: (wasResolved: boolean) => void;
}

interface FeedbackData {
  was_resolved: boolean;
  resolution_rating?: number;
  feedback_comment?: string;
}

const ResolutionFeedback: React.FC<ResolutionFeedbackProps> = ({
  conversationId,
  messageId,
  onFeedbackSubmitted
}) => {
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [wasResolved, setWasResolved] = useState<boolean | null>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [showDetailedFeedback, setShowDetailedFeedback] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleResolutionFeedback = async (resolved: boolean) => {
    setWasResolved(resolved);
    
    if (resolved) {
      setShowDetailedFeedback(true);
    } else {
      // For unresolved issues, submit immediately
      await submitFeedback(resolved, null, '');
    }
  };

  const submitFeedback = async (resolved: boolean, userRating?: number | null, userComment?: string) => {
    setSubmitting(true);
    setError('');

    try {
      const feedbackData: FeedbackData = {
        was_resolved: resolved,
      };

      if (resolved && userRating) {
        feedbackData.resolution_rating = userRating;
      }

      if (userComment) {
        feedbackData.feedback_comment = userComment;
      }

      await apiService.submitResolutionFeedback(conversationId, messageId, feedbackData);
      
      setFeedbackGiven(true);
      setSuccess(true);
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(resolved);
      }

      // Auto-hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDetailedSubmit = async () => {
    if (wasResolved !== null) {
      await submitFeedback(wasResolved, rating, comment);
    }
  };

  if (feedbackGiven && !showDetailedFeedback) {
    return (
      <Box sx={{ mt: 2 }}>
        <Alert 
          severity={wasResolved ? "success" : "info"} 
          icon={<CheckCircle />}
          sx={{ 
            backgroundColor: wasResolved ? '#e8f5e8' : '#e3f2fd',
            border: `1px solid ${wasResolved ? '#4caf50' : '#2196f3'}`
          }}
        >
          <Typography variant="body2">
            {wasResolved 
              ? "✅ Great! Thanks for confirming this resolved your query."
              : "📝 Thanks for the feedback. We'll work on improving our responses."
            }
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 2 }}>
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Feedback submitted successfully! Thank you for helping us improve.
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!feedbackGiven && (
        <Card 
          variant="outlined" 
          sx={{ 
            backgroundColor: '#f8f9fa',
            border: '1px solid #e0e0e0',
            borderRadius: 2
          }}
        >
          <CardContent sx={{ py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <HelpOutline sx={{ fontSize: 20, color: '#666', mr: 1 }} />
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                Did this response resolve your query?
              </Typography>
            </Box>
            
            <ButtonGroup 
              variant="outlined" 
              size="small"
              disabled={submitting}
              sx={{ mb: showDetailedFeedback ? 2 : 0 }}
            >
              <Button
                startIcon={<ThumbUp />}
                onClick={() => handleResolutionFeedback(true)}
                color="success"
                variant={wasResolved === true ? "contained" : "outlined"}
                sx={{ 
                  textTransform: 'none',
                  borderRadius: '20px 0 0 20px',
                  px: 2
                }}
              >
                Yes, resolved
              </Button>
              <Button
                startIcon={<ThumbDown />}
                onClick={() => handleResolutionFeedback(false)}
                color="error"
                variant={wasResolved === false ? "contained" : "outlined"}
                sx={{ 
                  textTransform: 'none',
                  borderRadius: '0 20px 20px 0',
                  px: 2
                }}
              >
                No, not resolved
              </Button>
            </ButtonGroup>

            {/* Detailed feedback form for resolved queries */}
            <Collapse in={showDetailedFeedback}>
              <Box sx={{ mt: 2, p: 2, backgroundColor: '#fff', borderRadius: 1, border: '1px solid #e0e0e0' }}>
                <Typography variant="body2" fontWeight={500} gutterBottom>
                  🌟 Please rate the quality of this solution:
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Rating
                    value={rating}
                    onChange={(event, newValue) => setRating(newValue)}
                    size="small"
                    precision={1}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    {rating ? `${rating} out of 5 stars` : 'Rate this solution'}
                  </Typography>
                </Box>

                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  placeholder="Any additional feedback? (optional)"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  variant="outlined"
                  size="small"
                  sx={{ mb: 2 }}
                />

                <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                  <Button
                    size="small"
                    onClick={() => setShowDetailedFeedback(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={handleDetailedSubmit}
                    disabled={submitting}
                    sx={{ 
                      backgroundColor: '#DB0011', 
                      '&:hover': { backgroundColor: '#b30010' }
                    }}
                  >
                    {submitting ? 'Submitting...' : 'Submit Feedback'}
                  </Button>
                </Box>
              </Box>
            </Collapse>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default ResolutionFeedback;