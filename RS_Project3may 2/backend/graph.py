from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "Okok@123")

driver = GraphDatabase.driver(URI, auth=AUTH)

_skill_cache: list = []


def load_skill_cache():
    global _skill_cache
    with driver.session() as session:
        result = session.run("MATCH (s:Skill) RETURN s.name AS name ORDER BY s.name")
        _skill_cache = [record["name"] for record in result]


def get_all_skills() -> list:
    return _skill_cache


def get_skill_difficulties(skill_names: list[str]) -> list[int]:
    """
    Returns a list of difficulty values (int) for skills that have difficulty set.
    Used by career.py for user level calculation.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Skill)
            WHERE s.name IN $skills AND s.difficulty IS NOT NULL
            RETURN s.difficulty AS d
            ORDER BY s.difficulty
        """, skills=skill_names)
        return [record["d"] for record in result]


def get_recommendations(known_skills: list[str], min_difficulty: int = 1, max_difficulty: int = 5):
    """
    Given known skills, find all unlocked skills within the difficulty range.
    b.difficulty IS NULL guard ensures new skills without difficulty still appear.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Skill)-[r:UNLOCKS]->(b:Skill)
            WHERE a.name IN $skills
            AND (b.difficulty IS NULL OR
                 (b.difficulty >= $min_diff AND b.difficulty <= $max_diff))
            RETURN b.name AS skill, r.track AS track, r.reason AS reason, b.difficulty AS difficulty
            """,
            skills=known_skills,
            min_diff=min_difficulty,
            max_diff=max_difficulty
        )

        grouped = {}
        for record in result:
            track = record["track"]
            if track not in grouped:
                grouped[track] = []
            grouped[track].append({
                "skill": record["skill"],
                "reason": record["reason"],
                "difficulty": record["difficulty"]
            })

        return grouped


def get_leaf_nodes(known_skills: list[str]):
    """
    Return input skills that are leaf nodes — no outgoing UNLOCKS edges.
    These get dynamically expanded by the LLM.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Skill)
            WHERE a.name IN $skills
            AND NOT (a)-[:UNLOCKS]->()
            RETURN a.name AS skill
            """,
            skills=known_skills
        )
        return [record["skill"] for record in result]


def get_specialization(known_skills: list[str], recent_skill: str = None) -> str | None:
    if not known_skills:
        return None
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Skill)-[r:UNLOCKS]->(b:Skill)
            WHERE a.name IN $skills
            RETURN r.track AS track, COUNT(*) AS cnt
            ORDER BY cnt DESC
        """, skills=known_skills)
        
        records = result.data()
        if not records:
            return None
        
        top_count = records[0]["cnt"]
        tied_tracks = [r["track"] for r in records if r["cnt"] == top_count]
        
        # No tie — return directly
        if len(tied_tracks) == 1:
            return tied_tracks[0]
        
        # Tie — use most recently learned skill's track as tiebreaker
        if recent_skill:
            result2 = session.run("""
                MATCH (a:Skill {name: $skill})-[r:UNLOCKS]->()
                RETURN r.track AS track LIMIT 1
            """, skill=recent_skill)
            rec = result2.single()
            if rec and rec["track"] in tied_tracks:
                return rec["track"]
        
        # Fallback — just return first tied track
        return tied_tracks[0]


def skill_exists(skill: str) -> bool:
    return skill in _skill_cache


def add_skill_node(skill: str, difficulty: int = None):
    with driver.session() as session:
        if difficulty is not None:
            session.run(
                "MERGE (s:Skill {name: $name}) SET s.difficulty = $difficulty",
                name=skill, difficulty=difficulty
            )
        else:
            session.run(
                "MERGE (s:Skill {name: $name})",
                name=skill
            )


def _relationship_cycle_exists(from_skill: str, to_skill: str) -> bool:
    """
    Check if reverse edge (to_skill → from_skill) already exists.
    Prevents cycles like Python → Django → Python.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Skill {name: $to_skill})-[:UNLOCKS]->(b:Skill {name: $from_skill})
            RETURN COUNT(*) AS cnt
        """, to_skill=to_skill, from_skill=from_skill)
        return result.single()["cnt"] > 0


def add_relationship(from_skill: str, to_skill: str, track: str, reason: str, difficulty: int = None):
    # Prevent self-loops
    if from_skill == to_skill:
        return

    # Prevent cycles
    if _relationship_cycle_exists(from_skill, to_skill):
        return

    # Track is normalized and validated before this function is called

    with driver.session() as session:
        session.run(
            """
            MERGE (a:Skill {name: $from_skill})
            MERGE (b:Skill {name: $to_skill})
            SET b.difficulty = CASE
                WHEN b.difficulty IS NULL AND $difficulty IS NOT NULL THEN $difficulty
                ELSE b.difficulty
            END
            MERGE (a)-[r:UNLOCKS]->(b)
            SET r.track = $track, r.reason = $reason
            """,
            from_skill=from_skill,
            to_skill=to_skill,
            track=track,
            reason=reason,
            difficulty=difficulty
        )