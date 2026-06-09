export function formatScore(score: number | undefined | null): string {
  if (score === undefined || score === null) return "0%";
  return `${Math.round(score)}%`;
}

export function formatFractionAsScore(fraction: number | undefined | null): string {
  if (fraction === undefined || fraction === null) return "0%";
  return `${Math.round(fraction * 100)}%`;
}

export function formatExperience(months: number | undefined | null): string {
  if (!months) return "Fresher / General Entry";
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;

  if (years === 0) {
    return `${remainingMonths} mo${remainingMonths > 1 ? "s" : ""}`;
  }
  if (remainingMonths === 0) {
    return `${years} yr${years > 1 ? "s" : ""}`;
  }
  return `${years} yr${years > 1 ? "s" : ""} ${remainingMonths} mo${remainingMonths > 1 ? "s" : ""}`;
}

export function cleanRecommendation(rec: string): string {
  if (!rec) return "";
  // Fix Finding F4: Replace references to "not_specified" or "not specified"
  return rec.replace(/\bnot_specified\b/g, "the target role")
            .replace(/\bnot specified\b/g, "the target role");
}

export function formatLabel(snakeCaseStr: string): string {
  if (!snakeCaseStr) return "";
  return snakeCaseStr
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}
