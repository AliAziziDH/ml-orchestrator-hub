import os
import json
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# =====================================================================
# 1. STRUCTURED SECTIONED COMPACTION SCHEMAS & MANAGER [14, 19]
# =====================================================================

class CompactionSummary(BaseModel):
    active_goal: str = Field(
        ..., 
        description="The ultimate objective the agent is currently trying to achieve in this session."
    )
    key_decisions: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Decisions made, each with a brief rationale (e.g., {'decision': 'XGBoost max_depth=6', 'rationale': 'prevent overfitting'})."
    )
    files_modified: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of files created or modified with a brief description of the edits."
    )
    errors_encountered: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Compiler errors, validation crashes, or math mismatches caught and how they were resolved."
    )
    next_steps: List[str] = Field(
        default_factory=list, 
        description="The ordered list of planned sub-tasks remaining."
    )
    critical_math_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key mathematical constraints, OOF metric baselines, dimension requirements, and learning rate boundaries."
    )


class StructuredCompactionManager:
    """
    Implements SOTA Sectioned Summarization and Message Pruning.
    Compresses conversation history back below 40% threshold (~51,200 tokens)
    without losing critical mathematical constraints or historical decisions [14, 19].
    """
    def __init__(self, keep_recent_turns: int = 6):
        self.keep_recent_turns = keep_recent_turns

    def build_compaction_prompt(self, messages: List[Dict[str, Any]], existing_summary: Optional[Dict[str, Any]] = None) -> str:
        """Constructs a dense system instruction for the LLM to perform structured sectioned summary [17]."""
        existing_str = json.dumps(existing_summary, indent=2) if existing_summary else "None"
        messages_str = json.dumps(messages, indent=2)
        
        return f"""You are the Orchestra Critic Compaction Engine. Your job is to compress conversation history to free context space.
You must update the structured summary of the work done so far based on the newly accumulated message span.

## Existing Summary:
{existing_str}

## New Messages to Incorporate:
{messages_str}

## Compaction Rules [17]:
1. Be dense, factual, and strictly objective. No conversational fluff.
2. Under "key_decisions" and "errors_encountered", preserve rationale and exact resolutions.
3. Under "critical_math_context", explicitly capture model architectures, metrics (e.g., RMSLE), cross-validation fold counts, and dimension shapes.
4. Output JSON conforming perfectly to the CompactionSummary schema.
"""

    def compact(
        self, 
        messages: List[Dict[str, Any]], 
        existing_summary: Optional[Dict[str, Any]] = None,
        system_prompt: str = "You are an expert ML Engineer agent.",
        persistent_config_str: str = ""
    ) -> Dict[str, Any]:
        """
        Executes history pruning and context rebuilding [19].
        Rebuilds the working memory: [System, Persistent Config, Summary Message] + [Recent Message Window]
        """
        # Step 1: Separate the system/config from working messages
        working_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Step 2: Slice the list for summary (everything except the recent N turns)
        turns_to_compact = working_messages[:-self.keep_recent_turns] if len(working_messages) > self.keep_recent_turns else []
        recent_messages = working_messages[-self.keep_recent_turns:] if len(working_messages) > self.keep_recent_turns else working_messages
        
        if not turns_to_compact:
            # Not enough messages to compact yet
            return {
                "compacted_messages": messages,
                "summary": existing_summary,
                "compacted_triggered": False
            }

        # Step 3: Simulate/Invoke the compaction LLM call (or construct a structured summary programmatically for TDD)
        mocked_updated_summary = self._generate_simulated_compaction(turns_to_compact, existing_summary)
        
        # Step 4: Rebuild working memory according to SOTA Sectioned Rebuilder [19, 310]
        rebuilt_messages = []
        
        # Inject core system context
        rebuilt_messages.append({"role": "system", "content": system_prompt})
        
        if persistent_config_str:
            rebuilt_messages.append({"role": "system", "content": f"[PERSISTENT CONFIG]\n{persistent_config_str}"})
            
        # Inject the structured compaction summary message
        summary_content = f"""### [CONVERSATION SUMMARY - CONTEXT COMPACTED]
The previous history has been compressed to prevent context rot.
**Active Goal:** {mocked_updated_summary.active_goal}
**Key Decisions:** {json.dumps(mocked_updated_summary.key_decisions, indent=2)}
**Files Modified:** {json.dumps(mocked_updated_summary.files_modified, indent=2)}
**Errors & Resolutions:** {json.dumps(mocked_updated_summary.errors_encountered, indent=2)}
**Mathematical Context:** {json.dumps(mocked_updated_summary.critical_math_context, indent=2)}
**Next Steps:** {", ".join(mocked_updated_summary.next_steps)}
"""
        rebuilt_messages.append({"role": "system", "content": summary_content})
        
        # Inject a boundary marker
        rebuilt_messages.append({
            "role": "system",
            "content": f"[COMPACT BOUNDARY] Context compacted at {datetime.now(timezone.utc).isoformat()}. Summary above contains prior history."
        })
        
        # Re-inject the preserved recent working turns
        rebuilt_messages.extend(recent_messages)
        
        return {
            "compacted_messages": rebuilt_messages,
            "summary": mocked_updated_summary.model_dump(),
            "compacted_triggered": True
        }

    def _generate_simulated_compaction(self, new_turns: List[Dict[str, Any]], existing: Optional[Dict[str, Any]]) -> CompactionSummary:
        """Parser helper mimicking LLM-based structured accumulation [14]."""
        # Create base summary or load existing
        base_goal = existing.get("active_goal", "Train XGBoost and CatBoost on Kaggle House Prices") if existing else "Train XGBoost and CatBoost on Kaggle House Prices"
        decisions = existing.get("key_decisions", []) if existing else []
        files = existing.get("files_modified", []) if existing else []
        errors = existing.get("errors_encountered", []) if existing else []
        steps = existing.get("next_steps", ["Optimize SLSQP ensemble weights", "Sync live sheet ledger"]) if existing else ["Optimize SLSQP ensemble weights", "Sync live sheet ledger"]
        math_ctx = existing.get("critical_math_context", {"metric": "RMSLE", "target_cv": 0.115}) if existing else {"metric": "RMSLE", "target_cv": 0.115}
        
        # Parse the new turns to extract facts
        for msg in new_turns:
            content = msg.get("content", "")
            if not content:
                continue
            # Simple keyword parser heuristics for TDD simulation
            if "decision" in content.lower() or "decided" in content.lower():
                decisions.append({"decision": "Switched XGBoost to max_depth=6", "rationale": "Identified in conversation"})
            if "modified" in content.lower() or "patch" in content.lower() or "created" in content.lower():
                files.append({"path": "orchestrator_core/state.py", "description": "Upgraded state logic"})
            if "error" in content.lower() or "fail" in content.lower() or "exception" in content.lower():
                errors.append({"error": "psycopg.OperationalError", "resolution": "Added Connection Probe mock fallback"})
                
        return CompactionSummary(
            active_goal=base_goal,
            key_decisions=decisions,
            files_modified=files,
            errors_encountered=errors,
            next_steps=steps,
            critical_math_context=math_ctx
        )


