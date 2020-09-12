
var imgpath = "static/icons/weather-icons-master/svg/";

function addSVGIcon(svgpath, id, width, height) {
  var svgtext = '<object id="' + id + '" data="' + svgpath + '" width="' + width + '" height="' + height + '" type="image/svg+xml"></object>';
  //var svgtext = '<embed id="' + id + '" src="' + svgpath + '" width="' + width + '" height="' + height + '" type="image/svg+xml">';
  console.log(svgtext);
  return svgtext;
}


function roundNicely(value) {
  if (isNaN(Math.round(value))) {
        console.log("Not a number.");
        value = "None";
  } else {
    value = Math.round(value);
  }
  return value;
}


function writeline(value, unit, label) {
  var tablerow = "";
  value = roundNicely(value);
  if (value == "None") {
    unit = "";
  }
  console.log("Now: " + value);
  tablerow = '<tr><td style="padding:3px;">' + label + "</td><td>" + value + " " + unit + '</td></tr>';
  return tablerow;
}


function coolrow(table, obs) {
  let row = document.createElement("tr");
  var value;
  var unit;
  let td = document.createElement("td");
  let text = document.createTextNode(obs['label']);
  td.appendChild(text);
  row.appendChild(td);

  let td1 = document.createElement("td");
  value = roundNicely(obs['value']);
  if (value == "None") {
    unit = "";
  } else {
    unit = obs['units'];
  }

  let text1 = document.createTextNode(value + ' ' + unit);
  td1.appendChild(text1);
  td1.setAttribute('class', "paddedCells");
  row.appendChild(td1);
  return row;
}



let request = new XMLHttpRequest();
request.open("GET", "http://192.168.0.199:5000/current_conditions");
request.send();
request.onload = () => {
  console.log(request);
  if (request.status == 200) {
    console.log(request.responseText);
    var curDict = JSON.parse(request.responseText);
    var table0 = '<table id="table0"><tr><td id="cc_col1"></td><td>&nbsp;&nbsp;</td><td id="cc_col2"></td></tr></table>';
    var table1 = '<table id="table1" style="font-size: large">';
    table1 = table1 + "<tr><td>Currently:</td><td class=\"paddedCells\">" + curDict["textdescription"] + "</td></tr>";
    table1 = table1 + '</table>';
    var table2 = '<table id="table2" align="right"><tr><td id="weather_icon_here"></td></tr><tr><td id="wind_direction_icon_here"></td></tr><tr><td id="beaufort_icon"></td></tr></table>';
    var numberkeys = ["temperature", "dewpoint", "humidity", "heatindex", "windchill", "wind", "gusts"];

    document.getElementById("currentConditions").innerHTML += table0 + ' ';

    document.getElementById("cc_col1").innerHTML += table1;
    var tableRef = document.getElementById("table1");
    for (var i of numberkeys) {
      console.log("Rounded value for " + curDict[i]['label'] + " (currently: " + curDict[i]['value'] + ")");
      tableRef.appendChild(coolrow(table1, curDict[i]));
    }
    document.getElementById("table1").innerHTML += "<tr><td>Wind</td><td class=\"paddedCells\">" + curDict["wind_cardinal"] + "</td></tr>";
    document.getElementById("table1").innerHTML += "<tr><td>Pressure</td><td class=\"paddedCells\">" + curDict["pressure"]["value"].toFixed(2) + " " + curDict["pressure"]["units"] + "</td></tr>";

    document.getElementById("cc_col2").innerHTML += table2;
    document.getElementById("weather_icon_here").innerHTML += addSVGIcon(imgpath + curDict['weather_icon'], id="current_weather_icon", width=70, height=70);
    document.getElementById("wind_direction_icon_here").innerHTML += addSVGIcon(imgpath + 'compass.svg', id="current_wind_direction", width=70, height=50);
    var wind_direction_arrow = (curDict['wind_direction']['value']) -180;
    document.getElementById("wind_direction_icon_here").style.transform = "rotate(" + wind_direction_arrow + "deg)";
    var bficon;
    var bfscale;
    if (typeof curDict['beaufort'] == 'number') {
      bfscale = curDict['beaufort'];
    }
    if (typeof(parseInt(curDict['beaufort']) == 'number')){
      bfscale = parseInt(curDict['beaufort']); 
    }
    if (isNaN(bfscale)) {
      bficon = 'wi-na.svg';
    } else {
      bficon = 'wi-wind-beaufort-' + bfscale + '.svg';
    }
    document.getElementById("beaufort_icon").innerHTML += addSVGIcon(imgpath + bficon, id="current_wind_speed", width=70, height=70);
    document.getElementById("moonphase").innerHTML += addSVGIcon(imgpath + curDict['moon_icon'], id="current_moon_phase", width=30, height=30);
  } else {
    console.log(`error ${request.status} ${request.statusText}`);
  }
}

let request2 = new XMLHttpRequest();
request2.open("GET", "http://192.168.0.199:5000/satellite");
request2.send();
request2.onload = () => {
  console.log(request2);
  if (request2.status == 200) {
    console.log(request2.responseText);
    var satdict = JSON.parse(request2.responseText);
    document.getElementById("sat_image_thumb").innerHTML += satdict['image_html'];
  }
}
