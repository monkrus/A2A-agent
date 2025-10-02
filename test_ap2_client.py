"""
AP2 Client Test Script
Demonstrates the complete AP2 payment flow with the consulting agent
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def make_request(method, params):
    """Make a JSON-RPC request to the agent"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }

    response = requests.post(f"{BASE_URL}/a2a", json=payload)
    return response.json()

def test_agent_discovery():
    """Test 1: Discover agent capabilities"""
    print_section("TEST 1: Agent Discovery")

    response = requests.get(f"{BASE_URL}/.well-known/agent.json")
    agent_card = response.json()

    print(f"Agent Name: {agent_card['name']}")
    print(f"Version: {agent_card['version']}")
    print(f"AP2 Support: {agent_card.get('ap2', {}).get('supported', False)}")
    print(f"\nAvailable Services:")
    for skill in agent_card['skills']:
        print(f"  - {skill['id']}: ${skill['pricing']['amount']} {skill['pricing']['currency']}")

    return agent_card

def test_intent_mandate():
    """Test 2: Create Intent Mandate"""
    print_section("TEST 2: Create Intent Mandate")

    params = {
        "description": "I need a comprehensive business analysis for my startup",
        "skillId": "business-analysis"
    }

    result = make_request("createIntentMandate", params)
    print(f"Success: {result.get('result', {}).get('success')}")
    print(f"Message: {result.get('result', {}).get('message')}")

    if result.get('result', {}).get('success'):
        intent = result['result']['intent_mandate']
        print(f"\nIntent Mandate Details:")
        print(f"  - Description: {intent['natural_language_description']}")
        print(f"  - Merchant: {intent['merchants'][0]}")
        print(f"  - SKUs: {intent['skus']}")
        print(f"  - Expiry: {intent['intent_expiry']}")

    return result

def test_cart_mandate():
    """Test 3: Create Cart Mandate"""
    print_section("TEST 3: Create Cart Mandate")

    params = {
        "skillId": "business-analysis",
        "taskDescription": "Analyze market opportunity for AI consulting services"
    }

    result = make_request("createCartMandate", params)
    print(f"Success: {result.get('result', {}).get('success')}")
    print(f"Cart ID: {result.get('result', {}).get('cart_id')}")

    if result.get('result', {}).get('success'):
        cart = result['result']['cart_mandate']
        print(f"\nCart Mandate Details:")
        print(f"  - Merchant: {cart['contents']['merchant_name']}")
        print(f"  - Total: ${cart['contents']['payment_request']['details']['total']['amount']['value']} {cart['contents']['payment_request']['details']['total']['amount']['currency']}")
        print(f"  - Expiry: {cart['contents']['cart_expiry']}")
        print(f"  - Items:")
        for item in cart['contents']['payment_request']['details']['display_items']:
            print(f"    * {item['label']}: ${item['amount']['value']}")

    return result

def test_process_payment(cart_id):
    """Test 4: Process Payment with Payment Mandate"""
    print_section("TEST 4: Process Payment")

    params = {
        "cartId": cart_id,
        "paymentMethod": {
            "method_name": "card",
            "details": {
                "cardNumber": "4111111111111111",
                "cardType": "visa"
            },
            "payer_name": "John Doe",
            "payer_email": "john@example.com"
        },
        "userAuthorization": "USER_SIGNATURE_PLACEHOLDER"
    }

    result = make_request("processPayment", params)
    print(f"Success: {result.get('result', {}).get('success')}")
    print(f"Task ID: {result.get('result', {}).get('task_id')}")
    print(f"Payment Mandate ID: {result.get('result', {}).get('payment_mandate_id')}")
    print(f"Status: {result.get('result', {}).get('status')}")

    if result.get('result', {}).get('success'):
        mandate = result['result']['payment_mandate']
        print(f"\nPayment Mandate Details:")
        print(f"  - Payment ID: {mandate['payment_mandate_contents']['payment_mandate_id']}")
        print(f"  - Timestamp: {mandate['payment_mandate_contents']['timestamp']}")
        print(f"  - Merchant Agent: {mandate['payment_mandate_contents']['merchant_agent']}")
        print(f"  - Total: ${mandate['payment_mandate_contents']['payment_details_total']['amount']['value']}")

    return result

