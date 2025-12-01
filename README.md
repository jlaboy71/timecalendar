# PTO and Market Calendar System

A comprehensive system for managing Paid Time Off (PTO) requests and market calendar events. This application provides functionality for tracking employee time off, managing approval workflows, and integrating with market calendar data to ensure proper business continuity.

## Features

- Employee PTO request management
- Approval workflow system
- Market calendar integration
- User authentication and authorization
- Database-driven architecture with PostgreSQL

## Setup Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Virtual environment (recommended)

### Installation
1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure your environment variables
5. Set up your PostgreSQL database
6. Run database migrations
7. Start the application

## Project Status

**Phase 1: Foundation Setup** ✅
- Project structure initialized
- Core dependencies defined
- Database models planned
- Authentication framework prepared

## Development

This project uses:
- SQLAlchemy 2.0 for database ORM
- Alembic for database migrations
- PostgreSQL as the primary database
- pytest for testing
- bcrypt for password hashing

## Contributing

Please ensure all tests pass before submitting pull requests.

## License

TBD
