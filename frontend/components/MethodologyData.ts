// Shape of GET /api/methodology (see backend/app/main.py).
export interface MethodologyData {
  methodology_version: string;
  categories: { id: string; title: string; weight: number }[];
  checks: {
    id: string;
    category: string;
    title: string;
    max_points: number;
    critical_if_missing: boolean;
    recommendation: string;
  }[];
  grades: Record<string, string>;
  partial_credit: string;
}
