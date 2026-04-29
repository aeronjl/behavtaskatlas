import { dataRequests } from "./data";

const DATA_REQUEST_FIELDS = [
  "request_id",
  "title",
  "status",
  "priority",
  "request_type",
  "blocker_type",
  "dataset_ids",
  "paper_ids",
  "protocol_ids",
  "slice_ids",
  "finding_ids",
  "model_roadmap_issue_types",
  "requested_files",
  "last_event_type",
  "last_event_date",
  "next_follow_up_date",
  "action_state",
  "action_summary",
  "days_since_last_event",
  "days_until_follow_up",
  "request_export_path",
  "suggested_command",
  "purpose",
  "next_action",
  "contact_instructions",
];

function csvValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join("|");
  const text = String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function toCsv(fields: string[], rows: Array<Record<string, unknown>>): string {
  const lines = [fields.join(",")];
  for (const row of rows) {
    lines.push(fields.map((field) => csvValue(row[field])).join(","));
  }
  return `${lines.join("\n")}\n`;
}

export function buildDataRequestsCsv(): string {
  const requests =
    (dataRequests.requests ?? []) as Array<
      Record<string, unknown> & {
        requested_files?: Array<Record<string, unknown>>;
      }
    >;
  const rows = requests.map((request) => ({
    ...request,
    requested_files: (request.requested_files ?? [])
      .map((file) => file.name)
      .join("|"),
  }));
  return toCsv(DATA_REQUEST_FIELDS, rows);
}
