import yaml
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "RSprojectShilpaM")

with open("H:\RS_Project\data\skills.yaml", "r") as f:
    data = yaml.safe_load(f)

driver = GraphDatabase.driver(URI, auth=AUTH)

def create_relationship(tx, from_skill, from_diff, to_skill, to_diff, track, reason):
    query = """
    MERGE (a:Skill {name: $from_skill})
    SET a.difficulty = $from_diff
    MERGE (b:Skill {name: $to_skill})
    SET b.difficulty = $to_diff
    MERGE (a)-[:UNLOCKS {track: $track, reason: $reason}]->(b)
    """
    tx.run(query, from_skill=from_skill, from_diff=from_diff,
           to_skill=to_skill, to_diff=to_diff, track=track, reason=reason)

with driver.session() as session:
    for entry in data["skills"]:
        # In the loop:
        session.execute_write(
            create_relationship,
            entry["from"],
            entry.get("from_difficulty", 3),
            entry["to"],
            entry.get("to_difficulty", 3),
            entry["track"],
            entry["reason"]
        )
        print(f"Added: {entry['from']} --> {entry['to']} [{entry['track']}]")

print("\nDone! All skills imported into Neo4j.")
driver.close()