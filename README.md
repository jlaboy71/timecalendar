# TJM Time Calendar

## Overview
TJM Time Calendar is a comprehensive PTO (Paid Time Off) and Market Calendar System designed for Haventech Solutions/TJM Holdings. This application integrates NYSE/CME/CBOE market holidays with employee time-off management, providing a centralized system for tracking availability and scheduling across the organization with role-based access control and approval workflows.

## Purpose
This system addresses the critical need for coordinating employee schedules with financial market operating hours, ensuring proper coverage during trading days while managing employee time-off requests efficiently through a modern, responsive web-based interface.

## Key Features
- **Modern NiceGUI Web Interface**: Responsive, component-based UI with native Python implementation
- **Authentication & Authorization**: Secure login system with role-based access control (Admin, Manager, Employee)
- **Market Calendar Integration**: Automatic tracking of NYSE, CME, and CBOE market holidays
- **PTO Request Management**: 
  - Multiple request types (Vacation, Sick Leave, Personal Day, Unpaid Leave)
  - Employee submission and tracking interface
  - Manager approval workflows
  - Request status tracking (Pending, Approved, Denied, Cancelled)
- **Vacation Policy Engine**: Automatic accrual calculation based on years of service
- **Employee Management**: Comprehensive CRUD operations for HR administration
- **Calendar Visualization**: Integrated view of employee availability and market closures
- **Conflict Detection**: Automatic identification of scheduling conflicts and coverage gaps

## Technology Stack
- **Backend**: Python 3.x with SQLAlchemy ORM
- **Database**: PostgreSQL (production-ready relational database)
- **Frontend**: NiceGUI (Python-based reactive UI framework)
- **Authentication**: Custom session-based authentication with bcrypt password hashing
- **Deployment**: Windows 11 native environment, intranet-accessible
- **Architecture**: Component-based design with reusable UI elements

## Project Timeline & History

### Early Development (Initial Attempt)
- **Challenge Encountered**: SQLAlchemy circular dependency issues in initial architecture
- **Decision**: Complete project restart with structured phased approach

### Phase 1: Database Foundation (Completed)
**Duration**: ~2 weeks
- Designed comprehensive PostgreSQL database schema
- Implemented core models:
  - `employees`: User accounts with role-based access
  - `pto_requests`: Time-off request tracking with approval workflows
  - `market_holidays`: Financial market closure calendar
  - `vacation_policies`: Years-of-service based accrual rules
- Established referential integrity and cascading relationships
- Created database initialization and migration scripts

### Phase 2: Service Layer (Completed)
**Duration**: ~1.5 weeks
- Built authentication service with bcrypt password hashing
- Implemented PTO service layer with business logic:
  - Request submission validation
  - Approval workflow management
  - Conflict detection algorithms
  - Balance calculation engine
- Developed vacation policy service for automatic accrual calculations
- Created employee management service (CRUD operations)
- Established market holiday integration service

### Phase 3: UI Development - Major Pivot (In Progress)
**Duration**: ~3 weeks (ongoing)

#### Initial Streamlit Implementation (Completed, Then Deprecated)
- Built multi-page Streamlit application
- Implemented all core features and workflows
- **Decision Point**: Streamlit's page reload behavior and limited interactivity led to architectural reassessment

#### Switch to NiceGUI (Current Focus)
**Rationale for Change**:
- **Superior Reactivity**: Real-time UI updates without page reloads
- **Component-Based Architecture**: Reusable UI components for maintainable code
- **Native Python**: Better integration with existing service layer
- **Modern UX**: Single-page application feel with smooth transitions
- **Flexibility**: More control over UI behavior and state management

**NiceGUI Implementation Progress**:
- ✅ Authentication system with login page
- ✅ Session management and security
- ✅ Role-based navigation and access control
- ✅ Dashboard/Home page with role-specific views
- ✅ Component library for consistent UI elements
- 🔄 PTO request forms and workflows (in progress)
- 🔄 Manager approval interface (in progress)
- 🔄 Employee management CRUD (in progress)
- 🔄 Calendar visualization (in progress)

### Current Status (December 2024)
**Total Development Time**: ~7-8 weeks (including pivot)
- ✅ Phase 1: Database Foundation - Complete
- ✅ Phase 2: Service Layer - Complete
- 🔄 Phase 3: NiceGUI UI - In Active Development (60% complete)
- ⏳ Phase 4: Testing & Deployment - Planned

## Architecture

### Technology Decision: Why NiceGUI?
After completing a full Streamlit implementation, the project pivoted to NiceGUI for the following reasons:
1. **Interactivity**: NiceGUI provides true reactive components without page reloads
2. **State Management**: Better control over application state and user sessions
3. **User Experience**: Single-page application architecture with smoother workflows
4. **Maintainability**: Component-based design reduces code duplication
5. **Performance**: More efficient rendering for complex forms and tables

