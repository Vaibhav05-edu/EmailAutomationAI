"""
Tests for the Email Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.email_agent.agent import EmailAgent
from src.email_agent.config import Config, EmailConfig, AIConfig, AgentConfig
from src.email_agent.email_client import EmailMessage
from src.email_agent.ai_processor import EmailAnalysis, EmailCategory


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        email=EmailConfig(
            provider="gmail",
            username="test@example.com",
            password="test_password"
        ),
        ai=AIConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test_key"
        ),
        agent=AgentConfig(
            check_interval=60,
            max_emails_per_batch=5,
            auto_reply=False,
            require_confirmation=True
        )
    )


@pytest.fixture
def sample_email():
    """Create a sample email for testing."""
    return EmailMessage(
        uid="123",
        subject="Test Email",
        sender="sender@example.com",
        recipient="test@example.com",
        body="This is a test email body.",
        date=datetime.now(),
        is_read=False
    )


@pytest.fixture
def sample_analysis():
    """Create a sample email analysis for testing."""
    return EmailAnalysis(
        category=EmailCategory.BUSINESS,
        sentiment="neutral",
        priority=3,
        requires_response=True,
        suggested_actions=["reply"],
        confidence=0.8
    )


class TestEmailAgent:
    """Test cases for EmailAgent class."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_config):
        """Test that EmailAgent initializes correctly."""
        agent = EmailAgent(mock_config)
        
        assert agent.config == mock_config
        assert agent.is_running is False
        assert isinstance(agent.processed_emails, dict)
        assert len(agent.processed_emails) == 0
    
    @pytest.mark.asyncio 
    async def test_stop_agent(self, mock_config):
        """Test stopping the email agent."""
        agent = EmailAgent(mock_config)
        agent.is_running = True
        
        with patch.object(agent.email_client, 'disconnect') as mock_disconnect:
            await agent.stop()
            
            assert agent.is_running is False
            mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_email(self, mock_config, sample_email, sample_analysis):
        """Test processing a single email."""
        agent = EmailAgent(mock_config)
        
        # Mock dependencies
        with patch.object(agent, '_apply_rules', return_value=[]) as mock_apply_rules, \
             patch.object(agent.email_client, 'mark_as_read', new_callable=AsyncMock) as mock_mark_read:
            
            await agent._process_single_email(sample_email, sample_analysis)
            
            # Verify email was processed
            assert sample_email.uid in agent.processed_emails
            mock_apply_rules.assert_called_once()
            mock_mark_read.assert_called_once_with(sample_email.uid)
    
    @pytest.mark.asyncio
    async def test_email_batch_processing_no_emails(self, mock_config):
        """Test batch processing when no emails are available."""
        agent = EmailAgent(mock_config)
        
        with patch.object(agent.email_client, 'fetch_unread_emails', 
                         new_callable=AsyncMock, return_value=[]) as mock_fetch:
            
            await agent._process_email_batch()
            
            mock_fetch.assert_called_once_with(limit=5)  # max_emails_per_batch
    
    @pytest.mark.asyncio
    async def test_email_batch_processing_with_emails(self, mock_config, sample_email, sample_analysis):
        """Test batch processing with emails."""
        agent = EmailAgent(mock_config)
        emails = [sample_email]
        analyses = [sample_analysis]
        
        with patch.object(agent.email_client, 'fetch_unread_emails', 
                         new_callable=AsyncMock, return_value=emails) as mock_fetch, \
             patch.object(agent.ai_processor, 'classify_batch', 
                         new_callable=AsyncMock, return_value=analyses) as mock_classify, \
             patch.object(agent, '_process_single_email', 
                         new_callable=AsyncMock) as mock_process:
            
            await agent._process_email_batch()
            
            mock_fetch.assert_called_once_with(limit=5)
            mock_classify.assert_called_once_with(emails)
            mock_process.assert_called_once_with(sample_email, sample_analysis)
    
    def test_rule_matching_subject_contains(self, mock_config, sample_email, sample_analysis):
        """Test rule matching based on subject contains."""
        agent = EmailAgent(mock_config)
        
        # Create a rule that should match
        from src.email_agent.config import ProcessingRule
        rule = ProcessingRule(
            name="test_rule",
            conditions={"subject_contains": ["test"]},
            actions=[{"type": "archive"}]
        )
        
        # Test matching
        result = agent._rule_matches(sample_email, sample_analysis, rule)
        assert result is True
        
        # Test non-matching
        rule.conditions = {"subject_contains": ["nonexistent"]}
        result = agent._rule_matches(sample_email, sample_analysis, rule)
        assert result is False
    
    def test_rule_matching_from_domain(self, mock_config, sample_email, sample_analysis):
        """Test rule matching based on sender domain."""
        agent = EmailAgent(mock_config)
        
        from src.email_agent.config import ProcessingRule
        rule = ProcessingRule(
            name="domain_rule",
            conditions={"from_domain": ["example.com"]},
            actions=[{"type": "mark_read"}]
        )
        
        result = agent._rule_matches(sample_email, sample_analysis, rule)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_execute_archive_action(self, mock_config, sample_email, sample_analysis):
        """Test executing archive action."""
        agent = EmailAgent(mock_config)
        
        from src.email_agent.config import ProcessingRule
        rule = ProcessingRule(
            name="archive_rule",
            conditions={},
            actions=[{"type": "archive"}]
        )
        
        with patch.object(agent.email_client, 'archive_email', 
                         new_callable=AsyncMock) as mock_archive:
            
            await agent._execute_rule_actions(sample_email, sample_analysis, rule)
            mock_archive.assert_called_once_with(sample_email.uid)
    
    @pytest.mark.asyncio
    async def test_execute_forward_action(self, mock_config, sample_email, sample_analysis):
        """Test executing forward action."""
        agent = EmailAgent(mock_config)
        
        from src.email_agent.config import ProcessingRule
        rule = ProcessingRule(
            name="forward_rule",
            conditions={},
            actions=[{"type": "forward", "to": "manager@example.com"}]
        )
        
        with patch.object(agent.email_client, 'send_email', 
                         new_callable=AsyncMock) as mock_send:
            
            await agent._execute_rule_actions(sample_email, sample_analysis, rule)
            mock_send.assert_called_once()
            
            # Check the call arguments
            args, kwargs = mock_send.call_args
            assert args[0] == "manager@example.com"  # to
            assert args[1].startswith("FWD:")  # subject