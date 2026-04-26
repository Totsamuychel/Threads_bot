# Automated Threads Content Manager

A production-ready system for automated Threads account management using LLM-powered content generation.

## Architecture Overview

**Tech Stack:**
- **Backend:** FastAPI (async, modern, API-first)
- **Scheduler:** APScheduler (lightweight, no broker needed)
- **Database:** PostgreSQL (production) / SQLite (development)
- **LLM Integration:** Pluggable abstraction (Ollama, OpenAI-compatible APIs)
- **Publisher:** Abstraction layer (mock, official API, or browser automation)

**Why FastAPI + APScheduler?**
- Modern async Python with excellent performance
- No need for separate message broker (Celery requires Redis/RabbitMQ)
- Built-in OpenAPI documentation
- Simpler deployment and maintenance
- Perfect scale for automated posting system

## Project Structure

```
threads-automation/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings and environment variables
│   ├── database.py             # Database connection and session
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── account.py          # Account configuration
│   │   ├── content.py          # Content plans and posts
│   │   └── log.py              # Activity logs
│   ├── schemas/                # Pydantic schemas for API
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── content.py
│   │   └── response.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── content_planner.py  # Generate content plans
│   │   ├── post_generator.py   # LLM-based post generation
│   │   └── post_publisher.py   # Publishing orchestration
│   ├── llm/                    # LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract LLM client
│   │   ├── ollama.py           # Ollama implementation
│   │   └── openai_compatible.py # OpenAI-compatible API
│   ├── publishers/             # Threads publishing layer
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract publisher
│   │   ├── mock.py             # Mock publisher for dev
│   │   └── threads_api.py      # Placeholder for real API
│   ├── scheduler/              # Scheduling logic
│   │   ├── __init__.py
│   │   └── tasks.py            # Scheduled tasks
│   └── api/                    # API routes
│       ├── __init__.py
│       ├── accounts.py
│       ├── content.py
│       └── dashboard.py
├── tests/
│   ├── __init__.py
│   ├── test_llm.py
│   ├── test_scheduler.py
│   └── test_publisher.py
├── alembic/                    # Database migrations
├── static/                     # Static files for UI
├── templates/                  # HTML templates
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Features

### 1. Account & Configuration Management
- Store Threads account credentials securely
- Configure posting schedule (times per day, CRON-like rules)
- Define content pillars and topics
- Set tone of voice and target audience
- Manage hashtag rules and language preferences

### 2. Content Planning
- Auto-generate content plans for upcoming days/weeks
- Manual content idea creation
- Track post status: planned → generated → scheduled → posted → failed
- Store LLM parameters per post

### 3. LLM-Powered Post Generation
- Pluggable LLM backend (Ollama, OpenAI, custom endpoints)
- Consistent tone and style enforcement
- Platform-optimized content (short, mobile-friendly)
- Auto-generate hashtags
- Store generation metadata for analytics

### 4. Automated Scheduling
- Periodic checks for upcoming posts
- Automatic content generation before posting time
- Retry logic with exponential backoff
- Duplicate prevention
- Status tracking and error handling

### 5. Threads Publishing
- Abstract publisher interface
- Mock publisher for development
- Placeholder for official Threads API
- Support for browser automation alternative
- Isolated from business logic

### 6. Monitoring & Logging
- Comprehensive event logging
- Admin dashboard for post history
- Failed post re-queuing
- Analytics and reporting

### 7. Admin Interface
- Web-based configuration UI
- Post preview and editing
- Manual generation/posting triggers
- Dashboard with metrics

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repo-url>
cd threads-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# - Database URL
# - LLM backend (Ollama or OpenAI-compatible)
# - Threads credentials (when ready)
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head
```

### 4. Run the Application

```bash
# Start the server (includes scheduler)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the application:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin UI: http://localhost:8000/admin

## Configuration Guide

### Setting Up Your First Account

1. Navigate to http://localhost:8000/admin
2. Create a new account configuration:
   - **Username:** Your Threads username
   - **Timezone:** Your preferred timezone (e.g., "America/New_York")
   - **Schedule:** Define posting times (e.g., "09:00,14:00,18:00" for 3 posts/day)
   - **Max Posts Per Day:** Safety limit

3. Configure content settings:
   - **Topics:** Add content pillars (e.g., "AI & coding tips", "productivity hacks")
   - **Tone:** Describe your voice (e.g., "casual, witty, educational")
   - **Target Audience:** Who you're writing for
   - **Language:** Content language
   - **Hashtags:** Base hashtags to include

### LLM Backend Configuration

The system supports multiple LLM backends through a unified interface.

#### Option 1: Ollama (Local)

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

#### Option 2: OpenAI-Compatible API

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

#### Option 3: Custom Endpoint

```env
LLM_PROVIDER=custom
LLM_BASE_URL=http://your-llm-server:8080
LLM_API_KEY=optional-key
LLM_MODEL=your-model
```

### Threads Publisher Configuration

#### Development (Mock Publisher)

```env
THREADS_PUBLISHER=mock
```

Posts will be logged to console and database but not actually published.

#### Production (Official API)

When Threads API is available:

```env
THREADS_PUBLISHER=api
THREADS_API_KEY=your-api-key
THREADS_API_URL=https://api.threads.net/v1
```

Implement the actual API calls in `app/publishers/threads_api.py`.

#### Alternative (Browser Automation)

If official API is not available, you can implement browser automation:

```env
THREADS_PUBLISHER=browser
THREADS_USERNAME=your-username
THREADS_PASSWORD=your-password
```

Implement Playwright/Selenium logic in `app/publishers/browser_automation.py`.

## How It Works

### Content Generation Flow

1. **Planning Phase:**
   - Scheduler checks if content plan exists for upcoming days
   - If not, `ContentPlanner` generates ideas based on topics and frequency
   - Creates `ContentPlan` records with status "planned"

2. **Generation Phase:**
   - 1-2 hours before scheduled time, scheduler triggers generation
   - `PostGenerator` builds prompt from account config and topic
   - LLM generates post text and hashtags
   - Stores result with status "generated"

3. **Publishing Phase:**
   - At scheduled time, scheduler triggers publishing
   - `PostPublisher` sends to Threads via publisher abstraction
   - Updates status to "posted" or "failed"
   - Logs all activity

4. **Error Handling:**
   - Failed posts are retried with exponential backoff
   - Errors are logged with full context
   - Admin can manually retry from dashboard

### LLM Prompt Design

The system uses carefully crafted prompts to ensure consistent, high-quality content:

**System Prompt Template:**
```
You are a social media content creator for Threads.

