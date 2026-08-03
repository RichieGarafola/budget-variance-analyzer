"""
Generate sample budget vs. actuals CSV for a fictional federal contractor.
12-month budget (Jan–Dec 2025) with actuals through Oct 2025.
Run once: python scripts/generate_sample_data.py
"""

import csv
import random
from pathlib import Path

random.seed(13)

OUTPUT = Path(__file__).parent.parent / "data" / "sample" / "sample_budget.csv"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

DEPARTMENTS = {
    "Operations":  1_800_000,
    "IT":          1_200_000,
    "HR":            420_000,
    "Finance":       360_000,
    "Business Dev":  540_000,
    "R&D":           900_000,
}

CATEGORIES = {
    "Operations":  ["Salaries", "Benefits", "Equipment", "Facilities", "Travel"],
    "IT":          ["Salaries", "Software Licenses", "Cloud Infrastructure", "Consulting", "Equipment"],
    "HR":          ["Salaries", "Benefits", "Training", "Recruiting"],
    "Finance":     ["Salaries", "Benefits", "Audit & Compliance", "Software Licenses"],
    "Business Dev":["Salaries", "Travel", "Marketing", "Conferences"],
    "R&D":         ["Salaries", "Benefits", "Equipment", "Contractors", "Software Licenses"],
}

# Budget split weights by category within each department
WEIGHTS = {
    "Salaries":             0.55,
    "Benefits":             0.15,
    "Equipment":            0.10,
    "Facilities":           0.08,
    "Travel":               0.06,
    "Software Licenses":    0.12,
    "Cloud Infrastructure": 0.20,
    "Consulting":           0.10,
    "Training":             0.05,
    "Recruiting":           0.08,
    "Audit & Compliance":   0.12,
    "Marketing":            0.18,
    "Conferences":          0.10,
    "Contractors":          0.14,
}

MONTHS_WITH_ACTUALS = [f"2025-{m:02d}-01" for m in range(1, 11)]   # Jan–Oct actual
ALL_MONTHS          = [f"2025-{m:02d}-01" for m in range(1, 13)]   # Jan–Dec budget


def variance_profile(dept: str, cat: str) -> float:
    """Return a persistent bias for this dept/category combo."""
    key = f"{dept}:{cat}"
    r = random.Random(key)
    return r.uniform(-0.18, 0.12)   # negative = tends to over-spend


rows = []
for dept, annual_budget in DEPARTMENTS.items():
    cats = CATEGORIES[dept]
    total_weight = sum(WEIGHTS.get(c, 0.07) for c in cats)

    for cat in cats:
        weight     = WEIGHTS.get(cat, 0.07) / total_weight
        cat_annual = annual_budget * weight
        monthly_budget = cat_annual / 12
        bias = variance_profile(dept, cat)

        for month in ALL_MONTHS:
            budgeted = round(monthly_budget * random.uniform(0.92, 1.08), 2)

            if month in MONTHS_WITH_ACTUALS:
                noise  = random.uniform(-0.05, 0.05)
                factor = 1 + bias + noise
                actual = round(max(0, budgeted * factor), 2)
            else:
                actual = ""   # future month — no actuals yet

            rows.append({
                "month":      month,
                "department": dept,
                "category":   cat,
                "budgeted":   budgeted,
                "actual":     actual,
            })

rows.sort(key=lambda r: (r["month"], r["department"], r["category"]))

with open(OUTPUT, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["month", "department", "category", "budgeted", "actual"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> {OUTPUT}")
n_actual = sum(1 for r in rows if r["actual"] != "")
print(f"  Rows with actuals: {n_actual} | Future (budget only): {len(rows) - n_actual}")
