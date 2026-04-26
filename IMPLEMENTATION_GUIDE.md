# Implementation Guide for Real Threads Integration

This guide walks you through implementing the actual Threads API integration and deploying to production.

## Phase 1: Development Setup (Complete ✅)

You already have:
- ✅ Complete project structure
- ✅ Database models and migrations
- ✅ LLM abstraction layer
- ✅ Publisher abstraction layer
- ✅ Scheduler and automation
- ✅ API endpoints
- ✅ Mock publisher for testing

## Phase 2: Implementing Real Threads Publisher

### Option A: Official Threads API (Recommended)

When Meta releases the official Threads API, follow these steps:

#### 1. Get API Credentials

```bash
# Visit Threads Developer Portal (when available)
# Create an app
# Get your API key and credentials
```

#### 2. Update Environment Variables

```env
THREADS_PUBLISHER=api
THREADS_API_URL=https://api.threads.net/v1
THREADS_API_KEY=your-api-key-here
```

#### 3. Implement API Client

Edit `app/publishers/threads_api.py`:

```python
async def publish(self, account_id: int, text: str, 
                 hashtags: list[str] = None, media_urls: list[str] = None) -> PublishResult:
    """Publish to Threads via official API."""
    
    # Get account from database
    result = await self.db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        return PublishResult(success=False, error="Account not found")
    
    # Format post
    formatted_text = self._format_post_text(text, hashtags)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Build request
            payload = {
                "text": formatted_text,
                "user_id": account.username,  # or account.threads_user_id
            }
            
            if media_urls:
                payload["media_urls"] = media_urls
            
            # Make API call
            response = await client.post(
                f"{self.api_url}/posts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {account.api_token or self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return PublishResult(
                    success=True,
                    post_id=data["id"],
                    post_url=data["url"],
                    published_at=datetime.utcnow(),
                    metadata=data
                )
            else:
                return PublishResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}"
                )
                
    except Exception as e:
        logger.error(f"Publishing error: {str(e)}")
        return PublishResult(success=False, error=str(e))
```

#### 4. Add Account Token Management

Update `app/models/account.py` to include OAuth flow if needed:

```python
# Add fields for OAuth
oauth_access_token = Column(String(500))
oauth_refresh_token = Column(String(500))
oauth_expires_at = Column(DateTime)
```

#### 5. Test with Real API

```bash
# Test health check
curl http://localhost:8000/api/dashboard/health

# Create account with real credentials
curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_threads_username",
    "api_token": "your-api-token",
    ...
  }'

# Test publishing
curl -X POST http://localhost:8000/api/content/publish/1
```

### Option B: Browser Automation (If API Not Available)

If official API is not available, use browser automation:

#### 1. Install Playwright

```bash
pip install playwright
playwright install chromium
```

#### 2. Create Browser Publisher

Create `app/publishers/browser_automation.py`:

```python
from playwright.async_api import async_playwright
from app.publishers.base import BasePublisher, PublishResult
import logging

logger = logging.getLogger(__name__)


class BrowserPublisher(BasePublisher):
    """Publisher using browser automation."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    async def publish(self, account_id: int, text: str,
                     hashtags: list[str] = None, media_urls: list[str] = None) -> PublishResult:
        """Publish via browser automation."""
        
        # Get account credentials
        # (implement credential retrieval)
        
        formatted_text = self._format_post_text(text, hashtags)
        
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to Threads
                await page.goto("https://www.threads.net/login")
                
                # Login (if not already logged in)
                # Check for login form
                if await page.is_visible('input[name="username"]'):
                    await page.fill('input[name="username"]', username)
                    await page.fill('input[name="password"]', password)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")
                
                # Navigate to compose
                await page.goto("https://www.threads.net/")
                
                # Click compose button
                await page.click('[aria-label="Create post"]')
                await page.wait_for_selector('textarea')
                
                # Fill post text
                await page.fill('textarea', formatted_text)
                
                # Upload media if provided
                if media_urls:
                    for media_url in media_urls:
                        # Download media locally first
                        # Then upload via file input
                        await page.set_input_files('input[type="file"]', media_url)
                
                # Click post button
                await page.click('button:has-text("Post")')
                
                # Wait for success
                await page.wait_for_selector('[data-post-id]', timeout=10000)
                
                # Extract post ID/URL
                post_element = await page.query_selector('[data-post-id]')
                post_id = await post_element.get_attribute('data-post-id')
                post_url = page.url
                
                await browser.close()
                
                return PublishResult(
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                    published_at=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Browser automation error: {str(e)}")
            return PublishResult(success=False, error=str(e))
    
    async def health_check(self) -> bool:
        """Check if browser automation is available."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
                return True
        except Exception:
            return False
    
    async def get_account_info(self, account_id: int) -> dict:
        """Get account info via scraping."""
        # Implement if needed
        return None
```

#### 3. Update Publisher Factory

Edit `app/publishers/__init__.py`:

```python
def get_publisher(publisher_type: Optional[str] = None) -> BasePublisher:
    publisher_type = publisher_type or settings.threads_publisher
    
    if publisher_type.lower() == "mock":
        return MockPublisher()
    elif publisher_type.lower() == "api":
        return ThreadsAPIPublisher(...)
    elif publisher_type.lower() == "browser":
        from app.publishers.browser_automation import BrowserPublisher
        return BrowserPublisher(headless=True)
    else:
        raise ValueError(f"Unknown publisher type: {publisher_type}")
```

#### 4. Secure Credential Storage

For browser automation, you need to store login credentials securely:

```python
# Option 1: Environment variables
THREADS_USERNAME=your_username
THREADS_PASSWORD=your_password

# Option 2: Encrypted in database
from cryptography.fernet import Fernet

def encrypt_password(password: str, key: bytes) -> str:
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

## Phase 3: Production Deployment

### Option A: Docker Deployment

#### 1. Build and Run

```bash
# Build image
docker build -t threads-automation .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f app
```

#### 2. Environment Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    image: threads-automation:latest
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/threads
      - LLM_PROVIDER=openai
      - LLM_API_KEY=${OPENAI_API_KEY}
      - THREADS_PUBLISHER=api
      - THREADS_API_KEY=${THREADS_API_KEY}
    restart: always
    
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: always
```

### Option B: Cloud Platform Deployment

#### AWS Deployment

```bash
# 1. Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier threads-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password ${DB_PASSWORD}

# 2. Deploy to ECS/Fargate
# Create task definition
# Create service
# Configure load balancer

# 3. Set environment variables in ECS task definition
```

#### Heroku Deployment

```bash
# 1. Create Heroku app
heroku create threads-automation

# 2. Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# 3. Set environment variables
heroku config:set LLM_PROVIDER=openai
heroku config:set LLM_API_KEY=your-key
heroku config:set THREADS_PUBLISHER=api

# 4. Deploy
git push heroku main

# 5. Run migrations
heroku run alembic upgrade head
```

#### DigitalOcean App Platform

```yaml
# app.yaml
name: threads-automation
services:
  - name: web
    github:
      repo: your-username/threads-automation
      branch: main
    build_command: pip install -r requirements.txt
    run_command: uvicorn app.main:app --host 0.0.0.0 --port 8080
    envs:
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
      - key: LLM_PROVIDER
        value: openai
      - key: LLM_API_KEY
        value: ${OPENAI_API_KEY}
    
databases:
  - name: db
    engine: PG
    version: "15"
```

### Option C: VPS Deployment

#### 1. Setup Server

```bash
# SSH into server
ssh user@your-server.com

# Install dependencies
sudo apt update
sudo apt install python3.10 python3-pip postgresql nginx

# Clone repository
git clone https://github.com/your-username/threads-automation.git
cd threads-automation

# Setup
./setup.sh
```

#### 2. Configure Systemd Service

Create `/etc/systemd/system/threads-automation.service`:

