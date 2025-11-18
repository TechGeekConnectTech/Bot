from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="active")  # active, resolved, escalated
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    sender_type = Column(String(20), nullable=False)  # user, bot, system
    message_content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store additional data like API responses
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")

class QueryResolution(Base):
    __tablename__ = "query_resolutions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    query_type = Column(String(50), nullable=False)  # auth_issue, payload_issue, resource_lock, other
    server_name = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True)
    root_cause = Column(Text, nullable=True)
    resolution_steps = Column(Text, nullable=True)
    data_sources_used = Column(JSON, nullable=True)  # splunk, ansible, etc.
    incident_created = Column(Boolean, default=False)
    incident_id = Column(String(50), nullable=True)
    resolved_automatically = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation")