"""
Database layer for persistence
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Task(Base):
    """Task table"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    skill_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    user_message = Column(String)
    result = Column(String)
    price = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    payment_status = Column(String, index=True)
    payment_mandate_id = Column(String, index=True)
    cart_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    task_metadata = Column(JSON)
    error = Column(String)


class CartMandateDB(Base):
    """Cart mandate table"""
    __tablename__ = "cart_mandates"

    id = Column(String, primary_key=True, index=True)
    skill_id = Column(String, nullable=False)
    task_description = Column(String)
    cart_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)


class PaymentMandateDB(Base):
    """Payment mandate table"""
    __tablename__ = "payment_mandates"

    id = Column(String, primary_key=True, index=True)
    cart_id = Column(String, nullable=False, index=True)
    payment_data = Column(JSON, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskRepository:
    """Task data access"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task"""
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def update(self, task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update task"""
        task = self.get(task_id)
        if task:
            for key, value in updates.items():
                setattr(task, key, value)
            self.db.commit()
            self.db.refresh(task)
        return task

    def get_by_status(self, status: str):
        """Get tasks by status"""
        return self.db.query(Task).filter(Task.status == status).all()


class CartMandateRepository:
    """Cart mandate data access"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, cart_data: Dict[str, Any]) -> CartMandateDB:
        """Create cart mandate"""
        cart = CartMandateDB(**cart_data)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get(self, cart_id: str) -> Optional[CartMandateDB]:
        """Get cart by ID"""
        return self.db.query(CartMandateDB).filter(CartMandateDB.id == cart_id).first()

    def mark_used(self, cart_id: str) -> bool:
        """Mark cart as used"""
        cart = self.get(cart_id)
        if cart:
            cart.is_used = True
            self.db.commit()
            return True
        return False


class PaymentMandateRepository:
    """Payment mandate data access"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, payment_data: Dict[str, Any]) -> PaymentMandateDB:
        """Create payment mandate"""
        payment = PaymentMandateDB(**payment_data)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get(self, payment_id: str) -> Optional[PaymentMandateDB]:
        """Get payment by ID"""
        return self.db.query(PaymentMandateDB).filter(PaymentMandateDB.id == payment_id).first()

    def get_by_cart(self, cart_id: str) -> Optional[PaymentMandateDB]:
        """Get payment by cart ID"""
        return self.db.query(PaymentMandateDB).filter(PaymentMandateDB.cart_id == cart_id).first()
