# Feature Slice Implementation Guide

## Overview

This guide provides practical steps for implementing the feature slice design in your Trip Planner project. It includes code organization, testing strategies, and migration paths.

## Directory Structure

```
src/
├── slices/
│   ├── api-gateway/
│   │   ├── __init__.py
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── trip_planning.py
│   │   │   ├── health.py
│   │   │   └── validation.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── rate_limiting.py
│   │   │   └── error_handling.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_handlers.py
│   │       └── test_middleware.py
│   │
│   ├── trip-planning-core/
│   │   ├── __init__.py
│   │   ├── workflow/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── state_manager.py
│   │   │   └── interrupt_handler.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── events.py
│   │   │   └── validators.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── plan_synthesizer.py
│   │   │   └── budget_estimator.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_workflow.py
│   │       └── test_domain.py
│   │
│   ├── research-agents/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── lodging_agent.py
│   │   │   ├── activities_agent.py
│   │   │   ├── food_agent.py
│   │   │   ├── transport_agent.py
│   │   │   └── safety_agent.py
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   ├── agent_coordinator.py
│   │   │   └── result_aggregator.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_agents.py
│   │
│   ├── knowledge-retrieval/
│   │   ├── __init__.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── rag_pipeline.py
│   │   │   ├── document_processor.py
│   │   │   └── vector_store.py
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── semantic_search.py
│   │   │   └── context_retriever.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_pipeline.py
│   │
│   ├── external-data/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── amadeus_service.py
│   │   │   ├── tripadvisor_service.py
│   │   │   ├── reddit_service.py
│   │   │   └── internet_service.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── flight_adapter.py
│   │   │   ├── hotel_adapter.py
│   │   │   └── activity_adapter.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_services.py
│   │
│   └── config-management/
│       ├── __init__.py
│       ├── settings/
│       │   ├── __init__.py
│       │   ├── api_settings.py
│       │   ├── database_settings.py
│       │   └── feature_flags.py
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── config_validator.py
│       │   └── environment_checker.py
│       └── tests/
│           ├── __init__.py
│           └── test_settings.py
│
├── shared/
│   ├── __init__.py
│   ├── exceptions/
│   │   ├── __init__.py
│   │   ├── base_exceptions.py
│   │   ├── validation_exceptions.py
│   │   └── external_service_exceptions.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── monitoring.py
│   │   └── serialization.py
│   └── interfaces/
│       ├── __init__.py
│       ├── trip_planning_interface.py
│       ├── research_interface.py
│       └── data_source_interface.py
│
└── tests/
    ├── __init__.py
    ├── integration/
    │   ├── __init__.py
    │   ├── test_workflow_integration.py
    │   └── test_api_integration.py
    └── e2e/
        ├── __init__.py
        └── test_trip_planning_e2e.py
```

## Implementation Steps

### Step 1: Create Slice Structure

1. **Create slice directories**:
```bash
mkdir -p src/slices/{api-gateway,trip-planning-core,research-agents,knowledge-retrieval,external-data,config-management}
```

2. **Set up shared utilities**:
```bash
mkdir -p src/shared/{exceptions,utils,interfaces}
```

### Step 2: Define Slice Interfaces

#### API Gateway Interface
```python
# src/shared/interfaces/trip_planning_interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.core.domain import Context, FinalPlan, ResearchPlan

class TripPlanningInterface(ABC):
    """Interface for trip planning operations."""
    
    @abstractmethod
    async def start_planning(self, context: Context, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a new trip planning workflow."""
        pass
    
    @abstractmethod
    async def resume_planning(self, thread_id: str, selections: Dict[str, Any]) -> Dict[str, Any]:
        """Resume planning after human review."""
        pass
    
    @abstractmethod
    async def get_plan_status(self, thread_id: str) -> Dict[str, Any]:
        """Get current status of a planning workflow."""
        pass
```

#### Research Interface
```python
# src/shared/interfaces/research_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.core.domain import Context, ResearchPlan, BudgetEstimate

class ResearchInterface(ABC):
    """Interface for research operations."""
    
    @abstractmethod
    async def research_lodging(self, context: Context, plan: ResearchPlan, budget: BudgetEstimate) -> Dict[str, Any]:
        """Research lodging options."""
        pass
    
    @abstractmethod
    async def research_activities(self, context: Context, plan: ResearchPlan, budget: BudgetEstimate) -> Dict[str, Any]:
        """Research activity options."""
        pass
    
    @abstractmethod
    async def research_food(self, context: Context, plan: ResearchPlan, budget: BudgetEstimate) -> Dict[str, Any]:
        """Research food options."""
        pass
    
    @abstractmethod
    async def research_transport(self, context: Context, plan: ResearchPlan, budget: BudgetEstimate) -> Dict[str, Any]:
        """Research transport options."""
        pass
```

