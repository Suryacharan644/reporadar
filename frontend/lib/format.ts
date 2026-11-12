const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function formatCount(n: number): string {
  return compact.format(n);
}

/** "3 days ago", "in 2 hours", "just now". Pure given `now`, so it is easy to test. */
export function timeAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "unknown";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const seconds = Math.round((then - now.getTime()) / 1000);
  const abs = Math.abs(seconds);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  if (abs < 45) return "just now";
  for (const [unit, size] of units) {
    if (abs >= size) {
      return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(Math.round(seconds / size), unit);
    }
  }
  return "just now";
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Quick, offline sanity check so obviously wrong input never reaches the API. */
export function quickRepoCheck(raw: string): string | null {
  const text = raw.trim();
  if (!text) return "Enter a GitHub repository URL or owner/repo.";
  if (/\s/.test(text)) return "Repository references cannot contain spaces.";
  return null;
}

export function gradeTone(score: number): "emerald" | "cyan" | "amber" | "rose" {
  if (score >= 85) return "emerald";
  if (score >= 70) return "cyan";
  if (score >= 50) return "amber";
  return "rose";
}
