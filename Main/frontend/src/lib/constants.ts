export const DOMAIN_LABELS: Record<string, string> = {
  software_dev: "Software Development",
  data_science: "Data Science & AI",
  business: "Business & Management",
  freshers: "Fresher Entry",
  devops: "DevOps & Infrastructure",
  cybersecurity: "Cybersecurity",
  product_management: "Product Management",
  design: "UI/UX Design",
  custom: "Custom Profile",
};

export const MATCH_LEVEL_THEME: Record<
  string,
  { label: string; bg: string; text: string; border: string; glow: string; color: string }
> = {
  EXCELLENT: {
    label: "Excellent Fit",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200/60",
    glow: "shadow-[0_2px_8px_rgba(22,163,74,0.05)]",
    color: "#16a34a",
  },
  GOOD: {
    label: "Good Fit",
    bg: "bg-sky-50",
    text: "text-sky-700",
    border: "border-sky-200/60",
    glow: "shadow-[0_2px_8px_rgba(2,132,199,0.05)]",
    color: "#0284c7",
  },
  MODERATE: {
    label: "Moderate Fit",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200/60",
    glow: "shadow-[0_2px_8px_rgba(217,119,6,0.05)]",
    color: "#d97706",
  },
  "BELOW AVERAGE": {
    label: "Below Average Fit",
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200/60",
    glow: "shadow-[0_2px_8px_rgba(234,88,12,0.05)]",
    color: "#ea580c",
  },
  POOR: {
    label: "Poor Fit",
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200/60",
    glow: "shadow-[0_2px_8px_rgba(220,38,38,0.05)]",
    color: "#dc2626",
  },
};

export const COMPONENT_LABELS: Record<string, string> = {
  S_sk: "Core Skills Match",
  S_pr: "Projects Relevance",
  S_in: "Internship Value",
  S_we: "Work Experience Match",
  S_ac: "Academic Alignment",
  S_ah: "Achievements & Certifications",
};

export const SAMPLE_JD = `Role: Senior Software Engineer (Full Stack)

Requirements:
- 5+ years of software development experience in high-growth SaaS environments.
- Strong proficiency in Python, FastAPI, and PostgreSQL.
- Modern frontend experience using React, Next.js, and Tailwind CSS.
- Familiarity with Docker, AWS cloud infrastructure (EC2, S3, RDS), and CI/CD pipelines.
- Experience writing clean, well-tested code (pytest, Jest).
- Bachelor's or Master's degree in Computer Science or a related engineering field.

Responsibilities:
- Architect, build, and scale resilient backend RESTful API services.
- Develop highly interactive, pixel-perfect frontend dashboards and user components.
- Collaborate with product managers and UI designers to implement premium user flows.
- Mentor junior engineers and conduct thorough code reviews.
`;
