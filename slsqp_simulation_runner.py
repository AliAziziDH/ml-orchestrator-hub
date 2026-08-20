import sys
import json
from datetime import datetime, timezone

# Ensure we can import our compaction and routing classes
sys.path.append("/workspace/artifacts")
sys.path.append("/workspace/scratch")

from compaction_and_routing import StructuredCompactionManager, SemanticToolFinder, ToolSchema

# =====================================================================
# 1. SLSQP EXPERIMENT CATALOG & METADATA DEFINITIONS
# =====================================================================

# Define our mock Kaggle tools catalog with stage affinities
KAGGLE_TOOL_CATALOG = [
    ToolSchema(
        name="data_loader_tool",
        description="Loads Out-Of-Fold (OOF) prediction arrays and true target values for XGBoost and CatBoost.",
        stage_affinity="CODE_DEVELOPMENT",
        parameters_schema={"project": "string", "folds": "integer"}
    ),
    ToolSchema(
        name="matrix_aligner_tool",
        description="Fixes shape mismatches in OOF arrays by aligning indices and cropping target mismatches.",
        stage_affinity="CODE_DEVELOPMENT",
        parameters_schema={"array_a": "array", "array_b": "array"}
    ),
    ToolSchema(
        name="slsqp_optimizer_tool",
        description="Executes Sequential Least Squares Programming to find convex weights summing to 1.0.",
        stage_affinity="EVALUATION",
        parameters_schema={"oof_predictions": "object", "targets": "array", "bounds": "array"}
    ),
    ToolSchema(
        name="google_sheets_sync_tool",
        description="Synchronizes the final optimized OOF CV score and weights to the live ML_Orchestrator_Experiment_Ledger.",
        stage_affinity="DEPLOY",
        parameters_schema={"experiment_id": "string", "metrics": "object"}
    )
]

# Initialize our core SOTA components
tool_finder = SemanticToolFinder(KAGGLE_TOOL_CATALOG)
compaction_manager = StructuredCompactionManager(keep_recent_turns=2)

# =====================================================================
# 2. RUN SIMULATION SCENARIO
# =====================================================================

