
function generateIconImage(iconname, alt_text) {
  var img = new Image();
  img.alt = alt_text;
  img.src = imgpath + iconname;
  img.width = "40";
  img.height = "40";
  return img;
}


function insertSVG(svgpath, id) {
  document.getElementById(id).setAttribute("data", svgpath);
}


function addSVGIcon(svgpath, id, width, height) {
  var svgtext = '<object id="' + id + '" data="' + svgpath + '" width="' + width + '" height="' + height + '" type="image/svg+xml"></object>';
  //var svgtext = '<embed id="' + id + '" src="' + svgpath + '" width="' + width + '" height="' + height + '" type="image/svg+xml">';
  console.log(svgtext);
  return svgtext;
}


function writeWarningsRow() {
  document.getElementById("warnings_row").innerHTML = '<div class="col-sm-9" id="warnings_row_container"></div>';
}


function writeWarningCard(eventdict, idx, warningicon) {
  var warniconlabel = 'warning' + idx;
  document.getElementById("warnings_row_container").innerHTML += '<div class="alert alert-danger" role="alert"><table><tr><td>' + addSVGIcon(svgpath=warningicon, id=warniconlabel, width=40, height=40) + '</td><td><h3>' + eventdict['event_type'] + ':</h3></td></tr></table>' + eventdict['summary'] + "</div>";
}


var imgpath = "static/icons/weather-icons-master/svg/";
var i;
var warning_icon;
var cardstring;
let requestg = new XMLHttpRequest();
requestg.open("GET", "http://192.168.0.199:5000/alerts");
requestg.send();
requestg.onload = () => {
  console.log(requestg);
  if (requestg.status == 200) {
    console.log("Alerts dictionary: ");
    var alertdict = JSON.parse(requestg.responseText);
    Object.entries(alertdict).forEach(([key, value]) => {
      console.log(key, value);
    });

    console.log('Day one HWO label: ' + alertdict['hwo']['dayone'][0]);
    console.log('Day one HWO content: ' + alertdict['hwo']['dayone'][1]);
    document.getElementById("hwo_dayonelabel").innerHTML += alertdict['hwo']['dayone'][0];
    document.getElementById("hwo_dayonecontent").innerHTML += alertdict['hwo']['dayone'][1];

    if (Boolean(alertdict['flags']['has_spotter'])) {
      document.getElementById("hwo_badge").className = "badge bg-yellow";
      document.getElementById("hwo_spotter").innerHTML += alertdict['hwo']['spotter'][1];
    } else {
      document.getElementById("hwo_badge").className = "badge bg-green";
      document.getElementById("hwo_spotter").innerHTML += "Spotter activation is not expected at this time.";
    }


    if (Boolean(alertdict['flags']['has_alerts'])) {
      console.log('Found alerts. Proceeding.');
      document.getElementById("alert_badge").className = "badge bg-yellow";
      document.getElementById("alert_badge").innerHTML += "Alert";
      for (var somealert of alertdict['alert']) {
        warning_icon = imgpath + somealert['alert_icon'];
        cardstring = '<div class="modal-body"><table><tr><td>' + addSVGIcon(svgpath=warning_icon, id="", width=40, height=40) + '</td><td><h4>' + somealert['event_type'] + ':</h4></td></tr></table>' + somealert['summary'] + '</div>';
        document.getElementById("alerts_entries").innerHTML += cardstring;
        console.log('Alert: ' + somealert);
      }


    } else {
      document.getElementById("alert_badge").className = "badge bg-green";
    }


    if (Boolean(alertdict['flags']['has_watches'])) {
      document.getElementById("watch_badge").className = "badge bg-orange";
      document.getElementById("watch_badge").innerHTML += "Watch";
    } else {
      document.getElementById("watch_badge").className = "badge bg-green";
    }


    if (Boolean(alertdict['flags']['has_warnings'])) {
      writeWarningsRow();
      for (var i in alertdict['warn']) {
        console.log('Warning list entry: ' + alertdict['warn'][i]['event_type']);
        warning_icon = imgpath + alertdict['warn'][i]['alert_icon'];
        writeWarningCard(alertdict['warn'][i], i, warning_icon);
      }
    }

    var para;
    var textnode;
    var summary;
    var h3;
    const keys = Object.keys(alertdict);
    console.log("Keys: " + keys );
    for (i of alertdict['watch']) {
      console.log('Alert dictionary entry: ' + i['event_type']);
      para = document.createElement("div");
      para.setAttribute("class", "alert alert-warning");
      para.setAttribute("role", "alert");
      summary = document.createTextNode(i['summary']);
      h3 = document.createElement("h3");
      textnode = document.createTextNode(i['event_type']);
      h3.appendChild(generateIconImage(i['alert_icon'], 'specific watch icon'));
      h3.appendChild(textnode);
      para.appendChild(h3);
      para.appendChild(summary);

      document.getElementById("watch_entries").appendChild(para);
      if (i['severity'] == "Severe") {
        console.log("Severity: " + i['severity']);
        if (i['certainty'] == "Observed") {
          document.getElementById("alert_icon_placeholder").appendChild(generateIconImage('watch.svg', 'weather watch icon'));
          document.getElementById("warning_alerts").appendChild(generateIconImage('watch.svg', 'weather watch icon'));
          document.getElementById("warning_alerts").innerHTML += i['event_type'] + "<br>";
        } else if (i['certainty'] == "Likely") {
          document.getElementById("alert_icon_placeholder").appendChild(generateIconImage('watch.svg', 'weather watch icon'));
        }
      }
      console.log("Certainty: " + i['certainty']);
    }
  } else {
    console.log(`error ${requestg.status} ${requestg.statusText}`);
  }
}

