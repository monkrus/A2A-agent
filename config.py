"""
Configuration Management for Production Agent
"""
import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings with validation"""

    # API Keys
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    base_url: str = Field(default="http://localhost:8000", env="BASE_URL")

    # Agent Configuration
    agent_name: str = Field(default="Business Consultant Agent (AP2)", env="AGENT_NAME")
    agent_description: str = Field(
        default="Professional business consulting agent with AP2 payment protocol support",
        env="AGENT_DESCRIPTION"
    )
    agent_version: str = Field(default="2.0.0", env="AGENT_VERSION")
    merchant_id: str = Field(default="consulting-agent-merchant-001", env="MERCHANT_ID")
    provider_name: str = Field(default="Your Company Name", env="PROVIDER_NAME")

    # Security
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="ALLOWED_ORIGINS"
    )
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # Database
    database_url: str = Field(default="sqlite:///./agent.db", env="DATABASE_URL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="agent.log", env="LOG_FILE")

    # Payment Configuration
    default_currency: str = Field(default="USD", env="DEFAULT_CURRENCY")
    refund_period_days: int = Field(default=30, env="REFUND_PERIOD_DAYS")
    cart_expiry_hours: int = Field(default=1, env="CART_EXPIRY_HOURS")
    intent_expiry_hours: int = Field(default=24, env="INTENT_EXPIRY_HOURS")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings"""
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        base_url=os.getenv("BASE_URL", "http://localhost:8000"),
        agent_name=os.getenv("AGENT_NAME", "Business Consultant Agent (AP2)"),
        agent_description=os.getenv("AGENT_DESCRIPTION", "Professional business consulting agent with AP2 payment protocol support"),
        agent_version=os.getenv("AGENT_VERSION", "2.0.0"),
        merchant_id=os.getenv("MERCHANT_ID", "consulting-agent-merchant-001"),
        provider_name=os.getenv("PROVIDER_NAME", "Your Company Name"),
        api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./agent.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "agent.log"),
        default_currency=os.getenv("DEFAULT_CURRENCY", "USD"),
        refund_period_days=int(os.getenv("REFUND_PERIOD_DAYS", "30")),
        cart_expiry_hours=int(os.getenv("CART_EXPIRY_HOURS", "1")),
        intent_expiry_hours=int(os.getenv("INTENT_EXPIRY_HOURS", "24")),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    )


# Pricing structure (could be moved to database in production)
PRICING = {
    "business-analysis": {"price": 50.00, "description": "Comprehensive business analysis"},
    "market-research": {"price": 75.00, "description": "Market research and competitive analysis"},
    "strategy-planning": {"price": 100.00, "description": "Strategic business planning"},
    "quick-consult": {"price": 25.00, "description": "Quick consultation (15 min equivalent)"}
}
