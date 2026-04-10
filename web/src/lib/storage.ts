import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import type { SecurityMapRow, WorkspaceState } from "@/lib/types";

const DATA_DIR = path.join(process.cwd(), "data");
const WORKSPACE_PATH = path.join(DATA_DIR, "workspace.json");
const TRANSACTIONS_PATH = path.join(DATA_DIR, "transactions.csv");
const SECURITY_MASTER_PATH = path.join(DATA_DIR, "security-master.json");
const SECURITY_MAP_PATH = path.join(DATA_DIR, "security-map.json");

async function ensureDataDir() {
  await mkdir(DATA_DIR, { recursive: true });
}

async function readJson<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await readFile(filePath, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

async function writeJson(filePath: string, value: unknown): Promise<void> {
  await ensureDataDir();
  await writeFile(filePath, JSON.stringify(value, null, 2), "utf8");
}

export async function readWorkspaceState(): Promise<WorkspaceState | null> {
  return readJson<WorkspaceState>(WORKSPACE_PATH);
}

export async function writeWorkspaceState(state: WorkspaceState): Promise<void> {
  await writeJson(WORKSPACE_PATH, state);
}

export async function saveImportedTransactionsCsv(csvText: string): Promise<void> {
  await ensureDataDir();
  await writeFile(TRANSACTIONS_PATH, csvText, "utf8");
}

export async function readImportedTransactionsCsv(): Promise<string | null> {
  try {
    return await readFile(TRANSACTIONS_PATH, "utf8");
  } catch {
    return null;
  }
}

export async function readSecurityMaster(): Promise<unknown[] | null> {
  return readJson<unknown[]>(SECURITY_MASTER_PATH);
}

export async function writeSecurityMaster(rows: unknown[]): Promise<void> {
  await writeJson(SECURITY_MASTER_PATH, rows);
}

export async function readSecurityMap(): Promise<SecurityMapRow[] | null> {
  return readJson<SecurityMapRow[]>(SECURITY_MAP_PATH);
}

export async function writeSecurityMap(rows: SecurityMapRow[]): Promise<void> {
  await writeJson(SECURITY_MAP_PATH, rows);
}
