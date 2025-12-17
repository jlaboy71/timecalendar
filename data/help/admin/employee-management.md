# Employee Management

Administrators can manage all employee records in the system.

## Accessing Employee Management

From Dashboard: **Admin** > **Manage Employees**

## Employee List

The main view shows:
- All employees (paginated)
- Search/filter by name, email, department
- Status indicators (active/inactive)
- Quick action buttons

## Adding a New Employee

1. Click **"Add Employee"**
2. Fill in required information:

**Personal Information:**
- First Name (required)
- Last Name (required)
- Email (required, must be unique)
- Username (auto-generated or custom)

**Employment Details:**
- Department (select from list)
- Role (Employee, Manager, Admin)
- Hire Date (required)
- Location State (for policy application)
- Location City (optional)

**Authentication:**
- Password (temporary or custom)
- Must be at least 8 characters

3. Click **"Save"** to create

## Editing an Employee

1. Find the employee in the list
2. Click **"Edit"** button
3. Modify any fields
4. Click **"Save Changes"**

**Editable Fields:**
- Personal information
- Department assignment
- Role/access level
- Remote schedule
- Location information
- Active status

## Deactivating an Employee

When an employee leaves:
1. Find their record
2. Click **"Deactivate"** (or toggle Active status)
3. Confirm the action

**What Happens:**
- Employee cannot log in
- Records are preserved
- Historical data intact
- Can be reactivated if needed

## Deleting an Employee

**Use with caution** - Soft delete is preferred

Deletion is only possible if:
- No PTO requests exist
- No associated records

## Best Practices

- Keep employee records up to date
- Deactivate instead of delete when possible
- Set correct roles for access control
- Verify email addresses are correct
- Update department assignments promptly
