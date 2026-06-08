// Standardized export button group (CSV / Excel / PDF). Role-aware via `canExport`;
// PDF is optional (the accounting journal has no PDF export). The actual export
// behavior is unchanged — these only call the existing handlers.

import { Button } from "@shared/components/Button";

export function ExportButtons({
  canExport,
  disabled = false,
  onCsv,
  onExcel,
  onPdf,
}: {
  canExport: boolean;
  disabled?: boolean;
  onCsv: () => void;
  onExcel: () => void;
  onPdf?: () => void;
}) {
  if (!canExport) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="primary" onClick={onCsv} disabled={disabled}>
        تنزيل CSV
      </Button>
      <Button variant="success" onClick={onExcel} disabled={disabled}>
        تنزيل Excel
      </Button>
      {onPdf ? (
        <Button variant="danger" onClick={onPdf} disabled={disabled}>
          تنزيل PDF
        </Button>
      ) : null}
    </div>
  );
}
