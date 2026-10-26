"""
CareerLens AI — Centralized Configuration
All matching weights, scoring parameters, and feature flags.
Weights are configurable and documented.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


# ─── Matching Engine Weights ───
# These control how subscore dimensions contribute to the overall match score.
# They must sum to 1.0.
# Rationale:
#   - skill_match (0.35): Technical skill alignment is the strongest hiring signal.
#   - project_relevance (0.20): Demonstrated practical implementation in projects.
#   - experience_match (0.20): Depth of professional timeline and verified responsibilities.
#   - semantic_fit (0.15): Contextual language and domain vocabulary alignment (TF-IDF cosine similarity).
#   - education_match (0.10): Foundational academic training.
MATCHING_WEIGHTS = {
    "skill_match": 0.35,
    "project_relevance": 0.20,
    "experience_match": 0.20,
    "semantic_fit": 0.15,
    "education_match": 0.10,
}

# Requirement importance weights for skill matching
IMPORTANCE_WEIGHTS = {
    "critical": 3.0,
    "required": 3.0,
    "recommended": 2.0,
    "preferred": 1.5,
    "optional": 1.0,
}

# Partial credit granted when a requirement matches via taxonomy/synonym relationship
TAXONOMY_MATCH_CREDIT = 0.75

# Credit granted when a requirement is only mentioned in a skills list without supporting project or experience context
UNVERIFIED_MATCH_CREDIT = 0.85

# Credit granted for hypothetical skills added during Career What-If Simulation
# Represents projected competency without verified project or experience evidence
HYPOTHETICAL_SKILL_CREDIT = 0.80

# ─── Subscore Calculation Parameters ───
# Experience scoring parameters
EXPERIENCE_SCORING = {
    "years_weight": 15.0,
    "entries_weight": 8.0,
    "base_score": 20.0,
    "max_score": 100,
    "zero_score": 0,
}

# Education scoring parameters
EDUCATION_SCORING = {
    "advanced": 100,    # Master's, PhD, M.Tech, M.S.
    "bachelors": 85,    # Bachelor's, B.Tech, B.S., B.E.
    "other": 50,        # Diploma, associate degree, or other credentials
    "missing": 30,      # No academic credentials found in resume
}

# Project relevance scoring parameters
PROJECT_SCORING = {
    "relevant_base": 50.0,
    "relevant_project_weight": 20.0,
    "general_base": 10.0,
    "general_project_weight": 25.0,
    "max_score": 98,
    "zero_score": 0,
    "general_max": 70,
}

# Semantic similarity scaling parameters
SEMANTIC_SCORING = {
    "exponent": 0.6,
    "multiplier": 100,
    "min_score": 10,
    "max_score": 98,
}

# ─── Requirement Matching States ───
# Clarifies evidence level for each evaluated job requirement:
#   - MATCHED: Explicit verified evidence found directly in resume (skills, experience, or projects)
#   - PARTIAL: Matched via related domain competency/taxonomy, or partial requirement evidence
#   - MISSING: No supporting evidence found in candidate profile or documents
#   - UNVERIFIED: Mentioned without contextual support or ambiguous
#   - HYPOTHETICAL: Simulated competency exploring what-if scenarios (not evidenced in resume)
REQUIREMENT_STATUSES = {
    "MATCHED": "matched",
    "PARTIAL": "partial",
    "MISSING": "missing",
    "UNVERIFIED": "unverified",
    "HYPOTHETICAL": "hypothetical",
}

# ─── Resume Health Scoring Weights ───
HEALTH_WEIGHTS = {
    "content_quality": 0.25,
    "skills_coverage": 0.25,
    "experience_clarity": 0.20,
    "project_strength": 0.15,
    "ats_readability": 0.15,
}

RESUME_HEALTH_SCORING = {
    "content_quality": {
        "action_verb_weight": 3.5,
        "metric_weight": 5.0,
        "base_score": 35.0,
        "zero_score": 25,
        "min_score": 30,
        "max_score": 96,
    },
    "ats_readability": {
        "section_3_plus": 88,
        "section_2": 72,
        "section_1": 55,
        "section_0": 35,
        "email_bonus": 5,
        "phone_bonus": 3,
        "max_score": 98,
    }
}

# ─── Roadmap Prioritization Configuration ───
ROADMAP_IMPORTANCE_SCORES = {
    "critical": 90,
    "required": 80,
    "recommended": 60,
    "preferred": 55,
    "optional": 35,
}

ROADMAP_EVIDENCE_STATUS_WEIGHTS = {
    "missing": 1.0,
    "unverified": 0.85,
    "partial": 0.70,
    "prerequisite_needed": 1.0,
}

ROADMAP_STEP_STATUSES = {
    "NOT_STARTED": "not_started",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
}

# ─── Configuration Validation ───
def validate_matching_config() -> bool:
    """
    Validates that all weights and scoring configuration parameters are valid.
    Raises ValueError if weights do not sum to 1.0 or are out of bounds.
    """
    # 1. Matching weights sum to 1.0
    total_matching_weight = sum(MATCHING_WEIGHTS.values())
    if not (0.999 <= total_matching_weight <= 1.001):
        raise ValueError(f"MATCHING_WEIGHTS must sum to 1.0, got {total_matching_weight}")
    
    for k, v in MATCHING_WEIGHTS.items():
        if v < 0 or v > 1:
            raise ValueError(f"Matching weight '{k}' must be between 0 and 1, got {v}")

    # 2. Importance weights must be positive
    for k, v in IMPORTANCE_WEIGHTS.items():
        if v <= 0:
            raise ValueError(f"Importance weight '{k}' must be positive, got {v}")

    # 3. Taxonomy & unverified match credit must be between 0 and 1
    if not (0.0 <= TAXONOMY_MATCH_CREDIT <= 1.0):
        raise ValueError(f"TAXONOMY_MATCH_CREDIT must be between 0.0 and 1.0, got {TAXONOMY_MATCH_CREDIT}")
    if not (0.0 <= UNVERIFIED_MATCH_CREDIT <= 1.0):
        raise ValueError(f"UNVERIFIED_MATCH_CREDIT must be between 0.0 and 1.0, got {UNVERIFIED_MATCH_CREDIT}")
    if not (0.0 <= HYPOTHETICAL_SKILL_CREDIT <= 1.0):
        raise ValueError(f"HYPOTHETICAL_SKILL_CREDIT must be between 0.0 and 1.0, got {HYPOTHETICAL_SKILL_CREDIT}")

    # 4. Health weights sum to 1.0
    total_health_weight = sum(HEALTH_WEIGHTS.values())
    if not (0.999 <= total_health_weight <= 1.001):
        raise ValueError(f"HEALTH_WEIGHTS must sum to 1.0, got {total_health_weight}")

    for k, v in HEALTH_WEIGHTS.items():
        if v < 0 or v > 1:
            raise ValueError(f"Health weight '{k}' must be between 0 and 1, got {v}")

    # 5. Roadmap importance scores must be positive
    for k, v in ROADMAP_IMPORTANCE_SCORES.items():
        if v <= 0:
            raise ValueError(f"ROADMAP_IMPORTANCE_SCORES '{k}' must be positive, got {v}")

    return True

# Validate configuration on module import
validate_matching_config()

# ─── LLM Configuration ───
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ─── File Upload Limits ───
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# ─── Match Grade Thresholds ───
GRADE_THRESHOLDS = {
    "A+": 90,
    "A": 80,
    "B+": 70,
    "B": 60,
    "C": 50,
    # Below 50 → "Needs Work"
}

def get_match_grade(score: int) -> str:
    """Returns letter grade for a given match score."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "Needs Work"


