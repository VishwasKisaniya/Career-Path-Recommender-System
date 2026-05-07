import os
import json
import re
import time
from groq import Groq

# We assume GROQ_API_KEY is available in the environment (e.g. via .env)
client = Groq()

def clean_json(text: str) -> str:
    """Strip markdown code fences if present."""
    text = re.sub(r"```json|```", "", text).strip()
    return text

def get_groq_response(prompt: str, max_tokens: int = 1000) -> str:
    """Helper to call Groq API with the specified model and settings."""
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_completion_tokens=max_tokens,
        top_p=1,
        stream=False,
        stop=None
    )
    return completion.choices[0].message.content

def validate_skill(skill: str, retries: int = 5) -> dict:
    """
    Validate and normalize a skill name.
    Returns {"valid": bool, "normalized": str | None}
    Used for BOTH user input and LLM-generated neighbor skills.
    """
    prompt = f"""
    You are a strictly JSON-only data formatting API. Do NOT output markdown, explanations, or code solutions.
    
    You are given a skill name: "{skill}"
    1. Determine if it is a valid technical skill (software/hardware/data/engineering).
    2. If valid, return its correct standardized name (e.g., "aws" → "AWS", "react js" → "React", "nodejs" → "Node.js").

    Return ONLY JSON in this exact format with no extra text:
    {{"valid": true/false, "normalized": "Standard Skill Name or null"}}
    """
    for attempt in range(retries):
        try:
            res_text = get_groq_response(prompt, max_tokens=100)
            try:
                data = json.loads(clean_json(res_text))
            except Exception as parse_e:
                print(f"      [LLM Parse Error] {parse_e}. Output was: {res_text[:200]}...")
                raise parse_e
            
            return {
                "valid": data.get("valid", False),
                "normalized": data.get("normalized")
            }
        except Exception as e:
            if attempt < retries - 1:
                print(f"      [LLM Error] {e} | Waiting 15s... (Attempt {attempt+1}/{retries})")
                time.sleep(15)
            
    return {"valid": False, "normalized": None}

def normalize_skill_name(skill: str) -> str:
    """
    Normalize an LLM-generated skill name to its canonical form.
    Prevents duplicates like "Node.js" and "NodeJS".
    """
    result = validate_skill(skill)
    if result.get("valid") and result.get("normalized"):
        return result["normalized"]
    return skill

def normalize_skills_batch(skills: list[str], retries: int = 5) -> dict:
    """
    Validate and normalize multiple skill names in a single LLM call.
    Returns a dict mapping the original skill name to its normalized form (or None if invalid).
    """
    if not skills:
        return {}
        
    prompt = f"""
    You are a strictly JSON-only data formatting API. Do NOT output markdown, explanations, or code solutions.
    
    You are given a list of skill names: {json.dumps(skills)}
    For each skill:
    1. Determine if it is a valid technical skill (software/hardware/data/engineering).
    2. If valid, return its correct standardized name (e.g., "aws" → "AWS", "react js" → "React").
    
    Return ONLY a JSON object mapping the exact original string to either its standardized name, or null if invalid.
    Example: {{"nodejs": "Node.js", "fake_skill123": null}}
    """
    
    for attempt in range(retries):
        try:
            res_text = get_groq_response(prompt, max_tokens=1000)
            try:
                return json.loads(clean_json(res_text))
            except Exception as parse_e:
                print(f"      [LLM Parse Error] {parse_e}. Output was: {res_text[:200]}...")
                raise parse_e
        except Exception as e:
            if attempt < retries - 1:
                print(f"      [LLM Error] {e} | Waiting 15s... (Attempt {attempt+1}/{retries})")
                time.sleep(15)
                
    # fallback to originals on total failure
    return {s: s for s in skills}

def normalize_track(track: str) -> str:
    """
    Normalize track names to a fixed enum. Fallback to 'Core'.
    Valid tracks: ["Web", "Data", "DevOps", "ML", "Mobile", "Systems", "Cloud", "Core", "Automation"]
    """
    VALID_TRACKS = ["Web", "Data", "DevOps", "ML", "Mobile", "Systems", "Cloud", "Core", "Automation"]
    if not track:
        return "Core"
    
    t = track.strip().title()
    if t in VALID_TRACKS:
        return t
        
    # Heuristics for common mismatches
    lower_t = track.lower()
    if "web" in lower_t or "frontend" in lower_t or "backend" in lower_t: return "Web"
    if "data" in lower_t: return "Data"
    if "devops" in lower_t or "ci/cd" in lower_t: return "DevOps"
    if "machine learning" in lower_t or "ml" in lower_t or "ai" in lower_t: return "ML"
    if "mobile" in lower_t or "android" in lower_t or "ios" in lower_t: return "Mobile"
    if "system" in lower_t: return "Systems"
    if "cloud" in lower_t or "aws" in lower_t or "azure" in lower_t or "gcp" in lower_t: return "Cloud"
    if "automation" in lower_t: return "Automation"
    
    return "Core"

def expand_skill(skill: str, retries: int = 5) -> list:
    """
    Given a skill the user knows, return a list of recommended next skills.
    Each item includes: skill, track, reason, difficulty (1-5).
    """
    prompt = f"""
    The user already knows: "{skill}". 
    You are an expert, highly opinionated Senior Software Engineer and Career Advisor.
    Suggest the NEXT MOST ESSENTIAL skills the user MUST learn.
    
    RULES:
    1. Do NOT suggest generic concepts (e.g., "Web Development", "Databases").
    2. DO suggest specific, industry-standard tools, libraries, or frameworks (e.g., "React", "PostgreSQL", "Docker").
    3. Limit your recommendations to the Top 3 to 5 absolute BEST, most logical next steps. Do not overwhelm the user.
    4. Provide a highly compelling, professional 1-sentence reason why this is essential.

    Return a JSON array. Each object MUST have exactly these 4 fields:
    - "skill": the recommended next skill — use the standardized name (e.g. "AWS", "Node.js", "React")
    - "track": a meaningful category (e.g. "Web", "Machine Learning", "Cloud", "Cybersecurity", "DevOps")
    - "reason": a clear, professional 1-sentence explanation of why this skill is recommended
    - "difficulty": an integer from 1 to 5:
        1 = absolute beginner (e.g. HTML, Git basics)
        2 = beginner (e.g. Python basics, SQL intro)
        3 = intermediate (e.g. Docker, REST APIs, React)
        4 = advanced (e.g. Kubernetes, System Design, AWS)
        5 = expert (e.g. Distributed Systems, MLOps, Compiler Design)

    Example output:
    [
      {{"skill": "Pandas", "track": "Data", "reason": "The absolute industry standard for data manipulation, making it the most logical step after basic Python.", "difficulty": 2}},
      {{"skill": "FastAPI", "track": "Web", "reason": "A modern, highly performant web framework for building APIs, perfect for intermediate Python developers.", "difficulty": 3}}
    ]

    No markdown. No explanation. Return ONLY the JSON array.
    """

    for attempt in range(retries):
        try:
            res_text = get_groq_response(prompt, max_tokens=2000)
            try:
                data = json.loads(clean_json(res_text))
            except Exception as parse_e:
                print(f"      [LLM Parse Error] {parse_e}. Output was: {res_text[:200]}...")
                raise parse_e # trigger retry

            # Optional: normalize tracks after generation (non-restrictive)
            for item in data:
                if "track" in item:
                    item["track"] = normalize_track(item["track"])

            return data

        except Exception as e:
            if attempt < retries - 1:
                print(f"      [LLM Error] {e} | Waiting 15s... (Attempt {attempt+1}/{retries})")
                time.sleep(15)

    return []