/** Simple reusable data table for dashboard monitoring views. */
export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, string>[];
}) {
  if (rows.length === 0) {
    return <p className="text-gray-400 text-sm">No data yet.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--card)]">
            {columns.map((col) => (
              <th key={col} className="text-left px-4 py-3 text-gray-400 font-medium capitalize">
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[var(--border)] last:border-0">
              {columns.map((col) => (
                <td key={col} className="px-4 py-3">
                  {row[col] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
