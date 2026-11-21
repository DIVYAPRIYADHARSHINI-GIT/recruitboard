"""Interactive first admin for a PRIVATE installation, not the shared demo.

Run only on an approved host with DATABASE_URL already configured there.
Never accepts credentials as command-line arguments or prints them.
"""
from getpass import getpass
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import Config
from .db import initialize, make_engine
from .models import User
from .schemas import UserCreate
from .security import hasher


def main():
    config = Config()
    config.validate()
    if config.demo or config.seed:
        raise SystemExit('Disable demo mode and seed before private bootstrap.')
    engine = make_engine(config.database_url)
    initialize(engine)
    with Session(engine) as db:
        if db.scalar(select(User.id).limit(1)):
            raise SystemExit('Bootstrap refuses to change a non-empty user table.')
        name = input('Admin display name: ')
        email = input('Admin email: ')
        password = getpass('New password (at least 12 characters, not displayed): ')
        if password != getpass('Confirm password (not displayed): '):
            raise SystemExit('Passwords did not match.')
        try:
            data = UserCreate(name=name, email=email, password=password, role='admin')
        except Exception:
            raise SystemExit('Invalid input. Check the email, name and password length.') from None
        db.add(User(name=data.name, email=data.email, password_hash=hasher.hash(data.password), role='admin', active=True, demo=False))
        db.commit()
    print('First admin created. No email was sent.')


if __name__ == '__main__':
    main()