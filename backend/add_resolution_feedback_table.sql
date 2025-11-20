-- Add Resolution Feedback table for tracking query resolution rates
-- Run this SQL script in your MySQL database

USE hsbc_autoassist;

CREATE TABLE IF NOT EXISTS resolution_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    message_id INT NOT NULL,
    user_id INT NOT NULL,
    
    -- Resolution feedback
    was_resolved BOOLEAN NOT NULL,
    resolution_rating INT DEFAULT NULL CHECK (resolution_rating >= 1 AND resolution_rating <= 5),
    feedback_comment TEXT DEFAULT NULL,
    
    -- Metadata
    response_time INT DEFAULT NULL COMMENT 'Time from bot response to user feedback (seconds)',
    category VARCHAR(50) DEFAULT NULL,
    ai_service_used VARCHAR(50) DEFAULT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes for better performance
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_was_resolved (was_resolved),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at),
    
    -- Unique constraint to prevent duplicate feedback for same message
    UNIQUE KEY unique_message_feedback (message_id, user_id)
);

-- Add some sample data for testing (optional)
INSERT INTO resolution_feedback (conversation_id, message_id, user_id, was_resolved, resolution_rating, feedback_comment, category, ai_service_used) 
VALUES 
(1, 2, 1, TRUE, 5, 'Perfect solution! Fixed the 404 error immediately.', 'hsbc_internal', 'openai_technical_analysis'),
(2, 4, 2, TRUE, 4, 'Good explanation of API concepts.', 'general', 'openai_educational'),
(3, 6, 1, FALSE, 2, 'Did not fully resolve my authentication issue.', 'hsbc_internal', 'fallback')
ON DUPLICATE KEY UPDATE was_resolved=VALUES(was_resolved);

SELECT 'Resolution Feedback table created successfully!' as status;