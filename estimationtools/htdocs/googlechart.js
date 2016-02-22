var EstimationCharts = [];
google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(function() {
  for (var n = 0; n < EstimationCharts.length; n++)
    EstimationCharts[n]();
});

function DrawBurndownChart(data, args) {
  var hticks = [];
  for (var n=1; n<data.length; n++) {
    var d = new Date(data[n][0])
    data[n][0] = d;
    if (n==1 || n==data.length-1 || d.getDate() == 1)
      hticks.push(d);
  }
  // args['options']['hAxis']['ticks'] = hticks;
  args['dataTable'] = data;
  google.visualization.drawChart(args);
}
