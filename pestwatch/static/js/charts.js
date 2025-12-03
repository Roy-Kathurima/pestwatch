function renderDoughnut(canvasId, a, b) {
  if (!document.getElementById(canvasId)) return;
  new Chart(document.getElementById(canvasId), {
    type: 'doughnut',
    data: { labels: ['Approved','Pending'], datasets: [{ data: [a,b], backgroundColor: ['#167f74','#ff9f43'] }] }
  });
}

function renderLine(canvasId, labels, values) {
  if (!document.getElementById(canvasId)) return;
  new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: { labels: labels, datasets: [{ label: 'Reports', data: values, fill: true, backgroundColor: 'rgba(22,127,116,0.12)', borderColor: '#167f74' }] }
  });
}
