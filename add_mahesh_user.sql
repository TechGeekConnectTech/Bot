-- Add Mahesh Gavandar user to HSBC AutoAssist database

-- First, let's check if user already exists
SELECT 'Checking for existing user...' as status;
SELECT id, username, email FROM users WHERE username = 'mahesh.gavandar' OR email = 'mahesh.gavandar@hsbc.com';

-- Insert new user with hashed password (bcrypt hash of 'abcd1234')
INSERT INTO users (
    username, 
    email, 
    full_name, 
    hashed_password, 
    department, 
    role, 
    is_active, 
    created_at, 
    updated_at
) VALUES (
    'mahesh.gavandar',
    'mahesh.gavandar@hsbc.com',
    'Mahesh Gavandar',
    '$2b$12$5pUFVQ.UgfBJNQjImsm/sulkHLYi.lgxiVBtLVtkQsSO2IA0ndy5K',  -- bcrypt hash of 'abcd1234'
    'DC Automation Support',
    'user',
    TRUE,
    NOW(),
    NOW()
);

-- Verify the user was added
SELECT 'New user added:' as status;
SELECT id, username, email, full_name, department, role, is_active, created_at 
FROM users 
WHERE username = 'mahesh.gavandar';

-- Show all users for reference
SELECT 'All users in system:' as status;
SELECT id, username, email, full_name, department, role, is_active 
FROM users 
ORDER BY created_at DESC;