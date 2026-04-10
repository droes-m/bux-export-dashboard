import { AppShell } from "@/components/app-shell";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";

export default async function MappingPage() {
  const bundle = await buildPortfolioBundleFromWorkspace();
  const securityMaster = bundle?.securityMaster ?? [];
  const securityMap = bundle?.securityMap ?? [];

  return (
    <AppShell
      eyebrow="Mapping"
      title="Security master and mapping foundation"
      summary="The Python app uses a ticker mapping file to value holdings. In the web version we keep the same concept, but move the storage into local JSON/CSV files that the Node server can read and write."
    >
      <section className="panel">
        <div className="panel-head">
          <h3>Known securities</h3>
        </div>
        {securityMaster.length === 0 ? (
          <div className="empty-state">Upload a CSV first to generate the security master.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Asset ID</th>
                  <th>Name</th>
                  <th>Currency</th>
                </tr>
              </thead>
              <tbody>
                {securityMaster.map((row) => (
                  <tr key={row.assetId}>
                    <td>{row.assetId}</td>
                    <td>{row.assetName}</td>
                    <td>{row.assetCurrency || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <h3>Effective mapping</h3>
        </div>
        {securityMap.length === 0 ? (
          <div className="empty-state">No security map available yet.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Ticker</th>
                  <th>Currency</th>
                  <th>Source</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {securityMap.map((row) => (
                  <tr key={row.assetId}>
                    <td>{row.assetName}</td>
                    <td>{row.ticker || "-"}</td>
                    <td>{row.assetCurrency || "-"}</td>
                    <td>{row.source}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AppShell>
  );
}