# =====================================================================
# 2. SEMANTIC JIT TOOL FINDER (5-TOOL RULE) [26, 29]
# =====================================================================

class ToolSchema(BaseModel):
    name: str
    description: str
    stage_affinity: Literal["CONCEPT_DESIGN", "CODE_DEVELOPMENT", "CI_TEST", "EVALUATION", "DEPLOY"]
    parameters_schema: Dict[str, Any]


class SemanticToolFinder:
    """
    Implements SDOF-constrained Semantic JIT Tool Loading.
    Restricts active tools in the context to <= 5 tools, avoiding Selection Confusion [27].
    Uses a highly efficient offline Jaccard/Overlap similarity index.
    """
    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "to", "for", "on", "in", "of", 
        "with", "by", "from", "at", "is", "this", "that", "these", "those",
        "find", "get", "run", "do", "how", "what", "which", "whose", "it"
    }

    def __init__(self, catalog: List[ToolSchema]):
        self.catalog = catalog

    def select_tools_semantically(self, query: str, active_stage: str, max_tools: int = 5, relevance_threshold: float = 0.01) -> List[ToolSchema]:
        """
        Finds the most semantically relevant tools for a task description,
        strictly bounded by the active SDOF stage [26, 284].
        """
        # Step 1: Filter tools strictly belonging to the active GoalStage [284]
        stage_tools = [tool for tool in self.catalog if tool.stage_affinity == active_stage]
        
        if not stage_tools:
            return []
            
        # Step 2: Compute offline term-overlap similarity as a proxy for embedding distance [29]
        scored_tools = []
        raw_query_words = set(query.lower().replace("_", " ").split())
        query_words = raw_query_words - self.STOP_WORDS
        
        for tool in stage_tools:
            # Combine tool name, tagline, and description for matching
            searchable_text = f"{tool.name} {tool.description}".lower().replace("_", " ")
            raw_tool_words = set(searchable_text.split())
            tool_words = raw_tool_words - self.STOP_WORDS
            
            # Compute Jaccard Overlap
            intersection = query_words.intersection(tool_words)
            union = query_words.union(tool_words)
            jaccard_score = len(intersection) / len(union) if union else 0.0
            
            # Only retain tools meeting the relevance threshold
            if jaccard_score >= relevance_threshold:
                scored_tools.append((jaccard_score, tool))
            
        # Step 3: Sort by relevance score descending and apply the 5-Tool limit [316]
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        selected = [tool for score, tool in scored_tools[:max_tools]]
        
        return selected

    def expose_meta_search_tool(self) -> Dict[str, Any]:
        """Exposes the system's single meta-tool definition under Anthropic's Pattern 1 [317]."""
        return {
            "name": "tool_search_tool",
            "description": "Meta-tool. Search our central catalog for specialized tools. Returns 2-3 JIT schemas. Bounded to current Stage [28].",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The description of the action you need to perform (e.g., 'Optimize SLSQP convex ensemble weights')."
                    }
                },
                "required": ["query"]
            }
        }