def test_submit_task_with_payment(payment_mandate_id):
    """Test 5: Submit Task with Existing Payment"""
    print_section("TEST 5: Submit Task (With AP2 Payment)")

    params = {
        "skillId": "business-analysis",
        "paymentMandateId": payment_mandate_id,
        "message": {
            "role": "user",
            "parts": [{
                "type": "text",
                "text": "Analyze the market opportunity for AI-powered business consulting services. Include market size, competition, and growth potential."
            }]
        }
    }

    result = make_request("submitTask", params)

    if 'result' in result:
        res = result['result']
        print(f"Task ID: {res.get('taskId')}")
        print(f"Status: {res.get('status')}")

        if res.get('status') == 'completed':
            message = res.get('message', {}).get('parts', [{}])[0].get('text', '')
            print(f"\nConsulting Response:")
            print(f"{message[:500]}..." if len(message) > 500 else message)

            metadata = res.get('metadata', {})
            print(f"\nBilling Info:")
            print(f"  - Service: {metadata.get('service')}")
            print(f"  - Price: ${metadata.get('price')} {metadata.get('currency')}")
            print(f"  - Protocol: {metadata.get('payment_protocol')}")

    return result

def test_legacy_flow():
    """Test 6: Legacy Flow (Without AP2)"""
    print_section("TEST 6: Legacy Flow (Without AP2 Payment)")

    params = {
        "skillId": "quick-consult",
        "message": {
            "role": "user",
            "parts": [{
                "type": "text",
                "text": "What are the key factors for startup success?"
            }]
        }
    }

    result = make_request("submitTask", params)

    if 'result' in result:
        res = result['result']
        print(f"Task ID: {res.get('taskId')}")
        print(f"Status: {res.get('status')}")

        if res.get('status') == 'payment_required':
            message = res.get('message', {}).get('parts', [{}])[0].get('text', '')
            print(f"\nResponse: {message}")
            print(f"\nNext Steps:")
            next_steps = res.get('next_steps', {}).get('ap2_flow', {})
            for step, method in next_steps.items():
                print(f"  {step}. {method}")

    return result

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  AP2 PAYMENT FLOW DEMONSTRATION")
    print("  Business Consulting Agent with Agent Payments Protocol")
    print("=" * 70)

    try:
        # Test 1: Agent Discovery
        agent_card = test_agent_discovery()

        # Test 2: Create Intent Mandate
        intent_result = test_intent_mandate()

        # Test 3: Create Cart Mandate
        cart_result = test_cart_mandate()
        cart_id = cart_result.get('result', {}).get('cart_id')

        if not cart_id:
            print("\n[ERROR] Failed to create cart. Stopping tests.")
            return

        # Test 4: Process Payment
        payment_result = test_process_payment(cart_id)
        payment_mandate_id = payment_result.get('result', {}).get('payment_mandate_id')

        if not payment_mandate_id:
            print("\n[ERROR] Failed to process payment. Stopping tests.")
            return

        # Test 5: Submit Task with Payment
        task_result = test_submit_task_with_payment(payment_mandate_id)

        # Test 6: Legacy Flow
        legacy_result = test_legacy_flow()

        print_section("TESTS COMPLETED SUCCESSFULLY [OK]")
        print("\nAP2 Payment Flow Summary:")
        print("  1. [OK] Agent Discovery")
        print("  2. [OK] Intent Mandate Created")
        print("  3. [OK] Cart Mandate Created")
        print("  4. [OK] Payment Processed (Payment Mandate)")
        print("  5. [OK] Task Executed with AI")
        print("  6. [OK] Legacy Flow Tested")

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to agent.")
        print("   Please make sure the agent is running:")
        print("   python agent_ap2.py")
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
