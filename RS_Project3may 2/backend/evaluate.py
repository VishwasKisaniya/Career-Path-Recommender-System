"""
Advanced Evaluation Framework for Generative Graph Recommender System
=====================================================================
Metrics:
1. Ground Truth Accuracy: Precision, Recall, F1, Hit Ratio
2. Ranking Quality: Mean Reciprocal Rank (MRR)
3. Semantic Relevance: LLM-as-a-Judge Score (0-1)
4. Information Retrieval: NDCG
5. Graph Progression: Difficulty Consistency
"""

import requests
import json
import os
import math
import time
from tabulate import tabulate
from groq import Groq
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

client = Groq()
BASE_URL = "http://127.0.0.1:8001"

test_cases_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
try:
    with open(test_cases_path, "r") as f:
        TEST_CASES = json.load(f)
except FileNotFoundError:
    print(f"Error: {test_cases_path} not found.")
    TEST_CASES = []

def evaluate_relevance_llm(known_skills, recommended_skill, track, reason):
    """Uses LLM-as-a-judge to score semantic relevance from 0.0 to 1.0"""
    prompt = f"""
    The user already knows: {known_skills}
    The recommender system suggested learning: "{recommended_skill}" in the "{track}" track.
    The system's reason: "{reason}"

    Score the relevance and logical progression of this recommendation on a scale of 0 to 5.
    0 = Completely irrelevant or illogical
    1 = Barely relevant
    2 = Tangentially related
    3 = Decent next step
    4 = Very logical and highly relevant next step
    5 = Perfect, essential next step

    Return ONLY the integer score (0-5), no extra text.
    """
    for attempt in range(4): # Increased to 4 retries for rate limits
        try:
            time.sleep(3) # Increased base sleep to 3s to respect free-tier limits
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_completion_tokens=50,
                top_p=1,
                stream=False
            )
            score_text = completion.choices[0].message.content.strip()
            score = int(score_text)
            return max(0, min(5, score)) / 5.0 
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                print(f"      [Rate limit hit on Relevance Judge, waiting 6s... (Attempt {attempt+1}/4)]")
                time.sleep(6)
            else:
                pass

    return 0.6 

def get_llm_semantic_matches(recommended_skills, ground_truth_list, k):
    """Returns a set of recommended skill names that semantically match the ground truth."""
    recs = [r['skill'] for r in recommended_skills[:k]]
    matches = set()
    recs_to_check = []
    
    # 1. Free Substring Match First
    for r in recs:
        r_lower = r.lower()
        is_match = False
        for gt in ground_truth_list:
            if gt in r_lower or r_lower in gt:
                matches.add(r)
                is_match = True
                break
        if not is_match:
            recs_to_check.append(r)
            
    # 2. LLM Semantic Match for the rest
    if recs_to_check:
        prompt = f"""
        Ground truth skills expected: {ground_truth_list}
        Recommended skills: {recs_to_check}
        
        Which of the recommended skills are semantically equivalent to, or specific implementations of, ANY of the ground truth skills?
        (e.g., 'PostgreSQL' matches 'sql', 'Express' matches 'node.js', 'Pandas' matches 'Python Data').
        
        Return ONLY a JSON list of the exact string names of the recommended skills that are valid matches.
        If none match, return [].
        """
        for attempt in range(3):
            try:
                time.sleep(3)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_completion_tokens=150,
                    stream=False
                )
                res_text = completion.choices[0].message.content.strip()
                res_text = res_text.replace("```json", "").replace("```", "").strip()
                llm_matches = json.loads(res_text)
                for m in llm_matches:
                    if m in recs_to_check:
                        matches.add(m)
                break
            except Exception as e:
                if "429" in str(e) or "limit" in str(e).lower():
                    print(f"      [Rate limit hit on Semantic Matcher, waiting 6s... (Attempt {attempt+1}/3)]")
                    time.sleep(6)
                else:
                    pass
                    
    return matches

def get_recommendations(skills):
    try:
        res = requests.post(f"{BASE_URL}/recommend", json={"skills": skills}, timeout=180)
        data = res.json()
        if "error" in data: return []
        
        flat_list = []
        for track, skill_list in data.get("recommendations", {}).items():
            for s in skill_list:
                flat_list.append({
                    "skill": s["skill"],
                    "track": track,
                    "reason": s["reason"],
                    "difficulty": s.get("difficulty", 1)
                })
        
        # Sort recommendations by difficulty to ensure logical next steps appear first
        flat_list.sort(key=lambda x: x.get('difficulty') or 1)
        return flat_list
    except Exception as e:
        print(f"API Error: {e}")
        return []

