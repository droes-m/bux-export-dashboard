import type { MonthlyCategoryRow } from "@/lib/types";

const DEFAULT_SERIES = ["deposits", "dividends", "interest", "fees", "tax"] as const;

export function MonthlyBars({
  rows,
  series = DEFAULT_SERIES
}: {
  rows: MonthlyCategoryRow[];
  series?: readonly string[];
}) {
  if (rows.length === 0) {
    return <div className="empty-chart">No monthly data yet. Import a CSV to populate this chart.</div>;
  }

  const values = rows.map((row) => series.reduce((total, key) => total + (row.totals[key] ?? 0), 0));
  const maxValue = Math.max(...values.map((value) => Math.abs(value)), 1);

  return (
    <div className="monthly-chart" role="img" aria-label="Monthly net cashflow">
      {rows.map((row, index) => {
        const value = values[index] ?? 0;
        const height = `${Math.max(8, (Math.abs(value) / maxValue) * 220)}px`;
        return (
        <div key={row.month} className="month-column">
          <div className="bars-stack">
            <div
              className={`monthly-bar ${value >= 0 ? "positive" : "negative"}`}
              style={{ height }}
              title={`${row.monthLabel}: ${value.toFixed(2)} EUR`}
            />
          </div>
          <span>{row.monthLabel}</span>
        </div>
        );
      })}
    </div>
  );
}
