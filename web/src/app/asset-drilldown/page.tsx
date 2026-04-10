import { AppShell } from "@/components/app-shell";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";
import { buildAssetDrilldown } from "@/lib/drilldown";
import { formatEuro } from "@/lib/portfolio";

type SearchParams = {
  assetId?: string;
};

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export default async function AssetDrilldownPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const bundle = await buildPortfolioBundleFromWorkspace();
  const params = (await searchParams) ?? {};

  if (!bundle) {
    return (
      <AppShell
        eyebrow="Asset Drilldown"
        title="Per-asset value, P/L, and trade replay"
        summary="Import a CSV first to unlock the drilldown."
      >
        <div className="empty-state">Import a CSV first to inspect individual assets.</div>
      </AppShell>
    );
  }

  const assets = bundle.securityMaster
    .map((row) => row.assetId)
    .filter(Boolean);
  const selectedAssetId = params.assetId && assets.includes(params.assetId) ? params.assetId : assets[0];
  const drilldown = buildAssetDrilldown(bundle, selectedAssetId);

  return (
    <AppShell
      eyebrow="Asset Drilldown"
      title="Per-asset value, P/L, and trade replay"
      summary="Pick one instrument to inspect its open quantity, realized/unrealized result, and price trajectory."
    >
      <div className="stack">
        <section className="panel">
          <div className="panel-head">
            <h3>Select asset</h3>
          </div>
          <form method="get">
            <select name="assetId" className="text-input" defaultValue={selectedAssetId}>
              {bundle.securityMaster.map((row) => (
                <option key={row.assetId} value={row.assetId}>
                  {row.assetName}
                </option>
              ))}
            </select>
            <div style={{ marginTop: 12 }}>
              <button type="submit">Open drilldown</button>
            </div>
          </form>
        </section>

        {!drilldown ? (
          <div className="empty-state">No transactions found for the selected asset.</div>
        ) : (
          <>
            <div className="grid-4">
              <section className="metric-card">
                <p>Current qty</p>
                <strong>{formatNumber(drilldown.summary.currentQuantity, 4)}</strong>
              </section>
              <section className="metric-card">
                <p>Current value</p>
                <strong>{formatEuro(drilldown.summary.currentValueEur)}</strong>
              </section>
              <section className="metric-card">
                <p>Realized P/L</p>
                <strong>{formatEuro(drilldown.summary.realizedPnlEur)}</strong>
              </section>
              <section className="metric-card">
                <p>Unrealized P/L</p>
                <strong>{formatEuro(drilldown.summary.unrealizedPnlEur)}</strong>
              </section>
            </div>

            <div className="grid-4">
              <section className="metric-card">
                <p>Avg buy price</p>
                <strong>{formatNumber(drilldown.summary.averageBuyPriceOriginal)}</strong>
              </section>
              <section className="metric-card">
                <p>Open avg cost</p>
                <strong>{formatNumber(drilldown.summary.openAverageCostOriginal)}</strong>
              </section>
              <section className="metric-card">
                <p>Latest unit price</p>
                <strong>{formatNumber(drilldown.summary.latestUnitPriceOriginal)}</strong>
              </section>
              <section className="metric-card">
                <p>Portfolio weight</p>
                <strong>{formatPercent(drilldown.summary.currentWeightPct)}</strong>
              </section>
            </div>

            <section className="panel">
              <div className="panel-head">
                <h3>Asset summary</h3>
              </div>
              <div className="panel-copy">
                {drilldown.summary.assetName} ({drilldown.summary.ticker || "no ticker"}) | Asset ID{" "}
                {drilldown.summary.assetId}
                <br />
                Currency: {drilldown.summary.assetCurrency || "-"} | Scale: {drilldown.summary.priceScale}
              </div>
            </section>

            <section className="panel">
              <div className="panel-head">
                <h3>Timeline</h3>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Quantity</th>
                      <th>Unit price EUR</th>
                      <th>Market value EUR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drilldown.points.slice(-24).map((row) => (
                      <tr key={row.date}>
                        <td>{row.date}</td>
                        <td>{formatNumber(row.quantity, 4)}</td>
                        <td>{formatNumber(row.unitPriceEur)}</td>
                        <td>{formatEuro(row.marketValueEur)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel">
              <div className="panel-head">
                <h3>Trade replay</h3>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Type</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th>P/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drilldown.transactions.map((row) => (
                      <tr key={`${row.transactionTime}-${row.transferType}-${row.transactionAmount}`}>
                        <td>{row.transactionTime}</td>
                        <td>{row.transferType}</td>
                        <td>{formatNumber(row.assetQuantity)}</td>
                        <td>{formatNumber(row.assetPrice)}</td>
                        <td>{formatEuro(row.profitAndLossAmount ?? 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
