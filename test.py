# -*- coding: utf8 -*-

import time
import json
import random
import platform
import configparser
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DATE_URL = "https://jsonplaceholder.typicode.com/todos"

def get_driver():
    print("get_driver...")
    #options_ = webdriver.ChromeOptions()
    #options_.add_argument("--headless")
    
    dr = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
  
    print("end get_driver...")
    return dr

driver = get_driver()

def get_date():
    print("\tget_consulatedate")
    # wait for the elment to be presented
    driver.execute_script(f'var resultConsulateDate,prescript=$("<pre />");prescript.attr({{id:"getConsulateDate_done",name:"getConsulateDate_done"}}),$.getJSON("{DATE_URL}",(function(e){{resultConsulateDate=e}})).done((function(){{$("body").append(prescript),document.getElementById("getConsulateDate_done").innerHTML=JSON.stringify(resultConsulateDate)}}));')    
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'getConsulateDate_done')))
    # print the text of the element    
    dates = driver.execute_script('return JSON.parse(document.getElementById("getConsulateDate_done").innerHTML);')
    print("")    
    print("\tend get_consulatedate")    
    return dates
    
def print_dates(dates):
    print("Available dates:")
    for d in dates:
        print("%s \t business_day: %s" % (d.get('id'), d.get('title')))
    print()
    
    
driver.get("https://api.jquery.com/jquery.getjson/")    
time.sleep(0.5)
    
Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, '/html/body')))  
    
d = get_date()
print_dates(d)

