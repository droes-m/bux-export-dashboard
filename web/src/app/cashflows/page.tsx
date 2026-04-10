import { AppShell } from "@/components/app-shell";
import { MonthlyBars } from "@/components/monthly-bars";
import { readWorkspaceState } from "@/lib/storage";

export default async function CashflowsPage() {
  const state = await readWorkspaceState();

  return (
    <AppShell
      eyebrow="Cashflows"
      title="Monthly cashflow pattern"
      summary="This section is the first candidate to migrate from Python with a cleaner React layout. It already shows the imported monthly cashflow shape, while the richer market-vs-deposit breakdown will come next."
    >
      {state ? (
        <section className="panel">
          <div className="panel-head">
            <h3>Monthly totals</h3>
          </div>
          <MonthlyBars rows={state.monthlyCategoryRows} />
        </section>
      ) : (
        <div className="empty-state">Import a CSV to see monthly cashflow totals.</div>
      )}
    </AppShell>
  );
}
