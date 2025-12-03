function renderStatusChart(canvasId, approved, pending) {
  if (!document.getElementById(canvasId)) return;
  new Chart(document.getElementById(canvasId), {
    type: 'doughnut',
    data: {
      labels: ['Approved','Pending'],
      datasets: [{ data: [approved, pending], backgroundColor:['#2e8b57','#ff9f43'] }]
    }
  });
}
function renderLineChart(canvasId, labels, values) {
  if (!document.getElementById(canvasId)) return;
  new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: { labels: labels, datasets: [{ label:'Reports', data: values, fill:true, backgroundColor:'rgba(46,139,87,0.12)', borderColor:'#2e8b57', tension:0.2 }] }
  });
}
