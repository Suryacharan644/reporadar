// Mirrors the JSON produced by backend/app/report.py and backend/app/main.py.

export type Status = "pass" | "partial" | "fail";
export type Severity = "critical" | "warning" | "good";

export interface Check {
  id: string;
  category: string;
  title: string;
  status: Status;
  severity: Severity;
  points: number;
  max_points: number;
  evidence: string;
  recommendation: string;
}

export interface Category {
  id: string;
  title: string;
  weight: number;
  points: number;
  max_points: number;
}

export interface RepoInfo {
  owner: string;
  name: string;
  full_name: string;
  url: string;
  description: string | null;
  language: string | null;
  license: string | null;
  default_branch: string;
  stars: number;
  forks: number;
  open_issues: number;
  topics: string[];
  archived: boolean;
  pushed_at: string | null;
  created_at: string | null;
}

export interface CommitActivityBucket {
  week: string;
  count: number;
}

export interface Stats {
  commit_activity: CommitActivityBucket[];
  recent_commits: { sha: string; message: string; author: string; date: string; url: string | null }[];
  recent_issues: { number: number; title: string; state: string; created_at: string; url: string | null; comments: number }[];
  recent_pulls: { number: number; title: string; state: string; created_at: string; merged: boolean; url: string | null }[];
  contributors: { login: string; contributions: number; url: string | null; avatar_url: string | null }[];
  workflow_runs: { name: string; status: string; conclusion: string | null; created_at: string; url: string | null }[];
}

export interface Report {
  schema_version: string;
  methodology_version: string;
  generated_at: string;
  repo: RepoInfo;
  score: number;
  grade: string;
  verdict: string;
  summary: Record<Severity, number>;
  categories: Category[];
  checks: Check[];
  stats: Stats;
  warnings: string[];
}

export interface Validation {
  valid: boolean;
  full_name: string;
  description: string | null;
  stars: number;
  language: string | null;
  private: boolean;
  archived: boolean;
  default_branch: string | null;
}

export interface GeneratedFile {
  path: string;
  content: string;
}

export interface Generated {
  kind: string;
  files: GeneratedFile[];
}

export interface ContributionItem {
  title: string;
  number: number;
  url: string;
  repo: string;
  comments: number;
  created_at: string;
  updated_at: string;
  labels: string[];
}

export interface ContributionsResponse {
  label: string;
  total_count: number;
  page: number;
  items: ContributionItem[];
}