def run_slsqp_simulation():
    print("=" * 80)
    print("ORCHESTRA: PHASE 7 - SLSQP OPTIMIZATION & CONTEXT COMPACTION SIMULATOR")
    print("=" * 80)
    
    # -----------------------------------------------------------------
    # STEP 1: Initialization of State
    # -----------------------------------------------------------------
    print("\n[STEP 1] Initializing Phase 4 Agent State for EXP-HP-001...")
    state = {
        "messages": [
            {"role": "system", "content": "You are Jules, the ML Engineer agent for Orchestra."},
            {"role": "user", "content": "Conductor: Start EXP-HP-001. Find optimal convex weights for XGBoost + CatBoost OOF ensemble using SLSQP."}
        ],
        "stage": "CODE_DEVELOPMENT",
        "downstream_repo_path": "downstream_repos/house-prices-kaggle",
        "active_tools": [],
        "experiment": {
            "experiment_id": "EXP-HP-001",
            "project_name": "house-prices-kaggle",
            "experiment_tag": "slsqp_ensemble_baseline",
            "model_architecture": "XGBoost [max_depth=6] + CatBoost [depth=6]",
            "cv_metric": "RMSLE",
            "status": "PENDING",
            "oof_cv_score": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "telemetry": {
            "current_fold": 0,
            "total_folds": 10,
            "fold_scores": [],
            "progress_percentage": 0.0
        },
        "cost_tracker": {
            "input_tokens": 1500,
            "output_tokens": 300,
            "accumulated_cost_usd": 0.0045,
            "budget_limit_usd": 5.0,
            "is_budget_exhausted": False
        },
        "circuit_breaker_triggered": False,
        "error_message": None,
        "requires_human_approval": False
    }
    
    print(f"-> Experiment ID: {state['experiment']['experiment_id']}")
    print(f"-> Budget Limit: ${state['cost_tracker']['budget_limit_usd']} USD")
    print(f"-> Current SDOF Stage: {state['stage']}")

    # -----------------------------------------------------------------
    # STEP 2: Turn 1 - JIT Tool Retrieval
    # -----------------------------------------------------------------
    print("\n[STEP 2] Turn 1 - Jules attempts to load data. Requesting data loader tool JIT...")
    query = "I need to load the training predictions and target variables to run SLSQP."
    
    # JIT tool selection strictly bounded by active SDOF stage
    selected_tools = tool_finder.select_tools_semantically(query, active_stage=state["stage"])
    state["active_tools"] = [t.name for t in selected_tools]
    
    print(f"-> Active Stage: {state['stage']}")
    print(f"-> Query: \"{query}\"")
    print(f"-> JIT Disclosed Tools (5-Tool Rule): {state['active_tools']}")
    
    # Simulate execution of data loading
    state["messages"].append({"role": "user", "content": query})
    state["messages"].append({"role": "assistant", "content": "Jules: Executing data_loader_tool for house-prices-kaggle fold 1-10."})
    
    # -----------------------------------------------------------------
    # STEP 3: Turn 2 - Encountering Matrix Dimension Mismatch
    # -----------------------------------------------------------------
    print("\n[STEP 3] Turn 2 - Jules encounters matrix mismatch and enters an error loop...")
    error_msg = "ValueError: OOF predictions shape mismatch. XGBoost has shape (1460, 1) but CatBoost has (1459, 1). Fold 10 corrupted."
    print(f"-> Simulated Error: {error_msg}")
    
    # Simulate Jules attempting to solve it unsuccessfully 3 times (stall_rounds loop)
    for attempt in range(1, 4):
        state["messages"].append({
            "role": "user", 
            "content": f"Compiler/Test: Attempt {attempt} failed. {error_msg}"
        })
        state["messages"].append({
            "role": "assistant", 
            "content": "Jules: Trying to re-run with modified seed or dropping NaN index. Attempting execution."
        })
        # Simulate heavy token accumulation in each attempt
        state["cost_tracker"]["input_tokens"] += 25000
        state["cost_tracker"]["output_tokens"] += 4000
        
    # Calculate accumulated cost based on SOTA rates ($3/1M input, $15/1M output)
    input_cost = (state["cost_tracker"]["input_tokens"] / 1_000_000) * 3.0
    output_cost = (state["cost_tracker"]["output_tokens"] / 1_000_000) * 15.0
    state["cost_tracker"]["accumulated_cost_usd"] = input_cost + output_cost
    
    print(f"-> Accumulated Messages in History: {len(state['messages'])}")
    print(f"-> Total Accumulated Tokens: {state['cost_tracker']['input_tokens'] + state['cost_tracker']['output_tokens']}")
    print(f"-> Total Accumulated Cost: ${state['cost_tracker']['accumulated_cost_usd']:.4f} USD")

    # -----------------------------------------------------------------
    # STEP 4: Token Monitor & Yield Point Check (Compaction Triggered)
    # -----------------------------------------------------------------
    print("\n[STEP 4] Evaluator: Checking Token Monitor and Yield Point logic...")
    
    # Check if context > 60% of limit (limit is roughly 128k, 60% is ~76.8k)
    total_tokens = state["cost_tracker"]["input_tokens"] + state["cost_tracker"]["output_tokens"]
    should_compact = total_tokens > 76800
    
    # SDOF Yield Point Condition Logic
    stall_rounds = 3  # We simulated 3 repeated identical failures
    yield_point_triggered = stall_rounds >= 3 or state["cost_tracker"]["accumulated_cost_usd"] > 4.0
    
    print(f"-> Does context exceed 60% limit? {should_compact} (Tokens: {total_tokens})")
    print(f"-> Has Yield Point been reached? {yield_point_triggered} (Stall Rounds: {stall_rounds})")
    
    if should_compact or yield_point_triggered:
        print("\n[CRITICAL INTERVENTION] Activating Critic Compaction Node to prevent Context Rot!")
        
        # Build initial compaction summary
        initial_summary = {
            "active_goal": "Optimize SLSQP ensemble weights on house-prices-kaggle OOF.",
            "key_decisions": [],
            "files_modified": [],
            "errors_encountered": [],
            "next_steps": ["Align arrays", "Run SLSQP weight optimization"],
            "critical_math_context": {"metric": "RMSLE", "target_cv": 0.115}
        }
        
        # Execute structured compaction (pruning all but last 2 turns)
        compaction_result = compaction_manager.compact(
            messages=state["messages"],
            existing_summary=initial_summary,
            system_prompt="You are an expert ML Optimizer agent inside the Antigravity IDE.",
            persistent_config_str="Repo: house-prices-kaggle\nEngine: SLSQP Convex Optimizer"
        )
        
        # Update our active state messages
        state["messages"] = compaction_result["compacted_messages"]
        print("-> Context compacted successfully!")
        print(f"-> Compacted History Message Count: {len(state['messages'])}")
        print("\n--- Compacted Message Content ---")
        for msg in state["messages"]:
            if msg["role"] == "system" and "CONVERSATION SUMMARY" in msg["content"]:
                print(msg["content"])
        print("---------------------------------")

    # -----------------------------------------------------------------
    # STEP 5: Antigravity IDE Recovery & JIT Jaccard Optimization Tooling
    # -----------------------------------------------------------------
    print("\n[STEP 5] Antigravity IDE Recovery Node Activated (The Ultimate Optimizer)...")
    state["stage"] = "EVALUATION"
    state["experiment"]["status"] = "RUNNING"
    
    recovery_query = "Resolve fold 10 dimension mismatch, crop array to 1459, and run SLSQP convex optimizer."
    print(f"-> Recovery Query: \"{recovery_query}\"")
    
    # Retrieve tools semantically for the EVALUATION stage
    corrective_tools = tool_finder.select_tools_semantically(recovery_query, active_stage=state["stage"])
    state["active_tools"] = [t.name for t in corrective_tools]
    print(f"-> JIT Disclosed Corrective Tools (SDOF EVALUATION): {state['active_tools']}")
    
    # Simulate SLSQP execution
    print("-> Executing slsqp_optimizer_tool on aligned arrays...")
    optimal_weights = {"XGBoost": 0.6432, "CatBoost": 0.3568}
    optimized_oof_score = 0.1102
    
    state["messages"].append({"role": "user", "content": recovery_query})
    state["messages"].append({
        "role": "assistant",
        "content": f"Antigravity Optimizer: Successfully resolved OOF dimension mismatch by cropping Fold 10 to 1459.\n"
                   f"Executed SLSQP optimization. Resulting weights: {optimal_weights}.\n"
                   f"Achieved OOF CV RMSLE: {optimized_oof_score:.4f}"
    })
    
    # -----------------------------------------------------------------
    # STEP 6: Finalization & Live Ledger Synchronization
    # -----------------------------------------------------------------
    print("\n[STEP 6] Syncing successful experiment to live Google Sheets and terminating...")
    state["stage"] = "DEPLOY"
    state["experiment"]["oof_cv_score"] = optimized_oof_score
    state["experiment"]["status"] = "SUCCESS"
    state["experiment"]["key_insights"] = f"Optimal weights: XGB={optimal_weights['XGBoost']:.2f}, Cat={optimal_weights['CatBoost']:.2f}. Dimension issue solved."
    
    deploy_tools = tool_finder.select_tools_semantically("Sync experiment to ledger", active_stage=state["stage"])
    state["active_tools"] = [t.name for t in deploy_tools]
    print(f"-> Deploy Stage Tools JIT: {state['active_tools']}")
    
    print("\n" + "=" * 80)
    print("SIMULATION SUCCESSFUL! EXPERIMENT RECORD UPDATED:")
    print(json.dumps(state["experiment"], indent=2, ensure_ascii=False))
    print("=" * 80)

if __name__ == "__main__":
    run_slsqp_simulation()
