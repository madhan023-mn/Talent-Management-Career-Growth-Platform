from __future__ import annotations
import os
import json
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# List of Gemini models in order of priority
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

def get_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieves Gemini API key from parameter, environment, or .env file."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key if key else None

def call_gemini_api(
    prompt: str,
    system_instruction: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Dict[str, Any]:
    """
    Calls the Google Gemini REST API using requests.
    Supports automatic model fallback and handles errors gracefully.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        return {
            "success": False,
            "text": "",
            "error": "No Gemini API key provided. Set GEMINI_API_KEY in .env or provide it in the UI.",
            "model_used": None
        }

    headers = {"Content-Type": "application/json"}
    
    payload: Dict[str, Any] = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    last_error = ""
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text:
                            return {
                                "success": True,
                                "text": text.strip(),
                                "error": None,
                                "model_used": model
                            }
                except (KeyError, IndexError) as parse_err:
                    last_error = f"Response parsing error: {parse_err}"
            elif resp.status_code == 404:
                # Model name not found on this endpoint version, try next model
                last_error = f"Model {model} returned 404, attempting fallback..."
                continue
            elif resp.status_code == 400:
                # Bad request, check message
                err_detail = resp.json().get("error", {}).get("message", resp.text)
                return {
                    "success": False,
                    "text": "",
                    "error": f"Gemini API Error (400): {err_detail}",
                    "model_used": model
                }
            elif resp.status_code in (401, 403):
                err_detail = resp.json().get("error", {}).get("message", "Invalid API key or unauthorized.")
                return {
                    "success": False,
                    "text": "",
                    "error": f"Gemini API Auth Error ({resp.status_code}): {err_detail}",
                    "model_used": model
                }
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text}"
        except requests.RequestException as req_err:
            last_error = f"Network connection error: {req_err}"

    return {
        "success": False,
        "text": "",
        "error": last_error or "Unable to reach Gemini API.",
        "model_used": None
    }

def generate_ai_coaching_guidance(
    user_name: str,
    question: str,
    profile: Dict[str, Any],
    skills: List[Dict[str, Any]],
    target_role: str,
    gap_data: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates tailored, high-impact executive career strategy advice.
    Uses Gemini when key is present; returns rule-based fallback when offline.
    """
    key = get_gemini_api_key(api_key)
    
    # Format skills summary
    skills_summary = ", ".join(f"{s['name']} ({s.get('proficiency', 'Intermediate')})" for s in skills) if skills else "No skills recorded yet"
    gaps_summary = ", ".join(f"{g['skill']} (Gap: -{g['gap']}, Priority: {g['priority']})" for g in gap_data) if gap_data else "No critical gaps identified"
    
    system_prompt = (
        "You are an Elite Executive Career Strategist and Chief People Officer mentor at a top tech enterprise. "
        "Your task is to provide rigorous, actionable, highly personalized career progression plans for professionals. "
        "Structure your response cleanly with clear headings, crisp bullet points, and specific timelines (30/60/90 days). "
        "Avoid generic corporate platitudes. Provide concrete technical architectures, leadership habits, and measurable KPIs."
    )

    user_prompt = f"""
Employee Profile:
- Name: {user_name}
- Current Job Title: {profile.get('job_title') or 'Not specified'}
- Department / Industry: {profile.get('department') or 'Technology'} / {profile.get('industry') or 'Software'}
- Years of Experience: {profile.get('years_experience') or 0} years
- Target Role: {target_role or 'Senior Engineer'}
- Current Recorded Skills: {skills_summary}
- Identified Skill Gaps against Target Role: {gaps_summary}
- Career Growth Aspirations: {profile.get('career_goal') or 'Advance technically and lead high-impact initiatives'}

Employee's Specific Question or Challenge:
"{question}"

Please provide a tailored Strategic Career Blueprint covering:
1. **Executive Posture & Position Assessment**: Analysis of where the candidate stands relative to the target role.
2. **Prioritized Skill Gap Closure Plan (30-60-90 Days)**: Specific technical, architectural, and domain learning actions.
3. **High-Leverage Career Moves & Project Visibility**: How to earn leadership trust, drive architecture decisions, and document business impact.
4. **Measurable Success Metrics for the Next Review Cycle**: Concrete KPIs, deliverables, and artifacts to bring to the promotion table.
"""

    if key:
        res = call_gemini_api(user_prompt, system_instruction=system_prompt, api_key=key, temperature=0.6)
        if res["success"]:
            return {
                "source": "gemini",
                "model": res["model_used"],
                "content": res["text"],
                "error": None
            }
        else:
            # Fallback with error note
            offline_content = _build_rule_based_coaching(user_name, question, profile, skills, target_role, gap_data)
            return {
                "source": "offline_fallback",
                "model": None,
                "content": offline_content,
                "error": res["error"]
            }
    
    # Offline rule-based generation
    offline_content = _build_rule_based_coaching(user_name, question, profile, skills, target_role, gap_data)
    return {
        "source": "offline_rules",
        "model": None,
        "content": offline_content,
        "error": None
    }

def analyze_resume_with_ai(
    resume_text: str,
    target_role: str,
    target_skills: List[str],
    profile: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs an in-depth AI ATS Audit and Bullet Optimization on resume content.
    Returns structured analysis with score, detected keywords, missing terms, and rewritten STAR bullets.
    """
    key = get_gemini_api_key(api_key)

    system_prompt = (
        "You are an expert Technical Recruiter and ATS (Applicant Tracking System) Algorithm Specialist. "
        "Analyze the provided resume against the target role and benchmark skills. "
        "Provide your analysis in clean JSON format matching the schema specified in the user prompt."
    )

    user_prompt = f"""
Target Role: {target_role}
Target Essential Benchmark Skills: {', '.join(target_skills)}
Candidate Current Title: {profile.get('job_title', 'Not specified')}
Candidate Experience: {profile.get('years_experience', 0)} years

Resume Content to Audit:
\"\"\"
{resume_text[:4000]}
\"\"\"

Analyze the resume rigorously and return a JSON object with EXACTLY the following structure (do NOT include markdown backticks around JSON):
{{
  "ats_score": <integer from 0 to 100>,
  "alignment_summary": "<2-3 sentence executive assessment of resume strength and alignment with the target role>",
  "detected_keywords": ["<matched keyword 1>", "<matched keyword 2>", ...],
  "missing_keywords": ["<critical missing keyword 1>", "<critical missing keyword 2>", ...],
  "strong_action_verbs_found": ["<verb 1>", "<verb 2>", ...],
  "weak_phrases_to_replace": [
    {{"original": "<weak phrase from resume>", "suggested": "<high-impact replacement>"}}
  ],
  "bullet_optimizations": [
    {{
      "original_bullet": "<extract or construct an existing weak bullet from resume>",
      "rewritten_bullet": "<STAR-format bullet with action verb, metric, and clear business result>",
      "improvement_reason": "<why this rewrite passes recruiter screens>"
    }}
  ],
  "top_recommendations": [
    "<actionable advice 1>",
    "<actionable advice 2>",
    "<actionable advice 3>"
  ]
}}
"""

    if key:
        res = call_gemini_api(user_prompt, system_instruction=system_prompt, api_key=key, temperature=0.3)
        if res["success"]:
            text = res["text"].strip()
            # Clean possible markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            try:
                parsed = json.loads(text.strip())
                parsed["source"] = "gemini"
                parsed["model"] = res["model_used"]
                return parsed
            except json.JSONDecodeError:
                # Return wrapped raw text if JSON parsing failed
                return {
                    "source": "gemini_raw",
                    "model": res["model_used"],
                    "ats_score": 75,
                    "alignment_summary": text,
                    "detected_keywords": [s for s in target_skills if s.lower() in resume_text.lower()],
                    "missing_keywords": [s for s in target_skills if s.lower() not in resume_text.lower()],
                    "strong_action_verbs_found": ["Architected", "Engineered", "Deployed", "Optimized"],
                    "weak_phrases_to_replace": [],
                    "bullet_optimizations": [],
                    "top_recommendations": ["Incorporate quantified revenue or latency impact metrics into all bullet points."]
                }
    
    # Offline rule-based heuristic fallback
    return _build_rule_based_resume_audit(resume_text, target_role, target_skills, profile)

def _build_rule_based_coaching(
    user_name: str,
    question: str,
    profile: Dict[str, Any],
    skills: List[Dict[str, Any]],
    target_role: str,
    gap_data: List[Dict[str, Any]]
) -> str:
    top_skills = [s['name'] for s in skills[:3]] if skills else ["Core Software Development"]
    gaps_list = [f"{g['skill']} (priority: {g['priority']})" for g in gap_data[:4]] if gap_data else ["Continuous Integration", "System Architecture"]
    
    return f"""### 🚀 Strategic Career Blueprint for {user_name}
**Inquiry Focus:** *"{question}"*

---

#### 1. Executive Posture & Role Positioning
Your cataloged expertise reflects verified competence in **{', '.join(top_skills)}**. To achieve top-tier benchmark parity for **{target_role or 'Senior Engineer'}**, transition from individual task delivery toward system architecture ownership, technical mentorship, and business KPI stewardship.

#### 2. Prioritized 90-Day Competency Sprint
- **Days 1–30 (Foundation)**: Focus on closing foundational gaps in **{gaps_list[0] if gaps_list else 'Core Systems'}**. Build a reference implementation or proof-of-concept repository.
- **Days 31–60 (Impact)**: Champion an architectural improvement or automation pipeline in **{gaps_list[1] if len(gaps_list) > 1 else 'Cloud Infrastructure'}** within your current project workflow.
- **Days 61–90 (Leadership)**: Author an Architecture Decision Record (ADR) or technical RFC and present it to cross-functional engineering peers.

#### 3. High-Leverage Strategic Moves
- **Quantify Business Value**: Frame every achievement in terms of latency reduced, dollars saved, or engineering velocity unlocked.
- **Cross-Functional Alignment**: Partner with Product and DevOps stakeholders to solve unblocking friction across services.
- **Mentorship Multiplier**: Review junior engineers' pull requests with thoughtful architectural commentary to demonstrate lead caliber.

#### 4. Success Milestones for Your Next Review
1. Deliver at least 1 major production release with zero-downtime deployment.
2. Formally close **{len(gap_data)} identified competency gaps** through targeted self-study or certification.
3. Secure sponsor alignment with your manager on the concrete prerequisites for **{target_role or 'Senior Engineer'}**.
"""

def _build_rule_based_resume_audit(
    resume_text: str,
    target_role: str,
    target_skills: List[str],
    profile: Dict[str, Any]
) -> Dict[str, Any]:
    text_lower = (resume_text or "").lower()
    matched = [s for s in target_skills if s.lower() in text_lower]
    missing = [s for s in target_skills if s.lower() not in text_lower]
    
    score = round(100 * len(matched) / max(1, len(target_skills))) if target_skills else 70
    
    action_verbs = ["architected", "engineered", "spearheaded", "accelerated", "deployed", "optimized", "streamlined", "orchestrated", "automated", "mentored"]
    found_verbs = [v.capitalize() for v in action_verbs if v in text_lower]
    if not found_verbs:
        found_verbs = ["Developed", "Managed", "Built"]

    return {
        "source": "rule_based_engine",
        "model": None,
        "ats_score": max(35, min(95, score)),
        "alignment_summary": (
            f"Resume contains {len(matched)} of {len(target_skills)} target benchmark keywords for {target_role}. "
            "To maximize ATS pass-through rates and recruiter engagement, weave missing core technical competencies directly into quantifiable bullet points."
        ),
        "detected_keywords": matched,
        "missing_keywords": missing,
        "strong_action_verbs_found": found_verbs,
        "weak_phrases_to_replace": [
            {"original": "Responsible for managing tasks", "suggested": "Spearheaded end-to-end execution and operational delivery"},
            {"original": "Worked on bug fixes", "suggested": "Diagnosed and resolved critical production bottlenecks, reducing downtime by 35%"},
            {"original": "Helped team with deployment", "suggested": "Automated CI/CD release pipelines, accelerating deployment frequency"}
        ],
        "bullet_optimizations": [
            {
                "original_bullet": "Developed APIs and maintained backend database for user management.",
                "rewritten_bullet": f"Engineered high-throughput REST APIs and optimized SQLite/PostgreSQL schemas, reducing query latency by 42% across 10k+ active users.",
                "improvement_reason": "Applies the Google XYZ/STAR formula with strong action verb, metric, and tangible business outcome."
            },
            {
                "original_bullet": "Assisted with system monitoring and code reviews.",
                "rewritten_bullet": f"Orchestrated observability dashboards and conducted rigorous peer reviews across 50+ PRs, boosting sprint delivery velocity by 20%.",
                "improvement_reason": "Transforms passive involvement into quantifiable engineering leadership."
            }
        ],
        "top_recommendations": [
            f"Incorporate missing core keywords: {', '.join(missing[:4]) if missing else 'Distributed systems, Cloud resilience'}.",
            "Ensure every bullet point starts with a powerful action verb and concludes with a quantifiable metric (%, $, or hours saved).",
            f"Tailor your Professional Summary at the top to specifically target the '{target_role}' designation."
        ]
    }
