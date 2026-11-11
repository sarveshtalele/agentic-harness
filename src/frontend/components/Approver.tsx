/** Who decided: "name (role)" and the mail id when the viewer may see it. Reads the decided_by_* fields the API adds beside the stored id. */
export function Approver({ item, prefix = "" }: { item: { decided_by?: string | null; decided_by_name?: string; decided_by_role?: string; decided_by_email?: string }; prefix?: string }) {
  if (!item.decided_by) return null;
  return (
    <span data-testid="approver">
      {prefix}{item.decided_by_name || item.decided_by}{item.decided_by_role ? ` (${item.decided_by_role})` : ""}
      {item.decided_by_email && <> · <span data-testid="approver-email">{item.decided_by_email}</span></>}
    </span>
  );
}
