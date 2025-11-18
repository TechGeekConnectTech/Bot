-- HSBC AutoAssist Database Schema
-- Created for DC Automation Support Team

CREATE DATABASE IF NOT EXISTS hsbc_autoassist;
USE hsbc_autoassist;

-- Users Table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) DEFAULT 'DC Automation Support',
    role ENUM('user', 'admin', 'support') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_department (department)
);

-- Chat Conversations Table
CREATE TABLE chat_conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    status ENUM('active', 'resolved', 'escalated') DEFAULT 'active',
    priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
);

-- Chat Messages Table
CREATE TABLE chat_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    sender_type ENUM('user', 'bot', 'system') NOT NULL,
    message_content TEXT NOT NULL,
    message_metadata JSON NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sender_type (sender_type),
    INDEX idx_timestamp (timestamp)
);

-- Query Resolutions Table
CREATE TABLE query_resolutions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    query_type ENUM('auth_issue', 'payload_issue', 'resource_lock', 'performance_issue', 'configuration_issue', 'other') NOT NULL,
    server_name VARCHAR(100) NULL,
    correlation_id VARCHAR(100) NULL,
    root_cause TEXT NULL,
    resolution_steps TEXT NULL,
    data_sources_used JSON NULL,
    incident_created BOOLEAN DEFAULT FALSE,
    incident_id VARCHAR(50) NULL,
    resolved_automatically BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_query_type (query_type),
    INDEX idx_server_name (server_name),
    INDEX idx_correlation_id (correlation_id),
    INDEX idx_incident_created (incident_created),
    INDEX idx_resolved_automatically (resolved_automatically)
);

-- API Integration Logs Table
CREATE TABLE api_integration_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NULL,
    service_name ENUM('splunk', 'ansible', 'gpt4o', 'other') NOT NULL,
    request_data JSON NULL,
    response_data JSON NULL,
    status_code INT NULL,
    error_message TEXT NULL,
    response_time_ms INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE SET NULL,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_service_name (service_name),
    INDEX idx_status_code (status_code),
    INDEX idx_created_at (created_at)
);

-- User Sessions Table
CREATE TABLE user_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_token (session_token),
    INDEX idx_expires_at (expires_at)
);

-- System Configuration Table
CREATE TABLE system_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT NULL,
    is_sensitive BOOLEAN DEFAULT FALSE,
    updated_by INT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_config_key (config_key)
);

-- Insert Initial Data

-- Default Admin User (password: admin123)
INSERT INTO users (username, email, hashed_password, full_name, department, role) VALUES 
('admin', 'admin@hsbc.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2TQ.1X6.5m', 'System Administrator', 'DC Automation Support', 'admin');

-- Sample Support User (password: support123)
INSERT INTO users (username, email, hashed_password, full_name, department, role) VALUES 
('support_user', 'support@hsbc.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2TQ.1X6.5m', 'Support Team Lead', 'DC Automation Support', 'support');

-- System Configuration
INSERT INTO system_config (config_key, config_value, description) VALUES 
('bot_name', 'DC AutoAssist', 'Official name of the chatbot'),
('company_name', 'HSBC', 'Company name for branding'),
('department_name', 'DC Automation Support Team', 'Department using the chatbot'),
('max_conversation_length', '100', 'Maximum messages per conversation'),
('session_timeout_minutes', '480', 'Session timeout in minutes (8 hours)'),
('enable_external_apis', 'true', 'Enable integration with external APIs'),
('default_query_priority', 'medium', 'Default priority for new queries'),
('auto_escalation_threshold', '3', 'Auto-escalate after N failed resolution attempts');

-- Create Views for Analytics

CREATE VIEW conversation_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_conversations,
    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_conversations,
    COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated_conversations,
    COUNT(CASE WHEN priority = 'high' OR priority = 'critical' THEN 1 END) as high_priority_conversations
FROM chat_conversations
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE VIEW user_activity AS
SELECT 
    u.id,
    u.username,
    u.full_name,
    u.department,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(DISTINCT qr.id) as total_queries,
    COUNT(CASE WHEN qr.resolved_automatically = TRUE THEN 1 END) as auto_resolved_queries,
    u.last_login
FROM users u
LEFT JOIN chat_conversations c ON u.id = c.user_id
LEFT JOIN query_resolutions qr ON c.id = qr.conversation_id
GROUP BY u.id, u.username, u.full_name, u.department, u.last_login;

CREATE VIEW daily_metrics AS
SELECT 
    DATE(c.created_at) as date,
    COUNT(DISTINCT c.id) as conversations,
    COUNT(DISTINCT c.user_id) as active_users,
    COUNT(DISTINCT qr.id) as total_queries,
    COUNT(CASE WHEN qr.resolved_automatically = TRUE THEN 1 END) as auto_resolved,
    ROUND(COUNT(CASE WHEN qr.resolved_automatically = TRUE THEN 1 END) * 100.0 / COUNT(DISTINCT qr.id), 2) as resolution_rate
FROM chat_conversations c
LEFT JOIN query_resolutions qr ON c.id = qr.conversation_id
GROUP BY DATE(c.created_at)
ORDER BY date DESC;

-- Create Stored Procedures

DELIMITER //

CREATE PROCEDURE GetDashboardStats()
BEGIN
    DECLARE total_users INT DEFAULT 0;
    DECLARE total_conversations INT DEFAULT 0;
    DECLARE total_queries_resolved INT DEFAULT 0;
    DECLARE active_conversations INT DEFAULT 0;
    DECLARE queries_today INT DEFAULT 0;
    
    SELECT COUNT(*) INTO total_users FROM users WHERE is_active = TRUE;
    SELECT COUNT(*) INTO total_conversations FROM chat_conversations;
    SELECT COUNT(*) INTO total_queries_resolved FROM query_resolutions WHERE resolved_automatically = TRUE;
    SELECT COUNT(*) INTO active_conversations FROM chat_conversations WHERE status = 'active';
    SELECT COUNT(*) INTO queries_today FROM chat_conversations WHERE DATE(created_at) = CURDATE();
    
    SELECT 
        total_users,
        total_conversations,
        total_queries_resolved,
        active_conversations,
        queries_today,
        CASE 
            WHEN (SELECT COUNT(*) FROM query_resolutions) > 0 
            THEN ROUND(total_queries_resolved * 100.0 / (SELECT COUNT(*) FROM query_resolutions), 2)
            ELSE 0 
        END as resolution_rate;
END //

CREATE PROCEDURE CleanupOldSessions()
BEGIN
    DELETE FROM user_sessions WHERE expires_at < NOW();
    SELECT ROW_COUNT() as deleted_sessions;
END //

DELIMITER ;

-- Create Indexes for Performance
CREATE INDEX idx_messages_conversation_timestamp ON chat_messages(conversation_id, timestamp);
CREATE INDEX idx_resolutions_type_created ON query_resolutions(query_type, created_at);
CREATE INDEX idx_logs_service_created ON api_integration_logs(service_name, created_at);

-- Grant Permissions
GRANT ALL PRIVILEGES ON hsbc_autoassist.* TO 'root'@'localhost';
FLUSH PRIVILEGES;

SELECT 'HSBC AutoAssist Database Schema Created Successfully!' as Status;