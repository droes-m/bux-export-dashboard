import { AppShell } from "@/components/app-shell";
import { readImportedTransactionsCsv } from "@/lib/storage";
import { parseTransactionsCsv } from "@/lib/portfolio";

export default async function TransactionsPage() {
  const csvText = await readImportedTransactionsCsv();
  const transactions = csvText ? parseTransactionsCsv(csvText) : [];

  return (
    <AppShell
      eyebrow="Ledger"
      title="Transactions"
      summary="Raw BUX rows are available here once you upload a CSV. This becomes the basis for drilldowns, reconciliation, and exports in the React version."
    >
      {transactions.length === 0 ? (
        <div className="empty-state">No transactions imported yet.</div>
      ) : (
        <section className="panel">
          <div className="panel-head">
            <h3>Imported rows</h3>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Category</th>
                  <th>Type</th>
                  <th>Asset</th>
                  <th>Amount</th>
                  <th>Cash balance</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((row) => (
                  <tr key={`${row.transactionTime}-${row.assetId}-${row.transactionType}`}>
                    <td>{row.transactionTime}</td>
                    <td>{row.transactionCategory}</td>
                    <td>{row.transactionType}</td>
                    <td>{row.assetName}</td>
                    <td>{row.transactionAmount?.toFixed(2) ?? "-"}</td>
                    <td>{row.cashBalanceAmount?.toFixed(2) ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </AppShell>
  );
}
