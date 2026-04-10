"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

export function UploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("csv") as HTMLInputElement | null;
    const file = input?.files?.[0];

    if (!file) {
      setError("Choose a CSV export first.");
      return;
    }

    setBusy(true);
    setError(null);

    try {
      const payload = new FormData();
      payload.append("csv", file);
      const response = await fetch("/api/upload", {
        method: "POST",
        body: payload
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { error?: string } | null;
        throw new Error(body?.error ?? "Upload failed");
      }
      form.reset();
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="upload-form" onSubmit={onSubmit}>
      <label className="upload-dropzone">
        <input name="csv" type="file" accept=".csv,text/csv" />
        <span>Drop or choose a BUX export CSV</span>
        <small>Stored locally under `web/data/` and never committed.</small>
      </label>
      <button type="submit" disabled={busy}>
        {busy ? "Importing..." : "Import CSV"}
      </button>
      {error ? <p className="form-error">{error}</p> : null}
    </form>
  );
}
