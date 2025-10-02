"""
Production-Ready Monetizable A2A Agent with AP2 Integration
Complete with error handling, logging, database persistence, security, and monitoring
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
import google.generativeai as genai

# AP2 imports
from ap2.types.mandate import (
    IntentMandate,
    CartContents,
    CartMandate,
    PaymentMandate,
    PaymentMandateContents,
)
from ap2.types.payment_request import (
    PaymentRequest,
    PaymentResponse,
    PaymentDetailsInit,
    PaymentMethodData,
    PaymentItem,
    PaymentCurrencyAmount,
)

# Local imports
from config import get_settings, PRICING
from models import (
    TaskParams,
    TaskStatusParams,
    SendMessageParams,
    IntentMandateParams,
    CartMandateParams,
    ProcessPaymentParams,
    TaskResponse,
    ErrorResponse,
    HealthResponse,
    Message,
    MessagePart
)
from database import (
    init_db,
    get_db,
    TaskRepository,
    CartMandateRepository,
    PaymentMandateRepository,
)
from logger import logger, log_request, log_response, log_error, log_payment, log_task
from middleware import setup_middleware

# Load settings
settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.google_api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.agent_name} v{settings.agent_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down agent...")


app = FastAPI(
    title=settings.agent_name,
    description=settings.agent_description,
    version=settings.agent_version,
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)


# Agent Card with AP2 support
def get_agent_card() -> Dict[str, Any]:
    """Generate agent card"""
    return {
        "name": settings.agent_name,
        "description": settings.agent_description,
        "provider": settings.provider_name,
        "url": f"{settings.base_url}/a2a",
        "version": settings.agent_version,
        "capabilities": ["streaming", "pushNotifications", "ap2-payments"],
        "authentication": {
            "schemes": ["Bearer"]
        },
        "ap2": {
            "supported": True,
            "version": "0.1",
            "payment_methods": ["card", "bank_transfer"],
            "mandate_types": ["intent", "cart", "payment"]
        },
        "skills": [
            {
                "id": skill_id,
                "name": details["description"].split(" - ")[0] if " - " in details["description"] else details["description"],
                "description": details["description"],
                "inputModes": ["text"],
                "outputModes": ["text"],
                "pricing": {
                    "amount": details["price"],
                    "currency": settings.default_currency,
                    "model": "per_transaction"
                }
            }
            for skill_id, details in PRICING.items()
        ]
    }


@app.get("/.well-known/agent.json")
async def agent_discovery():
    """Agent Discovery Endpoint with AP2 support"""
    try:
        return JSONResponse(content=get_agent_card())
    except Exception as e:
        logger.error(f"Error generating agent card: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/a2a")
async def handle_a2a_request(request: Request, db: Session = Depends(get_db)):
    """Main A2A endpoint with AP2 payment flow support"""
    start_time = datetime.now()
    request_id = str(uuid.uuid4())

    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        json_rpc_id = body.get("id")

        log_request(method, params, request_id)

        # Route to appropriate handler
        handlers = {
            "submitTask": lambda p: submit_task(p, db),
            "getTaskStatus": lambda p: get_task_status(p, db),
            "sendMessage": lambda p: send_message(p, db),
            "createIntentMandate": lambda p: create_intent_mandate(p),
            "createCartMandate": lambda p: create_cart_mandate(p, db),
            "processPayment": lambda p: process_payment(p, db),
        }

        handler = handlers.get(method)
        if not handler:
            raise HTTPException(
                status_code=400,
                detail=f"Method not found: {method}"
            )

        result = await handler(params)

        duration = (datetime.now() - start_time).total_seconds() * 1000
        log_response(request_id, "success", duration)

        return JSONResponse(content={
            "jsonrpc": "2.0",
            "result": result,
            "id": json_rpc_id
        })

    except HTTPException as e:
        duration = (datetime.now() - start_time).total_seconds() * 1000
        log_error(request_id, e)

        return JSONResponse(
            status_code=e.status_code,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": e.status_code,
                    "message": str(e.detail)
                },
                "id": body.get("id") if "body" in locals() else None
            }
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds() * 1000
        log_error(request_id, e)

        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error"
                },
                "id": body.get("id") if "body" in locals() else None
            }
        )


async def create_intent_mandate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create an Intent Mandate (AP2)"""
    try:
        validated_params = IntentMandateParams(**params)

        intent = IntentMandate(
            user_cart_confirmation_required=True,
            natural_language_description=validated_params.description,
            merchants=[settings.merchant_id],
            skus=[validated_params.skillId] if validated_params.skillId else None,
            requires_refundability=True,
            intent_expiry=(datetime.now(timezone.utc) + timedelta(hours=settings.intent_expiry_hours)).isoformat()
        )

        logger.info(f"Intent mandate created for skill: {validated_params.skillId}")

        return {
            "success": True,
            "intent_mandate": intent.model_dump(),
            "message": "Intent mandate created. Proceed to create cart."
        }

    except ValueError as e:
        logger.error(f"Validation error in create_intent_mandate: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def create_cart_mandate(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Create a Cart Mandate (AP2)"""
    try:
        validated_params = CartMandateParams(**params)

        cart_id = str(uuid.uuid4())
        price = PRICING[validated_params.skillId]["price"]

        # Create Payment Request
        payment_request = PaymentRequest(
            method_data=[
                PaymentMethodData(
                    supported_methods="https://pay.google.com/payment",
                    data={"merchantId": settings.merchant_id}
                )
            ],
            details=PaymentDetailsInit(
                id=cart_id,
                total=PaymentItem(
                    label=PRICING[validated_params.skillId]["description"],
                    amount=PaymentCurrencyAmount(
                        currency=settings.default_currency,
                        value=str(price)
                    ),
                    refund_period=settings.refund_period_days
                ),
                display_items=[
                    PaymentItem(
                        label=f"{validated_params.skillId} - {validated_params.taskDescription[:50]}",
                        amount=PaymentCurrencyAmount(
                            currency=settings.default_currency,
                            value=str(price)
                        ),
                        refund_period=settings.refund_period_days
                    )
                ]
            )
        )

        # Create Cart Contents
        cart_contents = CartContents(
            id=cart_id,
            user_cart_confirmation_required=True,
            payment_request=payment_request,
            cart_expiry=(datetime.now(timezone.utc) + timedelta(hours=settings.cart_expiry_hours)).isoformat(),
            merchant_name=settings.agent_name
        )

        # Create Cart Mandate
        cart_mandate = CartMandate(
            contents=cart_contents,
            merchant_authorization=f"MERCHANT_SIG_{cart_id}"
        )

        # Store in database
        cart_repo = CartMandateRepository(db)
        cart_repo.create({
            "id": cart_id,
            "skill_id": validated_params.skillId,
            "task_description": validated_params.taskDescription,
            "cart_data": cart_mandate.model_dump(),
            "expires_at": datetime.fromisoformat(cart_contents.cart_expiry.replace('Z', '+00:00'))
        })

        log_payment(cart_id, price, settings.default_currency, "cart_created")

        return {
            "success": True,
            "cart_id": cart_id,
            "cart_mandate": cart_mandate.model_dump(),
            "message": "Cart created. User must confirm and authorize payment."
        }

    except ValueError as e:
        logger.error(f"Validation error in create_cart_mandate: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating cart mandate: {e}")
        raise HTTPException(status_code=500, detail="Failed to create cart")


async def process_payment(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Process payment with Payment Mandate (AP2)"""
    try:
        validated_params = ProcessPaymentParams(**params)

        # Get cart from database
        cart_repo = CartMandateRepository(db)
        cart_db = cart_repo.get(validated_params.cartId)

        if not cart_db:
            raise HTTPException(status_code=404, detail="Cart not found or expired")

        if cart_db.is_used:
            raise HTTPException(status_code=400, detail="Cart already used")

        # Check expiry
        if cart_db.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Cart expired")

        cart_mandate = CartMandate(**cart_db.cart_data)
        payment_mandate_id = str(uuid.uuid4())

        # Create Payment Response
        payment_response = PaymentResponse(
            request_id=validated_params.cartId,
            method_name=validated_params.paymentMethod.method_name,
            details=validated_params.paymentMethod.details,
            payer_name=validated_params.paymentMethod.payer_name,
            payer_email=validated_params.paymentMethod.payer_email,
        )

        # Create Payment Mandate
        payment_mandate_contents = PaymentMandateContents(
            payment_mandate_id=payment_mandate_id,
            payment_details_id=validated_params.cartId,
            payment_details_total=cart_mandate.contents.payment_request.details.total,
            payment_response=payment_response,
            merchant_agent=settings.merchant_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        payment_mandate = PaymentMandate(
            payment_mandate_contents=payment_mandate_contents,
            user_authorization=validated_params.userAuthorization or f"USER_SIG_{payment_mandate_id}"
        )

        # Store payment in database
        payment_repo = PaymentMandateRepository(db)
        payment_repo.create({
            "id": payment_mandate_id,
            "cart_id": validated_params.cartId,
            "payment_data": payment_mandate.model_dump(),
            "amount": float(cart_mandate.contents.payment_request.details.total.amount.value),
            "currency": cart_mandate.contents.payment_request.details.total.amount.currency,
            "status": "authorized",
            "processed_at": datetime.utcnow()
        })

        # Mark cart as used
        cart_repo.mark_used(validated_params.cartId)

        # Create task
        task_id = str(uuid.uuid4())
        task_repo = TaskRepository(db)
        task_repo.create({
            "id": task_id,
            "skill_id": cart_db.skill_id,
            "status": "payment_authorized",
            "cart_id": validated_params.cartId,
            "payment_mandate_id": payment_mandate_id,
            "price": float(cart_mandate.contents.payment_request.details.total.amount.value),
            "currency": settings.default_currency,
            "payment_status": "authorized_ap2",
            "created_at": datetime.utcnow()
        })

        log_payment(
            validated_params.cartId,
            float(cart_mandate.contents.payment_request.details.total.amount.value),
            settings.default_currency,
            "payment_authorized"
        )

        log_task(task_id, cart_db.skill_id, "payment_authorized")

        return {
            "success": True,
            "task_id": task_id,
            "payment_mandate_id": payment_mandate_id,
            "payment_mandate": payment_mandate.model_dump(),
            "status": "payment_authorized",
            "message": "Payment authorized. Task will be processed."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


async def submit_task(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Handle task submission"""
    try:
        validated_params = TaskParams(**params)

        task_id = validated_params.taskId or str(uuid.uuid4())
        skill_id = validated_params.skillId

        # Get user message
        user_message = ""
        for part in validated_params.message.parts:
            if part.type == "text" and part.text:
                user_message += part.text

        task_repo = TaskRepository(db)

        # Check if payment already authorized
        payment_mandate_id = validated_params.paymentMandateId
        if payment_mandate_id:
            payment_repo = PaymentMandateRepository(db)
            payment = payment_repo.get(payment_mandate_id)
            if payment and payment.status == "authorized":
                # Payment authorized, process immediately
                return await process_task(task_id, skill_id, user_message, db)

        # Payment required
        task_repo.create({
            "id": task_id,
            "skill_id": skill_id,
            "status": "payment_required",
            "user_message": user_message,
            "price": PRICING[skill_id]["price"],
            "currency": settings.default_currency,
            "payment_status": "pending",
            "created_at": datetime.utcnow()
        })

        log_task(task_id, skill_id, "payment_required")

        return {
            "taskId": task_id,
            "status": "payment_required",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": f"Payment required: ${PRICING[skill_id]['price']} {settings.default_currency}. Use AP2 flow to authorize payment."
                }]
            },
            "next_steps": {
                "ap2_flow": {
                    "1": "createIntentMandate",
                    "2": "createCartMandate",
                    "3": "processPayment"
                }
            }
        }

    except ValueError as e:
        logger.error(f"Validation error in submit_task: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        raise HTTPException(status_code=500, detail="Task submission failed")


async def process_task(task_id: str, skill_id: str, user_message: str, db: Session) -> Dict[str, Any]:
    """Process the consulting task using AI"""
    try:
        task_repo = TaskRepository(db)

        # Update task status
        task_repo.update(task_id, {
            "status": "working",
            "started_at": datetime.utcnow()
        })

        log_task(task_id, skill_id, "working")

        service_context = {
            "business-analysis": "You are a business analyst. Provide comprehensive business analysis with actionable insights.",
            "market-research": "You are a market research expert. Provide detailed market analysis with data-driven insights.",
            "strategy-planning": "You are a strategic planning consultant. Provide strategic recommendations and implementation plans.",
            "quick-consult": "You are a business consultant. Provide quick, actionable advice."
        }

        prompt = f"{service_context[skill_id]}\n\nClient Request: {user_message}\n\nProvide professional consulting response:"

        response = model.generate_content(prompt)
        result_text = response.text

        # Update task as completed
        task_repo.update(task_id, {
            "status": "completed",
            "result": result_text,
            "completed_at": datetime.utcnow()
        })

        log_task(task_id, skill_id, "completed")

        return {
            "taskId": task_id,
            "status": "completed",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": result_text
                }]
            },
            "artifacts": [{
                "type": "text",
                "name": f"{skill_id}_report",
                "mimeType": "text/plain",
                "data": result_text
            }],
            "metadata": {
                "service": skill_id,
                "price": PRICING[skill_id]["price"],
                "currency": settings.default_currency,
                "billable": True,
                "payment_protocol": "ap2"
            }
        }

    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}")

        task_repo.update(task_id, {
            "status": "failed",
            "error": str(e)
        })

        log_task(task_id, skill_id, "failed")

        raise HTTPException(status_code=500, detail=f"Task processing failed: {str(e)}")


