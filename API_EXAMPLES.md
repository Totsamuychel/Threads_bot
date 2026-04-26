# API Examples

Complete examples of API calls for common workflows.

## 🚀 Getting Started

### 1. Check System Health

```bash
curl http://localhost:8000/api/dashboard/health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "llm": "healthy",
    "publisher": "healthy"
  }
}
```

## 👤 Account Management

### Create an Account

```bash
curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tech_creator",
    "display_name": "Tech Content Creator",
    "timezone": "America/New_York",
    "schedule_type": "times",
    "schedule_config": {
      "times": ["09:00", "14:00", "18:00"]
    },
    "max_posts_per_day": 3,
    "topics": [
      "AI and machine learning",
      "coding tips and tricks",
      "developer productivity",
      "tech industry news"
    ],
    "tone": "casual, witty, educational",
    "target_audience": "developers and tech enthusiasts aged 25-40",
    "language": "en",
    "base_hashtags": ["#coding", "#tech", "#AI"],
    "auto_generate_hashtags": true,
    "max_hashtags": 5,
    "min_length": 150,
    "max_length": 400,
    "is_active": true
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "tech_creator",
  "display_name": "Tech Content Creator",
  "timezone": "America/New_York",
  "schedule_config": {
    "times": ["09:00", "14:00", "18:00"]
  },
  "topics": ["AI and machine learning", "coding tips and tricks", ...],
  "tone": "casual, witty, educational",
  ...
}
```

### List All Accounts

```bash
curl http://localhost:8000/api/accounts
```

### Get Account Details

```bash
curl http://localhost:8000/api/accounts/1
```

### Update Account

```bash
curl -X PUT http://localhost:8000/api/accounts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "professional, informative",
    "max_posts_per_day": 5
  }'
```

### Delete Account

```bash
curl -X DELETE http://localhost:8000/api/accounts/1
```

## 📝 Content Planning

### Generate Content Plan

```bash
# Generate plans for next 7 days
curl -X POST "http://localhost:8000/api/content/plan/1?days_ahead=7"
```

**Response:**
```json
{
  "success": true,
  "message": "Generated 21 content plans",
  "data": {
    "plans_created": 21
  }
}
```

### List Content Plans

```bash
# All plans
curl http://localhost:8000/api/content/plans

# Filter by account
curl "http://localhost:8000/api/content/plans?account_id=1"

# Filter by status
curl "http://localhost:8000/api/content/plans?status=planned"

# Pagination
curl "http://localhost:8000/api/content/plans?skip=0&limit=10"
```

**Response:**
```json
[
  {
    "id": 1,
    "account_id": 1,
    "topic": "AI and machine learning",
    "specific_idea": null,
    "scheduled_time": "2024-01-15T09:00:00",
    "status": "planned",
    "llm_model": "llama2",
    "llm_temperature": "0.7",
    "llm_max_tokens": 500,
    "created_at": "2024-01-14T10:00:00",
    "updated_at": "2024-01-14T10:00:00"
  },
  ...
]
```

## 🤖 Post Generation

### Generate Post for Plan

```bash
curl -X POST http://localhost:8000/api/content/generate/1
```

**Response:**
```json
{
  "id": 1,
  "account_id": 1,
  "content_plan_id": 1,
  "text": "Ever wondered how neural networks actually learn? 🧠\n\nIt's all about backpropagation - the algorithm that adjusts weights based on errors. Think of it like learning from mistakes, but at lightning speed!\n\nThe magic happens when gradients flow backward through layers, fine-tuning each connection.",
  "hashtags": ["#AI", "#MachineLearning", "#NeuralNetworks", "#coding", "#tech"],
  "media_urls": null,
  "scheduled_time": "2024-01-15T09:00:00",
  "published_at": null,
  "threads_post_id": null,
  "threads_post_url": null,
  "status": "generated",
  "retry_count": 0,
  "last_error": null,
  "llm_model_used": "llama2",
  "generation_time_seconds": 3,
  "created_at": "2024-01-14T10:05:00",
  "updated_at": "2024-01-14T10:05:00"
}
```

### Create Manual Post

```bash
curl -X POST http://localhost:8000/api/content/posts \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "text": "Just shipped a new feature! 🚀 Check it out!",
    "hashtags": ["#coding", "#tech", "#launch"],
    "scheduled_time": "2024-01-15T14:00:00"
  }'
```

### List Posts

