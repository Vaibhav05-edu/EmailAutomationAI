"""
AI processor for email analysis and response generation.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

from .config import AIConfig
from .email_client import EmailMessage

logger = logging.getLogger(__name__)


class EmailCategory(Enum):
    """Email category classifications."""
    URGENT = "urgent"
    SPAM = "spam"
    PERSONAL = "personal"
    BUSINESS = "business"
    NEWSLETTER = "newsletter"
    SUPPORT = "support"
    OTHER = "other"


class EmailAnalysis:
    """Results of email analysis."""
    
    def __init__(self, category: EmailCategory, sentiment: str, priority: int,
                 requires_response: bool, suggested_actions: List[str],
                 confidence: float = 0.0):
        self.category = category
        self.sentiment = sentiment  # positive, negative, neutral
        self.priority = priority  # 1-5 scale
        self.requires_response = requires_response
        self.suggested_actions = suggested_actions
        self.confidence = confidence


class AIProcessor:
    """AI processor for email analysis and response generation."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup AI client based on provider."""
        try:
            if self.config.provider == "openai":
                import openai
                self.client = openai.OpenAI(api_key=self.config.api_key)
            elif self.config.provider == "anthropic":
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.config.api_key)
            else:
                logger.error(f"Unsupported AI provider: {self.config.provider}")
                
        except ImportError as e:
            logger.error(f"Failed to import AI client library: {e}")
        except Exception as e:
            logger.error(f"Failed to setup AI client: {e}")
    
    async def analyze_email(self, email: EmailMessage) -> EmailAnalysis:
        """Analyze an email and categorize it."""
        if not self.client:
            logger.error("AI client not initialized")
            return self._default_analysis()
        
        try:
            analysis_prompt = self._build_analysis_prompt(email)
            
            if self.config.provider == "openai":
                response = await self._analyze_with_openai(analysis_prompt)
            elif self.config.provider == "anthropic":
                response = await self._analyze_with_anthropic(analysis_prompt)
            else:
                return self._default_analysis()
            
            return self._parse_analysis_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            return self._default_analysis()
    
    def _build_analysis_prompt(self, email: EmailMessage) -> str:
        """Build prompt for email analysis."""
        return f\"\"\"
Analyze the following email and provide a structured analysis:

From: {email.sender}
Subject: {email.subject}
Body: {email.body[:1000]}...

Please analyze this email and respond with a JSON object containing:
- category: one of [urgent, spam, personal, business, newsletter, support, other]
- sentiment: one of [positive, negative, neutral]
- priority: integer from 1-5 (5 being highest priority)
- requires_response: boolean
- suggested_actions: array of suggested actions
- confidence: float between 0-1

Focus on:
1. Email classification based on content and sender
2. Urgency and priority assessment
3. Whether the email requires a response
4. Appropriate actions to take

Respond only with valid JSON.
\"\"\"
    
    async def _analyze_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Analyze email using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an expert email assistant that analyzes emails and provides structured responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        import json
        return json.loads(response.choices[0].message.content)
    
    async def _analyze_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Analyze email using Anthropic Claude."""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        return json.loads(response.content[0].text)
    
    def _parse_analysis_response(self, response: Dict[str, Any]) -> EmailAnalysis:
        """Parse AI response into EmailAnalysis object."""
        try:
            category = EmailCategory(response.get('category', 'other'))
            sentiment = response.get('sentiment', 'neutral')
            priority = int(response.get('priority', 3))
            requires_response = bool(response.get('requires_response', False))
            suggested_actions = response.get('suggested_actions', [])
            confidence = float(response.get('confidence', 0.5))
            
            return EmailAnalysis(
                category=category,
                sentiment=sentiment,
                priority=priority,
                requires_response=requires_response,
                suggested_actions=suggested_actions,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return self._default_analysis()
    
    def _default_analysis(self) -> EmailAnalysis:
        """Return default analysis when AI processing fails."""
        return EmailAnalysis(
            category=EmailCategory.OTHER,
            sentiment="neutral",
            priority=3,
            requires_response=False,
            suggested_actions=["manual_review"],
            confidence=0.0
        )
    
    async def generate_response(self, email: EmailMessage, 
                              analysis: EmailAnalysis,
                              context: Optional[str] = None) -> str:
        """Generate a response to an email."""
        if not self.client:
            logger.error("AI client not initialized")
            return ""
        
        try:
            response_prompt = self._build_response_prompt(email, analysis, context)
            
            if self.config.provider == "openai":
                response = await self._generate_with_openai(response_prompt)
            elif self.config.provider == "anthropic":
                response = await self._generate_with_anthropic(response_prompt)
            else:
                return ""
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ""
    
    def _build_response_prompt(self, email: EmailMessage, 
                              analysis: EmailAnalysis, 
                              context: Optional[str]) -> str:
        """Build prompt for response generation."""
        context_text = f"Additional context: {context}" if context else ""
        
        return f\"\"\"
Generate a professional email response based on the following:

Original Email:
From: {email.sender}
Subject: {email.subject}
Body: {email.body}

Analysis:
- Category: {analysis.category.value}
- Priority: {analysis.priority}/5
- Sentiment: {analysis.sentiment}

{context_text}

Please generate a professional, appropriate response that:
1. Addresses the sender's concerns or questions
2. Maintains a professional tone
3. Is concise but complete
4. Includes appropriate pleasantries

Respond with only the email body text, no subject line.
\"\"\"
    
    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate response using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a professional email assistant that writes clear, concise, and appropriate email responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        return response.choices[0].message.content.strip()
    
    async def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate response using Anthropic Claude."""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text.strip()
    
    async def classify_batch(self, emails: List[EmailMessage]) -> List[EmailAnalysis]:
        """Analyze a batch of emails."""
        analyses = []
        
        for email in emails:
            analysis = await self.analyze_email(email)
            analyses.append(analysis)
            
        return analyses