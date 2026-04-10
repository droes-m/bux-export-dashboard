import { NextResponse } from "next/server";

import {
  buildMonthlyCategoryRows,
  buildSecurityMaster,
  computeBasicMetrics,
  parseTransactionsCsv
} from "@/lib/portfolio";
import { buildInitialSecurityMap } from "@/lib/mapping";
import {
  saveImportedTransactionsCsv,
  writeSecurityMap,
  writeSecurityMaster,
  writeWorkspaceState
} from "@/lib/storage";

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("csv");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "No CSV file received." }, { status: 400 });
  }

  const csvText = await file.text();
  const transactions = parseTransactionsCsv(csvText);
  const securityMaster = buildSecurityMaster(transactions);
  const securityMap = buildInitialSecurityMap(securityMaster);
  const metrics = computeBasicMetrics(transactions);
  const monthlyCategoryRows = buildMonthlyCategoryRows(transactions);

  await saveImportedTransactionsCsv(csvText);
  await writeSecurityMaster(securityMaster);
  await writeSecurityMap(securityMap);
  await writeWorkspaceState({
    sourceFileName: file.name,
    importedAt: new Date().toISOString(),
    transactionCount: transactions.length,
    metrics,
    monthlyCategoryRows
  });

  return NextResponse.json({
    ok: true,
    sourceFileName: file.name,
    transactionCount: transactions.length
  });
}
