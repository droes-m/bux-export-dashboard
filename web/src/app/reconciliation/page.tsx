import { AppShell } from "@/components/app-shell";
import { readWorkspaceState } from "@/lib/storage";

export default async function ReconciliationPage() {
  const state = await readWorkspaceState();

  return (
    <AppShell
      eyebrow="Reconciliation"
      title="Reconciling the exported data"
      summary="This page will compare local calculations against the values visible in the BUX app. The shell is ready; the market-value and gain parity logic comes after the pricing layer."
    >
      {state ? (
        <div className="empty-state">
          Imported transactions: <strong>{state.transactionCount.toLocaleString("nl-BE")}</strong>
        </div>
      ) : (
        <div className="empty-state">Import a CSV to start reconciling values.</div>
      )}
    </AppShell>
  );
}