### Step 3: Implement Slice Components

#### API Gateway Slice
```python
# src/slices/api-gateway/handlers/trip_planning.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from src.shared.interfaces.trip_planning_interface import TripPlanningInterface
from src.slices.api-gateway.models.requests import PlanRequest
from src.slices.api-gateway.models.responses import PlanResponse, InterruptResponse

class TripPlanningHandler:
    """Handler for trip planning API endpoints."""
    
    def __init__(self, trip_planning_service: TripPlanningInterface):
        self.trip_planning_service = trip_planning_service
    
    async def start_planning(self, request: PlanRequest) -> InterruptResponse:
        """Start trip planning workflow."""
        try:
            result = await self.trip_planning_service.start_planning(
                context=request.context,
                thread_id=request.thread_id
            )
            return InterruptResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def resume_planning(self, request: ResumeRequest) -> PlanResponse:
        """Resume planning after human review."""
        try:
            result = await self.trip_planning_service.resume_planning(
                thread_id=request.thread_id,
                selections=request.human_selections
            )
            return PlanResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
```

#### Trip Planning Core Slice
```python
# src/slices/trip-planning-core/workflow/orchestrator.py
from typing import Dict, Any, Optional
from src.core.domain import Context, State, FinalPlan
from src.shared.interfaces.research_interface import ResearchInterface

class TripPlanningOrchestrator:
    """Orchestrates the trip planning workflow."""
    
    def __init__(self, research_service: ResearchInterface):
        self.research_service = research_service
    
    async def execute_workflow(self, context: Context, state: State) -> Dict[str, Any]:
        """Execute the main trip planning workflow."""
        # Budget estimation
        budget = await self._estimate_budget(context)
        state.estimated_budget = budget
        
        # Research planning
        research_plan = await self._create_research_plan(context, budget)
        state.research_plan = research_plan
        
        # Execute research agents
        research_results = await self._execute_research(context, research_plan, budget)
        state.update(research_results)
        
        # Synthesize final plan
        final_plan = await self._synthesize_plan(context, state)
        state.final_plan = final_plan
        
        return state.model_dump()
    
    async def _estimate_budget(self, context: Context) -> BudgetEstimate:
        """Estimate budget for the trip."""
        # Implementation details...
        pass
    
    async def _create_research_plan(self, context: Context, budget: BudgetEstimate) -> ResearchPlan:
        """Create research plan based on context and budget."""
        # Implementation details...
        pass
    
    async def _execute_research(self, context: Context, plan: ResearchPlan, budget: BudgetEstimate) -> Dict[str, Any]:
        """Execute research agents in parallel."""
        # Implementation details...
        pass
    
    async def _synthesize_plan(self, context: Context, state: State) -> FinalPlan:
        """Synthesize final trip plan from research results."""
        # Implementation details...
        pass
```

### Step 4: Dependency Injection

#### Dependency Container
```python
# src/shared/container.py
from typing import Dict, Any, Type
from src.shared.interfaces.trip_planning_interface import TripPlanningInterface
from src.shared.interfaces.research_interface import ResearchInterface
from src.slices.trip-planning-core.workflow.orchestrator import TripPlanningOrchestrator
from src.slices.research-agents.orchestration.agent_coordinator import AgentCoordinator

class DependencyContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._setup_services()
    
    def _setup_services(self):
        """Set up service dependencies."""
        # Research interface implementation
        research_service = AgentCoordinator()
        self._services[ResearchInterface] = research_service
        
        # Trip planning interface implementation
        trip_planning_service = TripPlanningOrchestrator(research_service)
        self._services[TripPlanningInterface] = trip_planning_service
    
    def get(self, service_type: Type) -> Any:
        """Get service instance by type."""
        return self._services.get(service_type)
```

### Step 5: Testing Strategy

