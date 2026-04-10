import { NextResponse } from "next/server";

import { writeSecurityMap } from "@/lib/storage";
import type { SecurityMapRow } from "@/lib/types";

function toString(value: unknown): string {
  return String(value ?? "").trim();
}

function toNumber(value: unknown): number {
  const parsed = Number(String(value ?? "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 1;
}

function normalizeRow(row: Partial<SecurityMapRow>): SecurityMapRow {
  return {
    assetId: toString(row.assetId),
    assetName: toString(row.assetName),
    assetCurrency: toString(row.assetCurrency),
    ticker: toString(row.ticker),
    priceScale: toNumber(row.priceScale),
    exchange: toString(row.exchange),
    source: toString(row.source) || "pending",
    confidence: toString(row.confidence) || "unmapped",
    notes: toString(row.notes)
  };
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => null)) as unknown;
  if (!Array.isArray(payload)) {
    return NextResponse.json({ error: "Expected an array of mapping rows." }, { status: 400 });
  }

  const rows = payload.map((row) => normalizeRow(row as Partial<SecurityMapRow>));
  await writeSecurityMap(rows);

  return NextResponse.json({ ok: true, count: rows.length });
}