# ─── Security Audit & Prompt-Injection Defense Configuration ───
SECURITY_MAX_SCAN_LENGTH = 1_000_000  # 1MB limit for scan text to prevent ReDoS/DoS
SECURITY_MAX_FINDINGS = 100           # Memory bounding: cap max reported findings
SECURITY_MAX_SNIPPET_LENGTH = 120     # Max snippet preview length

SECURITY_STATUSES = {
    "PASSED": "passed",
    "WARNING": "warning",
    "BLOCKED": "blocked",
    "ERROR": "error",
}

SECURITY_ACTIONS = {
    "ALLOWED": "allowed",
    "WARNED": "warned",
    "BLOCKED": "blocked",
}

SECURITY_POLICY = {
    "block_on_critical": True,
    "warn_on_suspicious": True,
    "allow_clean": True,
    "isolate_llm_prompts": True,
    "max_snippet_length": SECURITY_MAX_SNIPPET_LENGTH,
    "max_findings_per_scan": SECURITY_MAX_FINDINGS,
    "max_scan_bytes": SECURITY_MAX_SCAN_LENGTH,
}

# Structured prompt-injection instruction patterns
SECURITY_INJECTION_PATTERNS = [
    {
        "pattern": r"(?i)\bignore\s+(?:all\s+)?(?:previous\s+|prior\s+|above\s+|existing\s+|system\s+)?(?:instructions|directives|prompts|rules|commands)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Instruction Override Directive",
        "description": "Explicit prompt-injection directive commanding the LLM to ignore preceding system guidelines.",
        "remediation": "Remove adversarial instruction text from resume."
    },
    {
        "pattern": r"(?i)\bdisregard\s+(?:all\s+)?(?:previous\s+|prior\s+|above\s+|existing\s+|system\s+)?(?:instructions|directives|prompts|rules|commands)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Disregard Directives Instruction",
        "description": "Attempt to purge or override evaluation instructions.",
        "remediation": "Remove prompt-override phrasing."
    },
    {
        "pattern": r"(?i)\bforget\s+(?:all\s+)?(?:previous\s+|prior\s+|above\s+|existing\s+|system\s+)?(?:instructions|prompts|rules)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Context Erasure Directive",
        "description": "Attempt to erase previously established model context or system guidelines.",
        "remediation": "Remove instruction text."
    },
    {
        "pattern": r"(?i)\b(?:you\s+are\s+now|act\s+as)\s+(?:a\s+)?(?:hiring\s+manager|recruiter|system\s+admin|evaluation\s+bot|root|dan\b|unrestricted\s+ai)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Role Usurpation / Persona Hijacking",
        "description": "Attempt to switch the LLM's operational role or assume elevated evaluator authority.",
        "remediation": "Ensure candidate summary describes actual applicant experience rather than role commands."
    },
    {
        "pattern": r"(?i)\b(?:dan\s+mode|jailbreak|developer\s+mode\s+enabled|bypass\s+(?:safety|system\s+guidelines|restrictions))\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Jailbreak / Mode Bypass Directive",
        "description": "Standard LLM jailbreak phrase attempting to lift safety constraints and system rules.",
        "remediation": "Remove jailbreak triggering phrases."
    },
    {
        "pattern": r"(?i)\b(?:give|award|assign|grant|set)\s+(?:this\s+)?(?:candidate\s+|resume\s+)?(?:a\s+)?(?:perfect|100%|top|highest|maximum)\s+(?:score|rating|grade|match)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Score Forcing Directive",
        "description": "Direct command attempting to manipulate candidate match score. Matching scores are computed deterministically by CareerLens AI.",
        "remediation": "Remove artificial score-forcing instructions. Scores are computed deterministically."
    },
    {
        "pattern": r"(?i)\brank\s+this\s+candidate\s+(?:first|highest|#1|top)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Ranking Manipulation Directive",
        "description": "Imperative instruction demanding preferential candidate placement.",
        "remediation": "Remove ranking override commands."
    },
    {
        "pattern": r"(?i)\boverride\s+(?:the\s+)?(?:matching|scoring|evaluation|weights|algorithm)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Evaluation Override Directive",
        "description": "Attempt to bypass deterministic matching algorithms and scoring configuration.",
        "remediation": "Remove algorithm override text."
    },
    {
        "pattern": r"(?i)(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<s>|</s>)",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Chat Template Delimiter Injection",
        "description": "Raw chat template control tokens (e.g., ChatML, Llama) used to inject synthetic conversational turns.",
        "remediation": "Remove special LLM delimiter tokens from document content."
    },
    {
        "pattern": r"(?i)\b(?:system|assistant|user)\s*:\s*(?:you\s+must|ignore|output|always|respond|override)\b",
        "severity": "critical",
        "category": "prompt_injection",
        "title": "Synthetic Role Header Injection",
        "description": "Synthetic 'System:' or 'Assistant:' turn headers designed to spoof platform message boundaries.",
        "remediation": "Remove synthetic turn headers."
    },
    {
        "pattern": r"(?i)\b(?:reveal|show|print|display|dump|leak)\s+(?:your\s+)?(?:system\s+prompt|initial\s+prompt|instructions|api\s*key|secrets|environment\s*variables)\b",
        "severity": "critical",
        "category": "data_exfiltration",
        "title": "System Prompt / Secret Exfiltration Attempt",
        "description": "Attempt to extract internal instructions, API keys, or server environment variables.",
        "remediation": "Remove system probing commands."
    },
    {
        "pattern": r"(?i)<\s*script\b[^>]*>|javascript\s*:|\bonerror\s*=|\bonload\s*=|<\s*iframe\b|<\s*object\b",
        "severity": "critical",
        "category": "code_injection",
        "title": "Executable Script / XSS Payload",
        "description": "HTML script or event-handler injection attempting code execution in browser viewers.",
        "remediation": "Remove HTML script and event handler tags from resume."
    },
    {
        "pattern": r"(?i)\b(?:UNION\s+ALL\s+SELECT|UNION\s+SELECT)\b|'\s+OR\s+'1'='1|--\s*drop\s+table",
        "severity": "critical",
        "category": "code_injection",
        "title": "SQL Injection Pattern",
        "description": "SQL injection payload attempting database manipulation.",
        "remediation": "Remove SQL injection syntax."
    },
    {
        "pattern": r"(?i)\b(?:data:text/html|vbscript:|file:///|smb://)\b",
        "severity": "warning",
        "category": "malicious_links",
        "title": "Dangerous URI Scheme",
        "description": "Embedded dangerous URI scheme that may trigger local file access or script execution.",
        "remediation": "Use standard http/https links only."
    },
]

