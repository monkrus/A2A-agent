# Monetizable A2A Agent

A business consulting agent that implements the Agent-to-Agent (A2A) protocol with usage-based pricing. Powered by Google's Gemini AI.

## Features

- **Business Analysis** - Comprehensive business analysis and strategic recommendations ($25/request)
- **Market Research** - In-depth market research and competitive analysis ($50/request)
- **Financial Planning** - Financial projections and business planning assistance ($75/request)

## Project Structure

```
my-a2a-agent/
├── agent_server.py    # Main A2A agent server
├── test_client.py     # Client for testing the agent
├── requirements.txt   # Python dependencies
├── .env              # Environment configuration
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   - Get a Google API key from https://aistudio.google.com/apikey
   - Edit `.env` and set your `GOOGLE_API_KEY`

## Usage

### Start the Agent Server

```bash
python agent_server.py
```

The server will start at `http://localhost:8000`

### Test the Agent

In a separate terminal:

```bash
python test_client.py
```

This will:
1. Discover agent capabilities
2. Submit a business analysis request
3. Submit a market research request
4. Display responses and pricing

### API Endpoints

- `GET /.well-known/agent.json` - Agent discovery (returns capabilities and pricing)
- `POST /a2a` - A2A protocol endpoint (JSON-RPC 2.0)

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "submitTask",
  "params": {
    "taskId": "unique-task-id",
    "skillId": "business-analysis",
    "message": {
      "role": "user",
      "parts": [{
        "type": "text",
        "text": "Analyze the market opportunity for an online tutoring platform"
      }]
    }
  },
  "id": 1
}
```

## Services & Pricing

| Service | Description | Price |
|---------|-------------|-------|
| business-analysis | Comprehensive business analysis and strategic recommendations | $25 USD |
| market-research | In-depth market research and competitive analysis | $50 USD |
| financial-planning | Financial projections and business planning assistance | $75 USD |

## A2A Protocol

This agent implements the Agent-to-Agent (A2A) protocol, allowing it to:
- Advertise capabilities via agent card
- Receive and process tasks from other agents
- Return structured responses with pricing metadata
- Support usage-based billing

## Security Note

- Never commit your `.env` file with real API keys
- The `.env` file is already in `.gitignore`
- Replace placeholder API key before running

## License

MIT