Target Audience: {target_audience}
Tone of Voice: {tone}
Language: {language}

Guidelines:
- Keep posts short and engaging (1-3 paragraphs max)
- Mobile-friendly formatting
- Include relevant hashtags
- Be authentic and conversational
- Focus on value for the audience

Topic: {topic}
```

**User Prompt Template:**
```
Create a Threads post about: {specific_topic}

Requirements:
- Length: 150-300 characters
- Include 3-5 relevant hashtags
- Match the tone: {tone}
- Target audience: {target_audience}

Return JSON format:
{
  "text": "post content here",
  "hashtags": ["tag1", "tag2", "tag3"]
}
```

## Extending the System

### Adding a New LLM Provider

1. Create a new file in `app/llm/` (e.g., `anthropic.py`)
2. Inherit from `BaseLLMClient`
3. Implement `generate()` method
4. Register in `app/llm/__init__.py`

```python
from app.llm.base import BaseLLMClient, LLMResponse

class AnthropicClient(BaseLLMClient):
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        # Your implementation
        pass
```

### Implementing Real Threads Publisher

#### Option A: Official API

Edit `app/publishers/threads_api.py`:

```python
async def publish(self, account_id: int, text: str, media_urls: list = None) -> PublishResult:
    # Get account credentials
    account = await self._get_account(account_id)
    
    # Call Threads API
    response = await self.client.post(
        f"{self.api_url}/posts",
        headers={"Authorization": f"Bearer {account.api_token}"},
        json={"text": text, "media": media_urls}
    )
    
    if response.status_code == 200:
        data = response.json()
        return PublishResult(
            success=True,
            post_id=data["id"],
            published_at=datetime.utcnow()
        )
    else:
        return PublishResult(
            success=False,
            error=response.text
        )
```

#### Option B: Browser Automation

Create `app/publishers/browser_automation.py`:

```python
from playwright.async_api import async_playwright

class BrowserPublisher(BasePublisher):
    async def publish(self, account_id: int, text: str, media_urls: list = None) -> PublishResult:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to Threads
            await page.goto("https://threads.net")
            
            # Login (if needed)
            # Fill post text
            # Click publish
            # Extract post ID
            
            await browser.close()
            
            return PublishResult(success=True, post_id="...")
```

## API Endpoints

### Accounts
- `POST /api/accounts` - Create account configuration
- `GET /api/accounts` - List all accounts
- `GET /api/accounts/{id}` - Get account details
- `PUT /api/accounts/{id}` - Update account
- `DELETE /api/accounts/{id}` - Delete account

### Content
- `POST /api/content/plan` - Generate content plan
- `GET /api/content/plans` - List content plans
- `POST /api/content/generate/{plan_id}` - Generate post for plan
- `POST /api/content/publish/{plan_id}` - Publish post
- `GET /api/content/posts` - List all posts
- `POST /api/content/retry/{post_id}` - Retry failed post

### Dashboard
- `GET /api/dashboard/stats` - Get posting statistics
- `GET /api/dashboard/upcoming` - Get upcoming posts
- `GET /api/dashboard/recent` - Get recent activity

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_llm.py -v
```

## Production Deployment

### Using Docker

```bash
# Build image
docker build -t threads-automation .

# Run container
docker run -d \
  --name threads-bot \
  -p 8000:8000 \
  --env-file .env \
  threads-automation
```

### Using systemd

Create `/etc/systemd/system/threads-automation.service`:

```ini
[Unit]
Description=Threads Automation Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/threads-automation
Environment="PATH=/opt/threads-automation/venv/bin"
ExecStart=/opt/threads-automation/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Considerations

- Never commit `.env` file
- Use strong database passwords
- Rotate API keys regularly
- Use HTTPS in production
- Implement rate limiting
- Validate all user inputs
- Use prepared statements (SQLAlchemy handles this)

## Troubleshooting

### Scheduler Not Running
- Check logs for errors
- Verify APScheduler is initialized in `main.py`
- Ensure database is accessible

### LLM Generation Fails
- Verify LLM endpoint is reachable
- Check API key is valid
- Review prompt length (may exceed model limits)
- Check LLM server logs

### Posts Not Publishing
- Verify publisher configuration
- Check Threads credentials
- Review publisher logs
- Test with mock publisher first

## Contributing

This is a portfolio project, but suggestions are welcome!

## License

MIT License - feel free to use for your own projects.
