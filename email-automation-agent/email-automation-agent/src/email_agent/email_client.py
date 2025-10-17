"""
Email client for handling IMAP and SMTP operations.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .config import EmailConfig

logger = logging.getLogger(__name__)


class EmailMessage:
    """Represents an email message."""
    
    def __init__(self, uid: str, subject: str, sender: str, recipient: str, 
                 body: str, date: datetime, is_read: bool = False):
        self.uid = uid
        self.subject = subject
        self.sender = sender
        self.recipient = recipient
        self.body = body
        self.date = date
        self.is_read = is_read
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert email to dictionary format."""
        return {
            'uid': self.uid,
            'subject': self.subject,
            'sender': self.sender,
            'recipient': self.recipient,
            'body': self.body,
            'date': self.date.isoformat(),
            'is_read': self.is_read
        }


class EmailClient:
    """Email client for IMAP and SMTP operations."""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.imap_connection = None
        self.smtp_connection = None
    
    async def connect_imap(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.config.use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(
                    self.config.imap_server, 
                    self.config.imap_port
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    self.config.imap_server,
                    self.config.imap_port
                )
            
            self.imap_connection.login(self.config.username, self.config.password)
            logger.info(f"Connected to IMAP server: {self.config.imap_server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False
    
    async def connect_smtp(self) -> bool:
        """Connect to SMTP server."""
        try:
            if self.config.use_ssl:
                self.smtp_connection = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port
                )
            else:
                self.smtp_connection = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port
                )
                self.smtp_connection.starttls()
            
            self.smtp_connection.login(self.config.username, self.config.password)
            logger.info(f"Connected to SMTP server: {self.config.smtp_server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            return False
    
    async def fetch_unread_emails(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Fetch unread emails from the inbox."""
        if not self.imap_connection:
            await self.connect_imap()
        
        emails = []
        try:
            self.imap_connection.select('INBOX')
            status, messages = self.imap_connection.search(None, 'UNSEEN')
            
            if status == 'OK':
                message_ids = messages[0].split()
                if limit:
                    message_ids = message_ids[-limit:]  # Get most recent emails
                
                for msg_id in message_ids:
                    status, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_message = self._parse_email(msg_id.decode(), msg_data[0][1])
                        if email_message:
                            emails.append(email_message)
            
            logger.info(f"Fetched {len(emails)} unread emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _parse_email(self, uid: str, raw_email: bytes) -> Optional[EmailMessage]:
        """Parse raw email data into EmailMessage object."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            subject = msg.get('Subject', 'No Subject')
            sender = msg.get('From', 'Unknown Sender')
            recipient = msg.get('To', self.config.username)
            date_str = msg.get('Date', '')
            
            # Parse date
            try:
                date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
            except:
                date = datetime.now()
            
            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8')
            
            return EmailMessage(uid, subject, sender, recipient, body, date)
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    async def send_email(self, to: str, subject: str, body: str, 
                        reply_to: Optional[str] = None) -> bool:
        """Send an email."""
        if not self.smtp_connection:
            await self.connect_smtp()
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.username
            msg['To'] = to
            msg['Subject'] = subject
            
            if reply_to:
                msg['In-Reply-To'] = reply_to
                msg['References'] = reply_to
            
            msg.attach(MIMEText(body, 'plain'))
            
            self.smtp_connection.send_message(msg)
            logger.info(f"Email sent to: {to}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def mark_as_read(self, uid: str) -> bool:
        """Mark an email as read."""
        if not self.imap_connection:
            await self.connect_imap()
        
        try:
            self.imap_connection.select('INBOX')
            self.imap_connection.store(uid.encode(), '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {uid} as read")
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    async def archive_email(self, uid: str) -> bool:
        """Archive an email."""
        if not self.imap_connection:
            await self.connect_imap()
        
        try:
            self.imap_connection.select('INBOX')
            self.imap_connection.store(uid.encode(), '+FLAGS', '\\Deleted')
            self.imap_connection.expunge()
            logger.debug(f"Archived email {uid}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving email: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email servers."""
        if self.imap_connection:
            self.imap_connection.close()
            self.imap_connection.logout()
        
        if self.smtp_connection:
            self.smtp_connection.quit()
        
        logger.info("Disconnected from email servers")