```bash
# All posts
curl http://localhost:8000/api/content/posts

# Filter by account
curl "http://localhost:8000/api/content/posts?account_id=1"

# Filter by status
curl "http://localhost:8000/api/content/posts?status=generated"

# Pagination
curl "http://localhost:8000/api/content/posts?skip=0&limit=20"
```

### Get Post Details

```bash
curl http://localhost:8000/api/content/posts/1
```

### Delete Post

```bash
curl -X DELETE http://localhost:8000/api/content/posts/1
```

## 📤 Publishing

### Publish Post Immediately

```bash
curl -X POST http://localhost:8000/api/content/publish/1
```

**Response:**
```json
{
  "success": true,
  "message": "Post 1 published successfully",
  "data": null
}
```

### Retry Failed Post

```bash
curl -X POST http://localhost:8000/api/content/retry/1
```

## 📊 Dashboard & Analytics

### Get Statistics

```bash
# Last 7 days
curl http://localhost:8000/api/dashboard/stats

# Last 30 days
curl "http://localhost:8000/api/dashboard/stats?days=30"

# Specific account
curl "http://localhost:8000/api/dashboard/stats?account_id=1&days=7"
```

**Response:**
```json
{
  "period_days": 7,
  "posts": {
    "total": 21,
    "posted": 18,
    "failed": 2,
    "pending": 1,
    "success_rate": 85.71
  },
  "plans": {
    "total": 21,
    "planned": 3,
    "generated": 18
  }
}
```

### Get Upcoming Posts

```bash
# Next 24 hours
curl http://localhost:8000/api/dashboard/upcoming

# Next 48 hours
curl "http://localhost:8000/api/dashboard/upcoming?hours=48"

# Specific account
curl "http://localhost:8000/api/dashboard/upcoming?account_id=1&hours=24"
```

**Response:**
```json
{
  "count": 3,
  "posts": [
    {
      "id": 5,
      "account_id": 1,
      "text": "Quick tip: Use list comprehensions...",
      "scheduled_time": "2024-01-15T09:00:00",
      "status": "generated"
    },
    {
      "id": 6,
      "account_id": 1,
      "text": "The future of AI is...",
      "scheduled_time": "2024-01-15T14:00:00",
      "status": "generated"
    },
    {
      "id": 7,
      "account_id": 1,
      "text": "Developer productivity hack...",
      "scheduled_time": "2024-01-15T18:00:00",
      "status": "generated"
    }
  ]
}
```

### Get Recent Activity

```bash
# Last 50 events
curl http://localhost:8000/api/dashboard/recent

# Last 100 events
curl "http://localhost:8000/api/dashboard/recent?limit=100"

# Specific account
curl "http://localhost:8000/api/dashboard/recent?account_id=1&limit=50"
```

**Response:**
```json
{
  "count": 50,
  "logs": [
    {
      "id": 123,
      "event_type": "post_published",
      "event_category": "publisher",
      "message": "Successfully published post 5",
      "created_at": "2024-01-15T09:00:15",
      "error_details": null
    },
    {
      "id": 122,
      "event_type": "post_generated",
      "event_category": "llm",
      "message": "Generated post for plan 5",
      "created_at": "2024-01-15T07:00:05",
      "error_details": null
    },
    ...
  ]
}
```

## 🔄 Complete Workflow Examples

### Workflow 1: Automated Content Pipeline

```bash
# 1. Create account
ACCOUNT_ID=$(curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{...}' | jq -r '.id')

# 2. Generate content plans
curl -X POST "http://localhost:8000/api/content/plan/${ACCOUNT_ID}?days_ahead=7"

# 3. Check upcoming posts
curl "http://localhost:8000/api/dashboard/upcoming?account_id=${ACCOUNT_ID}"

# 4. Let scheduler handle the rest automatically!
```

### Workflow 2: Manual Content Creation

```bash
# 1. Create account
ACCOUNT_ID=1

# 2. Create manual post
POST_ID=$(curl -X POST http://localhost:8000/api/content/posts \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": '${ACCOUNT_ID}',
    "text": "Custom post content here",
    "hashtags": ["#custom", "#manual"],
    "scheduled_time": "2024-01-15T15:00:00"
  }' | jq -r '.id')

# 3. Review post
curl http://localhost:8000/api/content/posts/${POST_ID}

# 4. Publish immediately (or wait for scheduled time)
curl -X POST http://localhost:8000/api/content/publish/${POST_ID}
```

### Workflow 3: Content Review & Edit

