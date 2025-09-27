# Agent Instructions for Trip Planner Implementation

## Understanding the Core Implementation
The repository centers on `trip_planner.ipynb`, which contains the complete discovery-to-output workflow. This notebook serves as the authoritative source for understanding how the trip planning system works. Always reference this notebook when implementing or modifying any part of the system.

## Key Implementation Areas to Study

### Workflow Structure & Graph Definition
Study the LangGraph implementation in the notebook to understand:
- How `StateGraph` is constructed with nodes and edges
- The parallel research phase execution pattern
- Human-in-the-loop interrupt and resume mechanisms
- State management through the `State` model

### Agent Implementations
Examine each agent's implementation in the notebook:
- **Budget Estimate Agent**: Look for budget calculation logic and currency handling
- **Research Plan Agent**: Study how research priorities and candidate counts are determined
- **Research Agents** (Lodging, Activities, Food, Transport): Understand tool usage patterns and output formatting
- **Planner Agent**: Study the final plan synthesis and itinerary creation logic

### Data Models & Schemas
Review the Pydantic models defined in the notebook:
- `State`, `Context`, `BudgetEstimate`, `ResearchPlan`
- Candidate models (`CandidateLodging`, `CandidateActivity`, etc.)
- Output models (`LodgingAgentOutput`, `ActivitiesAgentOutput`, etc.)
- `FinalPlan` and day-by-day planning structures

## Implementation Synchronization Guidelines

### When Adding New Features
1. **Start with the notebook**: Implement new functionality in `trip_planner.ipynb` first
2. **Test thoroughly**: Ensure all cells execute without errors using `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`
3. **Extract to modules**: Move stable logic to appropriate `src/` modules that mirror notebook sections
4. **Maintain consistency**: Ensure Python modules match notebook implementation exactly

### When Modifying Existing Code
1. **Compare implementations**: Always check if notebook and Python code are synchronized
2. **Update both**: When making changes, update both the notebook and corresponding Python files
3. **Preserve structure**: Maintain the same node names, edge connections, and data flow patterns
4. **Test integration**: Run both notebook cells and Python tests to ensure compatibility

## Code Structure & Organization

### Module Mapping
Follow this mapping between notebook sections and Python modules:
- **Domain Models**: `src/core/domain.py` — All Pydantic models and data structures
- **Workflow Logic**: `src/workflows/planner.py` — Graph construction and node implementations
- **RAG Pipeline**: `src/pipelines/rag.py` — Document processing and retrieval logic
- **API Surface**: `src/api/app.py` — FastAPI endpoints and request/response handling
- **Services**: `src/services/` — External API integrations (geocoding, TripAdvisor, Amadeus)
- **Tools**: `src/tools/` — Search and research tool implementations

### Testing Strategy
Ensure comprehensive testing coverage:
- **Unit Tests**: `tests/` directory with tests for each module
- **Integration Tests**: Test complete workflow execution from start to finish
- **Notebook Regression**: Use `pytest --nbmake trip_planner.ipynb` for notebook validation
- **API Tests**: Test all FastAPI endpoints with various input scenarios

## Development Workflow

### Environment Setup
Work in a dedicated virtual environment for reproducibility:
- `python -m venv .venv` — create isolated interpreter
- `source .venv/bin/activate` (or `./.venv/Scripts/activate` on Windows) — activate environment
- `pip install -r requirements.txt` — install all dependencies
- `jupyter lab` — launch notebook environment for development

### Quality Assurance
Before committing any changes:
1. **Notebook Validation**: Run `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`
2. **Test Suite**: Execute `py -m pytest tests/ -v` to ensure all tests pass
3. **Code Review**: Verify that Python implementation matches notebook logic
4. **Documentation**: Update relevant documentation to reflect changes

## Common Patterns & Best Practices

### Graph Construction
Follow the notebook's graph construction pattern:
```python
graph_builder = StateGraph(state_schema=State, context_schema=Context)
# Add nodes with explicit names
graph_builder.add_node("node_name", node_function)
# Add edges following the established flow
graph_builder.add_edge(START, "first_node")
# Use conditional edges for routing logic
graph_builder.add_conditional_edges("node", routing_function)
```

### Agent Implementation
When implementing agents, follow the notebook's patterns:
- Use structured prompts with clear input/output specifications
- Implement proper error handling and validation
- Return data in the exact format specified by output models
- Include comprehensive logging and debugging information

### API Integration
Maintain consistency with notebook's API usage:
- Use the same tool configurations and parameters
- Follow the same request/response patterns
- Implement proper rate limiting and error handling
- Preserve the same data transformation logic

## Troubleshooting & Debugging

### Common Issues
1. **Synchronization Problems**: When notebook and Python code diverge, always refer to notebook as source of truth
2. **Import Errors**: Ensure all dependencies are properly installed and imported
3. **State Issues**: Verify that state models match exactly between implementations
4. **Graph Errors**: Check that node names and edge connections match the notebook

### Debugging Tools
- **Notebook Output**: Use notebook cell outputs to understand expected behavior
- **Test Output**: Run tests with `-v` flag for detailed output
- **Logging**: Add comprehensive logging to track execution flow
- **State Inspection**: Use notebook state inspection to understand data flow

## Maintenance & Updates

### Regular Synchronization
- **Weekly Reviews**: Compare notebook and Python implementations
- **Version Control**: Keep notebook and Python code in sync through git
- **Documentation**: Update documentation when implementations change
- **Testing**: Maintain comprehensive test coverage for both implementations

### Future Development
- **New Features**: Always prototype in notebook first, then extract to modules
- **Performance**: Profile both implementations to ensure optimal performance
- **Scalability**: Consider how changes affect both notebook and production deployments
- **Compatibility**: Ensure changes work across different environments and platforms