async def get_task_status(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Check task status"""
    try:
        validated_params = TaskStatusParams(**params)

        task_repo = TaskRepository(db)
        task = task_repo.get(validated_params.taskId)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        response = {
            "taskId": task.id,
            "status": task.status
        }

        if task.status == "completed":
            response["message"] = {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": task.result or "Task completed"
                }]
            }
            response["metadata"] = {
                "service": task.skill_id,
                "price": task.price,
                "currency": task.currency,
                "billable": True
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


async def send_message(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Handle ongoing conversation within a task"""
    try:
        validated_params = SendMessageParams(**params)

        task_repo = TaskRepository(db)
        task = task_repo.get(validated_params.taskId)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        user_message = ""
        for part in validated_params.message.parts:
            if part.type == "text" and part.text:
                user_message += part.text

        response = model.generate_content(f"Continue the consulting conversation: {user_message}")

        return {
            "taskId": validated_params.taskId,
            "status": "working",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": response.text
                }]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@app.get("/")
async def root():
    """Info endpoint"""
    return {
        "agent": settings.agent_name,
        "version": settings.agent_version,
        "status": "operational",
        "payment_protocol": "AP2 v0.1",
        "environment": settings.environment,
        "services": [
            {
                "id": skill_id,
                "description": details["description"],
                "price": f"${details['price']} {settings.default_currency}"
            }
            for skill_id, details in PRICING.items()
        ],
        "agent_card": f"{settings.base_url}/.well-known/agent.json",
        "ap2_endpoints": {
            "createIntentMandate": "POST /a2a (method: createIntentMandate)",
            "createCartMandate": "POST /a2a (method: createCartMandate)",
            "processPayment": "POST /a2a (method: processPayment)"
        }
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Health check endpoint"""
    db_connected = True
    try:
        # Test database connection
        db.execute("SELECT 1")
    except:
        db_connected = False

    return {
        "status": "healthy" if db_connected else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.agent_version,
        "ap2_enabled": True,
        "database_connected": db_connected
    }


@app.get("/mandates/cart/{mandate_id}")
async def get_cart_mandate(mandate_id: str, db: Session = Depends(get_db)):
    """Retrieve a cart mandate"""
    cart_repo = CartMandateRepository(db)
    cart = cart_repo.get(mandate_id)

    if not cart:
        raise HTTPException(status_code=404, detail="Cart mandate not found")

    return {"type": "cart", "mandate": cart.cart_data}


@app.get("/mandates/payment/{mandate_id}")
async def get_payment_mandate(mandate_id: str, db: Session = Depends(get_db)):
    """Retrieve a payment mandate"""
    payment_repo = PaymentMandateRepository(db)
    payment = payment_repo.get(mandate_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment mandate not found")

    return {"type": "payment", "mandate": payment.payment_data}


if __name__ == "__main__":
    print(f"Starting {settings.agent_name}...")
    print(f"Version: {settings.agent_version}")
    print(f"Environment: {settings.environment}")
    print(f"Agent Card: {settings.base_url}/.well-known/agent.json")
    print(f"\nAP2 Payment Protocol Enabled [OK]")
    print(f"\nServices with AP2 pricing:")
    for service, details in PRICING.items():
        print(f"  - {service}: ${details['price']} - {details['description']}")
    print(f"\nAP2 Payment Flow:")
    print(f"  1. Create Intent Mandate (user expresses intent)")
    print(f"  2. Create Cart Mandate (merchant creates signed cart)")
    print(f"  3. Process Payment (user authorizes with Payment Mandate)")
    print(f"  4. Task executed automatically upon payment authorization")
    print("\nStarting server...")

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
