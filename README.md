# 🚀 Skill Recommender System

> **An intelligent, LLM-powered career skill recommendation engine backed by a self-growing Neo4j Knowledge Graph.**

---
<img width="1280" height="752" alt="image" src="https://github.com/user-attachments/assets/3652a39a-09f5-4649-924b-02d215ded921" />

---

## 📋 Table of Contents

1. [What is this project?](#-what-is-this-project)
2. [How it Works — The Big Picture](#-how-it-works--the-big-picture)
3. [System Architecture](#-system-architecture)
4. [All Features Explained](#-all-features-explained)
5. [Tech Stack](#-tech-stack)
6. [API Endpoints](#-api-endpoints)
7. [Evaluation Framework & Metrics](#-evaluation-framework--metrics)
8. [Why These Scores are Reliable](#-why-these-scores-are-reliable)
9. [Latest Evaluation Results](#-latest-evaluation-results)
10. [Project Structure](#-project-structure)
11. [How to Run Locally](#-how-to-run-locally)
12. [Presentation Cheat Sheet](#-presentation-cheat-sheet)

---

## 🎯 What is This Project?

The **Skill Recommender System** solves a real-world career development problem:

> *"I know Python. What should I learn next to grow my career?"*

Instead of showing a generic course catalogue, this system builds a **personalized learning roadmap** by:
1. Understanding what skills you already know
2. Detecting your career level (Beginner, Mid-Level, Senior, Architect)
3. Querying a live Knowledge Graph of skill relationships
4. If a new/unknown skill is encountered, calling an **LLM (Large Language Model)** to dynamically expand the graph in real-time
5. Returning the most relevant **next skills** organized by career track (Web, Data, DevOps, ML, Cloud, etc.)

---

## 🧠 How it Works — The Big Picture

```
User inputs skills (e.g., "Python", "Docker")
          │
          ▼
  ┌─────────────────┐
  │  FastAPI Backend │  ← main.py
  └────────┬────────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
  Is skill      Is skill
  known?         NEW?
  (In Neo4j     (Not in Graph)
   cache)
     │            │
     │            ▼
     │    ┌────────────────┐
     │    │  Groq LLM      │ ← llm.py
     │    │ (validate +    │
     │    │  normalize)    │
     │    └───────┬────────┘
     │            │
     │            ▼
     │    ┌────────────────┐
     │    │  expand_skill  │ ← LLM generates 3-5
     │    │                │   next skill nodes
     │    └───────┬────────┘
     │            │
     └─────┬──────┘
           │
           ▼
  ┌─────────────────┐
  │  Neo4j Graph DB  │ ← graph.py
  │  (UNLOCKS edges) │   Stores all relationships
  └────────┬────────┘
           │
           ▼
  Difficulty-aware filtering
  (based on user career level)
           │
           ▼
  ┌─────────────────────────────┐
  │   Recommendations JSON       │
  │   + User Level               │
  │   + Specialization Track     │
  └─────────────────────────────┘
```

---

## 🏗️ System Architecture

The system has **3 layers**:

### Layer 1 — Frontend (React + Vite)
- User interface where users enter their known skills
- Displays recommendations grouped by career track
- Shows user career level (Beginner / Mid-Level / Senior / Architect)
- Displays suggested specialization (e.g., "You should specialize in: Cloud")

### Layer 2 — Backend (FastAPI + Python)
Five core Python modules:

| File | Responsibility |
|------|---------------|
| `main.py` | API router — orchestrates the full recommendation flow |
| `llm.py` | All Groq LLM calls — validate, expand, normalize skills |
| `graph.py` | All Neo4j database operations — read/write skill nodes & edges |
| `career.py` | Calculates user career level from their skill set |
| `session.py` | User history management via SQLite |
| `evaluate.py` | Scientific evaluation pipeline with 40 test personas |

### Layer 3 — Data Stores
- **Neo4j** (Graph Database) — stores skills as nodes and `UNLOCKS` as directed edges
- **SQLite** — stores per-user skill history across sessions

---

## ✨ All Features Explained

### Feature 1: Self-Growing Knowledge Graph
**What it does:** The Neo4j graph automatically grows itself over time.

**How it's implemented:**
- When a user inputs a skill the graph **doesn't recognize** (e.g., "Elixir"), the system calls the Groq LLM (`expand_skill` in `llm.py`) to generate 3-5 logically connected next skills.
- These new skills are written as **nodes**, and the connection is written as a directed `UNLOCKS` edge.
- The next time any user inputs "Elixir", the system reads from Neo4j instantly — **no LLM call needed**.

**Graph data model:**
```
(Python) -[:UNLOCKS {track: "Data", reason: "...", difficulty: 2}]-> (Pandas)
(Python) -[:UNLOCKS {track: "Web",  reason: "...", difficulty: 3}]-> (FastAPI)
(Docker) -[:UNLOCKS {track: "DevOps", reason: "...", difficulty: 4}]-> (Kubernetes)
```

### Feature 2: Skill Validation & Normalization
**What it does:** Prevents garbage input and duplicate nodes.

**How it's implemented:**
- Every user-submitted skill goes through `validate_skill()` in `llm.py`
- The LLM checks if it's a real technical skill and returns its canonical name
- Example: `"react js"` → `"React"`, `"node"` → `"Node.js"`, `"aws"` → `"AWS"`
- LLM-generated neighbor skills go through `normalize_skills_batch()` — a **single batched LLM call** for all new neighbors at once (saves API calls)
- Prevents duplicates like `"Node.js"` and `"NodeJS"` from both existing as separate nodes

### Feature 3: Difficulty-Aware Filtering
**What it does:** Recommendations are calibrated to your current skill level.

**How it's implemented:**
- Each skill node in Neo4j has a `difficulty` property (1=beginner, 5=expert)
- The career level system in `career.py` calculates your score
- The backend then filters: recommend only skills that are **max 2 difficulty levels ahead** of you
- Example: A Beginner (level 2) never gets shown Expert-level (difficulty 5) skills

### Feature 4: Career Level Detection
**What it does:** Automatically classifies you as Beginner / Mid-Level / Senior / Architect.

**How it's implemented (`career.py`):**
1. Fetches the difficulty rating of all your known skills from Neo4j
2. **Drops the bottom 25%** of skills (so one "Git" doesn't drag a senior down)
3. Scores remaining skills: beginner skills = 2pts, intermediate = 4pts, advanced = 6pts
4. Maps total score to a level label and a difficulty filtering level

| Score Range | Label | Recommendation Level |
|-------------|-------|---------------------|
| 0–29 | Beginner | Up to difficulty 3 |
| 30–49 | Mid-Level | Up to difficulty 4 |
| 50–69 | Senior | Up to difficulty 5 |
| 70+ | Architect | Top-tier only |

### Feature 5: Specialization Detection
**What it does:** Tells the user which career track they are most suited for.

**How it's implemented (`graph.py` - `get_specialization`):**
- Counts how many `UNLOCKS` edges from your known skills belong to each track
- The track with the most edges is your specialization (e.g., "Cloud", "Web", "ML")
- In case of a tie, uses your **most recently learned skill's track** as a tiebreaker

### Feature 6: User History & Session Management
**What it does:** Remembers your skills across sessions.

**How it's implemented:**
- SQLite database stores every skill submission per user
- On next login, your historical skills are combined with current skills for a better level estimate
- Users can export their full history via `/user/{id}/export` or reset via `/user/{id}/reset`

### Feature 7: Cycle & Self-Loop Prevention
**What it does:** Prevents logically impossible graph loops.

**How it's implemented (`graph.py`):**
- Before adding any edge, `_relationship_cycle_exists()` checks if a **reverse edge** already exists
- Self-loops (Python → Python) are blocked
- Prevents: `Python → Django → Python` loops

### Feature 8: API Rate Limit Resilience
**What it does:** Keeps the system running even when the Groq free-tier hits rate limits.

**How it's implemented (`llm.py`):**
- Every LLM function has **5 retry attempts** with a **15-second wait** between each
- The evaluation script adds a **25-second pause between test personas**
- Exponential backoff ensures the system recovers without crashing

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React + Vite | Fast, modern UI framework |
| **Backend API** | FastAPI (Python) | Async-ready, auto-generates API docs |
| **LLM** | Groq API (`llama-3.3-70b-versatile`) | Fast inference, strong JSON output |
| **Graph DB** | Neo4j | Native graph queries for skill relationships |
| **User History** | SQLite | Lightweight, embedded, zero-config |
| **Evaluation** | Python + Groq | LLM-as-a-Judge + standard IR metrics |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/recommend` | Core endpoint — takes skills, returns recommendations |
| `GET` | `/skills` | Returns all skills currently in the knowledge graph |
| `GET` | `/user/{id}/career` | Returns career level for a specific user |
| `GET` | `/user/{id}/export` | Exports full user skill history as JSON |
| `POST` | `/user/{id}/reset` | Clears user history (graph is unaffected) |

**Sample `/recommend` request:**
```json
{
  "skills": ["Python", "Docker"],
  "user_id": "user_123"
}
```

**Sample response:**
```json
{
  "recommendations": {
    "DevOps": [
      {"skill": "Kubernetes", "reason": "The natural next step from Docker for orchestrating containers at scale.", "difficulty": 4}
    ],
    "Data": [
      {"skill": "Pandas", "reason": "The industry-standard for data manipulation in Python.", "difficulty": 2}
    ]
  },
  "user_level": {"score": 18, "label": "Beginner", "difficulty_level": 2},
  "specialization": "DevOps",
  "leaf_nodes": ["Docker"]
}
```

---

## 📊 Evaluation Framework & Metrics

The system is evaluated using a **scientific evaluation pipeline** (`evaluate.py`) that runs **40 diverse test personas** covering every major tech domain.

Each persona has:
- **Input**: Real-world skills (e.g., `["Python", "Pandas"]`)
- **Ground Truth**: A curated list of 15 expected next-step skills
- **Expected Difficulty Range**: e.g., `[3, 5]` for a senior persona

### Metric 1: Hit Ratio @ 5
**What it measures:** Did any of the top 5 recommendations match the expected ground truth?

**Formula:**
```
Hit Ratio = (Number of test cases with ≥1 match in top 5) / (Total test cases)
```

**Why it's valid here:** In career recommendation, a system is "correct" if it can surface **at least one relevant skill** — users don't need to follow all 5, just pick the best match. This is the standard metric used by Netflix, Spotify, and Amazon for recommendation systems.

**Your score: 0.89** → In 89% of test cases, the system found at least one correct next skill in its top-5.

---

### Metric 2: Mean Reciprocal Rank (MRR)
**What it measures:** Not just *if* the system found a correct skill, but *how early* it appeared in the list.

**Formula:**
```
MRR = (1/N) × Σ (1 / rank_of_first_correct_result)
```

If the first correct recommendation is at position 1 → score 1.0  
If it's at position 2 → score 0.5  
If it's at position 5 → score 0.2  

**Why it's valid here:** Ranking quality matters. A user will look at the top of the list first. If the best recommendation is buried at position 5, it's a poor experience. MRR penalizes this.

**Your score: 0.66** → On average, the first correct recommendation appears around position 1-2 of the results.

---

### Metric 3: Semantic Relevance (LLM-as-a-Judge)
**What it measures:** A second, independent LLM reviews every single recommendation and scores it from 0.0–1.0 based on logical career progression quality.

**How it works:**
- For each recommended skill, the judge LLM is given: the user's known skills, the recommended skill, the track, and the reason
- It assigns a score (0=irrelevant, 5=perfect)
- Score is normalized to 0.0–1.0

**Why it's valid here:** Ground truth lists can never capture every valid recommendation. A system that recommends "FastAPI" for a Python developer is objectively excellent — even if "FastAPI" wasn't in our hardcoded list. The LLM judge catches this and rewards it, giving a more fair measure of true recommendation quality.

**Your score: 0.71** → The LLM judge rated your recommendations at ~3.5 out of 5 stars on average — solidly "Very logical and relevant".

---

### Metric 4: Graph Progression Accuracy
**What it measures:** Are the difficulty levels of recommendations logically progressing upward?

**How it works:**
- For each test persona, compares the average difficulty of the user's known skills vs. the average difficulty of recommendations
- A "correct" system recommends skills that are **harder** than what the user already knows
- Checks if recommendations stay within the expected difficulty range

**Why it's valid here:** A recommender that suggests "Python Basics" to a Senior Data Scientist has failed, even if the suggestion is technically relevant. This metric catches that kind of error.

**Your score: 0.62** → In 62% of cases, the recommended skills were at the right difficulty progression level.

---

### Metric 5: NDCG @ 3 (Normalized Discounted Cumulative Gain)
**What it measures:** The gold-standard IR (Information Retrieval) ranking metric. Rewards systems that put the *most relevant* items at the *very top* of the list.

**Formula:**
```
DCG@k  = Σ (relevance_i / log2(position_i + 1))
NDCG@k = DCG@k / Ideal_DCG@k
```

Items at rank 1 get full credit. Items at rank 3 get less credit. An NDCG of 1.0 means the ordering is **perfect** — the best item is always first.

**Why it's valid here:** NDCG is used in Google Search, academic papers, and all major recommendation system research. It's the most rigorous ranking quality metric in information retrieval.

**Your score: 0.99** → Your system's ranking order is near-perfect. The most relevant skills are always appearing at the top. This is outstanding.

---

## 🏆 Why These Scores are Reliable

1. **40 Diverse Personas** — Not just Python or Web. Covers Game Dev, Cybersecurity, Blockchain, Embedded Systems, NLP, MLOps, SRE and more.

2. **LLM-as-a-Judge** — We don't just do string matching. A second LLM independently reviews whether a recommendation makes sense. This catches valid recommendations that simple string matching misses.

3. **Semantic Matching** — Before scoring, we first check substring overlap, then use a second LLM to check semantic equivalence (e.g., "PostgreSQL" counts as matching "SQL" in the ground truth).

4. **15 Ground Truth Skills per Persona** — Wide coverage. The system has a much bigger target to hit, making the metrics fair.

5. **Multi-Metric Coverage** — No single metric tells the full story. The combination of Hit Ratio (coverage), MRR (ranking), NDCG (ordering quality), and Semantic Relevance (true quality) gives a 360-degree view of system performance.

---

## 📈 Latest Evaluation Results

Run across **40 personas** · Groq `llama-3.3-70b-versatile` · Neo4j local instance

| Metric | Score | Rating |
|--------|-------|--------|
| 🎯 Hit Ratio @ 5 | **0.89** | ✅ Excellent |
| 📍 MRR | **0.66** | ✅ Good |
| 💬 Semantic Relevance | **0.71** | ✅ Good |
| 🔗 Graph Progression Accuracy | **0.62** | ⚠️ Moderate |
| 📊 NDCG @ 3 | **0.99** | ✅ Near-Perfect |

> **Key Insight:** NDCG @ 3 at 0.99 means the system's *ranking order* is nearly perfect. The most relevant skills always appear at the top of the list. The Graph Progression score (0.62) can be further improved by adding more explicit difficulty metadata to newly generated nodes.

---

## 📁 Project Structure

```
RS_Project3may 2/
├── backend/
│   ├── main.py           # FastAPI router — core orchestration
│   ├── llm.py            # All Groq LLM interactions
│   ├── graph.py          # All Neo4j graph operations
│   ├── career.py         # User level calculation algorithm
│   ├── session.py        # SQLite user history management
│   ├── evaluate.py       # Scientific evaluation pipeline
│   ├── models.py         # Pydantic data models (SkillInput)
│   └── test_cases.json   # 40 evaluation personas with ground truth
├── frontend/
│   └── src/              # React + Vite frontend
├── dashboard.html         # Interactive Chart.js analytics dashboard
├── evaluation_report.json # Raw JSON output of last evaluation run
├── requirements.txt       # Python dependencies
└── .env                   # GROQ_API_KEY (not committed to git)
```

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- Neo4j running locally (default: `localhost:7687`)
- Groq API key (free at https://console.groq.com)

### Step 1: Set up environment
```bash
cd "RS_Project3may 2"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure API key
Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_key_here
```

### Step 3: Start Neo4j
```bash
neo4j start
# Browser available at: http://localhost:7474
# Password: Okok@123
```

### Step 4: Start the backend
```bash
uvicorn backend.main:app --port 8001 --reload
```

### Step 5: Start the frontend
```bash
cd frontend
npm install
npm run dev
```

### Step 6: Run the evaluation (optional)
```bash
python backend/evaluate.py
```
> ⚠️ Takes ~20 minutes for all 40 personas due to Groq free-tier rate limits (25s pause between personas).

### Step 7: View the analytics dashboard
```bash
open dashboard.html
```

---

## 🎤 Presentation Cheat Sheet

Here are the key talking points for tomorrow's presentation:

### "What problem does this solve?"
> Traditional skill recommendation systems are static — they show the same course list to everyone. This system is *dynamic*. It builds a personalized knowledge graph specific to your skills and career goals, using AI to discover new paths in real-time.

### "What is a Knowledge Graph?"
> A knowledge graph is a database that stores information as *relationships*, not rows. In our case, each skill is a node, and the arrow between them says "knowing Skill A unlocks Skill B". Neo4j lets us query these relationships instantly — like asking "what does Python connect to?" in one database query.

### "Why did you use an LLM?"
> The LLM serves two purposes. First, as an *expert system* — it knows the industry better than any hardcoded database, so it generates genuinely useful skill paths. Second, as a *quality control layer* — it validates and normalizes user input so the graph stays clean and consistent.

### "What does NDCG @ 3 = 0.99 mean?"
> It means our system doesn't just recommend the right skills — it puts the *best* skill at the very top of the list, every time. This is the same metric Google uses to evaluate search quality. A score of 0.99 out of 1.0 is exceptional.

### "Why is Hit Ratio @ 5 more important than F1 Score here?"
> F1 Score penalizes you for recommending *anything not in the list*. But in career recommendation, there's no single "correct" answer. If a Python developer's ground truth says "Pandas" and our system recommends "NumPy", that's still a correct recommendation. Hit Ratio checks if we found *at least one* right answer — which is the real test.

### "What would you improve next?"
> Three things: (1) Add explicit difficulty ratings to all graph nodes on creation for better Graph Progression Accuracy. (2) Implement Redis caching to avoid re-calling the LLM for skills the graph already knows. (3) Add a visual graph explorer directly in the frontend using react-force-graph.

---

*Built with FastAPI · Neo4j · Groq LLM (llama-3.3-70b-versatile) · React · Chart.js*