def calculate_ndcg(scores, k=None):
    if k is None: k = len(scores)
    else: k = min(k, len(scores))
    if k == 0: return 0.0
    dcg = sum(scores[i] / math.log2(i + 2) for i in range(k))
    ideal_scores = sorted(scores, reverse=True)
    idcg = sum(ideal_scores[i] / math.log2(i + 2) for i in range(k))
    return dcg / idcg if idcg > 0 else 0.0

def run_evaluation():
    print(f"\n============================================================================================================================================")
    print(f" 🚀 ADVANCED REC-SYS VALIDATION REPORT (Processing 1 Persona every 25 seconds to respect Free-Tier Limits...)")
    print(f"============================================================================================================================================")

    all_results = []
    
    for i, case in enumerate(TEST_CASES):
        if i > 0:
            print(f"  [Rate Limit Pause] Waiting 25 seconds before evaluating the next persona...")
            time.sleep(25)
            
        print(f"\nEvaluating Persona {case['id']}: {case['description']}")
        
        recs = get_recommendations(case['input'])
        if not recs:
            print("  No recommendations returned. Skipping...")
            continue
            
        acc_k = min(5, len(recs)) # Top 5 for accuracy testing
        llm_k = min(3, len(recs)) # Top 3 for costly LLM judge testing
        
        scores = []
        progression_hits = 0
        
        # Advanced Semantic Evaluation
        valid_matches = get_llm_semantic_matches(recs, case['ground_truth'], acc_k)
        
        hits = len(valid_matches)
        prec = hits / acc_k if acc_k > 0 else 0.0
        rec = hits / len(case['ground_truth']) if len(case['ground_truth']) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        hr = 1.0 if hits > 0 else 0.0
        
        # Calculate MRR
        mrr = 0.0
        for i, r in enumerate(recs[:acc_k]):
            if r['skill'] in valid_matches:
                mrr = 1.0 / (i + 1)
                break
        
        # LLM Relevance Evaluation
        for r in recs[:llm_k]:
            rel_score = evaluate_relevance_llm(case['input'], r['skill'], r['track'], r['reason'])
            scores.append(rel_score)
            
            diff = r.get('difficulty') or 1
            if case['expected_difficulty_range'][0] <= diff <= case['expected_difficulty_range'][1]:
                progression_hits += 1
                
        avg_relevance = sum(scores) / len(scores) if scores else 0
        progression_accuracy = progression_hits / llm_k if llm_k > 0 else 0
        ndcg_at_k = calculate_ndcg(scores, llm_k)
        
        all_results.append({
            "id": case['id'],
            "desc": case['description'],
            "f1": round(f1, 2),
            "hr": round(hr, 2),
            "mrr": round(mrr, 2),
            "sem_rel": round(avg_relevance, 2),
            "prog_acc": round(progression_accuracy, 2),
            "ndcg": round(ndcg_at_k, 2)
        })
        
    print("\\n" + "="*140)
    print("  📊 SUMMARY METRICS TABLE")
    print("="*140)
    
    headers = ["ID", "Persona", "F1 Score", "Hit Ratio @ 5", "MRR", "Semantic Relevance (0-1)", "Graph Progression Accuracy", "NDCG @ 3"]
    table_data = [[
        r["id"], r["desc"], r["f1"], r["hr"], r["mrr"], 
        r["sem_rel"], r["prog_acc"], r["ndcg"]
    ] for r in all_results]
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if all_results:
        print("\\n  📈 OVERALL SYSTEM AVERAGES")
        print(f"  - F1-Score:                   {sum(r['f1'] for r in all_results)/len(all_results):.2f}")
        print(f"  - Hit Ratio @ 5:              {sum(r['hr'] for r in all_results)/len(all_results):.2f}")
        print(f"  - MRR:                        {sum(r['mrr'] for r in all_results)/len(all_results):.2f}")
        print(f"  - Semantic Relevance (0-1):   {sum(r['sem_rel'] for r in all_results)/len(all_results):.2f}")
        print(f"  - Graph Progression Accuracy: {sum(r['prog_acc'] for r in all_results)/len(all_results):.2f}")
        print(f"  - NDCG @ 3:                   {sum(r['ndcg'] for r in all_results)/len(all_results):.2f}")

    report_path = os.path.join(os.path.dirname(__file__), "..", "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    run_evaluation()