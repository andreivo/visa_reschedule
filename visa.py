# -*- coding: utf8 -*-

import time
import json
import random
import platform
import configparser
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE'] 
FACILITY_ID = config['USVISA']['FACILITY_ID']

SENDGRID_API_KEY = config['SENDGRID']['SENDGRID_API_KEY']
PUSH_TOKEN = config['PUSHOVER']['PUSH_TOKEN']
PUSH_USER = config['PUSHOVER']['PUSH_USER']

LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

REGEX_CONTINUE = "//a[contains(text(),'Continuar')]"

# def MY_CONDITION(month, day): return int(month) == 11 and int(day) >= 5
def MY_CONDITION(month, day): return True # No custom condition wanted for the new scheduled date

STEP_TIME = 0.5  # time between steps (interactions with forms): 0.5 seconds
RETRY_TIME = 60*10  # wait time between retries/checks for available dates: 10 minutes
EXCEPTION_TIME = 60*30  # wait time when an exception occurs: 30 minutes
COOLDOWN_TIME = 60*60  # wait time when temporary banned (empty list): 60 minutes

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False

def send_notification(msg):
    print(f"Sending notification: {msg}")

    if SENDGRID_API_KEY:
        print(f"Sending SENDGRID_API: {SENDGRID_API_KEY}")
        message = Mail(
            from_email=USERNAME,
            to_emails=USERNAME,
            subject=f"VISA-REESCHEDULER ({SCHEDULE_ID})",
            html_content=msg)
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            print(response.status_code)
            print(response.body)
            print(response.headers)
        except Exception as e:
            print(e.message)

    if PUSH_TOKEN:
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSH_TOKEN,
            "user": PUSH_USER,
            "message": msg
        }
        requests.post(url, data)

def get_driver():
    print("get_driver...")
    #options_ = webdriver.ChromeOptions()
    #options_.add_argument("--headless")
    
    if LOCAL_USE:
        dr = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    else:
        dr = webdriver.Remote(command_executor=HUB_ADDRESS, options=webdriver.ChromeOptions())    
    print("end get_driver...")
    return dr

driver = get_driver()


def login():
    # Bypass reCAPTCHA
    driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
    time.sleep(STEP_TIME)
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)
    
    print("Login start...")
    href = driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[1]/div[1]/div[2]/div[1]/ul/li[3]/a')
   
    href.click()
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

    print("\tclick bounce")
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)

    do_login_action()


def do_login_action():
    print("\tinput email")
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    time.sleep(random.randint(1, 3))

    print("\tinput pwd")
    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    time.sleep(random.randint(1, 3))

    print("\tclick privacy")
    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box .click()
    time.sleep(random.randint(1, 3))

    print("\tcommit")
    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    print("\tlogin successful!")

def go_to_reschedulepage():
    print("Go to reschedule page...")
    print("\tcontinue")
    a = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div[2]/div[1]/div/div/div[1]/div[2]/ul/li/a')
    a.click()
    time.sleep(STEP_TIME)
    
    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="forms"]/ul/li[4]')))
          
    print("\treschedule 1 ")
    a = driver.find_element(By.XPATH, '//*[@id="forms"]/ul/li[4]')
    a.click()
    time.sleep(STEP_TIME)
    
    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[4]/main/div[2]/div[2]/div/section/ul/li[4]/div/div/div[2]/p[2]/a')))
                   
    print("\treschedule 2 - button")
    a = driver.find_element(By.XPATH, '/html/body/div[4]/main/div[2]/div[2]/div/section/ul/li[4]/div/div/div[2]/p[2]/a')
    a.click()
    time.sleep(STEP_TIME)
    
    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="appointments_consulate_appointment_facility_id"]')))   

def get_consulateDate():    
    print("\tget_consulatedate")
    #########################
    # Workaround to avoid blocking the site (we use a $.getJSON insted of native driver.get with a son.loads)
    #
    # original code
    # ---------------------------------------
    # driver.get(DATE_URL)
    # if not is_logged_in():
    #     login()
    #     return get_date()
    # else:
    #     content = driver.find_element(By.TAG_NAME, 'pre').text
    #     date = json.loads(content)
    #     return date
    # ---------------------------------------
    #########################
    
    # execute $.getJSON and writes a <pre> html element
    driver.execute_script(f'var resultConsulateDate,prescript=$("<pre />");prescript.attr({{id:"getConsulateDate_done",name:"getConsulateDate_done"}}),$.getJSON("{DATE_URL}",(function(e){{resultConsulateDate=e}})).done((function(){{$("body").append(prescript),document.getElementById("getConsulateDate_done").innerHTML=JSON.stringify(resultConsulateDate)}}));')    
    # wait for a <pre> html element
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'getConsulateDate_done')))
    # get data from <pre> html element
    dates = driver.execute_script('return JSON.parse(document.getElementById("getConsulateDate_done").innerHTML);')
    print("")    
    print("\tend get_consulatedate")    
    return dates
    
