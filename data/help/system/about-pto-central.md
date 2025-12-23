# About PTO Central

## What Is PTO Central?

PTO Central is an employee time-off management system built for Haventech Solutions. It helps employees request paid time off, managers approve those requests, and administrators manage company-wide policies.

Think of it like a specialized calendar and request system just for time off. Instead of sending emails or filling out paper forms, employees use PTO Central to:

- See how much vacation, sick, and personal time they have
- Submit requests for time off
- Track the status of their requests
- View when teammates are out

## Who Created It?

PTO Central was created by **Jose Manuel Laboy**, Chief Technology Officer at Haventech Solutions.

The system was built with assistance from AI tools including:
- **Claude** (by Anthropic)
- **ChatGPT** (by OpenAI)
- **Gemini** (by Google)

These AI tools helped with coding, documentation, and testing. However, all design decisions were made by Jose. The AI tools followed his direction - they didn't make choices on their own.

## Key Features

### For Employees
- **Submit PTO Requests**: Request vacation, sick days, personal time, and more
- **Balance Dashboard**: See exactly how much time off you have available
- **Team Calendar**: Check when teammates are scheduled to be out
- **WFH Day Swap**: Trade work-from-home days with coworkers

### For Managers
- **Approve Requests**: Review and approve or deny team requests
- **Coverage View**: See who's available on any given day
- **Team Reports**: Track PTO usage across the team

### For Administrators
- **Employee Management**: Add, edit, and manage employee records
- **Policy Configuration**: Set up leave policies by location
- **Year-End Processing**: Handle balance rollovers and new year setup

## Is PTO Central "Smart"?

PTO Central includes AI-powered features like the Smart Scheduler Agent, which helps find good dates for vacation. However, there are important things to understand:

### What the AI CAN Do
- Help find dates when team coverage is good
- Check your balance before you submit a request
- Answer questions about company policies
- Suggest optimal times for vacation

### What the AI CANNOT Do
- The system is **not** conscious or self-aware
- The system does **not** learn or remember things between sessions
- The system does **not** have feelings or opinions
- All AI actions require human confirmation before they actually happen

### The Safety Gate
When the AI assistant wants to do something important (like submit a PTO request for you), it must ask for your confirmation first. This is called the "Safety Gate." You always have the final say.

## How Was This Built?

PTO Central demonstrates how complex software systems can be built responsibly with AI assistance. The codebase includes:

- **20 database models** - Storing employee, request, and balance data
- **31 services** - Business logic for approvals, notifications, and more
- **28 UI pages** - The screens you see and interact with
- **14 MCP tools** - Connections for AI to read and write data safely
- **Comprehensive audit logging** - Every action is recorded

## Technical Details

For those interested in the technical side:

| Component | Technology |
|-----------|------------|
| Frontend | NiceGUI (Python web framework) |
| Backend | Python with SQLAlchemy |
| Database | SQLite |
| AI Integration | Anthropic Claude via MCP |

## Getting Help

If you need assistance:
1. Check the Help section in the app (click the ? icon)
2. Contact your manager for policy questions
3. Contact IT support for technical issues

## Version Information

- **Current Version**: 2.0
- **Last Updated**: December 2025
- **Organization**: Haventech Solutions
