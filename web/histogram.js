var stats = {};
var dataUrl = 'http://tinker-access.s3-website-us-east-1.amazonaws.com/tinker-access-stats.json';
var barChartData = {
	labels: ['Midnight', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am', '10am', '11am', 'Noon', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm'],
	datasets: []
};



var init = function()
{
	var ctx = document.getElementById('histogram').getContext('2d');
	window.myBar = new Chart(ctx, {
		type: 'bar',
		data: barChartData,
		options: {
			scales: {
				yAxes : [{
					ticks : {
						max : 100,
						min : 0
					}
				}]
			},
			responsive: true,
			legend: {
				position: 'top',
			},
			title: {
				display: true,
				text: 'Select Tool and Day of Week'
			}
		}
	});

  $.ajax(
    {
      method: 'GET',
      url: dataUrl,
      success: initSuccess,
      error: initError
    }
  );
};


var initSuccess = function(response)
{
  select = $('#toolSelect');
  stats  = JSON.parse(response);

  for( var tool in stats )
    if( stats.hasOwnProperty(tool) )
    	if( tool !== 'updated' )
				$('<option>')
					.text(tool)
					.appendTo(select);

  $('.update').text('Statistics last updated on ' + new Date(stats['updated']*1000));
  changeTool();
};


var initError = function(response)
{
  console.log(response);
};


var changeTool = function()
{
  var tool = $('#toolSelect').val();
  var day  = $('#daySelect').val();

  var offset  = new Date().getTimezoneOffset() / 60;
  var shifted = [];
  for( var i = 0; i < 24; i++ )
    shifted[i] = 100 * stats[tool][day][(i+offset)%24];

	var title = tool + ' usage history on ' + day + 's';
  barChartData.datasets.length = 0;
	var newDataset = {
		label: '% In Use',
		borderWidth: 1,
		data: shifted
	};
	barChartData.datasets.push(newDataset);
	window.myBar.update();
};

