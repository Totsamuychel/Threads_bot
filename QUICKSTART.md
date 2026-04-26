# Quick Start Guide

Get your Threads automation system running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- (Optional) Ollama installed for local LLM
- (Optional) PostgreSQL for production database

## Installation

### 1. Clone and Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# For quick start, the defaults work fine (SQLite + mock publisher)
```

### 3. Initialize Database

```bash
# Run database migrations
alembic upgrade head
```

### 4. Start the Server

```bash
# Start the application
uvicorn app.main:app --reload
```

The server will start at http://localhost:8000

## First Steps

### 1. Create Your First Account

```bash
curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "username": "my_threads_account",
    "display_name": "My Awesome Account",
    "timezone": "America/New_York",
    "schedule_config": {
      "times": ["09:00", "14:00", "18:00"]
    },
    "max_posts_per_day": 3,
    "topics": [
      "AI and machine learning",
      "coding tips",
      "tech industry insights"
    ],
    "tone": "casual, witty, educational",
    "target_audience": "developers and tech enthusiasts",
    "language": "en",
    "base_hashtags": ["#coding", "#tech", "#AI"],
    "auto_generate_hashtags": true,
    "max_hashtags": 5,
    "min_length": 150,
    "max_length": 400
  }'
```

### 2. Generate Content Plan

```bash
# Generate plans for the next 7 days
curl -X POST "http://localhost:8000/api/content/plan/1?days_ahead=7"
```

### 3. View Upcoming Posts

```bash
# See what's planned
curl http://localhost:8000/api/dashboard/upcoming
```

### 4. Manually Generate a Post

```bash
# Generate content for a specific plan
curl -X POST http://localhost:8000/api/content/generate/1
```

### 5. View Generated Post

```bash
# Get post details
curl http://localhost:8000/api/content/posts/1
```

### 6. Publish Immediately (Optional)

```bash
# Publish a post right away (instead of waiting for scheduled time)
curl -X POST http://localhost:8000/api/content/publish/1
```

## Using the Web Interface

1. Open your browser to http://localhost:8000
2. Click on "API Documentation" to explore all endpoints
3. Use the interactive Swagger UI to test API calls

## Monitoring

### Check System Health

```bash
curl http://localhost:8000/api/dashboard/health
```

### View Statistics

```bash
curl http://localhost:8000/api/dashboard/stats
```

### View Recent Activity

```bash
curl http://localhost:8000/api/dashboard/recent
```

## Automated Operation

The scheduler runs automatically when the server starts. It will:

1. **Daily at 1 AM**: Generate content plans for upcoming days
2. **Every hour**: Generate posts for plans scheduled in the next 2 hours
3. **Every minute**: Publish posts at their scheduled time
4. **Every 5 minutes**: Retry failed posts

You don't need to do anything - just keep the server running!

## Using with Ollama (Local LLM)

### 1. Install Ollama

```bash
# Visit https://ollama.ai and follow installation instructions
# Or use:
curl https://ollama.ai/install.sh | sh
```

### 2. Pull a Model

```bash
ollama pull llama2
# or
ollama pull mistral
```

### 3. Update .env

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2
```

### 4. Restart Server

The system will now use your local LLM!

## Using with OpenAI

### 1. Get API Key

Sign up at https://platform.openai.com and get your API key

### 2. Update .env

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-3.5-turbo
```

### 3. Restart Server

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services (app + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

The app will be available at http://localhost:8000

## Troubleshooting

### Server won't start

- Check if port 8000 is already in use
- Verify Python version: `python --version` (should be 3.10+)
- Check logs in `logs/app.log`

### LLM generation fails

- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check LLM_BASE_URL in .env
- Try a different model

### Posts not publishing

- Check if scheduler is enabled: `SCHEDULER_ENABLED=True` in .env
- Verify posts have scheduled_time in the past
- Check publisher type: `THREADS_PUBLISHER=mock` for testing

### Database errors

- Delete `threads_automation.db` and run `alembic upgrade head` again
- Check DATABASE_URL in .env

## Next Steps

1. **Customize prompts**: Edit prompt templates in `app/services/post_generator.py`
2. **Add more accounts**: Create multiple accounts with different configurations
3. **Implement real publisher**: Follow instructions in `app/publishers/threads_api.py`
4. **Set up monitoring**: Use the dashboard endpoints to build a monitoring UI
5. **Deploy to production**: Use Docker or deploy to a cloud platform

## Example Workflows

### Daily Content Creator

```bash
# Morning: Check what's scheduled for today
curl "http://localhost:8000/api/dashboard/upcoming?hours=24"

# Review generated posts
curl "http://localhost:8000/api/content/posts?status=generated"

# Edit a post if needed (via API or database)

# Let the scheduler handle publishing automatically
```

### Manual Content Creation

```bash
# Create a post manually
curl -X POST http://localhost:8000/api/content/posts \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "text": "Just shipped a new feature! 🚀",
    "hashtags": ["#coding", "#tech"],
    "scheduled_time": "2024-01-15T14:00:00Z"
  }'

# Publish immediately
curl -X POST http://localhost:8000/api/content/publish/1
```

## Support

- Check the main README.md for detailed documentation
- Review PROMPTS.md for prompt customization
- Examine the code in `app/` for implementation details
- Open an issue on GitHub for bugs or questions

Happy automating! 🧵✨
