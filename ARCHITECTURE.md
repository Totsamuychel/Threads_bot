# Architecture Documentation

## System Overview

The Threads Automation system is built with a clean, layered architecture that separates concerns and makes the codebase maintainable and extensible.

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Server                        │
│                     (app/main.py)                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  API Routes  │    │  Scheduler   │    │   Database   │
│ (app/api/)   │    │(app/scheduler)│    │(app/database)│
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │   Services   │    │    Models    │
            │(app/services)│    │(app/models)  │
            └──────────────┘    └──────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│   LLM    │ │Publisher │ │ Schemas  │
│(app/llm) │ │(app/pub) │ │(app/sch) │
└──────────┘ └──────────┘ └──────────┘
```

## Layer Descriptions

### 1. API Layer (`app/api/`)

**Purpose**: HTTP endpoints for external interaction

**Components**:
- `accounts.py`: Account CRUD operations
- `content.py`: Content planning and post management
- `dashboard.py`: Analytics and monitoring

**Responsibilities**:
- Request validation (Pydantic schemas)
- Response formatting
- Error handling
- Authentication (future)

**Example**:
```python
@router.post("/api/content/generate/{plan_id}")
async def generate_post(plan_id: int, db: AsyncSession = Depends(get_db)):
    generator = PostGenerator(db)
    post = await generator.generate_post_for_plan(plan_id)
    return post
```

### 2. Service Layer (`app/services/`)

**Purpose**: Business logic and orchestration

**Components**:
- `content_planner.py`: Content planning logic
- `post_generator.py`: LLM-based post generation
- `post_publisher.py`: Publishing orchestration

**Responsibilities**:
- Coordinate between different components
- Implement business rules
- Handle complex workflows
- Transaction management

**Design Pattern**: Service pattern with dependency injection

**Example**:
```python
class PostGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()
    
    async def generate_post_for_plan(self, plan_id: int) -> Post:
        # 1. Get plan and account
        # 2. Build prompts
        # 3. Call LLM
        # 4. Parse response
        # 5. Create post record
        # 6. Update plan status
```

### 3. LLM Abstraction Layer (`app/llm/`)

**Purpose**: Unified interface for different LLM providers

**Components**:
- `base.py`: Abstract base class
- `ollama.py`: Ollama implementation
- `openai_compatible.py`: OpenAI-compatible API implementation

**Design Pattern**: Strategy pattern + Factory pattern

**Key Features**:
- Provider-agnostic interface
- Consistent error handling
- Response normalization
- Health checking

**Adding a New Provider**:
```python
class AnthropicClient(BaseLLMClient):
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        # Implementation
        pass
    
    async def health_check(self) -> bool:
        # Implementation
        pass
```

### 4. Publisher Abstraction Layer (`app/publishers/`)

**Purpose**: Unified interface for different publishing methods

**Components**:
- `base.py`: Abstract base class
- `mock.py`: Mock publisher for development
- `threads_api.py`: Placeholder for real API

**Design Pattern**: Strategy pattern + Factory pattern

**Key Features**:
- Publishing method agnostic
- Consistent result format
- Error handling
- Account info retrieval

**Implementing Real Publisher**:
```python
class ThreadsAPIPublisher(BasePublisher):
    async def publish(self, account_id: int, text: str, 
                     hashtags: list = None, media_urls: list = None) -> PublishResult:
        # 1. Get account credentials
        # 2. Format post
        # 3. Call Threads API
        # 4. Return result
```

### 5. Scheduler Layer (`app/scheduler/`)

**Purpose**: Automated task execution

**Components**:
- `__init__.py`: Scheduler initialization
- `tasks.py`: Scheduled task implementations

**Technology**: APScheduler (AsyncIOScheduler)

**Scheduled Tasks**:
1. **Content Plan Generation** (Daily 1 AM)
   - Generate plans for all active accounts
   - Ensures content pipeline is full

2. **Post Generation** (Hourly)
   - Generate content for upcoming posts
   - Runs N hours before scheduled time

3. **Post Publishing** (Every minute)
   - Publish posts at scheduled time
   - Updates status and logs results

4. **Retry Failed Posts** (Every 5 minutes)
   - Retry with exponential backoff
   - Respects max retry limit

5. **Cleanup Old Logs** (Daily 3 AM)
   - Remove logs older than 90 days
   - Keeps database size manageable

### 6. Database Layer (`app/database.py`, `app/models/`)

**Purpose**: Data persistence and ORM

**Technology**: SQLAlchemy (async) + Alembic

**Models**:
- `Account`: Account configuration
- `ContentPlan`: Planned posts
- `Post`: Generated and published posts
- `ActivityLog`: System activity logs

**Key Features**:
- Async operations
- Relationship management
- Migration support
- Connection pooling

**Database Support**:
- SQLite (development)
- PostgreSQL (production)
- Easy to add others (MySQL, etc.)

### 7. Configuration Layer (`app/config.py`)

**Purpose**: Centralized configuration management

**Technology**: Pydantic Settings

**Features**:
- Environment variable loading
- Type validation
- Default values
- Computed properties

**Example**:
```python
class Settings(BaseSettings):
    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    
    class Config:
        env_file = ".env"
