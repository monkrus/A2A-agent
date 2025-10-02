"""
Pydantic models for request/response validation
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class MessagePart(BaseModel):
    """Message part schema"""
    type: Literal["text", "image", "file"] = "text"
    text: Optional[str] = None
    url: Optional[str] = None
    mimeType: Optional[str] = None


class Message(BaseModel):
    """Message schema"""
    role: Literal["user", "agent", "system"]
    parts: List[MessagePart]


class TaskParams(BaseModel):
    """Task submission parameters"""
    taskId: Optional[str] = None
    skillId: str
    message: Message
    paymentMandateId: Optional[str] = None

    @field_validator("skillId")
    @classmethod
    def validate_skill(cls, v):
        from config import PRICING
        if v not in PRICING:
            raise ValueError(f"Invalid skillId: {v}. Must be one of: {', '.join(PRICING.keys())}")
        return v


class TaskStatusParams(BaseModel):
    """Task status query parameters"""
    taskId: str


class SendMessageParams(BaseModel):
    """Send message parameters"""
    taskId: str
    message: Message


class IntentMandateParams(BaseModel):
    """Intent mandate creation parameters"""
    description: str = Field(..., min_length=1, max_length=500)
    skillId: Optional[str] = None

    @field_validator("skillId")
    @classmethod
    def validate_skill(cls, v):
        if v is None:
            return v
        from config import PRICING
        if v not in PRICING:
            raise ValueError(f"Invalid skillId: {v}")
        return v


class CartMandateParams(BaseModel):
    """Cart mandate creation parameters"""
    skillId: str
    taskDescription: str = Field(..., min_length=1, max_length=1000)

    @field_validator("skillId")
    @classmethod
    def validate_skill(cls, v):
        from config import PRICING
        if v not in PRICING:
            raise ValueError(f"Invalid skillId: {v}")
        return v


class PaymentMethodData(BaseModel):
    """Payment method data"""
    method_name: str = "card"
    details: Dict[str, Any] = {}
    payer_name: Optional[str] = None
    payer_email: Optional[str] = None


class ProcessPaymentParams(BaseModel):
    """Payment processing parameters"""
    cartId: str
    paymentMethod: PaymentMethodData
    userAuthorization: Optional[str] = None


class TaskMetadata(BaseModel):
    """Task metadata"""
    service: str
    price: float
    currency: str
    billable: bool
    payment_protocol: str = "ap2"
    created_at: datetime
    completed_at: Optional[datetime] = None


class Artifact(BaseModel):
    """Task artifact"""
    type: Literal["text", "file", "json"]
    name: str
    mimeType: str
    data: Any


class TaskResponse(BaseModel):
    """Task response schema"""
    taskId: str
    status: Literal["pending", "working", "completed", "failed", "payment_required", "payment_authorized"]
    message: Optional[Message] = None
    artifacts: Optional[List[Artifact]] = None
    metadata: Optional[TaskMetadata] = None
    next_steps: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    code: int
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "unhealthy"]
    timestamp: datetime
    version: str
    ap2_enabled: bool
    database_connected: bool
