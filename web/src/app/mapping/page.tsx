import { AppShell } from "@/components/app-shell";
import { MappingEditor } from "@/components/mapping-editor";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";

export default async function MappingPage() {
  const bundle = await buildPortfolioBundleFromWorkspace();
  const securityMaster = bundle?.securityMaster ?? [];
  const securityMap = bundle?.securityMap ?? [];

  return (
    <AppShell
      eyebrow="Mapping"
      title="Security master and mapping foundation"
      summary="The Python app uses a ticker mapping file to value holdings. In the web version we keep the same concept, but move the storage into local JSON files that the Node server can read and write."
    >
      {bundle ? (
        <div className="stack">
          <MappingEditor initialRows={securityMap} />

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
        </div>
      ) : (
        <div className="empty-state">Import a CSV first to generate the security master and mapping.</div>
      )}
    </AppShell>
  );
}