```ini
[Unit]
Description=Threads Automation Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/threads-automation
Environment="PATH=/opt/threads-automation/venv/bin"
EnvironmentFile=/opt/threads-automation/.env
ExecStart=/opt/threads-automation/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable threads-automation
sudo systemctl start threads-automation
sudo systemctl status threads-automation
```

#### 3. Configure Nginx

Create `/etc/nginx/sites-available/threads-automation`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/threads-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Phase 4: Monitoring and Maintenance

### 1. Setup Logging

```python
# Add to app/config.py
SENTRY_DSN=your-sentry-dsn

# Add to app/main.py
import sentry_sdk
sentry_sdk.init(dsn=settings.sentry_dsn)
```

### 2. Setup Monitoring

```bash
# Install Prometheus exporter
pip install prometheus-fastapi-instrumentator

# Add to app/main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

### 3. Database Backups

```bash
# Automated PostgreSQL backups
0 2 * * * pg_dump threads_automation > /backups/threads_$(date +\%Y\%m\%d).sql
```

### 4. Log Rotation

```bash
# /etc/logrotate.d/threads-automation
/opt/threads-automation/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

## Phase 5: Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  app:
    image: threads-automation:latest
    deploy:
      replicas: 3
    environment:
      - SCHEDULER_ENABLED=false  # Only enable on one instance
    
  scheduler:
    image: threads-automation:latest
    environment:
      - SCHEDULER_ENABLED=true
    deploy:
      replicas: 1
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Caching Layer

```python
# Add Redis caching
pip install redis aioredis

# app/cache.py
import aioredis

redis = await aioredis.create_redis_pool('redis://localhost')

async def get_account_config(account_id: int):
    cached = await redis.get(f"account:{account_id}")
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    account = await db.get(Account, account_id)
    await redis.setex(f"account:{account_id}", 3600, json.dumps(account))
    return account
```

## Troubleshooting

### Common Issues

**Issue**: Posts not generating
- Check LLM connection: `python scripts/test_llm.py`
- Verify scheduler is running: Check logs
- Ensure content plans exist

**Issue**: Publishing fails
- Check publisher health: `/api/dashboard/health`
- Verify credentials are correct
- Check Threads API status

**Issue**: Database connection errors
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Ensure migrations are up to date

**Issue**: High memory usage
- Reduce scheduler frequency
- Implement caching
- Use connection pooling

## Security Checklist

- [ ] Change default admin password
- [ ] Use strong SECRET_KEY
- [ ] Enable HTTPS in production
- [ ] Encrypt sensitive data at rest
- [ ] Implement rate limiting
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Backup database regularly
- [ ] Use environment variables for secrets
- [ ] Implement API authentication

## Performance Optimization

1. **Database Indexes**: Already implemented on frequently queried fields
2. **Connection Pooling**: Configured in SQLAlchemy
3. **Async Operations**: Used throughout the application
4. **Caching**: Implement Redis for frequently accessed data
5. **CDN**: Use CDN for static assets if adding frontend
6. **Database Query Optimization**: Use `select_related` and `prefetch_related`

## Next Steps

1. ✅ Complete development setup
2. ⏳ Implement real Threads publisher
3. ⏳ Deploy to staging environment
4. ⏳ Test with real accounts
5. ⏳ Deploy to production
6. ⏳ Monitor and optimize
7. ⏳ Add additional features

## Additional Features to Consider

- **Analytics Dashboard**: Build a React/Vue frontend
- **Multi-account Management**: Support multiple Threads accounts
- **Content Calendar**: Visual calendar interface
- **A/B Testing**: Test different post variations
- **Engagement Tracking**: Track likes, comments, shares
- **Content Suggestions**: AI-powered topic suggestions
- **Image Generation**: Integrate DALL-E or Stable Diffusion
- **Webhook Support**: Notify external systems of events
- **API Rate Limiting**: Protect against abuse
- **User Management**: Multi-user support with permissions

Good luck with your implementation! 🚀
