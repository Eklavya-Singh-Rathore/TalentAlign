"""Sample resume section data for testing the Experience Intelligence Engine.

Each fixture provides realistic resume section data (internships,
work_experience, skills, etc.) as dictionaries matching the output
format of resume_parser.parse_resume().
"""

# ─── Fresher Resume (no internships, no work experience) ────────────────────

FRESHER_RESUME = {
    "skills": ["python", "java", "html", "css", "javascript", "sql", "git"],
    "projects": [
        "Built a weather app using React and OpenWeatherMap API",
        "Developed a chat application using Node.js and Socket.io",
    ],
    "certifications": ["AWS Cloud Practitioner"],
    "internships": [],
    "work_experience": [],
    "education": [
        "B.Tech in Computer Science, XYZ University, 2024, CGPA: 8.5/10"
    ],
    "achievements": ["Participated in Smart India Hackathon 2023"],
}

# ─── Intern Resume (1 internship, no work experience) ───────────────────────

INTERN_RESUME = {
    "skills": ["python", "react", "javascript", "sql", "git", "docker"],
    "projects": [
        "Full-stack e-commerce app with React frontend and FastAPI backend",
        "ML-based sentiment analysis tool using Python and scikit-learn",
    ],
    "certifications": [],
    "internships": [
        "Software Development Intern at TechStartup Inc - 3 months "
        "(May 2023 - Jul 2023). Built REST APIs using FastAPI and PostgreSQL. "
        "Implemented CI/CD pipeline with GitHub Actions.",
    ],
    "work_experience": [],
    "education": [
        "B.Tech in Computer Science, ABC Engineering College, 2024, CGPA: 9.0/10"
    ],
    "achievements": [],
}

# ─── Multiple Internships Resume ────────────────────────────────────────────

MULTIPLE_INTERNSHIPS_RESUME = {
    "skills": [
        "python", "java", "react", "node.js", "postgresql", "mongodb",
        "docker", "kubernetes", "aws", "git",
    ],
    "projects": [
        "Microservices-based food delivery platform",
        "Real-time analytics dashboard using React and D3.js",
    ],
    "certifications": ["AWS Solutions Architect Associate"],
    "internships": [
        "Backend Engineering Intern at Google - 6 months "
        "(Jan 2023 - Jun 2023). Developed microservices in Java and Python. "
        "Worked with Kubernetes and Docker for container orchestration.",
        "Full Stack Developer Intern at Flipkart - Summer 2022. "
        "Built React components and Node.js APIs. Used MongoDB for data storage.",
        "Data Engineering Intern at Startup XYZ - 8 weeks "
        "(May 2022 - Jul 2022). Built data pipelines using Python and SQL.",
    ],
    "work_experience": [],
    "education": [
        "B.Tech in Computer Science, IIT Delhi, 2024, CGPA: 9.2/10"
    ],
    "achievements": [
        "Won Smart India Hackathon 2023 - Grand Finale",
        "Published paper on distributed systems at IEEE conference",
    ],
}

# ─── Early Career Resume (internships + some work experience) ───────────────

EARLY_CAREER_RESUME = {
    "skills": [
        "python", "django", "react", "postgresql", "redis",
        "docker", "aws", "git", "ci/cd",
    ],
    "projects": [
        "Open-source contribution to Django REST Framework",
    ],
    "certifications": ["AWS Developer Associate"],
    "internships": [
        "Backend Intern at TechCorp - 6 months (Jan 2022 - Jun 2022). "
        "Built REST APIs with Django. Deployed on AWS EC2.",
    ],
    "work_experience": [
        "Software Engineer at StartupABC - 1.5 years (Jul 2022 - Dec 2023). "
        "Led backend development using Python and Django. "
        "Managed PostgreSQL databases and Redis caching layer. "
        "Implemented CI/CD pipelines with GitHub Actions.",
    ],
    "education": [
        "B.Tech in Computer Science, NIT Trichy, 2022, CGPA: 8.7/10"
    ],
    "achievements": [],
}

# ─── Experienced Professional Resume ────────────────────────────────────────

