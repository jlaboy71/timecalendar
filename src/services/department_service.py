from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models import Department, User


class DepartmentService:
    """
    Service class for managing department operations.
    
    This service provides methods for creating, retrieving, updating, and
    deleting departments, as well as managing department-employee relationships.
    """

    @staticmethod
    def get_all_departments(db: Session) -> List[Department]:
        """
        Get all departments ordered by name.
        
        Args:
            db: Database session
            
        Returns:
            List of all departments with manager info, ordered by name
        """
        return db.query(Department).order_by(Department.name).all()

    @staticmethod
    def get_department_by_id(db: Session, department_id: int) -> Optional[Department]:
        """
        Get a single department by ID.
        
        Args:
            db: Database session
            department_id: ID of the department to retrieve
            
        Returns:
            Department object if found, None otherwise
        """
        return db.query(Department).filter(Department.id == department_id).first()

    @staticmethod
    def create_department(db: Session, name: str, code: str, manager_id: Optional[int] = None) -> Department:
        """
        Create a new department.
        
        Args:
            db: Database session
            name: Name of the department
            code: Department code
            manager_id: Optional ID of the manager user
            
        Returns:
            Created department object
            
        Raises:
            ValueError: If department name or code already exists or manager_id is invalid
        """
        # Check if department name already exists
        existing_dept = db.query(Department).filter(Department.name == name).first()
        if existing_dept:
            raise ValueError(f"Department with name '{name}' already exists")
        
        # Check if department code already exists
        existing_code = db.query(Department).filter(Department.code == code).first()
        if existing_code:
            raise ValueError(f"Department with code '{code}' already exists")
        
        # Validate manager_id if provided
        if manager_id is not None:
            manager = db.query(User).filter(User.id == manager_id).first()
            if not manager:
                raise ValueError(f"Manager with ID {manager_id} does not exist")
        
        # Create new department
        department = Department(
            name=name,
            code=code,
            manager_id=manager_id,
            is_active=True
        )
        
        db.add(department)
        db.commit()
        db.refresh(department)
        
        return department

    @staticmethod
    def update_department(
        db: Session, 
        department_id: int, 
        name: Optional[str] = None, 
        code: Optional[str] = None,
        manager_id: Optional[int] = None
    ) -> Department:
        """
        Update department name, code, and/or manager.
        
        Args:
            db: Database session
            department_id: ID of the department to update
            name: Optional new name for the department
            code: Optional new code for the department
            manager_id: Optional new manager ID
            
        Returns:
            Updated department object
            
        Raises:
            ValueError: If department not found, name/code conflicts, or manager_id is invalid
        """
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ValueError(f"Department with ID {department_id} not found")
        
        # Check if new name conflicts with existing departments
        if name is not None and name != department.name:
            existing_dept = db.query(Department).filter(
                and_(Department.name == name, Department.id != department_id)
            ).first()
            if existing_dept:
                raise ValueError(f"Department with name '{name}' already exists")
            department.name = name
        
        # Check if new code conflicts with existing departments
        if code is not None and code != department.code:
            existing_code = db.query(Department).filter(
                and_(Department.code == code, Department.id != department_id)
            ).first()
            if existing_code:
                raise ValueError(f"Department with code '{code}' already exists")
            department.code = code
        
        # Validate and update manager_id if provided
        if manager_id is not None:
            if manager_id != department.manager_id:
                manager = db.query(User).filter(User.id == manager_id).first()
                if not manager:
                    raise ValueError(f"Manager with ID {manager_id} does not exist")
                department.manager_id = manager_id
        
        db.commit()
        db.refresh(department)
        
        return department

    @staticmethod
    def delete_department(db: Session, department_id: int) -> bool:
        """
        Delete a department if it has no employees.
        
        Args:
            db: Database session
            department_id: ID of the department to delete
            
        Returns:
            True if department was deleted successfully
            
        Raises:
            ValueError: If department has employees or department not found
        """
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ValueError(f"Department with ID {department_id} not found")
        
        # Check if department has employees
        employee_count = db.query(User).filter(User.department_id == department_id).count()
        if employee_count > 0:
            raise ValueError(f"Cannot delete department '{department.name}' because it has {employee_count} employee(s)")
        
        db.delete(department)
        db.commit()
        
        return True

    @staticmethod
    def get_department_employees(db: Session, department_id: int) -> List[User]:
        """
        Get all employees in a department.
        
        Args:
            db: Database session
            department_id: ID of the department
            
        Returns:
            List of users in the department, ordered by last_name, first_name
        """
        return (
            db.query(User)
            .filter(User.department_id == department_id)
            .order_by(User.last_name, User.first_name)
            .all()
        )
