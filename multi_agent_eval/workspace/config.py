"""Configuration module."""

class Config:
    """Application configuration."""
    
    DEBUG = True
    MAX_RETRIES = 3
    TIMEOUT = 30
    
    # TODO: Add configuration validation
    
    @classmethod
    def validate(cls):
        """Validate configuration."""
        return True
