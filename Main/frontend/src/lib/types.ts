export interface ComponentBreakdownItem {
  component: string;
  weight: number;
  component_score: number;
  score_achieved: number;
  pct_contribution: number;
  active: boolean;
  reason?: string;
}

export interface ExcludedComponent {
  component: string;
  reason: string;
}

export interface MatchedSkillDetail {
  resume_phrase: string;
  jd_phrase: string;
  similarity: number;
  match_score: number;
  match_type: string;
}

export interface SkillsAnalysis {
  total_jd_skills: number;
  matched_count: number;
  missing_skills: string[];
  skill_coverage_pct: number;
  match_details: MatchedSkillDetail[];
  skills_score_S_sk: number;
}

export interface ImprovementSuggestion {
  rank: number;
  improvement: string;
  current_score: number;
  predicted_score: number;
  delta_gain: number;
}

export interface CombinedImprovement {
  current_score?: number;
  new_score?: number;
  delta?: number;
  applied_improvements?: string[];
}

export interface GapItem {
  gap_item: string;
  component: string;
  impact_pct: number;
  severity: 'high' | 'medium' | 'low';
}

export interface GapAnalysis {
  ranked_gaps: GapItem[];
  total_recoverable_pct: number;
}

export interface ResumeExtraction {
  sections_present: string[];
  empty_sections: string[];
  skills: string[];
  certifications: string[];
  projects: string[];
  internships: string[];
  work_experience: string[];
  education: string[];
  achievements: string[];
  skill_sources: Record<string, number>;
}

export interface JDExtraction {
  required_skills: string[];
  preferred_skills: string[];
  optional_skills: string[];
  domain_detected: string;
  primary_domain: string;
  secondary_domain: string | null;
  role_title: string;
  experience_years: number;
  education_level: string;
  rules: {
    requires_experience?: boolean;
    requires_academics?: boolean;
    requires_achievements?: boolean;
  };
  llm_excluded_noise: string[] | null;
  llm_responsibilities: string[] | null;
}

export interface MatchedPair {
  resume_phrase: string;
  jd_phrase: string;
  similarity: number;
  match_score: number;
}

export interface DebugInfo {
  resume_skill_count: number;
  jd_skill_count: number;
  match_type_counts: Record<string, number>;
  weighted_jd_coverage: number;
  avg_match_confidence: number;
  resume_pool_coverage: number;
  final_skill_score: number;
  jd_bucket_counts: Record<string, number>;
  resume_skill_source_counts: Record<string, number>;
  rejected_jd_candidates: string[];
  llm_validation: any;
  embedding_backend: string;
  llm_backend?: string;
}

export interface FinalSummary {
  overall_assessment: string;
  candidate_category: string;
  strengths: string[] | null;
  weaknesses: string[] | null;
  key_missing_requirements: string[];
  recommended_next_actions: string[] | Record<string, string[]>;
}

export interface InternshipAnalysisItem {
  title: string;
  company: string;
  duration_months: number;
  relevance_score: number;
  score: number;
}

export interface WorkExperienceAnalysisItem {
  title: string;
  company: string;
  duration_months: number;
  relevance_score: number;
  score: number;
}

export interface ExperienceIntelligence {
  candidate_category: string;
  classification_confidence: string;
  classification_signals: string[];
  internship_count: number;
  internship_analyses: InternshipAnalysisItem[];
  internship_total_months: number;
  internship_quality_score: number;
  work_experience_count: number;
  work_experience_analyses: WorkExperienceAnalysisItem[];
  work_experience_total_months: number;
  work_experience_quality_score: number;
  experience_quality_score: number;
  total_experience_months: number;
  experience_meets_jd_requirement: boolean;
  jd_required_years: number;
  llm_candidate_type: string | null;
  llm_relevant_experience_months: number | null;
  llm_leadership_signals: string[] | null;
  llm_impact_metrics: string[] | null;
  llm_rationale: string | null;
}

export interface ProjectAnalysisItem {
  rank: number;
  title: string;
  raw_text: string;
  tech_stack: string[];
  similarity_score: number;
  complexity_score: number;
  impact_score: number;
  domain_alignment_score: number;
  final_score: number;
  complexity_signals: string[];
  impact_signals: string[];
  matched_jd_skills: string[];
}

export interface ProjectIntelligence {
  project_count: number;
  ranked_projects: ProjectAnalysisItem[];
  best_score: number;
  average_score: number;
  coverage_score: number;
  jd_role: string;
  jd_domain: string;
  jd_required_skills: string[];
  embedding_backend: string;
  llm_top_strengths: string[] | null;
  llm_top_gaps: string[] | null;
}

export interface ExplainabilityTopProject {
  rank: number;
  title: string;
  final_score: number;
  similarity_score: number;
  llm_relevance: number | null;
  llm_rationale: string | null;
  matched_jd_skills: string[];
}

export interface ExplainabilityValidationPair {
  resume_phrase?: string;
  jd_phrase?: string;
  similarity?: number;
  match_score?: number;
  is_valid_match?: boolean;
  confidence?: number;
  reason?: string;
}

export interface ExplainabilityPayload {
  overall_summary: string | null;
  next_steps: string[] | null;
  top_strengths: string[];
  top_gaps: string[];
  jd_role: string | null;
  jd_role_confidence: string | null;
  jd_responsibilities: string[] | null;
  jd_excluded_noise: string[] | null;
  jd_seniority_llm: string | null;
  jd_seniority_baseline: string | null;
  jd_llm_confidence: number | null;
  candidate_type_baseline: string | null;
  candidate_type_llm: string | null;
  relevant_experience_months: number | null;
  total_experience_months: number | null;
  experience_rationale: string | null;
  leadership_signals: string[];
  impact_metrics: string[];
  top_projects: ExplainabilityTopProject[];
  matches_validated_kept: number;
  matches_validated_rejected: number;
  validation_skipped_reason: string | null;
  rejected_pairs: ExplainabilityValidationPair[];
  kept_pairs: ExplainabilityValidationPair[];
  embedding_backend: string | null;
  llm_polishing_used: boolean;
  missing_skills: string[];
}

export interface AnalysisPayload {
  placement_score: number;
  placement_score_raw_pct: number;
  placement_score_fraction: number;
  match_level: 'EXCELLENT' | 'GOOD' | 'MODERATE' | 'BELOW AVERAGE' | 'POOR';
  domain_detected: string;
  role_title: string;
  llm_role_summary: string | null;
  seniority_level: string;
  llm_seniority: string | null;
  component_breakdown: ComponentBreakdownItem[];
  excluded_components: ExcludedComponent[];
  weight_profile_used: string;
  weights: Record<string, number>;
  effective_weights: Record<string, number>;
  component_scores: Record<string, number>;
  skills_analysis: SkillsAnalysis;
  improvement_suggestions: ImprovementSuggestion[];
  combined_improvement: CombinedImprovement;
  gap_analysis: GapAnalysis;
  recommendations: Record<string, string[]> | string[];
  resume_extraction: ResumeExtraction;
  jd_extraction: JDExtraction;
  matching_transparency: Record<string, MatchedPair[]>;
  debug: DebugInfo;
  final_summary: FinalSummary;
  experience_intelligence: ExperienceIntelligence;
  project_intelligence: ProjectIntelligence;
  explainability: ExplainabilityPayload;
  warnings?: string[];
}
