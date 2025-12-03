function renderStatusChart(canvasId, approved, pending) {
  var ctx = document.getElementById(canvasId).getContext('2d');
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Approved', 'Pending'],
      datasets: [{
        data: [approved, pending],
        backgroundColor: ['#2e8b57', '#ff9f43']
      }]
    },
    options: { responsive:true, maintainAspectRatio:false }
  });
}

function renderLineChart(canvasId, labels, dataPoints) {
  var ctx = document.getElementById(canvasId).getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Reports',
        data: dataPoints,
        fill: true,
        backgroundColor: 'rgba(46,139,87,0.12)',
        borderColor: '#2e8b57',
        tension: 0.2
      }]
    },
    options: { responsive:true, maintainAspectRatio:false }
  });
}

function renderMiniChart(containerId, approved, pending){
  // create a small inline canvas
  var container = document.getElementById(containerId);
  container.innerHTML = '<canvas id="miniCanvas" style="height:120px"></canvas>';
  renderStatusChart('miniCanvas', approved, pending);
}
