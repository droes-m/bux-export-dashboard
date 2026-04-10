import { AppShell } from "@/components/app-shell";
import { UploadForm } from "@/components/upload-form";
import { readWorkspaceState } from "@/lib/storage";

export default async function ImportPage() {
  const state = await readWorkspaceState();

  return (
    <AppShell
      eyebrow="Import"
      title="Bring in a local BUX export"
      summary="This first migration step keeps the workflow file-based. Upload a CSV once, and the app stores the raw export and derived workspace state locally under web/data/."
    >
      <div className="stack">
        <section className="panel">
          <div className="panel-head">
            <h3>Upload</h3>
          </div>
          <p className="panel-copy">
            Use the same CSV export format as the Python app. The importer will persist the raw file, compute a local workspace snapshot, and prepare the data for the rest of the migration.
          </p>
          <UploadForm />
        </section>

        <section className="panel">
          <div className="panel-head">
            <h3>Last import</h3>
          </div>
          {state ? (
            <div className="stack">
              <p className="panel-copy">
                File: <strong>{state.sourceFileName}</strong>
                <br />
                Imported at: <strong>{new Date(state.importedAt).toLocaleString("nl-BE")}</strong>
                <br />
                Transactions: <strong>{state.transactionCount.toLocaleString("nl-BE")}</strong>
              </p>
            </div>
          ) : (
            <div className="empty-state">No local workspace yet. Upload your first CSV to create one.</div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
