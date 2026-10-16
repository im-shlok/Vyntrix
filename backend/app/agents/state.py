from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentState(BaseModel):
    # Inputs
    user_query: str = ""
    language: str = "en"
    farmer_profile: Dict[str, Any] = Field(default_factory=dict)
    
    # Internal agent orchestration
    current_agent: str = "planner"
    execution_plan: List[str] = Field(default_factory=list)
    llm_already_called: bool = False

    # Retrieval (RAG)
    # Documents retrieved for this query. The explanation agent injects these
    # into the generation prompt, which is what makes the pipeline genuinely
    # retrieval-augmented rather than just labelled as such.
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    # Computed once by the planner and reused by every downstream agent, so one
    # request costs a single embedding call no matter how many agents retrieve.
    query_vector: Optional[List[float]] = None
    # "semantic" or "keyword" - which router produced execution_plan.
    routing_mode: str = "keyword"
    
    # Specialized outputs from each agent
    vision_results: Optional[Dict[str, Any]] = None
    weather_info: Optional[Dict[str, Any]] = None
    soil_data: Optional[Dict[str, Any]] = None
    market_rates: Optional[Dict[str, Any]] = None
    schemes: List[Dict[str, Any]] = Field(default_factory=list)
    medical_advice: Optional[Dict[str, Any]] = None
    disaster_alerts: Optional[Dict[str, Any]] = None
    tutorials: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Final explainable system recommendations and trace logs
    explanation: str = ""
    # "provider:model" that wrote the explanation, or "fallback" when every
    # model failed and the agents' raw outputs were shown instead.
    explanation_source: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
