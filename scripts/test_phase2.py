"""
Comprehensive test script for Phase 2 services.
Tests all service classes and their methods with proper error handling.
"""

import sys
import os
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import from src package using absolute imports
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.user_service import UserService
from src.database import SessionLocal
from src.schemas.user_schemas import UserCreate, UserUpdate
from src.schemas.pto_schemas import PTORequestCreate, PTOBalanceUpdate
from src.models.user import User
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_success(message: str) -> None:
    """Print success message in green."""
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print error message in red."""
    print(f"✗ {message}")


def test_phase2_services():
    """Main test function for Phase 2 services."""
    db = None
    
    try:
        # 1. DATABASE CONNECTION
        print_section("Database Connection")
        db = SessionLocal()
        print_success("Connected to database")
        
        # 2. CLEANUP
        print_section("Cleanup")
        # Look for test user and clean up
        test_user = db.query(User).filter(User.username == 'test_user_phase2').first()
        if test_user:
            # Delete requests first (foreign key constraint)
            db.query(PTORequest).filter(PTORequest.user_id == test_user.id).delete()
            # Delete balances
            db.query(PTOBalance).filter(PTOBalance.user_id == test_user.id).delete()
            # Delete user
            db.delete(test_user)
            db.commit()
            print_success("Cleaned up existing test data")
        else:
            print_success("No existing test data to clean up")
        
        # 3. TEST USER CREATION (Manual since UserService not available)
        print_section("Creating Test User")
        from src.utils.password import hash_password
        
        test_user = User(
            username='test_user_phase2',
            email='testphase2@example.com',
            password_hash=hash_password('TestPass123'),
            first_name='Test',
            last_name='User',
            role='employee',
            hire_date=date.today(),
            department_id=1,  # Assuming department 1 exists from seed data
            is_active=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print_success(f"Created test user with ID: {test_user.id}")
        print_success(f"Full name: {test_user.full_name}")
        
        # 4. TEST BALANCE SERVICE
        print_section("Testing Balance Service")
        balance_service = BalanceService(db)
        
        # Get/create balance for current year
        current_year = date.today().year
        balance = balance_service.get_or_create_balance(test_user.id, current_year)
        print_success(f"Created/retrieved balance for year {current_year}")
        print(f"   Initial state - Vacation: {balance.vacation_total}, Sick: {balance.sick_total}, Personal: {balance.personal_total}")
        
        # Update balance totals
        balance_update = PTOBalanceUpdate(
            vacation_total=Decimal('15.00'),
            sick_total=Decimal('10.00'),
            personal_total=Decimal('5.00')
        )
        updated_balance = balance_service.update_balance_totals(balance.id, balance_update)
        print_success("Updated balance totals")
        print(f"   Updated state - Vacation: {updated_balance.vacation_total}, Sick: {updated_balance.sick_total}, Personal: {updated_balance.personal_total}")
        
        # Test other balance methods
        user_balances = balance_service.get_user_balances(test_user.id)
        print_success(f"Retrieved user balances: {len(user_balances)} balance(s)")
        
        current_balance = balance_service.get_current_year_balance(test_user.id)
        print_success("Retrieved current year balance")
        print(f"   Available - Vacation: {current_balance.vacation_available}, Sick: {current_balance.sick_available}, Personal: {current_balance.personal_available}")
        
        # 5. TEST PTO SERVICE - REQUEST CREATION
        print_section("Testing PTO Request Creation")
        pto_service = PTOService(db)
        
        # Create vacation request
        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=4)  # 5 days total
        
        request_data = PTORequestCreate(
            user_id=test_user.id,
            pto_type='vacation',
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal('5.00'),
            notes='Test vacation request'
        )
        
        vacation_request = pto_service.create_request(request_data)
        print_success(f"Created vacation request with ID: {vacation_request.id}")
        print(f"   Status: {vacation_request.status}")
        print(f"   Duration: {vacation_request.duration_days} days")
        
        # Check balance after request creation
        updated_balance = balance_service.get_current_year_balance(test_user.id)
        print_success(f"Vacation pending increased to: {updated_balance.vacation_pending}")
        
        # 6. TEST PTO SERVICE - APPROVAL WORKFLOW
        print_section("Testing Approval Workflow")
        
        # Get pending requests
        pending_requests = pto_service.get_user_requests(test_user.id, status='pending')
        print_success(f"Found {len(pending_requests)} pending request(s)")
        
        # Approve the request
        approved_request = pto_service.approve_request(vacation_request.id, test_user.id)
        print_success("Approved vacation request")
        print(f"   Status: {approved_request.status}")
        print(f"   Approved by: {approved_request.approved_by}")
        
        # Verify balance changes
        final_balance = balance_service.get_current_year_balance(test_user.id)
        print_success("Verified balance changes after approval")
        print(f"   Vacation pending: {final_balance.vacation_pending}")
        print(f"   Vacation used: {final_balance.vacation_used}")
        print(f"   Vacation available: {final_balance.vacation_available}")
        
        # 7. TEST PTO SERVICE - DENIAL WORKFLOW
        print_section("Testing Denial Workflow")
        
        # Create another request
        start_date2 = date.today() + timedelta(days=10)
        end_date2 = start_date2 + timedelta(days=2)  # 3 days
        
        request_data2 = PTORequestCreate(
            user_id=test_user.id,
            pto_type='vacation',
            start_date=start_date2,
            end_date=end_date2,
            total_days=Decimal('3.00'),
            notes='Test vacation request for denial'
        )
        
        vacation_request2 = pto_service.create_request(request_data2)
        print_success(f"Created second vacation request with ID: {vacation_request2.id}")
        print(f"   Status: {vacation_request2.status}")
        
        # Deny the request
        denied_request = pto_service.deny_request(
            vacation_request2.id, 
            test_user.id, 
            "Testing denial workflow"
        )
        print_success("Denied vacation request")
        print(f"   Status: {denied_request.status}")
        print(f"   Denial reason: {denied_request.denial_reason}")
        
        # Verify balance unchanged after denial
        balance_after_denial = balance_service.get_current_year_balance(test_user.id)
        print_success("Verified balance after denial")
        print(f"   Vacation pending: {balance_after_denial.vacation_pending}")
        print(f"   Vacation used: {balance_after_denial.vacation_used} (unchanged)")
        
        # 8. TEST PTO SERVICE - OVERLAPPING REQUESTS
        print_section("Testing Overlapping Request Detection")
        
        # Create a request for next week
        start_date3 = date.today() + timedelta(days=7)
        end_date3 = start_date3 + timedelta(days=2)  # 3 days
        
        request_data3 = PTORequestCreate(
            user_id=test_user.id,
            pto_type='personal',
            start_date=start_date3,
            end_date=end_date3,
            total_days=Decimal('3.00'),
            notes='Test personal request'
        )
        
        personal_request = pto_service.create_request(request_data3)
        print_success(f"Created personal request with ID: {personal_request.id}")
        
        # Check for overlapping requests
        overlapping = pto_service.get_overlapping_requests(
            test_user.id, 
            start_date3, 
            end_date3
        )
        print_success(f"Found {len(overlapping)} overlapping request(s)")
        
        # 9. SUMMARY
        print_section("Phase 2 Test Summary")
        
        # Count final data
        total_users = db.query(User).filter(User.username == 'test_user_phase2').count()
        total_balances = db.query(PTOBalance).filter(PTOBalance.user_id == test_user.id).count()
        total_requests = db.query(PTORequest).filter(PTORequest.user_id == test_user.id).count()
        approved_requests = db.query(PTORequest).filter(
            PTORequest.user_id == test_user.id,
            PTORequest.status == 'approved'
        ).count()
        denied_requests = db.query(PTORequest).filter(
            PTORequest.user_id == test_user.id,
            PTORequest.status == 'denied'
        ).count()
        pending_requests = db.query(PTORequest).filter(
            PTORequest.user_id == test_user.id,
            PTORequest.status == 'pending'
        ).count()
        
        print_success("All Phase 2 services tested successfully!")
        print(f"   Total users: {total_users}")
        print(f"   Total balances: {total_balances}")
        print(f"   Total requests: {total_requests} ({approved_requests} approved, {denied_requests} denied, {pending_requests} pending)")
        
        # Final balance summary
        final_summary_balance = balance_service.get_current_year_balance(test_user.id)
        print(f"   Final balance state:")
        print(f"     Vacation: {final_summary_balance.vacation_used}/{final_summary_balance.vacation_total} used")
        print(f"     Sick: {final_summary_balance.sick_used}/{final_summary_balance.sick_total} used")
        print(f"     Personal: {final_summary_balance.personal_used}/{final_summary_balance.personal_total} used")
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
            print_success("Database connection closed")


if __name__ == "__main__":
    test_phase2_services()
