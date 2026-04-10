import { AppShell } from "@/components/app-shell";

export default function ForecastPage() {
  return (
    <AppShell
      eyebrow="Forecast"
      title="Forecast layer, to be ported next"
      summary="The React migration now has a place for the Python forecasting page. Next step is to port the regression and scenario logic into typed frontend/server utilities."
    >
      <div className="empty-state">Forecast migration is not wired yet.</div>
    </AppShell>
  );
}
