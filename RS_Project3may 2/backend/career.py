from .graph import get_skill_difficulties

# Score thresholds
BEGINNER_MAX = 30
MID_MAX = 50
SENIOR_MAX = 70


def get_label(score: float) -> str:
    if score < BEGINNER_MAX:
        return "Beginner"
    elif score < MID_MAX:
        return "Mid-Level"
    elif score < SENIOR_MAX:
        return "Senior"
    else:
        return "Architect"


def score_to_difficulty_level(score: float) -> int:
    """
    Map score to a 1–5 difficulty level used for recommendation filtering.
    Beginner → recommend up to difficulty 3
    Mid-Level → recommend up to difficulty 4
    Senior → recommend up to difficulty 5
    Architect → recommend top-tier only
    """
    if score < BEGINNER_MAX:
        return 2
    elif score < MID_MAX:
        return 3
    elif score < SENIOR_MAX:
        return 4
    else:
        return 5


def calculate_user_level(known_skills: list[str]) -> dict:
    """
    Calculate user level from their consciously submitted skills.

    Algorithm:
    1. Fetch difficulty (1-5) for each skill from Neo4j
    2. Drop the bottom 25% — prevents beginner skills dragging a senior down
    3. Score each remaining skill:
       - difficulty 1-2 (beginner)      → 2 pts
       - difficulty 3   (intermediate)  → 4 pts
       - difficulty 4-5 (advanced)      → 6 pts
    4. Map total score to label + difficulty_level for filtering

    Returns: {"score": int, "label": str, "difficulty_level": int}
    """
    if not known_skills:
        return {"score": 0, "label": "Beginner", "difficulty_level": 1}

    difficulties = get_skill_difficulties(known_skills)

    if not difficulties:
        # No difficulty data yet — treat as pure beginner
        return {"score": 0, "label": "Beginner", "difficulty_level": 1}

    # Sort ascending and drop bottom 25%
    difficulties.sort()
    cutoff = len(difficulties) // 4
    trimmed = difficulties[cutoff:]

    # Score
    score = 0
    for d in trimmed:
        if d <= 2:
            score += 2
        elif d == 3:
            score += 4
        else:
            score += 6

    label = get_label(score)
    difficulty_level = score_to_difficulty_level(score)

    return {
        "score": score,
        "label": label,
        "difficulty_level": difficulty_level
    }