def get_consulateTime(date):
    print("\tget_consulatetime")
    #########################
    # Workaround to avoid blocking the site (we use a $.getJSON insted of native driver.get with a son.loads)
    #
    # original code
    # ---------------------------------------
    # time_url = TIME_URL % date
    # driver.get(time_url)
    # content = driver.find_element(By.TAG_NAME, 'pre').text
    # data = json.loads(content)
    # time = data.get("available_times")[-1]
    # print(f"Got time successfully! {date} {time}")
    # return time
    # ---------------------------------------    
    #########################
    
    time_url = TIME_URL % date
    # execute $.getJSON and writes a <pre> html element
    driver.execute_script(f'var resultConsulateTime,prescript=$("<pre />");prescript.attr({{id:"getConsulateTime_done",name:"getConsulateTime_done"}}),$.getJSON("{time_url}",(function(e){{resultConsulateTime=e}})).done((function(){{$("body").append(prescript),document.getElementById("getConsulateTime_done").innerHTML=JSON.stringify(resultConsulateTime)}}));')    
    # wait for a <pre> html element
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'getConsulateTime_done')))
    # get data from <pre> html element
    times = driver.execute_script('return JSON.parse(document.getElementById("getConsulateTime_done").innerHTML);')
    print("")       
    time = times.get("available_times")[-1]
    print(f"\tGot time successfully! {date} {time}")
    print("\tend get_consulatetime")  
    return time
    
def get_time(date):
    time_url = TIME_URL % date
    driver.get(time_url)
    content = driver.find_element(By.TAG_NAME, 'pre').text
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time       
    
def reschedule_best_date():
    consulateDates = get_consulateDate()[:5]
    if not consulateDates:
        msg = f"List of consulate dates is empty. Query is {datetime.today()}"
        send_notification(msg)
        return False
        
    print_dates(consulateDates)
    consulateDate = get_available_date(consulateDates)
    print()
    print(f"New date: {consulateDate}")
    if consulateDate:
        consulateTime = get_consulateTime(date)
        print(f"reschedule({date})")
        # reschedule(date)
        # push_notification(dates)

    return True

def reschedule(date):
    global EXIT
    print(f"Starting Reschedule ({date})")

    time = get_time(date)
    driver.get(APPOINTMENT_URL)

    data = {
        "utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
        "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": FACILITY_ID,
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }

    r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    if(r.text.find('Successfully Scheduled') != -1):
        msg = f"Rescheduled Successfully! {date} {time}"
        send_notification(msg)
        EXIT = True
    else:
        msg = f"Reschedule Failed. {date} {time}"
        send_notification(msg)


def is_logged_in():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def print_dates(dates):
    print("Available dates:")
    for d in dates:
        print("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))
    print()

last_seen = None

def get_available_date(dates):
    global last_seen

    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        print(f'Is {my_date} > {new_date}:\t{result}')
        return result

    print("Checking for an earlier date:")
    for d in dates:
        date = d.get('date')
        if is_earlier(date) and date != last_seen:
            _, month, day = date.split('-')
            if(MY_CONDITION(month, day)):
                last_seen = date
                return date


def push_notification(dates):
    msg = "date: "
    for d in dates:
        msg = msg + d.get('date') + '; '
    send_notification(msg)


if __name__ == "__main__":
    try:
        login()
        retry_count = 0
        while 1:    
            if retry_count > 6:
                break
            try:
                print("------------------")
                print(datetime.today())
                print(f"Retry count: {retry_count}")
                print()

                go_to_reschedulepage()

                EXIT = not reschedule_best_date()

                #dates = get_date()[:5]
                #if not dates:
                #  msg = "List is empty"
                #  send_notification(msg)
                #  EXIT = True
                #print_dates(dates)
                #date = get_available_date(dates)
                #print()
                #print(f"New date: {date}")
                #if date:
                #    print(f"reschedule({date})")
                    # reschedule(date)
                    # push_notification(dates)

                if(EXIT):
                    print("------------------exit")
                    break

                if not dates:
                  msg = "List is empty"
                  send_notification(msg)
                  #EXIT = True
                  time.sleep(COOLDOWN_TIME)
                else:
                  time.sleep(RETRY_TIME)

            except:
                print("------------------")
                print(f"Exception: Sleep {EXCEPTION_TIME}")
                retry_count += 1
                time.sleep(EXCEPTION_TIME)

        if(not EXIT):
            send_notification("HELP! Crashed.")

    except Exception as EX:         
        print("------------------")
        print(f"Exception: {EX}")
        #msg = f"Failed attempt on {datetime.today()}"
        #send_notification(msg)