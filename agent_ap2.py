"""
Monetizable A2A Agent with AP2 Integration
This agent provides paid consulting services via A2A protocol with AP2 payment support
"""

import os
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

app = FastAPI()

# Agent configuration
AGENT_NAME = "Business Consultant Agent (AP2)"
AGENT_DESCRIPTION = "Professional business consulting agent with AP2 payment protocol support"
AGENT_VERSION = "2.0.0"
BASE_URL = "http://localhost:8000"
MERCHANT_ID = "consulting-agent-merchant-001"

# Pricing structure (in USD)
PRICING = {
    "business-analysis": {"price": 50.00, "description": "Comprehensive business analysis"},
    "market-research": {"price": 75.00, "description": "Market research and competitive analysis"},
    "strategy-planning": {"price": 100.00, "description": "Strategic business planning"},
    "quick-consult": {"price": 25.00, "description": "Quick consultation (15 min equivalent)"}
}

# In-memory storage
tasks: Dict[str, Dict[str, Any]] = {}
cart_mandates: Dict[str, CartMandate] = {}
payment_mandates: Dict[str, PaymentMandate] = {}

# Agent Card with AP2 support
AGENT_CARD = {
    "name": AGENT_NAME,
    "description": AGENT_DESCRIPTION,
    "provider": "Your Company Name",
    "url": f"{BASE_URL}/a2a",
    "version": AGENT_VERSION,
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
            "name": details["description"].split(" - ")[0],
            "description": details["description"],
            "inputModes": ["text"],
            "outputModes": ["text"],
            "pricing": {
                "amount": details["price"],
                "currency": "USD",
                "model": "per_transaction"
            }
        }
        for skill_id, details in PRICING.items()
    ]
}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Agent Discovery Endpoint with AP2 support"""
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a")
async def handle_a2a_request(request: Request):
    """Main A2A endpoint with AP2 payment flow support"""
    body = await request.json()

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    # Route to appropriate handler
    handlers = {
        "submitTask": submit_task,
        "getTaskStatus": get_task_status,
        "sendMessage": send_message,
        "createIntentMandate": create_intent_mandate,
        "createCartMandate": create_cart_mandate,
        "processPayment": process_payment,
    }

    handler = handlers.get(method)
    if not handler:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        })

    result = await handler(params)

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    })


async def create_intent_mandate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an Intent Mandate (AP2)
    User expresses intent to purchase consulting services
    """
    natural_language_description = params.get("description", "")
    skill_id = params.get("skillId")

    # Validate skill
    if skill_id and skill_id not in PRICING:
        return {
            "success": False,
            "error": f"Unknown service: {skill_id}"
        }

    # Create Intent Mandate
    intent = IntentMandate(
        user_cart_confirmation_required=True,
        natural_language_description=natural_language_description,
        merchants=[MERCHANT_ID],
        skus=[skill_id] if skill_id else None,
        requires_refundability=True,
        intent_expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    )

    return {
        "success": True,
        "intent_mandate": intent.model_dump(),
        "message": "Intent mandate created. Proceed to create cart."
    }


