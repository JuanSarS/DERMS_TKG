/** Gráficos sincronizados de energía y condiciones eléctricas. */
import Chart from "chart.js/auto";

const instances = new Map();

export function drawSeries(canvas, rows, title, fields, options = {}) {
  if (!canvas) return;
  const old = instances.get(canvas.id);
  if (old) old.destroy();
  const colors = ["#3cb5e6", "#4bd49d", "#edb65d", "#c89ff6", "#ef7d78"];
  const datasets = fields.map((field, i) => ({
    label: field.label,
    data: rows.map((r) => r[field.key] ?? null),
    borderColor: colors[i % colors.length],
    pointRadius: 0,
    tension: 0.17,
    borderWidth: 2,
    spanGaps: false,
  }));
  const chart = new Chart(canvas, {
    type: "line",
    data: { labels: rows.map((r) => r.step), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { labels: { color: "#cbd7e4" } },
        title: { display: true, text: title, color: "#e8f0fb" },
      },
      scales: { x: { ticks: { color: "#8997ae" } }, y: { ticks: { color: "#8997ae" } } },
      ...options,
    },
  });
  instances.set(canvas.id, chart);
}
