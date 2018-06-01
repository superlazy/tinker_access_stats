var stats = {};

var init = function()
{
  url = 'http://tinker-access.s3-website-us-east-1.amazonaws.com/tinker-access-stats.json';

  $.ajax(
    {
      method: 'GET',
      url: url,
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
      $('<option>')
        .text(tool)
        .appendTo(select);

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
    shifted[i] = stats[tool][day][(i+offset)%24];

  var barChartData = {
    labels: ['Midnight', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am', '10am', '11am', 'noon', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm'],
    datasets: [{
      label: '% In Use',
      borderWidth: 1,
      data: shifted
    }]
  };

  var ctx = document.getElementById('histogram').getContext('2d');
  window.myBar = new Chart(ctx, {
    type: 'bar',
    data: barChartData,
    options: {
      responsive: true,
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: tool + ' usage history on ' + day + 's'
      }
    }
  });
};


