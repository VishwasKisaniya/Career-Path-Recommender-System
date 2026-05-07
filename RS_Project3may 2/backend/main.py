from dotenv import load_dotenv
import os

env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(env_path)

print("ENV PATH:", env_path)
print("API KEY:", os.getenv("GROQ_API_KEY"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import SkillInput
from .llm import validate_skill, expand_skill, normalize_skill_name, normalize_track, normalize_skills_batch
from .graph import (
    get_recommendations,
    get_leaf_nodes,
    get_specialization,
    load_skill_cache,
    get_all_skills,
    skill_exists,
    add_skill_node,
    add_relationship
)
from .session import init_db, upsert_user, save_skills, get_user_skills, get_all_user_data, delete_user_data
from .career import calculate_user_level

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    load_skill_cache()
    init_db()  # creates SQLite tables if they don't exist


@app.post("/recommend")
def recommend(input: SkillInput):

    # --- Input hygiene ---
    input.skills = list(dict.fromkeys(input.skills))  # deduplicate, preserve order

    if len(input.skills) > 10:
        return {"error": "Maximum 10 skills allowed per request."}

    normalized_map = {}

    # --- Expand / validate each skill ---
    for skill in input.skills:
        
        normalized_skill = skill
        if skill_exists(skill):
            normalized_map[skill] = skill
            if skill not in get_leaf_nodes([skill]):
                continue # Known skill, not a leaf, no expansion needed
        else:
            # CASE 2: New skill — validate first
            validation = validate_skill(skill)
            if not validation["valid"]:
                return {"error": f"'{skill}' is not a recognised technical skill"}

            normalized_skill = validation["normalized"] or skill
            normalized_map[skill] = normalized_skill
            add_skill_node(normalized_skill)

        # Expand either a leaf node or a newly added node
        expansions = expand_skill(normalized_skill)
        
        # Collect raw neighbor names for batched normalization
        raw_skills = []
        valid_items = []
        for item in expansions:
            # Validate structure before writing to graph (Objective 9)
            if not isinstance(item.get("skill"), str) or not item["skill"].strip():
                continue
            if not isinstance(item.get("track"), str) or not item.get("reason"):
                continue
            if not isinstance(item.get("difficulty"), int):
                continue
            raw_skills.append(item["skill"].strip())
            valid_items.append(item)
            
        # Batch normalize to prevent duplicate nodes efficiently (Objective 6 + Performance)
        normalized_neighbors = normalize_skills_batch(raw_skills)
        
        for item in valid_items:
            raw_s = item["skill"].strip()
            canonical = normalized_neighbors.get(raw_s)
            
            if not canonical:
                continue # skip if validation marked it as invalid
                
            add_relationship(
                normalized_skill,
                canonical,
                normalize_track(item["track"]),
                item["reason"],
                item.get("difficulty")
            )

    # Refresh cache after any new additions
    load_skill_cache()

    normalized_inputs = [normalized_map[s] for s in input.skills]

    # --- User history & level (Objectives 4 & 5) ---
    user_level_info = {"score": 0, "label": "Beginner", "difficulty_level": 1}

    if input.user_id:
        upsert_user(input.user_id)

        # Fetch full skill history across all sessions (only user-submitted)
        historical_skills = get_user_skills(input.user_id)

        # Combine history + current session for level calculation
        all_known_for_level = list(set(historical_skills + normalized_inputs))
        user_level_info = calculate_user_level(all_known_for_level)

        # Save current session skills to history (chosen_in_session = True)
        save_skills(input.user_id, normalized_inputs, chosen=True)

    # --- Difficulty-aware filtering (Objective 3) ---
    user_diff_level = user_level_info["difficulty_level"]
    min_diff = max(1, user_diff_level - 1)   # never more than 1 level below user
    max_diff = min(5, user_diff_level + 2)   # recommend up to 2 levels ahead

    # --- Fetch recommendations, leaf nodes, specialization ---
    recommendations = get_recommendations(normalized_inputs, min_diff, max_diff)
    leaf_nodes = get_leaf_nodes(normalized_inputs)
    
    # Timestamp-based tiebreaker for specialization
    historical_skills = get_user_skills(input.user_id) if input.user_id else []
    recent_skill = historical_skills[-1] if historical_skills else (normalized_inputs[-1] if normalized_inputs else None)
    specialization = get_specialization(normalized_inputs, recent_skill)

    # --- Filter out already-known skills (Objective 11) ---
    normalized_inputs_set = set(normalized_inputs)
    filtered_recommendations = {}
    for track, skills in recommendations.items():
        filtered = [s for s in skills if s["skill"] not in normalized_inputs_set]
        if filtered:
            filtered_recommendations[track] = filtered

    return {
        "recommendations": filtered_recommendations,
        "leaf_nodes": leaf_nodes,
        "user_level": user_level_info,
        "specialization": specialization
    }


@app.get("/skills")
def skills():
    return {"skills": get_all_skills()}


@app.get("/user/{user_id}/career")
def career(user_id: str):
    """Return current career level for a user based on their full history."""
    historical_skills = get_user_skills(user_id)
    if not historical_skills:
        return {"score": 0, "label": "Beginner", "difficulty_level": 1, "skills_count": 0}
    level_info = calculate_user_level(historical_skills)
    level_info["skills_count"] = len(historical_skills)
    return level_info


@app.get("/user/{user_id}/export")
def export_user(user_id: str):
    """Export full user history as JSON (Objective 12)."""
    data = get_all_user_data(user_id)
    return JSONResponse(content=data)


@app.post("/user/{user_id}/reset")
def reset_user(user_id: str):
    """Wipe all user data from SQLite. Neo4j graph is unaffected (Objective 12)."""
    delete_user_data(user_id)
    return {"message": "User data cleared successfully."}


@app.get("/")
def root():
    return {"message": "Skill Recommender API is running"}
