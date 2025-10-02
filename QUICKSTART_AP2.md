# Quick Start Guide - AP2 Monetizable Agent

Get your AP2-enabled consulting agent running in 5 minutes!

## Prerequisites

- Python 3.10 or higher ✓ (You have 3.13.7)
- Google API Key ([Get one here](https://aistudio.google.com/app/apikey))

## 1. Install Dependencies

```bash
pip install -r requirements_ap2.txt
```

This installs:
- FastAPI & Uvicorn (web framework)
- Google Generative AI (Gemini)
- AP2 Protocol library
- Other dependencies

## 2. Set Up Environment

Create a `.env` file in your project directory:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

## 3. Start the Agent

```bash
python agent_ap2.py
```

You should see:

```
Starting Business Consultant Agent (AP2)...
Agent Card: http://localhost:8000/.well-known/agent.json

AP2 Payment Protocol Enabled ✓

Services with AP2 pricing:
  - business-analysis: $50 - Comprehensive business analysis
  - market-research: $75 - Market research and competitive analysis
  - strategy-planning: $100 - Strategic business planning
  - quick-consult: $25 - Quick consultation (15 min equivalent)

AP2 Payment Flow:
  1. Create Intent Mandate (user expresses intent)
  2. Create Cart Mandate (merchant creates signed cart)
  3. Process Payment (user authorizes with Payment Mandate)
  4. Task executed automatically upon payment authorization

Starting server...
INFO:     Started server process [xxxx]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 4. Test the Agent

Open a **new terminal** and run the test client:

```bash
python test_ap2_client.py
```

This will run through the complete AP2 payment flow:
1. ✓ Discover agent capabilities
2. ✓ Create Intent Mandate
3. ✓ Create Cart Mandate
4. ✓ Process Payment
5. ✓ Execute consulting task with AI
6. ✓ Test legacy flow

## What You'll See

The test will demonstrate:

### Step 1: Agent Discovery
```json
{
  "name": "Business Consultant Agent (AP2)",
  "version": "2.0.0",
  "ap2": {
    "supported": true,
    "version": "0.1"
  }
}
```

### Step 2: Intent Mandate
User expresses: *"I need a comprehensive business analysis for my startup"*

### Step 3: Cart Mandate
Merchant creates signed cart:
- Service: Business Analysis
- Price: $50 USD
- Expiry: 1 hour

### Step 4: Payment Mandate
User authorizes payment with cryptographic signature

### Step 5: AI Response
Agent delivers comprehensive business consulting response powered by Gemini 2.0 Flash

## Key Files

| File | Purpose |
|------|---------|
| `agent_ap2.py` | Main AP2-enabled agent |
| `test_ap2_client.py` | Test client demonstrating AP2 flow |
| `agent.py` | Original A2A agent (legacy) |
| `README_AP2.md` | Complete documentation |
| `requirements_ap2.txt` | Python dependencies |

## API Endpoints

Once running, your agent exposes:

- `http://localhost:8000/` - Agent info
- `http://localhost:8000/.well-known/agent.json` - Agent card
- `http://localhost:8000/a2a` - Main JSON-RPC endpoint
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/mandates/{id}` - Mandate retrieval

## Manual Testing with cURL

### Get Agent Card
```bash
curl http://localhost:8000/.well-known/agent.json
```

### Create Intent Mandate
```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "createIntentMandate",
    "params": {
      "description": "I want business analysis",
      "skillId": "business-analysis"
    },
    "id": 1
  }'
```

### Create Cart
```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "createCartMandate",
    "params": {
      "skillId": "business-analysis",
      "taskDescription": "Market opportunity analysis"
    },
    "id": 1
  }'
```

### Process Payment
```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "processPayment",
    "params": {
      "cartId": "YOUR_CART_ID",
      "paymentMethod": {
        "method_name": "card",
        "payer_name": "Jane Doe",
        "payer_email": "jane@example.com"
      }
    },
    "id": 1
  }'
```

## Understanding AP2 Flow

```
┌──────────────────────────────────────────────────────┐
│                   AP2 PAYMENT FLOW                   │
└──────────────────────────────────────────────────────┘

1️⃣  USER INTENT
    ↓
    User expresses desire to purchase
    Creates: Intent Mandate
    Contains: Natural language description, merchants, SKUs

2️⃣  CART CREATION
    ↓
    Merchant creates cart with items & pricing
    Creates: Cart Mandate (signed by merchant)
    Contains: Items, prices, expiry, payment request

3️⃣  PAYMENT AUTHORIZATION
    ↓
    User reviews and authorizes payment
    Creates: Payment Mandate (signed by user)
    Contains: Payment details, user authorization

4️⃣  TASK EXECUTION
    ↓
    Agent processes the consulting request
    Delivers: AI-powered consulting response

5️⃣  DELIVERY
    ↓
    Results delivered with billing metadata
```

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Alternative: Change port in agent_ap2.py
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Google API Key Issues
- Get key from: https://aistudio.google.com/app/apikey
- Make sure it's in `.env` file
- Restart the agent after adding the key

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements_ap2.txt
```

### Connection Refused
- Make sure agent is running (`python agent_ap2.py`)
- Check firewall settings
- Verify port 8000 is accessible

## Next Steps

1. **Customize Services**: Edit `PRICING` dictionary in `agent_ap2.py`
2. **Improve AI Prompts**: Modify `service_context` prompts
3. **Add Real Signatures**: Implement cryptographic signing
4. **Deploy**: Use deployment guide in `README_AP2.md`
5. **Integrate Payment Processor**: Add Stripe, PayPal, etc.

## Production Readiness

⚠️ **This is a demo**. For production:

- [ ] Implement real cryptographic signatures
- [ ] Add payment processor integration
- [ ] Set up database (PostgreSQL, MongoDB)
- [ ] Add authentication & authorization
- [ ] Implement rate limiting
- [ ] Add comprehensive logging
- [ ] Set up monitoring & alerts
- [ ] Perform security audit
- [ ] Add unit & integration tests
- [ ] Deploy with HTTPS

## Resources

- [AP2 Specification](https://ap2-protocol.org/)
- [GitHub Repo](https://github.com/google-agentic-commerce/AP2)
- [Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol)

---

**Happy Building! 🚀**
