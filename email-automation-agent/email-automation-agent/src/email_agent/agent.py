"""
Main Email Agent - Orchestrates email automation workflow.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from .config import Config, ProcessingRule
from .email_client import EmailClient, EmailMessage
from .ai_processor import AIProcessor, EmailAnalysis

logger = logging.getLogger(__name__)


class EmailAgent:
    """Main email automation agent."""
    
    def __init__(self, config: Config):
        self.config = config
        self.email_client = EmailClient(config.email)
        self.ai_processor = AIProcessor(config.ai)
        self.is_running = False
        self.processed_emails: Dict[str, datetime] = {}
    
    async def run(self):
        """Start the email agent main loop."""
        logger.info("Email Agent starting...")
        self.is_running = True
        
        try:
            # Initial connection setup
            await self.email_client.connect_imap()
            
            while self.is_running:
                await self._process_email_batch()
                
                logger.info(f"Sleeping for {self.config.agent.check_interval} seconds...")
                await asyncio.sleep(self.config.agent.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping agent...")
            await self.stop()
        except Exception as e:
            logger.error(f"Error in agent main loop: {e}")
            raise
    
    async def stop(self):
        """Stop the email agent."""
        logger.info("Stopping Email Agent...")
        self.is_running = False
        self.email_client.disconnect()
    
    async def _process_email_batch(self):
        """Process a batch of unread emails."""
        try:
            # Fetch unread emails
            emails = await self.email_client.fetch_unread_emails(
                limit=self.config.agent.max_emails_per_batch
            )
            
            if not emails:
                logger.info("No new emails to process")
                return
            
            logger.info(f"Processing {len(emails)} emails...")
            
            # Analyze emails with AI
            analyses = await self.ai_processor.classify_batch(emails)
            
            # Process each email based on analysis and rules
            for email, analysis in zip(emails, analyses):
                await self._process_single_email(email, analysis)
            
            logger.info(f"Completed processing {len(emails)} emails")
            
        except Exception as e:
            logger.error(f"Error processing email batch: {e}")
    
    async def _process_single_email(self, email: EmailMessage, analysis: EmailAnalysis):
        """Process a single email based on analysis and rules."""
        try:
            logger.info(f"Processing email: {email.subject[:50]}... from {email.sender}")
            logger.info(f"Analysis: {analysis.category.value}, Priority: {analysis.priority}")
            
            # Skip if already processed
            if email.uid in self.processed_emails:
                logger.debug(f"Email {email.uid} already processed, skipping")
                return
            
            # Apply processing rules
            applied_rules = self._apply_rules(email, analysis)
            
            # Execute rule actions
            for rule in applied_rules:
                await self._execute_rule_actions(email, analysis, rule)
            
            # Generate and send response if needed
            if analysis.requires_response and not self.config.agent.require_confirmation:
                if self.config.agent.auto_reply:
                    await self._generate_and_send_response(email, analysis)
                else:
                    logger.info(f"Email requires response but auto_reply is disabled: {email.subject}")
            
            # Mark as processed
            self.processed_emails[email.uid] = datetime.now()
            
            # Mark as read if not urgent
            if analysis.priority < 4:
                await self.email_client.mark_as_read(email.uid)
            
        except Exception as e:
            logger.error(f"Error processing email {email.uid}: {e}")
    
    def _apply_rules(self, email: EmailMessage, analysis: EmailAnalysis) -> List[ProcessingRule]:
        """Apply processing rules to determine actions."""
        applied_rules = []
        
        for rule in self.config.rules:
            if self._rule_matches(email, analysis, rule):
                logger.info(f"Rule '{rule.name}' matched for email: {email.subject}")
                applied_rules.append(rule)
        
        return applied_rules
    
    def _rule_matches(self, email: EmailMessage, analysis: EmailAnalysis, rule: ProcessingRule) -> bool:
        """Check if a processing rule matches the email."""
        conditions = rule.conditions
        
        # Check subject conditions
        if 'subject_contains' in conditions:
            for keyword in conditions['subject_contains']:
                if keyword.lower() in email.subject.lower():
                    return True
        
        # Check sender domain conditions
        if 'from_domain' in conditions:
            sender_domain = email.sender.split('@')[-1] if '@' in email.sender else ''
            if sender_domain in conditions['from_domain']:
                return True
        
        # Check sender contains conditions
        if 'from_contains' in conditions:
            for keyword in conditions['from_contains']:
                if keyword.lower() in email.sender.lower():
                    return True
        
        # Check category conditions
        if 'category' in conditions:
            if analysis.category.value in conditions['category']:
                return True
        
        # Check priority conditions
        if 'min_priority' in conditions:
            if analysis.priority >= conditions['min_priority']:
                return True
        
        return False
    
    async def _execute_rule_actions(self, email: EmailMessage, analysis: EmailAnalysis, rule: ProcessingRule):
        """Execute actions defined in a processing rule."""
        for action in rule.actions:
            action_type = action.get('type')
            
            try:
                if action_type == 'archive':
                    await self.email_client.archive_email(email.uid)
                    logger.info(f"Archived email: {email.subject}")
                
                elif action_type == 'mark_read':
                    await self.email_client.mark_as_read(email.uid)
                    logger.info(f"Marked as read: {email.subject}")
                
                elif action_type == 'forward':
                    forward_to = action.get('to')
                    if forward_to:
                        forward_subject = f"FWD: {email.subject}"
                        forward_body = f"Forwarded message:\\n\\nFrom: {email.sender}\\nSubject: {email.subject}\\n\\n{email.body}"
                        await self.email_client.send_email(forward_to, forward_subject, forward_body)
                        logger.info(f"Forwarded email to: {forward_to}")
                
                elif action_type == 'notify':
                    priority = action.get('priority', 'normal')
                    logger.info(f"NOTIFICATION ({priority}): {email.subject} from {email.sender}")
                    # Here you could integrate with external notification systems
                
                elif action_type == 'auto_reply':
                    template = action.get('template', 'default')
                    await self._send_auto_reply(email, template)
                    logger.info(f"Sent auto-reply for: {email.subject}")
                
                else:
                    logger.warning(f"Unknown action type: {action_type}")
            
            except Exception as e:
                logger.error(f"Error executing action {action_type}: {e}")
    
    async def _generate_and_send_response(self, email: EmailMessage, analysis: EmailAnalysis):
        """Generate and send an AI-powered response."""
        try:
            logger.info(f"Generating response for: {email.subject}")
            
            # Generate response using AI
            response_body = await self.ai_processor.generate_response(email, analysis)
            
            if response_body:
                # Send response
                reply_subject = f"Re: {email.subject}" if not email.subject.startswith('Re:') else email.subject
                await self.email_client.send_email(
                    email.sender, 
                    reply_subject, 
                    response_body,
                    reply_to=email.uid
                )
                logger.info(f"Sent AI-generated response to: {email.sender}")
            else:
                logger.warning(f"Failed to generate response for: {email.subject}")
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
    
    async def _send_auto_reply(self, email: EmailMessage, template: str = 'default'):
        """Send an auto-reply message."""
        templates = {
            'default': "Thank you for your email. I have received your message and will respond as soon as possible.",
            'out_of_office': "I am currently out of the office and will return on [DATE]. For urgent matters, please contact [CONTACT].",
            'support': "Thank you for contacting support. Your request has been received and assigned ticket #[TICKET]. We will respond within 24 hours."
        }
        
        reply_body = templates.get(template, templates['default'])
        reply_subject = f"Re: {email.subject}"
        
        await self.email_client.send_email(
            email.sender,
            reply_subject,
            reply_body,
            reply_to=email.uid
        )
    
    async def process_single_email_manual(self, email_uid: str) -> Dict[str, Any]:
        """Manually process a single email and return results."""
        try:
            # This would require additional email fetching logic by UID
            # For now, return a placeholder
            return {
                'status': 'not_implemented',
                'message': 'Manual processing not yet implemented'
            }
            
        except Exception as e:
            logger.error(f"Error in manual processing: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }