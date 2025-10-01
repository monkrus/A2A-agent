"""
Test client to interact with your monetizable A2A agent
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def get_agent_card():
    """Discover agent capabilities"""
    response = requests.get(f"{BASE_URL}/.well-known/agent.json")
    return response.json()

def submit_task(skill_id: str, user_message: str):
    """Submit a task to the agent"""
    task_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "method": "submitTask",
        "params": {
            "taskId": task_id,
            "skillId": skill_id,
            "message": {
                "role": "user",
                "parts": [{
                    "type": "text",
                    "text": user_message
                }]
            }
        },
        "id": 1
    }
    
    response = requests.post(f"{BASE_URL}/a2a", json=payload)
    return response.json()

def main():
    print("=" * 60)
    print("Testing Monetizable A2A Agent")
    print("=" * 60)
    
    # 1. Discover agent
    print("\n1. Discovering agent capabilities...")
    card = get_agent_card()
    print(f"Agent: {card['name']}")
    print(f"Description: {card['description']}")
    print("\nAvailable Services:")
    for skill in card['skills']:
        pricing = skill.get('pricing', {})
        print(f"  - {skill['id']}: ${pricing.get('amount', 0)} {pricing.get('currency', 'USD')}")
        print(f"    {skill['description']}")
    
    # 2. Submit a paid task
    print("\n2. Submitting paid consultation request...")
    result = submit_task(
        "business-analysis",
        "I'm planning to start an online tutoring platform. Can you analyze the market opportunity and provide strategic recommendations?"
    )
    
    print("\nTask Result:")
    if "result" in result:
        task_result = result["result"]
        print(f"Status: {task_result.get('status')}")
        
        if "metadata" in task_result:
            metadata = task_result["metadata"]
            print(f"Service: {metadata.get('service')}")
            print(f"Price: ${metadata.get('price')} {metadata.get('currency')}")
            print(f"Billable: {metadata.get('billable')}")
        
        if "message" in task_result:
            message = task_result["message"]
            for part in message.get("parts", []):
                if part.get("type") == "text":
                    print(f"\nConsultation Response:")
                    print("-" * 60)
                    print(part.get("text"))
                    print("-" * 60)
    
    # 3. Try another service
    print("\n3. Requesting market research...")
    result = submit_task(
        "market-research",
        "What are the current trends in AI-powered education technology?"
    )
    
    if "result" in result and "message" in result["result"]:
        message = result["result"]["message"]
        for part in message.get("parts", []):
            if part.get("type") == "text":
                print(f"\nMarket Research Response:")
                print("-" * 60)
                print(part.get("text")[:500] + "...")  # Show first 500 chars
                print("-" * 60)

if __name__ == "__main__":
    main()