#!/usr/bin/env python
"""
Simple application to serve up JSON data using a few API endpoints.

"""
import sys
import os
from flask import Flask
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route('/current_conditions')
def current_conditions():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON is the current conditions.
  """
  with open('/var/www/html/dist/current_conditions.json', 'r') as cc:
    rettext = cc.read()
    return rettext


@app.route('/forecast')
def forecast():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON is the current forecast for 
  today and a few days in the future.
  """

  with open('/var/www/html/dist/forecast.json', 'r') as cc:
    forecastdict = cc.read()
    return forecastdict


@app.route('/alerts')
def alerts():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON contains all current alerts, 
  watches, warnings, and the hazardous weather outlook for a given county or 
  set of counties.
  """
  with open('/var/www/html/dist/alerts.json', 'r') as cc:
    alerts_text = cc.read()
    return alerts_text


@app.route('/afd')
def afd():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON is the area forecast discussion.
  """
  with open('/var/www/html/dist/afd.json', 'r') as cc:
    afd_text = cc.read()
    return afd_text


@app.route('/satellite')
def satellite():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON is the current conditions.

  """
  with open('/var/www/html/dist/goes.json', 'r') as cc:
    sat_text = cc.read()
    return sat_text


@app.route('/zoneforecast')
def zoneforecast():
  """
  Each of these small functions reads the current JSON from a location and
  provides it for HTTP API calls. This JSON is the text forecast for
  today and up to six days in the future.
  """

  with open('/var/www/html/dist/zoneforecast.json', 'r') as cc:
    zoneforecastdict = cc.read()
    return zoneforecastdict
