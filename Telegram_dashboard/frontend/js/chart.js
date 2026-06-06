let chartInstance = null;

const palette = [
  "#2aabee",
  "#6c5ce7",
  "#3dd68c",
  "#f9ca24",
  "#f07178",
  "#00cec9",
];

export function renderCommandChart(canvas, analytics) {
  if (!canvas || !window.Chart) return;

  const labels = analytics?.labels || [];
  const datasets = (analytics?.datasets || []).map((dataset, index) => ({
    label: dataset.label,
    data: dataset.data,
    borderColor: palette[index % palette.length],
    backgroundColor: `${palette[index % palette.length]}33`,
    tension: 0.3,
    fill: true,
  }));

  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets = datasets;
    chartInstance.update();
    return;
  }

  chartInstance = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}