async def create_cart_mandate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Cart Mandate (AP2)
    Merchant creates a signed cart with specific items and pricing
    """
    skill_id = params.get("skillId")
    task_description = params.get("taskDescription", "")

    # Validate skill
    if skill_id not in PRICING:
        return {
            "success": False,
            "error": f"Unknown service: {skill_id}"
        }

    cart_id = str(uuid.uuid4())
    price = PRICING[skill_id]["price"]

    # Create Payment Request (W3C Payment Request API format)
    payment_request = PaymentRequest(
        method_data=[
            PaymentMethodData(
                supported_methods="https://pay.google.com/payment",
                data={"merchantId": MERCHANT_ID}
            )
        ],
        details=PaymentDetailsInit(
            id=cart_id,
            total=PaymentItem(
                label=PRICING[skill_id]["description"],
                amount=PaymentCurrencyAmount(
                    currency="USD",
                    value=str(price)
                ),
                refund_period=30  # 30 days refund period
            ),
            display_items=[
                PaymentItem(
                    label=f"{skill_id} - {task_description[:50]}",
                    amount=PaymentCurrencyAmount(
                        currency="USD",
                        value=str(price)
                    ),
                    refund_period=30
                )
            ]
        )
    )

    # Create Cart Contents
    cart_contents = CartContents(
        id=cart_id,
        user_cart_confirmation_required=True,
        payment_request=payment_request,
        cart_expiry=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        merchant_name=AGENT_NAME
    )

    # Create Cart Mandate (in production, this should be cryptographically signed)
    cart_mandate = CartMandate(
        contents=cart_contents,
        merchant_authorization=f"MERCHANT_SIG_{cart_id}"  # Replace with actual signature
    )

    # Store cart mandate
    cart_mandates[cart_id] = cart_mandate

    return {
        "success": True,
        "cart_id": cart_id,
        "cart_mandate": cart_mandate.model_dump(),
        "message": "Cart created. User must confirm and authorize payment."
    }


async def process_payment(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process payment with Payment Mandate (AP2)
    User authorizes payment for the cart
    """
    cart_id = params.get("cartId")
    payment_method = params.get("paymentMethod", {})
    user_authorization = params.get("userAuthorization", "")  # User's cryptographic signature

    # Validate cart exists
    if cart_id not in cart_mandates:
        return {
            "success": False,
            "error": "Cart not found or expired"
        }

    cart_mandate = cart_mandates[cart_id]
    payment_mandate_id = str(uuid.uuid4())

    # Create Payment Response
    payment_response = PaymentResponse(
        request_id=cart_id,
        method_name=payment_method.get("method_name", "card"),
        details=payment_method.get("details", {}),
        payer_name=payment_method.get("payer_name"),
        payer_email=payment_method.get("payer_email"),
    )

    # Create Payment Mandate Contents
    payment_mandate_contents = PaymentMandateContents(
        payment_mandate_id=payment_mandate_id,
        payment_details_id=cart_id,
        payment_details_total=cart_mandate.contents.payment_request.details.total,
        payment_response=payment_response,
        merchant_agent=MERCHANT_ID,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Create Payment Mandate
    payment_mandate = PaymentMandate(
        payment_mandate_contents=payment_mandate_contents,
        user_authorization=user_authorization or f"USER_SIG_{payment_mandate_id}"
    )

    # Store payment mandate
    payment_mandates[payment_mandate_id] = payment_mandate

    # Create task for the service
    task_id = str(uuid.uuid4())

    # Extract skill from cart
    skill_id = None
    for item in cart_mandate.contents.payment_request.details.display_items:
        for skill in PRICING.keys():
            if skill in item.label:
                skill_id = skill
                break

    if not skill_id:
        return {
            "success": False,
            "error": "Could not determine service type from cart"
        }

    tasks[task_id] = {
        "skillId": skill_id,
        "status": "payment_authorized",
        "cartId": cart_id,
        "paymentMandateId": payment_mandate_id,
        "price": float(cart_mandate.contents.payment_request.details.total.amount.value),
        "currency": "USD",
        "startTime": datetime.now().isoformat()
    }

    return {
        "success": True,
        "task_id": task_id,
        "payment_mandate_id": payment_mandate_id,
        "payment_mandate": payment_mandate.model_dump(),
        "status": "payment_authorized",
        "message": "Payment authorized. Task will be processed."
    }


async def submit_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle task submission (can be used with or without AP2)
    If payment_mandate_id is provided, skip payment and process directly
    """
    task_id = params.get("taskId") or str(uuid.uuid4())
    skill_id = params.get("skillId")
    message = params.get("message", {})
    payment_mandate_id = params.get("paymentMandateId")

    # Validate skill
    if skill_id not in PRICING:
        return {
            "taskId": task_id,
            "status": "failed",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": f"Unknown service: {skill_id}"
                }]
            }
        }

    # Get user message
    user_message = ""
    for part in message.get("parts", []):
        if part.get("type") == "text":
            user_message += part.get("text", "")

    # Check if payment was already processed via AP2
    if payment_mandate_id and payment_mandate_id in payment_mandates:
        # Payment already authorized, process immediately
        payment_status = "authorized_ap2"
    else:
        # Legacy flow - payment required
        payment_status = "payment_required"

    # Store/update task
    if task_id not in tasks:
        tasks[task_id] = {
            "skillId": skill_id,
            "status": "working" if payment_status == "authorized_ap2" else "payment_required",
            "userMessage": user_message,
            "price": PRICING[skill_id]["price"],
            "currency": "USD",
            "paymentStatus": payment_status,
            "startTime": datetime.now().isoformat()
        }

    # If payment authorized, process the task
    if payment_status == "authorized_ap2":
        return await process_task(task_id, skill_id, user_message)
    else:
        # Return payment required
        return {
            "taskId": task_id,
            "status": "payment_required",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": f"Payment required: ${PRICING[skill_id]['price']} USD. Use AP2 flow or provide payment."
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


async def process_task(task_id: str, skill_id: str, user_message: str) -> Dict[str, Any]:
    """Process the consulting task using AI"""
    try:
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
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result_text
        tasks[task_id]["completedTime"] = datetime.now().isoformat()

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
                "currency": "USD",
                "billable": True,
                "payment_protocol": "ap2"
            }
        }

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

        return {
            "taskId": task_id,
            "status": "failed",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": f"Error processing request: {str(e)}"
                }]
            }
        }


async def get_task_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Check task status"""
    task_id = params.get("taskId")

    if task_id not in tasks:
        return {
            "taskId": task_id,
            "status": "failed",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": "Task not found"
                }]
            }
        }

    task = tasks[task_id]

    response = {
        "taskId": task_id,
        "status": task["status"]
    }

    if task["status"] == "completed":
        response["message"] = {
            "role": "agent",
            "parts": [{
                "type": "text",
                "text": task.get("result", "Task completed")
            }]
        }
        response["metadata"] = {
            "service": task["skillId"],
            "price": task["price"],
            "currency": task["currency"],
            "billable": True
        }

    return response