#### Unit Tests
```python
# src/slices/api-gateway/tests/test_handlers.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.slices.api-gateway.handlers.trip_planning import TripPlanningHandler
from src.slices.api-gateway.models.requests import PlanRequest

class TestTripPlanningHandler:
    """Test cases for trip planning handler."""
    
    @pytest.fixture
    def mock_trip_planning_service(self):
        """Mock trip planning service."""
        service = Mock()
        service.start_planning = AsyncMock(return_value={
            "thread_id": "test_thread",
            "status": "interrupt",
            "messages": ["Workflow started"]
        })
        return service
    
    @pytest.fixture
    def handler(self, mock_trip_planning_service):
        """Create handler with mocked service."""
        return TripPlanningHandler(mock_trip_planning_service)
    
    async def test_start_planning_success(self, handler):
        """Test successful planning start."""
        request = PlanRequest(
            context=Mock(),
            thread_id=None
        )
        
        result = await handler.start_planning(request)
        
        assert result.thread_id == "test_thread"
        assert result.status == "interrupt"
        assert len(result.messages) > 0
```

#### Integration Tests
```python
# src/tests/integration/test_workflow_integration.py
import pytest
from src.slices.trip-planning-core.workflow.orchestrator import TripPlanningOrchestrator
from src.slices.research-agents.orchestration.agent_coordinator import AgentCoordinator

class TestWorkflowIntegration:
    """Integration tests for workflow components."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with real dependencies."""
        research_service = AgentCoordinator()
        return TripPlanningOrchestrator(research_service)
    
    async def test_full_workflow_execution(self, orchestrator):
        """Test complete workflow execution."""
        context = Mock()  # Mock context
        state = Mock()    # Mock initial state
        
        result = await orchestrator.execute_workflow(context, state)
        
        assert "estimated_budget" in result
        assert "research_plan" in result
        assert "final_plan" in result
```

### Step 6: Configuration Management

#### Environment Configuration
```python
# src/slices/config-management/settings/api_settings.py
from pydantic import BaseSettings, Field
from typing import Optional

class ApiSettings(BaseSettings):
    """API configuration settings."""
    
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    tavily_api_key: Optional[str] = Field(None, env="TAVILY_API_KEY")
    reddit_client_id: Optional[str] = Field(None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(None, env="REDDIT_CLIENT_SECRET")
    trip_advisor_api_key: Optional[str] = Field(None, env="TRIP_ADVISOR_API")
    amadeus_api_key: Optional[str] = Field(None, env="AMADEUS_API")
    amadeus_api_secret: Optional[str] = Field(None, env="AMADEUS_SECRET")
    xai_api_key: Optional[str] = Field(None, env="XAI_API_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Step 7: Monitoring and Observability

#### Logging Configuration
```python
# src/shared/utils/logging.py
import logging
import structlog
from typing import Dict, Any

def setup_logging() -> None:
    """Set up structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger for a component."""
    return structlog.get_logger(name)
```

#### Health Checks
```python
# src/slices/api-gateway/handlers/health.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from src.shared.interfaces.trip_planning_interface import TripPlanningInterface

class HealthHandler:
    """Health check handler."""
    
    def __init__(self, trip_planning_service: TripPlanningInterface):
        self.trip_planning_service = trip_planning_service
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check service dependencies
            status = await self._check_dependencies()
            return {
                "status": "healthy",
                "service": "trip-planner-api",
                "dependencies": status
            }
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))
    
    async def _check_dependencies(self) -> Dict[str, str]:
        """Check external dependencies."""
        # Implementation details...
        return {"trip_planning": "healthy", "research_agents": "healthy"}
```

## Migration Strategy

### Phase 1: Extract Slices (Current)
1. Create slice directories
2. Move existing code to appropriate slices
3. Define slice interfaces
4. Implement dependency injection

### Phase 2: Decouple Slices
1. Remove direct dependencies between slices
2. Implement interface-based communication
3. Add comprehensive testing
4. Implement monitoring

### Phase 3: Microservices Preparation
1. Add service discovery
2. Implement message queues
3. Add distributed tracing
4. Prepare for containerization

## Best Practices

### Code Organization
- Keep slice interfaces stable
- Use dependency injection for testability
- Implement proper error handling
- Add comprehensive logging

### Testing
- Unit tests for each slice
- Integration tests for slice interactions
- End-to-end tests for complete workflows
- Contract tests for interfaces

### Documentation
- Document slice interfaces
- Maintain API documentation
- Create architecture decision records
- Provide migration guides

This implementation guide provides a practical roadmap for implementing the feature slice design in your Trip Planner project.
