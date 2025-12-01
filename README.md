<<<<<<< HEAD
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
=======
TJM Time Calendar
Overview
TJM Time Calendar is a comprehensive PTO (Paid Time Off) and Market Calendar System designed for Haventech Solutions/TJM Holdings. This application integrates NYSE/CME/CBOE market holidays with employee time-off management and approval workflows, providing a centralized system for tracking availability and scheduling across the organization.
Purpose
This system addresses the critical need for coordinating employee schedules with financial market operating hours, ensuring proper coverage during trading days while managing employee time-off requests efficiently.
Key Features

Market Calendar Integration: Automatic tracking of NYSE, CME, and CBOE market holidays
PTO Request Management: Employee submission and tracking of time-off requests
Approval Workflows: Multi-tier approval system for time-off requests
Calendar Visualization: Comprehensive view of employee availability and market closures
Conflict Detection: Automatic identification of scheduling conflicts and coverage gaps

Technology Stack

Backend: Python with SQLAlchemy ORM
Database: SQLite (development), with migration path for production database
Frontend: Streamlit for modern web-based GUI
Deployment: Windows 11 native environment

Project Status
This project is currently in active development, with a phased implementation approach to manage complexity:

Phase 1: Core database schema and models
Phase 2: Basic CRUD operations and business logic
Phase 3: User interface and workflow management
Phase 4: Advanced features and reporting

Architecture
The application follows a modular architecture:

Data Layer: SQLAlchemy models for employees, PTO requests, market holidays
Business Logic: Service layer for approval workflows and validation
Presentation Layer: Streamlit-based web interface

Development Approach
As a "Code-Enabled Executive" project, this system is designed with clear separation of concerns:

Business logic and architecture defined by leadership requirements
Implementation leverages AI-assisted development for rapid iteration
Focus on production-ready, maintainable code

Installation
(To be added as project stabilizes)
Usage
(To be added as project stabilizes)
Contributing
This is an internal Haventech Solutions project. For questions or contributions, contact the development team.
License
Proprietary - Haventech Solutions/TJM Holdings
>>>>>>> ce0506122c2e515718f74a5e48642fc9b08efab5
