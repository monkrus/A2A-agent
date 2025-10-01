"""
Monetizable A2A Agent - Consulting Service
This agent provides paid consulting services via A2A protocol
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

app = FastAPI()

# Agent configuration
AGENT_NAME = "Business Consultant Agent"
AGENT_DESCRIPTION = "Professional business consulting agent that provides strategic advice, market analysis, and business planning services"
AGENT_VERSION = "1.0.0"
BASE_URL = "http://localhost:8000"  # Change this to your deployed URL

# Pricing structure (in USD)
PRICING = {
    "business-analysis": {"price": 50, "description": "Comprehensive business analysis"},
    "market-research": {"price": 75, "description": "Market research and competitive analysis"},
    "strategy-planning": {"price": 100, "description": "Strategic business planning"},
    "quick-consult": {"price": 25, "description": "Quick consultation (15 min equivalent)"}
}

# In-memory task storage (use database in production)
tasks: Dict[str, Dict[str, Any]] = {}

# Agent Card - tells other agents what this agent can do
AGENT_CARD = {
    "name": AGENT_NAME,
    "description": AGENT_DESCRIPTION,
    "provider": "Your Company Name",
    "url": f"{BASE_URL}/a2a",
    "version": AGENT_VERSION,
    "capabilities": ["streaming", "pushNotifications"],
    "authentication": {
        "schemes": ["Bearer"]  # For production, implement proper auth
    },
    "skills": [
        {
            "id": "business-analysis",
            "name": "Business Analysis",
            "description": f"{PRICING['business-analysis']['description']} - ${PRICING['business-analysis']['price']}",
            "inputModes": ["text"],
            "outputModes": ["text"],
            "pricing": {
                "amount": PRICING['business-analysis']['price'],
                "currency": "USD"
            }
        },
        {
            "id": "market-research",
            "name": "Market Research",
            "description": f"{PRICING['market-research']['description']} - ${PRICING['market-research']['price']}",
            "inputModes": ["text"],
            "outputModes": ["text"],
            "pricing": {
                "amount": PRICING['market-research']['price'],
                "currency": "USD"
            }
        },
        {
            "id": "strategy-planning",
            "name": "Strategy Planning",
            "description": f"{PRICING['strategy-planning']['description']} - ${PRICING['strategy-planning']['price']}",
            "inputModes": ["text"],
            "outputModes": ["text"],
            "pricing": {
                "amount": PRICING['strategy-planning']['price'],
                "currency": "USD"
            }
        },
        {
            "id": "quick-consult",
            "name": "Quick Consultation",
            "description": f"{PRICING['quick-consult']['description']} - ${PRICING['quick-consult']['price']}",
            "inputModes": ["text"],
            "outputModes": ["text"],
            "pricing": {
                "amount": PRICING['quick-consult']['price'],
                "currency": "USD"
            }
        }
    ]
}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Agent Discovery Endpoint
    Other agents call this to learn about your agent's capabilities
    """
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a")
async def handle_a2a_request(request: Request):
    """
    Main A2A endpoint - handles all agent-to-agent communication
    Implements JSON-RPC 2.0 protocol
    """
    body = await request.json()
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    # Route to appropriate handler
    if method == "submitTask":
        result = await submit_task(params)
    elif method == "getTaskStatus":
        result = await get_task_status(params)
    elif method == "sendMessage":
        result = await send_message(params)
    else:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        })
    
    return JSONResponse(content={
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    })


async def submit_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle new task submission
    This is where clients request your paid services
    """
    task_id = params.get("taskId")
    skill_id = params.get("skillId")
    message = params.get("message", {})
    
    # Validate skill and get pricing
    if skill_id not in PRICING:
        return {
            "taskId": task_id,
            "status": "failed",
            "message": {
                "role": "agent",
                "parts": [{
                    "type": "text",
                    "text": f"Unknown service: {skill_id}. Available services: {', '.join(PRICING.keys())}"
                }]
            }
        }
    
    # Get the user's request
    user_message = ""
    for part in message.get("parts", []):
        if part.get("type") == "text":
            user_message += part.get("text", "")
    
    # Store task
    tasks[task_id] = {
        "skillId": skill_id,
        "status": "working",
        "userMessage": user_message,
        "price": PRICING[skill_id]["price"],
        "currency": "USD",
        "startTime": datetime.now().isoformat()
    }
    
    # Process the request with AI
    try:
        # Create context-aware prompt
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
                "billable": True
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
    """
    Check the status of a submitted task
    """
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
    """
    Handle ongoing conversation within a task
    """
    task_id = params.get("taskId")
    message = params.get("message", {})
    
    if task_id not in tasks:
        return {
            "taskId": task_id,
            "status": "failed"
        }
    
    # Extract user message
    user_message = ""
    for part in message.get("parts", []):
        if part.get("type") == "text":
            user_message += part.get("text", "")
    
    # Generate response
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
    """
    Info endpoint
    """
    return {
        "agent": AGENT_NAME,
        "version": AGENT_VERSION,
        "status": "operational",
        "services": [
            {
                "id": skill_id,
                "name": skill["name"],
                "price": f"${skill['pricing']['amount']} {skill['pricing']['currency']}"
            }
            for skill_id, skill in [(s["id"], s) for s in AGENT_CARD["skills"]]
        ],
        "agent_card": f"{BASE_URL}/.well-known/agent.json"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    print(f"Starting {AGENT_NAME}...")
    print(f"Agent Card available at: {BASE_URL}/.well-known/agent.json")
    print(f"\nMonetization enabled with pricing:")
    for service, details in PRICING.items():
        print(f"  - {service}: ${details['price']} - {details['description']}")
    print("\nStarting server...")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)