```

## Data Flow

### Content Generation Flow

```
1. Scheduler triggers content plan generation
   ↓
2. ContentPlanner creates ContentPlan records
   ↓
3. Scheduler triggers post generation (N hours before)
   ↓
4. PostGenerator:
   - Fetches ContentPlan and Account
   - Builds prompts from configuration
   - Calls LLM via abstraction layer
   - Parses response
   - Creates Post record
   ↓
5. Scheduler triggers publishing (at scheduled time)
   ↓
6. PostPublisher:
   - Fetches Post
   - Calls Publisher via abstraction layer
   - Updates Post status
   - Logs activity
```

### API Request Flow

```
1. HTTP Request → FastAPI
   ↓
2. Route Handler (app/api/)
   - Validates request (Pydantic)
   - Gets database session
   ↓
3. Service Layer (app/services/)
   - Implements business logic
   - Coordinates operations
   ↓
4. External Services (LLM/Publisher)
   - Via abstraction layers
   ↓
5. Database Operations
   - SQLAlchemy ORM
   ↓
6. Response
   - Formatted via Pydantic schemas
   - Returned to client
```

## Design Patterns Used

### 1. Dependency Injection
- Database sessions injected via FastAPI Depends
- Services receive dependencies in constructor
- Easy testing with mocks

### 2. Factory Pattern
- `get_llm_client()`: Creates appropriate LLM client
- `get_publisher()`: Creates appropriate publisher
- Configuration-driven instantiation

### 3. Strategy Pattern
- LLM clients implement common interface
- Publishers implement common interface
- Swappable implementations

### 4. Repository Pattern (implicit)
- Services encapsulate data access
- Business logic separated from persistence

### 5. Service Layer Pattern
- Business logic in dedicated service classes
- Orchestration of multiple operations
- Transaction management

## Extension Points

### Adding a New LLM Provider

1. Create `app/llm/your_provider.py`
2. Inherit from `BaseLLMClient`
3. Implement `generate()` and `health_check()`
4. Register in `app/llm/__init__.py`

### Adding a New Publisher

1. Create `app/publishers/your_publisher.py`
2. Inherit from `BasePublisher`
3. Implement required methods
4. Register in `app/publishers/__init__.py`

### Adding a New Scheduled Task

1. Add function to `app/scheduler/tasks.py`
2. Register in `app/scheduler/__init__.py`
3. Configure trigger (cron, interval, etc.)

### Adding a New API Endpoint

1. Add route to appropriate file in `app/api/`
2. Create Pydantic schemas if needed
3. Use service layer for business logic
4. Document in OpenAPI (automatic)

## Security Considerations

### Current Implementation

- Environment variables for secrets
- No hardcoded credentials
- SQL injection prevention (SQLAlchemy)
- Input validation (Pydantic)

### Future Enhancements

- API authentication (JWT)
- Rate limiting
- Credential encryption at rest
- Audit logging
- RBAC (Role-Based Access Control)

## Performance Considerations

### Current Optimizations

- Async operations throughout
- Database connection pooling
- Efficient queries with indexes
- Batch operations where possible

### Scalability Options

1. **Horizontal Scaling**
   - Multiple app instances behind load balancer
   - Shared PostgreSQL database
   - Distributed scheduler (APScheduler with database jobstore)

2. **Caching**
   - Redis for frequently accessed data
   - LLM response caching
   - Account configuration caching

3. **Queue-Based Processing**
   - Replace scheduler with Celery + Redis
   - Better for high-volume scenarios
   - More complex deployment

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test component interactions
- Use test database
- Mock external APIs (LLM, Threads)

### End-to-End Tests
- Test complete workflows
- Use mock publisher
- Verify database state

## Deployment Architecture

### Development
```
Local Machine
├── SQLite database
├── Ollama (local LLM)
├── Mock publisher
└── Single process (uvicorn)
```

### Production
```
Cloud Platform (AWS/GCP/Azure)
├── Load Balancer
├── App Servers (multiple instances)
├── PostgreSQL (managed service)
├── LLM API (OpenAI/Anthropic)
├── Threads API
└── Monitoring (logs, metrics)
```

## Monitoring and Observability

### Current Implementation
- Structured logging
- Activity logs in database
- Health check endpoint
- Dashboard API

### Future Enhancements
- Prometheus metrics
- Grafana dashboards
- Error tracking (Sentry)
- Performance monitoring (APM)

## Conclusion

This architecture provides:
- **Modularity**: Easy to modify individual components
- **Testability**: Clear boundaries for testing
- **Extensibility**: Simple to add new features
- **Maintainability**: Clean separation of concerns
- **Scalability**: Can grow with your needs

The system is designed to be production-ready while remaining simple enough for a portfolio project.