```bash
# 1. Get upcoming posts
curl http://localhost:8000/api/dashboard/upcoming

# 2. Review specific post
curl http://localhost:8000/api/content/posts/5

# 3. If you want to edit, delete and recreate
curl -X DELETE http://localhost:8000/api/content/posts/5

curl -X POST http://localhost:8000/api/content/posts \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "text": "Edited content here",
    "hashtags": ["#edited"],
    "scheduled_time": "2024-01-15T09:00:00"
  }'
```

### Workflow 4: Monitoring & Troubleshooting

```bash
# 1. Check system health
curl http://localhost:8000/api/dashboard/health

# 2. Get statistics
curl "http://localhost:8000/api/dashboard/stats?days=7"

# 3. Check recent activity
curl "http://localhost:8000/api/dashboard/recent?limit=20"

# 4. Find failed posts
curl "http://localhost:8000/api/content/posts?status=failed"

# 5. Retry failed post
curl -X POST http://localhost:8000/api/content/retry/3
```

## 🐍 Python Examples

### Using requests library

```python
import requests

BASE_URL = "http://localhost:8000"

# Create account
account_data = {
    "username": "python_creator",
    "topics": ["Python", "Data Science", "AI"],
    "tone": "educational, friendly",
    # ... other fields
}

response = requests.post(f"{BASE_URL}/api/accounts", json=account_data)
account = response.json()
account_id = account["id"]

# Generate content plan
response = requests.post(
    f"{BASE_URL}/api/content/plan/{account_id}",
    params={"days_ahead": 7}
)
print(response.json())

# Get upcoming posts
response = requests.get(
    f"{BASE_URL}/api/dashboard/upcoming",
    params={"account_id": account_id, "hours": 24}
)
upcoming = response.json()

for post in upcoming["posts"]:
    print(f"Post {post['id']}: {post['text'][:50]}...")
```

### Using httpx (async)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Get statistics
        response = await client.get(
            "http://localhost:8000/api/dashboard/stats",
            params={"days": 30}
        )
        stats = response.json()
        print(f"Success rate: {stats['posts']['success_rate']}%")
        
        # Get recent activity
        response = await client.get(
            "http://localhost:8000/api/dashboard/recent",
            params={"limit": 10}
        )
        logs = response.json()
        
        for log in logs["logs"]:
            print(f"{log['created_at']}: {log['message']}")

asyncio.run(main())
```

## 🧪 Testing Examples

### Test LLM Integration

```bash
# Health check
curl http://localhost:8000/api/dashboard/health | jq '.components.llm'

# Generate a test post
curl -X POST http://localhost:8000/api/content/generate/1 | jq '.text'
```

### Test Publisher Integration

```bash
# Health check
curl http://localhost:8000/api/dashboard/health | jq '.components.publisher'

# Test publish (with mock)
curl -X POST http://localhost:8000/api/content/publish/1

# Check logs for mock output
tail -f logs/app.log | grep "MOCK PUBLISH"
```

### Load Testing

```bash
# Create multiple accounts
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/accounts \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"test_user_$i\", ...}"
done

# Generate plans for all
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/content/plan/$i?days_ahead=7"
done

# Check system stats
curl http://localhost:8000/api/dashboard/stats
```

## 📱 Frontend Integration Examples

### React/Vue/Angular

```javascript
// API client
const API_BASE = 'http://localhost:8000';

async function getUpcomingPosts(accountId) {
  const response = await fetch(
    `${API_BASE}/api/dashboard/upcoming?account_id=${accountId}&hours=24`
  );
  return await response.json();
}

async function publishPost(postId) {
  const response = await fetch(
    `${API_BASE}/api/content/publish/${postId}`,
    { method: 'POST' }
  );
  return await response.json();
}

// Usage
const upcoming = await getUpcomingPosts(1);
console.log(`${upcoming.count} posts scheduled`);

await publishPost(5);
console.log('Post published!');
```

## 🔐 Authentication (Future)

When authentication is implemented:

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' \
  | jq -r '.access_token')

# Use token in requests
curl http://localhost:8000/api/accounts \
  -H "Authorization: Bearer ${TOKEN}"
```

## 📝 Notes

- All timestamps are in UTC
- Pagination defaults: skip=0, limit=100
- Rate limiting: Not implemented yet
- Authentication: Not implemented yet (all endpoints public)
- CORS: Configured for localhost:3000 and localhost:8000

## 🎯 Best Practices

1. **Always check health before operations**
2. **Use pagination for large datasets**
3. **Monitor recent activity for errors**
4. **Review generated content before publishing**
5. **Set up proper error handling in your client**
6. **Use environment-specific base URLs**
7. **Implement retry logic for failed requests**

Happy coding! 🚀
