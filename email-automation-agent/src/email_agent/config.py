"""
Configuration management for the Email Automation Agent.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from pydantic import BaseModel, Field


class EmailConfig(BaseModel):
    """Email provider configuration."""
    provider: str = "gmail"
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_ssl: bool = True


class AIConfig(BaseModel):
    """AI model configuration."""
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    api_key: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7


class AgentConfig(BaseModel):
    """Agent behavior configuration."""
    check_interval: int = 300
    max_emails_per_batch: int = 10
    auto_reply: bool = False
    require_confirmation: bool = True


class ProcessingRule(BaseModel):
    """Email processing rule definition."""
    name: str
    conditions: Dict[str, List[str]]
    actions: List[Dict[str, Any]]


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/agent.log"
    max_size: str = "10MB"
    backup_count: int = 5


class Config(BaseModel):
    """Main configuration class."""
    email: EmailConfig = Field(default_factory=EmailConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    rules: List[ProcessingRule] = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Handle environment variable substitution
        cls._substitute_env_vars(config_data)
        
        return cls(**config_data)
    
    @staticmethod
    def _substitute_env_vars(data: Dict[str, Any]) -> None:
        """Recursively substitute environment variables in config data."""
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                data[key] = os.getenv(env_var, "")
            elif isinstance(value, dict):
                Config._substitute_env_vars(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        Config._substitute_env_vars(item)
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, indent=2)