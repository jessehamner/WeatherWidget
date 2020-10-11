
function generateTableHead(table) {
  let thead = table.createTHead();
  let row = thead.insertRow();
  let columns = ["Conditions", "Temps", "Precip"];
  for (let i in columns) {
    let th = document.createElement("th");
    let text = document.createTextNode(i);
    th.appendChild(text);
    row.appendChild(th);
  }
}

function forecastrow(forecast, idx) {
  var daystring = "day" + idx + "";
  var summary = "summary" + daystring;
  var icon = "fc_icon_" + idx + "";
  document.getElementById(daystring).innerHTML += forecast[idx].day;
  document.getElementById(summary).innerHTML += forecast[idx].shortcast;
  document.getElementById(icon).src = "static/icons/weather-icons-master/svg/" + forecast[idx].icon;
}


function insertSVG(svgpath, id) {
  document.getElementById(id).setAttribute("data", svgpath);
}


function write_one_row(forecast, idx) {
  var height1 = "50";
  var width2 = "65";
  var width1 = "50";
  var daystring = "day" + idx + "";
  var summary = "summary" + daystring;
  var icon = "fc_icon_" + idx + "";
  var temp = "today_temp_plus_" + idx + ".svg";
  var precip = "today_precip_plus_" + idx + ".svg";
 
  var subheader = '<div class="d-flex align-items-center"><span><div class="subheader" id="' + daystring + '">' + forecast[idx].day + '</div></span></div>';
  var weather = '<div class="d-flex align-items-baseline"><span class="bg-gray forecastDiv mr-3" style="--icon-height: ' + height1 + 'px;"><img id="' + icon + '"  src="static/icons/weather-icons-master/svg/' + forecast[idx].icon + '" alt="weather icon daytime" width="' + width1 + '" height="' + height1 + '"></span>';
  var temps_pane = '<span class="bg-gray forecastDiv mr-3" style="--icon-height: ' + height1 + 'px;"><img src="static/photos/' + temp + '" alt="weather icon today temperatures" width="' + width1 + '" height="' + height1 + '"></span>';
  var precip_pane = '<span class="forecastDiv" style="--icon-height: ' + height1 + 'px;"> <img src="static/photos/' + precip + '" alt="weather icon today precipitation chances" width="' + width2 + '" height="' + height1  + '"></span></div>';
  var summarytext = '<div class="text-muted" style="font-size: large" id="' + summary + '">' + forecast[idx].shortcast + '</div>';

  return subheader + weather + temps_pane + precip_pane + summarytext;
}


let request_forecast = new XMLHttpRequest();
request_forecast.open("GET", "http://192.168.0.199:5000/forecast");
request_forecast.send();
request_forecast.onload = () => {
  console.log(request_forecast);
  if (request_forecast.status == 200) {
    console.log(request_forecast.responseText);
    let forecast = JSON.parse(request_forecast.responseText);
    for (var j=0; j < 4; j++ ) {
      document.getElementById("allforecast").innerHTML += write_one_row(forecast, j);
    }
  } else {
    console.log(`error ${request_forecast.status} ${request_forecast.statusText}`);
  }
}

let afd = new XMLHttpRequest();
afd.open("GET", "http://192.168.0.199:5000/afd");
afd.send();
afd.onload = () => {
  console.log(afd);
  if (afd.status == 200) {
    let afd_text = JSON.parse(afd.responseText);
    console.log(afd.responseText);
    document.getElementById("afd1").innerHTML += afd_text.short_term ;
    document.getElementById("afd2").innerHTML += afd_text.long_term ;
    document.getElementById("long-term-forecast-header").innerHTML += afd_text.long_title ;
    document.getElementById("short-term-forecast-header").innerHTML += afd_text.short_title ;
  } else {
    console.log(`error ${afd.status} ${afd.statusText}`);
  }
}



