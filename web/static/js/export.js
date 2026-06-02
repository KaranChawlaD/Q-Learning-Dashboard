/** Download the current training run as a JSON file (client-side, no server storage). */

export function downloadRunExport(data) {
  const stamp = data.exported_at?.slice(0, 19).replace(/[:T]/g, "-") ?? "run";
  const filename = `qlearning-run-${stamp}.json`;
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function requestRunExport(sendCommand) {
  return sendCommand({ type: "export" });
}
