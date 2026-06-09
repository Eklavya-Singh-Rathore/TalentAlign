"""Sample projects for Project Relevance Engine tests.

Each fixture is a raw project entry string as it would appear in
parsed_resume["projects"]. Designed to exercise different combinations
of complexity / impact / domain signals.
"""

# ─── Highly relevant ML project ─────────────────────────────────────────────

ML_PROJECT = (
    "VERA - Verifying Remedies Assertion\n"
    "Engineered an NLP preprocessing pipeline using Pandas and Scikit-learn (TF-IDF).\n"
    "Trained SVM classifier benchmarking Logistic Regression and Random Forest.\n"
    "Achieved 96.1% accuracy and 99.3% AUC on the final model.\n"
    "Deployed model artifacts via a Flask API."
)

# ─── Distributed-systems / DevOps project ───────────────────────────────────

DEVOPS_PROJECT = (
    "Ticket Auto-Routing System | 7,976 tickets processed\n"
    "Designed a distributed microservices architecture with Kafka and Kubernetes.\n"
    "Built CI/CD pipelines on GitHub Actions and Terraform-managed infrastructure.\n"
    "Reduced routing latency by 40%. Deployed on AWS using Docker."
)

# ─── Full-stack web project ─────────────────────────────────────────────────

WEB_PROJECT = (
    "E-commerce Platform\n"
    "Built a full-stack e-commerce site using React, Node.js, and PostgreSQL.\n"
    "Designed REST APIs for cart and checkout. Implemented JWT authentication.\n"
    "Served 10K+ users and processed 1M+ requests with 99.9% uptime."
)

# ─── Data engineering project ───────────────────────────────────────────────

DATA_ENG_PROJECT = (
    "Real-Time Analytics Pipeline\n"
    "Architected an ETL pipeline using Apache Spark and Airflow on Databricks.\n"
    "Migrated batch processing to streaming with Kafka, reducing latency from 4 hours to 5 minutes.\n"
    "Built data lake on AWS S3 with Snowflake warehouse for analytics queries."
)

# ─── Low-relevance / hobby project ──────────────────────────────────────────

HOBBY_PROJECT = (
    "Personal Travel Blog\n"
    "Used WordPress to share photos and stories from trips.\n"
    "Customized theme with some CSS tweaks."
)

# ─── Project missing structural metadata ────────────────────────────────────

MINIMAL_PROJECT = "A small Python script that prints hello world."

# ─── Empty project ──────────────────────────────────────────────────────────

EMPTY_PROJECT = ""


# ─── Sample JDs for cross-axis testing ──────────────────────────────────────

JD_DATA_SCIENCE = {
    "role_title": "Machine Learning Engineer",
    "primary_domain": "data_science",
    "required_skills": ["python", "scikit-learn", "pytorch", "machine learning", "nlp"],
    "preferred_skills": ["tensorflow", "spark"],
    "optional_skills": ["aws"],
    "clean_text": (
        "Looking for a Machine Learning Engineer with experience in Python, "
        "scikit-learn, pytorch, NLP and machine learning frameworks. "
        "Experience with feature engineering and model deployment a plus."
    ),
}

JD_DEVOPS = {
    "role_title": "Senior DevOps Engineer",
    "primary_domain": "devops",
    "required_skills": ["kubernetes", "docker", "terraform", "aws", "ci/cd"],
    "preferred_skills": ["kafka"],
    "optional_skills": [],
    "clean_text": (
        "Looking for a DevOps engineer with experience in Kubernetes, Docker, "
        "Terraform, AWS, CI/CD pipelines, and distributed systems."
    ),
}

JD_FULLSTACK = {
    "role_title": "Full Stack Engineer",
    "primary_domain": "software_dev",
    "required_skills": ["react", "node.js", "postgresql", "rest"],
    "preferred_skills": ["aws"],
    "optional_skills": [],
    "clean_text": (
        "Building user-facing web applications using React, Node.js, and PostgreSQL. "
        "Strong experience designing REST APIs."
    ),
}
