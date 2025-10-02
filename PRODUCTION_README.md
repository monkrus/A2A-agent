# Production-Ready A2A Agent with AP2 Payment Integration


A fully production-ready Agent-to-Agent (A2A) protocol implementation with AP2 payment support, designed for monetizable AI services.

## Features

### ✅ Production-Ready Components

1. **Configuration Management**
   - Environment-based configuration
   - Validation with Pydantic
   - Separate dev/prod settings

2. **Error Handling & Validation**
   - Comprehensive input validation
   - Structured error responses
   - Request/response validation with Pydantic models

3. **Logging & Monitoring**
   - Structured logging
   - Rotating file logs
   - Request/response tracking
   - Performance metrics

4. **Database Persistence**
   - SQLAlchemy ORM
   - SQLite for development
   - PostgreSQL-ready for production
   - Task, cart, and payment storage

5. **Security**
   - CORS configuration
   - Rate limiting (60 req/min default)
   - Security headers
   - Request logging

6. **Containerization**
   - Docker support
   - Docker Compose orchestration
   - Health checks
   - Volume management

7. **Testing**
   - Comprehensive test suite
   - Unit and integration tests
   - Database testing

## Architecture

```
my-a2a-agent/
├── agent_production.py      # Production-ready main application
├── config.py                 # Configuration management
├── models.py                 # Pydantic models for validation
├── database.py               # Database layer with SQLAlchemy
├── logger.py                 # Logging configuration
├── middleware.py             # Security, rate limiting, CORS
├── Dockerfile               # Docker container configuration
├── docker-compose.yml       # Multi-container orchestration
├── .env.example             # Environment variables template
├── requirements_production.txt  # Production dependencies
├── test_production.py       # Test suite
└── PRODUCTION_README.md     # This file
```

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` and set your values:
```env
GOOGLE_API_KEY=your_actual_api_key_here
BASE_URL=http://localhost:8000
ENVIRONMENT=development
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_production.txt
```

### 3. Run Locally

```bash
python agent_production.py
```

The agent will be available at:
- Main endpoint: `http://localhost:8000/a2a`
- Agent card: `http://localhost:8000/.well-known/agent.json`
- Health check: `http://localhost:8000/health`

### 4. Run with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | **Required** |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `BASE_URL` | Public URL | `http://localhost:8000` |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | Database connection string | `sqlite:///./agent.db` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:3000,http://localhost:8000` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |

### Pricing Configuration

Edit `config.py` to modify service pricing:

```python
PRICING = {
    "business-analysis": {"price": 50.00, "description": "..."},
    "market-research": {"price": 75.00, "description": "..."},
    # Add more services...
}
```

## AP2 Payment Flow

The agent implements the complete AP2 payment protocol:

### 1. Intent Mandate
User expresses intent to purchase:
```json
{
  "method": "createIntentMandate",
  "params": {
    "description": "I need business analysis",
    "skillId": "business-analysis"
  }
}
```

### 2. Cart Mandate
Merchant creates a signed cart:
```json
{
  "method": "createCartMandate",
  "params": {
    "skillId": "business-analysis",
    "taskDescription": "Analyze my startup idea"
  }
}
```

### 3. Payment Mandate
User authorizes payment:
```json
{
  "method": "processPayment",
  "params": {
    "cartId": "cart-id-from-step-2",
    "paymentMethod": {
      "method_name": "card",
      "details": {...}
    }
  }
}
```

### 4. Task Execution
Task is automatically executed after payment authorization.

## API Endpoints

### Discovery
- `GET /.well-known/agent.json` - Agent discovery card

### A2A Protocol
- `POST /a2a` - Main A2A JSON-RPC endpoint

### Health & Status
- `GET /` - Agent information
- `GET /health` - Health check

### Mandates
- `GET /mandates/cart/{mandate_id}` - Retrieve cart mandate
- `GET /mandates/payment/{mandate_id}` - Retrieve payment mandate

## Database

### SQLite (Development)
Default configuration uses SQLite:
```env
DATABASE_URL=sqlite:///./agent.db
```

### PostgreSQL (Production)
For production, use PostgreSQL:

1. Uncomment the PostgreSQL service in `docker-compose.yml`
2. Update environment variables:
```env
DATABASE_URL=postgresql://agent:password@postgres:5432/agent_db
```

### Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Security

### Rate Limiting
- Default: 60 requests per minute per IP
- Configurable via `RATE_LIMIT_PER_MINUTE`

### CORS
- Configurable allowed origins
- Credentials support
- Custom headers

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Content-Security-Policy (in production)

## Monitoring & Logging

### Logs
- Console output: INFO level
- File logs: DEBUG level (rotated at 10MB)
- Location: `./agent.log` or `LOG_FILE` env var

### Log Format
```
2025-01-15 10:30:45 - agent - INFO - [req_123] POST /a2a
2025-01-15 10:30:45 - agent - INFO - [req_123] 200 - 125.45ms
```

### Health Check
Monitor agent health at `/health`:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:45",
  "version": "2.0.0",
  "ap2_enabled": true,
  "database_connected": true
}
```

## Testing

### Run Tests
```bash
# All tests
pytest test_production.py -v

# Specific test
pytest test_production.py::test_agent_discovery -v

# With coverage
pytest --cov=. test_production.py
```

### Test Coverage
- Agent discovery
- Health checks
- AP2 payment flow
- Task submission
- Error handling
- Database operations

## Deployment

### Docker Deployment

```bash
# Build
docker build -t a2a-agent:latest .

# Run
docker run -d \
  -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  -e BASE_URL=https://your-domain.com \
  -e ENVIRONMENT=production \
  -v agent-data:/app/data \
  -v agent-logs:/app/logs \
  a2a-agent:latest
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Use strong `GOOGLE_API_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set appropriate `ALLOWED_ORIGINS`
- [ ] Configure rate limiting
- [ ] Set up log rotation
- [ ] Enable HTTPS
- [ ] Configure backup strategy
- [ ] Set up monitoring/alerting
- [ ] Review security headers
- [ ] Test all endpoints

### Environment-Specific Settings

#### Development
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./agent.db
```

#### Production
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@host/db
ALLOWED_ORIGINS=https://yourdomain.com
```

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Database Issues
```bash
# Reset database
rm agent.db
python agent_production.py
```

### Docker Issues
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## Performance

### Recommended Settings

**Development:**
- SQLite database
- Single worker
- Debug logging

**Production:**
- PostgreSQL database
- Multiple workers (via Gunicorn)
- INFO logging
- Connection pooling

### Scaling

For high traffic, use Gunicorn:
```bash
gunicorn agent_production:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Support

For issues or questions:
1. Check logs: `tail -f agent.log`
2. Verify environment variables
3. Test health endpoint: `curl http://localhost:8000/health`
4. Review AP2 documentation

## License

See main project README for license information.