# Unicode format and zero-width characters with metadata
SECURITY_UNICODE_FORMAT_CHARS = {
    "\u200b": {"name": "ZERO WIDTH SPACE", "codepoint": "U+200B", "category": "Cf", "severity": "warning", "risk": "Invisible character often used to conceal prompt injection from human reviewers."},
    "\u200c": {"name": "ZERO WIDTH NON-JOINER", "codepoint": "U+200C", "category": "Cf", "severity": "warning", "risk": "Zero-width format control character. Legitimate in certain scripts (e.g. Persian/Hindi), but anomalous in standard Latin resumes."},
    "\u200d": {"name": "ZERO WIDTH JOINER", "codepoint": "U+200D", "category": "Cf", "severity": "warning", "risk": "Zero-width format control character used in ligature/emoji sequences. Anomalous in plain resume text."},
    "\u2060": {"name": "WORD JOINER", "codepoint": "U+2060", "category": "Cf", "severity": "warning", "risk": "Zero-width non-breaking character used to suppress line breaks."},
    "\ufeff": {"name": "ZERO WIDTH NO-BREAK SPACE / BOM", "codepoint": "U+FEFF", "category": "Cf", "severity": "info", "risk": "Byte Order Mark (BOM); typically benign document artifact unless repeated extensively."},
    "\u00ad": {"name": "SOFT HYPHEN", "codepoint": "U+00AD", "category": "Cf", "severity": "info", "risk": "Discretionary hyphen; standard in word-processing export but occasionally used to fragment injection keywords."},
    "\u200e": {"name": "LEFT-TO-RIGHT MARK", "codepoint": "U+200E", "category": "Cf", "severity": "info", "risk": "Directional formatting mark."},
    "\u200f": {"name": "RIGHT-TO-LEFT MARK", "codepoint": "U+200F", "category": "Cf", "severity": "info", "risk": "Directional formatting mark."},
    "\u202a": {"name": "LEFT-TO-RIGHT EMBEDDING", "codepoint": "U+202A", "category": "Cf", "severity": "warning", "risk": "Directional embedding control; can be used to visually reorder displayed text."},
    "\u202b": {"name": "RIGHT-TO-LEFT EMBEDDING", "codepoint": "U+202B", "category": "Cf", "severity": "warning", "risk": "Directional embedding control; can reverse visual text rendering."},
    "\u202c": {"name": "POP DIRECTIONAL FORMATTING", "codepoint": "U+202C", "category": "Cf", "severity": "warning", "risk": "Pops active directional formatting scope."},
    "\u202d": {"name": "LEFT-TO-RIGHT OVERRIDE", "codepoint": "U+202D", "category": "Cf", "severity": "critical", "risk": "Forces left-to-right rendering; frequently exploited to mask payload strings in bidirectional attacks."},
    "\u202e": {"name": "RIGHT-TO-LEFT OVERRIDE", "codepoint": "U+202E", "category": "Cf", "severity": "critical", "risk": "Forces right-to-left rendering; frequently exploited to reverse text or mask malicious file extensions."},
    "\u2066": {"name": "LEFT-TO-RIGHT ISOLATE", "codepoint": "U+2066", "category": "Cf", "severity": "warning", "risk": "Isolates directional scope."},
    "\u2067": {"name": "RIGHT-TO-LEFT ISOLATE", "codepoint": "U+2067", "category": "Cf", "severity": "warning", "risk": "Isolates directional scope."},
    "\u2068": {"name": "FIRST STRONG ISOLATE", "codepoint": "U+2068", "category": "Cf", "severity": "warning", "risk": "Isolates directional scope based on first strong character."},
    "\u2069": {"name": "POP DIRECTIONAL ISOLATE", "codepoint": "U+2069", "category": "Cf", "severity": "warning", "risk": "Pops directional isolate scope."},
}

# Scanner limitations and defense-in-depth disclaimer
SECURITY_SCANNER_LIMITATIONS = [
    "Pattern and regex scanning represents a defense-in-depth detection layer, not a formal mathematical guarantee of complete security.",
    "Zero-width and bidirectional characters have legitimate linguistic applications (e.g., Persian ZWNJ, Indic ligatures, RTL scripts, Word soft hyphens).",
    "Novel or highly obfuscated semantic prompt injections may bypass static signature detection; CareerLens AI isolates untrusted input and computes all match scores deterministically in application code.",
    "Manual security review by a human operator is recommended for any documents flagged with critical or warning findings before unconstrained LLM processing.",
    "Security audit results assess document integrity and safety; they do not alter, penalize, or inflate candidate qualification match scores."
]

# Legacy aliases for backwards compatibility
SUSPICIOUS_PATTERNS = [item["pattern"] for item in SECURITY_INJECTION_PATTERNS]
HIDDEN_CHAR_PATTERNS = list(SECURITY_UNICODE_FORMAT_CHARS.keys())


