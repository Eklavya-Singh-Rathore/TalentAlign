"""Shared data constants for skill normalization.

Aliases, synonyms, blacklists, whitelists, cluster ontologies, bucket weights.
Pure data — no logic. Imported by every sibling sub-module in this package.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# L6 — Centralized noise blacklist (union of prior NB3 + NB8 sets)
# ---------------------------------------------------------------------------

NON_SKILL_WORDS: set = {
    # JD framing
    "hiring", "looking", "required", "preferred", "experience", "years",
    "education", "degree", "field", "related", "bachelor", "master",
    "candidate", "position", "role", "opportunity",
    # Connective / stopword-like
    "of", "in", "and", "or", "the", "a", "an", "to", "for", "with",
    "on", "at", "by", "is", "are", "we", "our", "their", "your",
    # Generic nouns that leak through
    "skills", "data", "analysis", "deep", "platforms", "team",
    "work", "tools", "strong", "good", "best", "knowledge",
    # Section labels
    "required skills", "preferred skills", "related field",
    "qualifications", "requirements", "responsibilities",
    "team player", "ability", "experience in", "knowledge of",
    "good to have", "nice to have", "must have",
    "certifications", "overview", "company", "about", "benefits",
    "perks", "salary", "date", "hands", "engineers", "implement",
    "controls", "specifications",
    "load", "e.g", "eg",
}

JD_NOISE_PHRASES: set = {
    "company overview", "role overview", "key responsibilities",
    "required qualifications", "preferred qualifications",
    "technical skills", "overview", "responsibilities",
    "qualifications", "requirements", "benefits", "perks",
    "job description", "about us", "about the role",
    "what you will do", "what we look for",
    "job title", "must have", "good to have", "nice to have",
    "compensation", "work mode", "hybrid", "remote", "onsite",
    "about the company", "minimum qualifications", "basic qualifications",
    "years of experience", "strong communication", "excellent communication",
    "or related field", "related field", "and related field",
    "about the team", "job responsibilities", "skills and capabilities",
    "maintain consistent communication", "including personal banking",
    "equal opportunity employer", "sexual orientation", "national origin",
    "race", "religion", "gender", "age", "color",
    "business requirements", "technical specifications", "strong controls",
    "bachelor s degree", "hands on experience",
    "deployment of data", "analytics technologies", "strategy to reporting",
}

SKILL_NOISE_SUBSTRINGS: List[str] = [
    "ability", "experience", "knowledge",
    "responsible", "working with", "understanding",
    "proficiency", "familiarity", "expertise",
]

JD_NOISE_SUBSTRINGS: List[str] = [
    "about the",
    "job responsibilities",
    "responsibilit",
    "equal opportunity",
    "sexual orientation",
    "national origin",
    "interpersonal",
    "communication",
    "results-driven",
    "including ",
    "maintain consistent",
]

JD_TOKEN_BLACKLIST: set = {
    "you", "your", "we", "our", "us", "them", "they", "the", "a", "an",
    "this", "that", "these", "those", "both", "regards",
    # Aggressive cleanup: pronouns/qualifiers that signal business prose.
    "their", "its", "all", "outstanding", "exceptional", "excellent", "appropriately",
}

JD_ACTION_VERBS: set = {
    "collaborate", "analyze", "design", "develop", "monitor", "provide",
    "translate", "document", "possess", "create", "creating", "eagerly",
    "maintain", "conduct", "work", "stay", "transform", "test", "understand",
    # P3patch.A: responsibility / accountability verbs (base + -ing forms)
    # that lead bullet lines in corporate JDs (e.g. Barclays "Accountabilities").
    # A genuine skill phrase virtually never starts with one of these.
    "improve", "improving", "identify", "identifying", "perform", "performing",
    "ensure", "ensuring", "build", "building", "developing", "execute",
    "executing", "manage", "managing", "support", "supporting", "demonstrate",
    "demonstrating", "allocate", "allocating", "coordinate", "coordinating",
    "communicate", "communicating", "contribute", "contributing", "deliver",
    "delivering", "drive", "driving", "lead", "leading", "supervise",
    "supervising", "guide", "guiding", "seek", "seeking", "evaluate",
    "evaluating", "review", "reviewing", "optimize", "optimise", "optimizing",
    "write", "writing", "embark", "spearhead", "take", "taking", "make",
    "making", "assess", "assessing", "check", "checking", "maintaining",
    "providing", "designing", "conducting", "collaborating", "leverage",
    "utilize", "utilise", "enable", "enabling", "owning", "own",
    # Aggressive cleanup: more responsibility/prose verbs that lead fragments.
    "assist", "assisting", "consume", "consuming", "integrate", "integrating",
    "connect", "connecting", "fulfill", "fulfilling", "fulfil", "remediate", "escalate",
}

JD_GENERIC_TAIL_TOKENS: set = {
    "team", "teams", "needs", "objectives", "products", "users", "training",
    "support", "insights", "trends", "documentation", "capabilities",
    "levels", "assignments", "timelines", "efforts", "progress", "future",
    "growth", "engagement", "history", "solutions", "businesses", "consumers",
    # Aggressive cleanup: business/soft-prose tails (team members, internal
    # partners, codes of conduct, innovation mindset, compliance obligations…).
    "members", "member", "partners", "partner", "organization", "organisation",
    "concept", "conduct", "obligations", "practices", "guidelines", "expectations",
    "responsibilities", "stakeholders", "escalation", "remediation", "disabilities",
    "peoples", "values", "mindset", "curiosity", "reasoning", "discipline",
    "awareness", "standards", "requirements", "identification", "issues", "compliance",
}

# Leading prepositions signal a sentence fragment, not a skill ("from concept").
_JD_PREPOSITION_LEADS: set = {
    "from", "of", "in", "to", "with", "by", "for", "at", "on", "into",
    "onto", "via", "across", "within", "through", "under", "over", "about",
}

TECH_SIGNAL_TOKENS: set = {
    "access", "agile", "ai", "alteryx", "amazon", "analytics",
    "api", "artificial", "aws", "azure", "bi", "cloud", "dashboard",
    "data", "database", "docker", "excel", "etl", "gcp", "google",
    "java", "javascript", "kubernetes", "machine", "microsoft", "model",
    "mongodb", "mysql", "office", "oracle", "pipeline", "postgresql",
    "power", "python", "reporting", "scikit-learn", "snowflake", "sql",
    "tableau", "tensorflow", "teradata", "visualization",
}

JD_BUCKET_WEIGHTS: Dict[str, float] = {
    "required": 1.0,
    "preferred": 0.75,
    "optional": 0.5,
}

MATCH_SCORE_BY_TYPE: Dict[str, Tuple[float, float]] = {
    "exact": (1.0, 1.0),
    "alias": (1.0, 1.0),
    "synonym": (0.9, 0.9),
    "semantic": (0.55, 0.80),
    "partial": (0.30, 0.50),
}

SKILL_SCORE_COMPONENT_WEIGHTS: Dict[str, float] = {
    "weighted_jd_coverage": 0.45,
    "avg_match_confidence": 0.35,
    "resume_pool_coverage": 0.20,
}

SKILL_CLUSTERS: Dict[str, List[str]] = {
    "python_ecosystem": ["python", "pandas", "numpy", "scipy", "matplotlib"],
    "cloud_platforms": ["aws", "azure", "gcp", "cloud computing", "google cloud platform"],
    "web_frontend": ["react", "angular", "vue", "html", "css", "javascript"],
    "databases": ["sql", "mysql", "postgresql", "mongodb", "redis"],
}

SOFT_SKILL_BLACKLIST: set = {
    "communication", "teamwork", "leadership", "problem-solving",
    "problem solving", "collaboration", "adaptability", "creativity",
    "time management", "critical thinking", "interpersonal skills",
}

SHORT_SKILL_WHITELIST: set = {
    "sql", "aws", "gcp", "api", "apis", "etl", "bi", "ui", "ux",
    "ml", "ai", "nlp", "cv", "sap", "erp", "crm", "css", "html",
}

WHITELIST_PATTERNS: List[re.Pattern] = [
    re.compile(r"^[a-z]+\+\+$"),          # C++
    re.compile(r"^[a-z]+#$"),              # C#, F#
    re.compile(r"^[a-z]+\.[a-z]+$"),       # react.js, node.js, vue.js
]


# ---------------------------------------------------------------------------
# L7 — Unified alias / normalization map
# ---------------------------------------------------------------------------

SKILL_ALIAS_MAP: Dict[str, str] = {
    # Abbreviations
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ai": "artificial intelligence",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "tf": "tensorflow",
    "k8s": "kubernetes",
    "gcp": "google cloud platform",
    "aws": "amazon web services",
    "gke": "google kubernetes engine",
    "eks": "amazon elastic kubernetes service",
    "ci/cd": "continuous integration",
    "oop": "object-oriented programming",
    "db": "database",
    "rdbms": "relational database",
    "eda": "exploratory data analysis",

    # Common variants / spellings
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "powerbi": "power bi",
    "power-bi": "power bi",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node js": "node.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "angular.js": "angular",
    "c++": "cpp",
    "c#": "csharp",
    ".net": "dotnet",
    "dot net": "dotnet",
    "tensor flow": "tensorflow",
    "py torch": "pytorch",
    "torch": "pytorch",

    # Conceptual equivalences (lightweight)
    "data wrangling": "data manipulation",
    "data cleaning": "data preprocessing",
    "etl": "data pipeline",
    "rest api": "rest",
    "restful api": "rest",
    "restful apis": "rest",
    "amazon web services": "aws",
    "google cloud": "google cloud platform",
    "google cloud services": "google cloud platform",
    "postgres sql": "postgresql",
    "mongo db": "mongodb",
    "expressjs": "express",
    "react js": "react",
    "java script": "javascript",
    "scikit learn library": "scikit-learn",

    # Frontend / backend / full-stack variants
    "frontend": "frontend development",
    "front-end": "frontend development",
    "front end": "frontend development",
    "backend": "backend development",
    "back-end": "backend development",
    "back end": "backend development",
    "full-stack": "full stack development",
    "fullstack": "full stack development",
    "full stack": "full stack development",
    "dashboarding tools": "dashboarding",
    "dashboard tools": "dashboarding",
    "rest apis": "rest",

    # Phase 1 (P1.4) — additional commonly-seen variants
    # Languages / runtimes
    "type script": "typescript",
    "java-script": "javascript",
    "html5": "html",
    "css3": "css",
    "es6": "javascript",
    "es2015": "javascript",
    "j2ee": "java",
    # JS frameworks
    "node-js": "node.js",
    "next js": "next.js",
    "nextjs": "next.js",
    "nest js": "nest.js",
    "nestjs": "nest.js",
    # SQL variants
    "ms sql": "sql server",
    "mssql": "sql server",
    "ms-sql": "sql server",
    "t-sql": "sql",
    "tsql": "sql",
    "pl/sql": "sql",
    "plsql": "sql",
    "no sql": "nosql",
    "no-sql": "nosql",
    # .NET family
    "asp.net": "dotnet",
    "asp net": "dotnet",
    ".net core": "dotnet",
    "dotnet core": "dotnet",
    # Big data / pipeline tools
    "apache spark": "spark",
    "py spark": "pyspark",
    "apache hadoop": "hadoop",
    "apache hive": "hive",
    "apache airflow": "airflow",
    "apache kafka": "kafka",
    # ML / DL aliases
    "tensor-flow": "tensorflow",
    "scikit_learn": "scikit-learn",
    "huggingface": "hugging face",
    "hf": "hugging face",
    # CSS / UI
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",
    # AI ecosystem
    "open ai": "openai",
    "lang chain": "langchain",
    "llm": "large language models",
    "llms": "large language models",
    "rag": "retrieval augmented generation",
    "genai": "generative ai",
    "gen ai": "generative ai",
    # Containers / orchestration
    "k8": "kubernetes",
    "github action": "github actions",
    # Search / observability
    "elk": "elasticsearch",
    "elk stack": "elasticsearch",
    # AWS service shorthand
    "amazon rds": "relational database",
    "amazon s3": "aws",
    "amazon ec2": "aws",
    "ddb": "dynamodb",
}


# ---------------------------------------------------------------------------
# L3 — Semantic synonym map (Phase 2)
# ---------------------------------------------------------------------------

SEMANTIC_SYNONYMS: Dict[str, List[str]] = {
    "pandas": ["data manipulation", "dataframes", "data wrangling"],
    "numpy": ["numerical computing", "numerical python", "array computing"],
    "scipy": ["scientific computing", "scientific python"],
    "matplotlib": ["data visualization", "plotting"],
    "seaborn": ["data visualization", "statistical plotting"],
    "scikit-learn": ["machine learning library", "sklearn"],
    "tensorflow": ["deep learning framework", "tf"],
    "pytorch": ["deep learning framework", "torch"],
    "keras": ["deep learning framework", "neural network library"],
    "opencv": ["computer vision library", "image processing"],

    "mongodb": ["nosql", "document database", "nosql database"],
    "postgresql": ["postgres", "relational database"],
    "mysql": ["relational database", "sql database"],
    "redis": ["in-memory database", "caching", "key-value store"],
    "elasticsearch": ["search engine", "full-text search"],

    "react": ["reactjs", "react.js", "frontend framework"],
    "angular": ["angularjs", "angular.js", "frontend framework"],
    "vue": ["vuejs", "vue.js", "frontend framework"],
    "node.js": ["nodejs", "server-side javascript", "backend javascript"],
    "express": ["expressjs", "node framework", "web framework"],
    "django": ["python web framework", "web framework"],
    "flask": ["python web framework", "micro framework"],
    "fastapi": ["python web framework", "async web framework"],

    "docker": ["containerization", "containers", "container platform"],
    "kubernetes": ["k8s", "container orchestration", "orchestration"],
    "terraform": ["infrastructure as code", "iac"],
    "jenkins": ["ci/cd", "continuous integration", "build automation"],
    "github actions": ["ci/cd", "continuous integration"],
    "aws": ["amazon web services", "cloud computing"],
    "gcp": ["google cloud platform", "cloud computing"],
    "azure": ["microsoft azure", "cloud computing"],

    "python": ["py"],
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "java": ["jvm"],
    "golang": ["go programming", "go language"],

    "deep learning": ["neural networks", "dl"],
    "machine learning": ["ml", "predictive modeling"],
    "natural language processing": ["nlp", "text mining", "text analytics"],
    "computer vision": ["cv", "image recognition", "image classification"],
    "data pipeline": ["etl", "data engineering", "data workflow"],
    "rest": ["rest api", "restful api", "restful apis"],
    "graphql": ["graph query language", "api query language"],
    "microservices": ["micro services", "service-oriented architecture"],
    "object-oriented programming": ["oop", "java", "cpp", "csharp", "polymorphism"],
    "software development": ["software engineering", "application development", "coding"],
    "web development": ["frontend development", "full stack development", "web application"],
    "dashboard development": ["data visualization", "reporting", "business intelligence"],
    "data cleaning": ["data preprocessing", "data wrangling", "data preparation"],
    "data extraction": ["data mining", "data scraping", "etl"],
    "predictive models": ["machine learning models", "predictive analytics", "ml models"],

    "frontend development": ["frontend", "front-end development", "ui development", "client-side"],
    "backend development": ["backend", "back-end development", "server-side"],
    "full stack development": ["full stack", "fullstack", "full-stack", "frontend backend"],
    "rest apis": ["rest", "restful api", "api development", "rest api"],

    "tableau": ["data visualization", "business intelligence", "dashboarding"],
    "power bi": ["data visualization", "business intelligence", "powerbi", "dashboarding"],
    "dashboarding": ["dashboard development", "data visualization", "reporting", "dashboarding tools"],
    "business reporting": ["data visualization", "reporting", "business intelligence"],

    # ── P5.2 expansion (reduce false negatives) ─────────────────────────────
    # Tight, high-confidence equivalences for commonly-missed matches.
    # Deliberately avoids broad cross-domain terms to not reintroduce the
    # false positives that P5.1 removed.
    "version control": ["git", "github", "gitlab", "source control", "vcs"],
    "ci/cd": ["continuous integration", "continuous deployment",
              "continuous delivery", "ci cd", "cicd", "build pipeline"],
    "agile": ["scrum", "kanban", "agile methodology", "agile development",
              "sprint planning"],
    "cloud computing": ["cloud", "cloud platform", "cloud platforms",
                        "cloud services", "cloud infrastructure"],
    "linux": ["unix", "shell scripting", "bash scripting", "linux administration"],
    "big data": ["apache spark", "spark", "hadoop", "distributed data processing",
                 "large-scale data"],
    "data analysis": ["data analytics", "analytics", "data analyst",
                      "analytical skills", "analyzing data"],
    "statistics": ["statistical analysis", "statistical modeling",
                   "probability and statistics", "statistical methods"],
    "data structures": ["dsa", "algorithms and data structures",
                        "data structures and algorithms"],
    "software architecture": ["system design", "software design",
                              "architectural design", "system architecture"],
    "feature engineering": ["feature extraction", "feature selection"],
    "model deployment": ["mlops", "ml deployment", "model serving",
                         "ml ops", "model productionization"],
    "data modeling": ["data models", "schema design", "dimensional modeling"],
    "large language models": ["llm", "llms", "gpt", "generative ai",
                              "foundation models"],
    "api development": ["api design", "api integration", "building apis"],
    "unit testing": ["test automation", "automated testing", "pytest",
                     "junit", "test-driven development", "tdd"],
    "spark": ["apache spark", "pyspark", "spark sql"],
    "hadoop": ["hdfs", "mapreduce", "apache hadoop"],
    "kafka": ["apache kafka", "event streaming", "message streaming"],
}

# Reverse lookup: synonym -> [canonical names that list this synonym]
_SYNONYM_REVERSE: Dict[str, List[str]] = {}
for _canonical, _syns in SEMANTIC_SYNONYMS.items():
    for _syn in _syns:
        _s = _syn.lower()
        _SYNONYM_REVERSE.setdefault(_s, []).append(_canonical)