async def send_message(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ongoing conversation within a task"""
    task_id = params.get("taskId")
    message = params.get("message", {})

    if task_id not in tasks:
        return {
            "taskId": task_id,
            "status": "failed"
        }

    user_message = ""
    for part in message.get("parts", []):
        if part.get("type") == "text":
            user_message += part.get("text", "")

    response = model.generate_content(f"Continue the consulting conversation: {user_message}")

    return {
        "taskId": task_id,
        "status": "working",
        "message": {
            "role": "agent",
            "parts": [{
                "type": "text",
                "text": response.text
            }]
        }
    }


@app.get("/")
async def root():
    """Info endpoint"""
    return {
        "agent": AGENT_NAME,
        "version": AGENT_VERSION,
        "status": "operational",
        "payment_protocol": "AP2 v0.1",
        "services": [
            {
                "id": skill_id,
                "description": details["description"],
                "price": f"${details['price']} USD"
            }
            for skill_id, details in PRICING.items()
        ],
        "agent_card": f"{BASE_URL}/.well-known/agent.json",
        "ap2_endpoints": {
            "createIntentMandate": "POST /a2a (method: createIntentMandate)",
            "createCartMandate": "POST /a2a (method: createCartMandate)",
            "processPayment": "POST /a2a (method: processPayment)"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ap2_enabled": True
    }


@app.get("/mandates/{mandate_id}")
async def get_mandate(mandate_id: str):
    """Retrieve a specific mandate (for verification)"""
    if mandate_id in cart_mandates:
        return {"type": "cart", "mandate": cart_mandates[mandate_id].model_dump()}
    elif mandate_id in payment_mandates:
        return {"type": "payment", "mandate": payment_mandates[mandate_id].model_dump()}
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Mandate not found"}
        )


if __name__ == "__main__":
    print(f"Starting {AGENT_NAME}...")
    print(f"Agent Card: {BASE_URL}/.well-known/agent.json")
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
