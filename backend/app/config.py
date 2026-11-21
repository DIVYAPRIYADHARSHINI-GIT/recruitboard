import os
from dataclasses import dataclass, field


@dataclass
class Config:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///./recruitboard.db'))
    environment: str = field(default_factory=lambda: os.getenv('APP_ENV', 'development'))
    origins: tuple[str, ...] = field(default_factory=lambda: tuple(x.strip().rstrip('/') for x in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:4173').split(',') if x.strip()))
    demo: bool = field(default_factory=lambda: os.getenv('DEMO_MODE', 'false').lower() == 'true')
    seed: bool = field(default_factory=lambda: os.getenv('SEED_DEMO', 'false').lower() == 'true')
    secure: bool = field(default_factory=lambda: os.getenv('COOKIE_SECURE', 'true').lower() == 'true')
    login_limit: int = field(default_factory=lambda: int(os.getenv('LOGIN_LIMIT', '10')))
    write_limit: int = field(default_factory=lambda: int(os.getenv('WRITE_LIMIT', '120')))

    def validate(self):
        if self.environment == 'production':
            if not self.secure or not self.database_url.startswith(('postgresql://', 'postgresql+psycopg://')):
                raise RuntimeError('Production requires PostgreSQL and Secure cookies')
            if not self.origins or any(not x.startswith('https://') or '*' in x for x in self.origins):
                raise RuntimeError('Production requires exact HTTPS allowed origins')