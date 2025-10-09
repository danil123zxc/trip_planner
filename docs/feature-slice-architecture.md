# Feature Slice Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Trip Planner System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   API Gateway   │    │ Trip Planning   │    │ Config Mgmt  │ │
│  │                 │    │     Core        │    │              │ │
│  │ • REST API      │◄──►│                 │◄──►│              │ │
│  │ • Auth/Validation│   │ • Workflow      │    │ • API Keys   │ │
│  │ • Error Handling│    │ • State Mgmt    │    │ • Env Vars   │ │
│  └─────────────────┘    │ • Orchestration│    │ • Settings  │ │
│           │              └─────────────────┘    └──────────────┘ │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ Research Agents │    │ Knowledge       │                     │
│  │                 │    │ Retrieval       │                     │
│  │ • Lodging       │◄──►│                 │                     │
│  │ • Activities    │    │ • RAG Pipeline  │                     │
│  │ • Food          │    │ • Vector Store  │                     │
│  │ • Transport     │    │ • Search        │                     │
│  │ • Safety        │    │ • Context       │                     │
│  └─────────────────┘    └─────────────────┘                     │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                External Data Sources                        │ │
│  │                                                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │ │
│  │  │   Amadeus   │ │ TripAdvisor │ │   Reddit    │ │ Internet│ │ │
│  │  │   Flights   │ │ Hotels/Act  │ │ Community   │ │ Search  │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Feature Slice Details

### 1. API Gateway Slice
```
┌─────────────────────────────────────┐
│           API Gateway               │
├─────────────────────────────────────┤
│ • FastAPI Application               │
│ • Request/Response Models           │
│ • Authentication & Authorization    │
│ • Error Handling & Logging          │
│ • Rate Limiting                     │
│ • Input Validation                  │
└─────────────────────────────────────┘
```

**Key Files:**
- `src/api/app.py`
- Request/Response models
- Middleware components

### 2. Trip Planning Core Slice
```
┌─────────────────────────────────────┐
│        Trip Planning Core           │
├─────────────────────────────────────┤
│ • LangGraph Workflow                │
│ • State Management                  │
│ • Human-in-the-Loop Handling        │
│ • Plan Synthesis                    │
│ • Workflow Orchestration            │
└─────────────────────────────────────┘
```

**Key Files:**
- `src/workflows/planner.py`
- `src/core/domain.py`
- `src/core/types.py`

### 3. Research Agents Slice
```
┌─────────────────────────────────────┐
│         Research Agents             │
├─────────────────────────────────────┤
│ • Lodging Agent                     │
│ • Activities Agent                  │
│ • Food Agent                        │
│ • Transport Agent                   │
│ • Safety Agent                      │
│ • Agent Orchestration               │
└─────────────────────────────────────┘
```

**Key Files:**
- Agent implementations in `src/workflows/planner.py`
- Agent output models in `src/core/domain.py`

### 4. Knowledge Retrieval Slice
```
┌─────────────────────────────────────┐
│       Knowledge Retrieval           │
├─────────────────────────────────────┤
│ • RAG Pipeline                      │
│ • Vector Store                      │
│ • Document Processing               │
│ • Semantic Search                    │
│ • Context Retrieval                 │
└─────────────────────────────────────┘
```

**Key Files:**
- `src/pipelines/rag.py`
- Vector store configuration
- Document processing utilities

### 5. External Data Slice
```
┌─────────────────────────────────────┐
│        External Data Sources        │
├─────────────────────────────────────┤
│ • Amadeus Flight API                │
│ • TripAdvisor API                   │
│ • Reddit API                        │
│ • Internet Search                   │
│ • Geocoding Services                │
└─────────────────────────────────────┘
```

**Key Files:**
- `src/services/amadeus/`
- `src/services/trip_advisor/`
- `src/services/geocoding/geocoding.py`
- `src/services/tavily_search/tools.py`
- `src/services/reddit/tools.py`