EXPERIENCED_RESUME = {
    "skills": [
        "java", "spring boot", "microservices", "kafka", "redis",
        "postgresql", "mongodb", "kubernetes", "docker", "aws",
        "terraform", "grafana", "prometheus", "python", "go",
    ],
    "projects": [],
    "certifications": [
        "AWS Solutions Architect Professional",
        "Certified Kubernetes Administrator",
    ],
    "internships": [],
    "work_experience": [
        "Senior Software Engineer at Amazon - 3 years (Jan 2021 - Present). "
        "Led design and implementation of high-throughput microservices "
        "processing 1M+ requests/day. Mentored 3 junior engineers. "
        "Technologies: Java, Spring Boot, Kafka, DynamoDB, AWS.",
        "Software Engineer at Infosys - 2 years (Jan 2019 - Dec 2020). "
        "Developed RESTful APIs using Java and Spring Boot. "
        "Migrated monolithic application to microservices architecture. "
        "Implemented monitoring with Prometheus and Grafana.",
        "Associate Software Engineer at TCS - 1.5 years (Jul 2017 - Dec 2018). "
        "Built backend services using Java and SQL Server. "
        "Participated in Agile sprints and code reviews.",
    ],
    "education": [
        "B.Tech in Computer Science, VIT Vellore, 2017, CGPA: 8.0/10"
    ],
    "achievements": [
        "Best Team Award at Amazon, 2022",
    ],
}

# ─── Senior Professional Resume ─────────────────────────────────────────────

SENIOR_PROFESSIONAL_RESUME = {
    "skills": [
        "java", "go", "python", "system design", "distributed systems",
        "kafka", "grpc", "kubernetes", "aws", "terraform",
        "team leadership", "architecture", "mentoring",
    ],
    "projects": [],
    "certifications": [
        "AWS Solutions Architect Professional",
        "Google Cloud Professional Cloud Architect",
    ],
    "internships": [],
    "work_experience": [
        "Principal Engineer at Microsoft - 4 years (Jan 2020 - Present). "
        "Led platform architecture for Azure services. "
        "Managed team of 8 engineers. Drove technical strategy.",
        "Staff Engineer at Google - 3 years (Jan 2017 - Dec 2019). "
        "Designed distributed storage systems. "
        "Published 2 papers on scalability patterns.",
        "Senior Engineer at Facebook - 2 years (Jan 2015 - Dec 2016). "
        "Built real-time data processing pipelines using Kafka and Go.",
        "Software Engineer at LinkedIn - 3 years (Jan 2012 - Dec 2014). "
        "Developed backend APIs and search infrastructure.",
    ],
    "education": [
        "M.S. in Computer Science, Stanford University, 2012",
        "B.Tech in Computer Science, IIT Bombay, 2010, CGPA: 9.5/10",
    ],
    "achievements": [
        "Published papers at OSDI and SOSP conferences",
        "Patent holder for distributed caching system",
    ],
}

# ─── Duration Edge Cases Resume ──────────────────────────────────────────────

DURATION_EDGE_CASES_RESUME = {
    "skills": ["python", "sql"],
    "projects": [],
    "certifications": [],
    "internships": [
        "Intern at CompanyA - 8 weeks",                          # weeks
        "Research Intern at Lab, Summer 2023",                    # season
        "Intern at CompanyC from January 2023 to March 2023",    # date range
        "Short stint at CompanyD",                                # no duration
    ],
    "work_experience": [
        "Developer at CompanyE for 2.5 years",                   # explicit years
        "Analyst at CompanyF (Apr 2020 - Present)",              # ongoing
    ],
    "education": ["B.Tech in CS, 2020"],
    "achievements": [],
}

# ─── Empty Resume ────────────────────────────────────────────────────────────

EMPTY_RESUME = {
    "skills": [],
    "projects": [],
    "certifications": [],
    "internships": [],
    "work_experience": [],
    "education": [],
    "achievements": [],
}


# ─── Sample JD Data (for relevance testing) ─────────────────────────────────

SAMPLE_JD_BACKEND = {
    "required_skills": ["python", "fastapi", "postgresql", "docker", "rest api"],
    "preferred_skills": ["kubernetes", "redis", "aws"],
    "optional_skills": ["kafka", "grpc"],
    "domain_detected": "software_dev",
    "role_title": "Backend Engineer",
    "experience_years": 3,
}

SAMPLE_JD_FRESHER = {
    "required_skills": ["python", "javascript", "sql", "git"],
    "preferred_skills": ["react", "node.js"],
    "optional_skills": [],
    "domain_detected": "software_dev",
    "role_title": "Software Developer",
    "experience_years": 0,
}

SAMPLE_JD_SENIOR = {
    "required_skills": ["java", "spring boot", "microservices", "kafka", "kubernetes"],
    "preferred_skills": ["aws", "terraform", "grpc"],
    "optional_skills": ["go", "python"],
    "domain_detected": "software_dev",
    "role_title": "Senior Software Engineer",
    "experience_years": 5,
}