### Three-Tier Modular Architecture

#### Data Layer
- **PostgreSQL Database**: Production-grade relational database
- **SQLAlchemy Models**: Type-safe ORM with relationship management
- **Schema**: Normalized design with referential integrity

#### Business Logic Layer
- **Authentication Service**: User login, session management, password security
- **PTO Service**: Request lifecycle management, approval workflows, conflict detection
- **Employee Service**: User management, role assignment, profile updates
- **Vacation Policy Service**: Accrual calculations, balance tracking
- **Market Holiday Service**: Calendar integration, trading day validation

#### Presentation Layer (NiceGUI)
- **Single-Page Application**: Reactive UI with dynamic content updates
- **Component Library**: Reusable UI elements (cards, forms, tables, modals)
- **Role-Based Navigation**: Dynamic menu based on user permissions
- **Session State Management**: Persistent authentication with secure sessions
- **Responsive Design**: Optimized for desktop, tablet, and mobile

## Development Approach
This project exemplifies the "Code-Enabled Executive" development model:
- **Business Logic First**: Clear requirements and architecture defined by leadership
- **AI-Assisted Implementation**: Leveraging Aider + Claude for rapid development
- **Iterative Refinement**: Willingness to pivot when better solutions emerge
- **Structured Phases**: Managing complexity through disciplined development cycles
- **Production Standards**: Emphasis on maintainable, scalable code
- **Version Control**: GitHub-based workflow for tracking progress

## Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Windows 11 (primary deployment target)

### Quick Start
```bash
# Clone repository
git clone [repository-url]

# Install dependencies
pip install -r requirements.txt

# Configure database connection
# (Update connection string in configuration)

# Initialize database
python init_db.py

# Run application
python app.py
```

### NiceGUI Deployment Notes
- NiceGUI runs on FastAPI backend
- Default port: 8080 (configurable)
- Supports both development and production modes
- Can be deployed as Windows service for intranet access

## Usage
1. **Login**: Access the application at `http://localhost:8080`
2. **Role-Based Features**:
   - **Employees**: Submit PTO requests, view request history, check balances
   - **Managers**: Approve/deny requests, view team calendars, manage direct reports
   - **Admins**: Manage all employees, configure vacation policies, maintain system

## Lessons Learned

### Streamlit Experience
- **Pros**: Rapid prototyping, built-in authentication options, simple deployment
- **Cons**: Page reload behavior, limited interactivity, state management challenges
- **Outcome**: Excellent for proof-of-concept; limitations apparent in production use

### NiceGUI Advantages
- **Real-time updates**: Forms and tables update without page reloads
- **Component reusability**: Reduced code duplication across pages
- **Better UX**: Single-page application feel improves user experience
- **Flexibility**: More control over UI behavior and styling

## Future Enhancements (Phase 4+)
- Advanced reporting and analytics dashboard
- Email notifications for request approvals
- Calendar export (iCal/Outlook integration)
- Mobile application (NiceGUI supports mobile views)
- Department-based reporting and analytics
- Historical data analysis and trending
- Integration with payroll systems
- Automated backup and disaster recovery

## Contributing
This is an internal Haventech Solutions project. For questions or contributions, contact the CTO.

## Project Structure
```
timecalendar/
├── models/          # SQLAlchemy database models
├── services/        # Business logic layer
├── components/      # NiceGUI reusable UI components
├── pages/           # Application pages/views
├── utils/           # Helper functions and utilities
├── config/          # Configuration files
├── app.py           # Main application entry point
└── requirements.txt # Python dependencies
```

## License
Proprietary - Haventech Solutions/TJM Holdings

---

**Project Lead**: Jose (CTO, TJM Holdings/Haventech Solutions)  
**Development Model**: Code-Enabled Executive with AI-Assisted Implementation  
**Current Phase**: Phase 3 - NiceGUI UI Development (60% complete)  
**Status**: Active Development - Target Completion Q1 2025  

*This system is part of Haventech Solutions' internal automation initiative, demonstrating the power of iterative development and technology selection based on real-world requirements.*

---

## Technical Notes

### Why We Switched from Streamlit to NiceGUI
This decision was made after completing a functional Streamlit implementation. Key factors:
- Streamlit's architecture requires page reloads for most interactions
- Form submissions and approvals felt clunky with full page refreshes
- NiceGUI's reactive components provide a more modern, responsive experience
- The switch demonstrates prioritizing user experience over sunk development costs
- Service layer remained unchanged, validating the three-tier architecture design

### Development Timeline Insight
The willingness to restart Phase 3 with a different framework added ~2 weeks to the timeline but will result in a significantly better end-user experience. This decision reflects the "Code-Enabled Executive" approach: understanding when technical limitations impact business value and making data-driven pivots.