### 6. Configuration Management Slice
```
┌─────────────────────────────────────┐
│      Configuration Management       │
├─────────────────────────────────────┤
│ • API Key Management                │
│ • Environment Variables             │
│ • Service Configuration             │
│ • Feature Flags                     │
│ • Settings Validation               │
└─────────────────────────────────────┘
```

**Key Files:**
- `src/core/config.py`
- Environment variable handling
- Service credential management

## Data Flow Architecture

```
User Request
     │
     ▼
┌─────────────┐
│ API Gateway │
└─────┬───────┘
      │
      ▼
┌─────────────────┐
│ Trip Planning   │
│ Core Workflow   │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Research Agents │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Knowledge       │
│ Retrieval       │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ External Data   │
│ Sources         │
└─────────────────┘
```

## Deployment Architecture

### Current Monolithic Deployment
```
┌─────────────────────────────────────────────────┐
│              Single Application                 │
│                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ API Gateway │ │ Trip Core   │ │ Research    │ │
│  │ Slice       │ │ Slice       │ │ Agents      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ │
│                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ Knowledge   │ │ External    │ │ Config     │ │
│  │ Retrieval   │ │ Data        │ │ Management │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────┘
```

### Future Microservices Deployment
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ API Gateway │ │ Trip Core   │ │ Research    │
│ Service     │ │ Service     │ │ Agents      │
│             │ │             │ │ Service     │
└─────────────┘ └─────────────┘ └─────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Knowledge   │ │ External    │ │ Config      │
│ Retrieval   │ │ Data        │ │ Service     │
│ Service     │ │ Service     │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Interface Contracts

### API Gateway ↔ Trip Planning Core
```typescript
interface TripPlanningRequest {
  context: Context;
  threadId?: string;
}

interface TripPlanningResponse {
  threadId: string;
  status: 'complete' | 'interrupt' | 'needs_follow_up';
  finalPlan?: FinalPlan;
  nextResearchPlan?: ResearchPlan;
  messages: string[];
}
```

### Trip Planning Core ↔ Research Agents
```typescript
interface ResearchRequest {
  context: Context;
  researchPlan: ResearchPlan;
  budget: BudgetEstimate;
}

interface ResearchResponse {
  lodging?: LodgingAgentOutput;
  activities?: ActivitiesAgentOutput;
  food?: FoodAgentOutput;
  transport?: IntercityTransportAgentOutput;
  recommendations?: RecommendationsOutput;
}
```

### Research Agents ↔ Knowledge Retrieval
```typescript
interface KnowledgeQuery {
  query: string;
  context: string;
  filters?: Record<string, any>;
}

interface KnowledgeResponse {
  documents: Document[];
  relevance: number;
  sources: string[];
}
```

### Knowledge Retrieval ↔ External Data
```typescript
interface ExternalDataRequest {
  service: 'amadeus' | 'tripadvisor' | 'reddit' | 'internet';
  query: string;
  parameters: Record<string, any>;
}

interface ExternalDataResponse {
  data: any[];
  metadata: {
    source: string;
    timestamp: string;
    confidence: number;
  };
}
```

## Security Architecture

```
┌─────────────────────────────────────────────────┐
│                Security Layer                  │
├─────────────────────────────────────────────────┤
│ • Authentication (JWT/OAuth)                   │
│ • Authorization (RBAC)                          │
│ • API Key Management                           │
│ • Rate Limiting                                │
│ • Input Validation                             │
│ • Data Encryption                              │
│ • Audit Logging                                │
└─────────────────────────────────────────────────┘
```

## Monitoring and Observability

```
┌─────────────────────────────────────────────────┐
│            Observability Stack                  │
├─────────────────────────────────────────────────┤
│ • Metrics Collection (Prometheus)               │
│ • Log Aggregation (ELK Stack)                   │
│ • Distributed Tracing (Jaeger)                 │
│ • Health Checks                                 │
│ • Alerting (AlertManager)                       │
│ • Dashboards (Grafana)                          │
└─────────────────────────────────────────────────┘
```

This architecture provides a clear, scalable foundation for the Trip Planner project with well-defined feature slices, clear interfaces, and a path for future microservices migration.
