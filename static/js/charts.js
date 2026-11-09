(() => {
  'use strict';
  function buildChart(canvasId, dataId) {
    const canvas = document.getElementById(canvasId);
    const source = document.getElementById(dataId);
    if (!canvas || !source) return;
    const fallback = document.getElementById('chart-fallback');
    if (!window.Chart) { canvas.hidden = true; if (fallback) fallback.hidden = false; return; }
    try {
      const data = JSON.parse(source.textContent);
      const font = "'Be Vietnam Pro', 'Segoe UI', sans-serif";
      new Chart(canvas, {
        type: 'bar',
        data: { labels: data.labels, datasets: [
          { label: 'Nhập kho', data: data.inbound, backgroundColor: '#27a78e', hoverBackgroundColor: '#138e76', borderRadius: 3, maxBarThickness: 17, categoryPercentage: .68, barPercentage: .78 },
          { label: 'Xuất kho', data: data.outbound, backgroundColor: '#bdd5e4', hoverBackgroundColor: '#8fb5cf', borderRadius: 3, maxBarThickness: 17, categoryPercentage: .68, barPercentage: .78 }
        ] },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 450 },
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { display: false }, tooltip: { backgroundColor: '#18304b', titleFont: { family: font, size: 10, weight: 500 }, bodyFont: { family: font, size: 10 }, padding: 12, cornerRadius: 8, displayColors: true, boxWidth: 6, boxHeight: 6, callbacks: { label: context => `${context.dataset.label}: ${Number(context.parsed.y).toLocaleString('vi-VN')} đơn vị` } } },
          scales: {
            x: { border: { display: false }, grid: { display: false }, ticks: { color: '#9daabb', maxRotation: 0, maxTicksLimit: 8, font: { family: font, size: 8 }, padding: 9 } },
            y: { beginAtZero: true, border: { display: false }, grid: { color: '#f0f3f7', drawTicks: false }, ticks: { color: '#a6b1be', maxTicksLimit: 5, font: { family: font, size: 8 }, padding: 12, callback: value => Number(value).toLocaleString('vi-VN') } }
          }
        }
      });
    } catch (_) { canvas.hidden = true; if (fallback) fallback.hidden = false; }
  }
  buildChart('movement-chart', 'movement-chart-data');
})();
