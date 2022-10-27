import selenium
import random
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import time, subprocess
import yaml


# TODO:
# 1. specific time run
# 2. change sleep to clicable condition
# 3. more setting for date and month
# 4. email notification
# 5. logging


UNCLICABLE_CLASS = "ui-state-disabled"

def wait_response(seconds=1):
  time.sleep(seconds)


def read_config(file_path):
  with open(file_path, "r") as f:
    return yaml.safe_load(f)

def get_page_source(driver):
  pageSource = driver.page_source
  with open("page_source.html", "w") as fileToWrite:
    fileToWrite.write(pageSource)
  with open("page_source.html", "r") as fileToRead:
    print(fileToRead.read())

def get_to_appointment_page(driver, CFG):
  reached_daily_limit = False
  driver.get(CFG['appointment_page'])  
  wait_response(seconds = 3)
  try:
    driver.find_element(By.ID,"appointments_consulate_appointment_date_input").click()
    wait_response(seconds = 1)
  except selenium.common.exceptions.ElementNotInteractableException:
    reached_daily_limit = True
    print("reached daily limit")
  return reached_daily_limit

def get_to_login_page(driver, CFG):
  no_internet = False
  try:
    driver.get("https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    #get_page_source(driver)
    wait_response(seconds = 2)
    username = driver.find_element(By.ID, "user_email")
    username.clear()
    username.send_keys(CFG['email']) 
    password = driver.find_element(By.ID, "user_password")
    password.clear()
    password.send_keys(CFG['pwd'])
    policy = driver.find_element(By.ID, "policy_confirmed")
    driver.execute_script("arguments[0].click();", policy)
    driver.find_element(By.NAME, "commit").click()
    wait_response(seconds = 3)
  except selenium.common.exceptions.WebDriverException:
    no_internet = True
    print("no internet connection")
  return no_internet

def is_bookable(month, date_str):
  bookable = False
  stop_checking = False
  # change below into the criteria you like
  date_num = int(date_str)
  if month == "November" and date_num >= 13:
    bookable = True
  elif month == "December":
    bookable = True
  elif month == "January" and date_num <= 13:
    bookable = True
  elif month in ["Feburary", "March"]:
    bookable = True
  else:
    stop_checking = True
  return bookable, stop_checking


def schedule_appointment(driver, month, date_str, debug):
  # get time slots
  driver.find_element(By.CSS_SELECTOR, "#appointments_consulate_appointment_time_input").click()
  wait_response(seconds = 1)
  # select time slot
  driver.find_element(By.CSS_SELECTOR, "#appointments_consulate_appointment_time > option:nth-child(2)").click()
  wait_response(seconds = 1)
  # schedule
  driver.find_element(By.NAME, "commit").click()
  wait_response(seconds = 1)
  # confirmation page
  confirm_botton = driver.find_element(By.CSS_SELECTOR, "body > div.reveal-overlay > div > div > a.button.alert")
  confirmable = confirm_botton.is_displayed()
  print(f"confirmable: {confirmable}.")
  if not debug:
    confirm_botton.click()
    message = f"Successfully rescheduled! date {month}-{date_str}"
  else:
    message = f"In debug mode, can schedule date {month}-{date_str} but won't schedule."
  print(message)
  # linux system specific sound notification
  # subprocess.call(["spd-say", message])
  return True

def get_appointment_date(driver):
  find_date = False
  stop_checking = False
  while True:
    # check calendar on the left
    left_calendar = driver.find_element(By.CSS_SELECTOR, "div.ui-datepicker-group-first")		
    month = left_calendar.find_element(By.CSS_SELECTOR, "span.ui-datepicker-month").text.strip()
    print(f"Month: {month}")
    dates = left_calendar.find_elements(By.CSS_SELECTOR, "td")
    for d in dates:
      d_class = d.get_attribute("class")
      if UNCLICABLE_CLASS in d_class:
        continue
      date_str = d.text.strip()
      bookable, stop_checking = is_bookable(month, date_str)

      if stop_checking:
        print("reached {}-{}, stop checking".format(month, date_str))
        break

      if not bookable:
        print("{}-{} can be booked but not ideal".format(month, date_str))
        continue

      earliest_bookable_date = month + "-" + date_str
      print("earliest_bookable_date: ", earliest_bookable_date)
      find_date = True
      d.click()
      break
    if stop_checking or find_date:
      break
    # go to next month
    driver.find_element(By.CSS_SELECTOR, "a.ui-datepicker-next").click()
    wait_response(seconds = 1)

  return find_date, month, date_str

def main():
  CFG = read_config("./cfg.yaml")
  print("CFG:", CFG)
  # Chrome options to run it in background
  options = webdriver.ChromeOptions()
  options.add_argument("headless")
  scheduled = False
  while True:
    with webdriver.Chrome("chromedriver",options=options) as driver:
      no_internet = get_to_login_page(driver, CFG)
      if no_internet:
        continue
      reached_daily_limit = get_to_appointment_page(driver, CFG)
      if reached_daily_limit:
        continue
      find_date, month, date_str = get_appointment_date(driver)
      if not find_date:
        continue
      scheduled = schedule_appointment(driver, month, date_str, CFG.get('debug', False))

    if scheduled:
      break
    # 12 quotas per day -> try every 2 hour 
    print("sleep 2 hours and continue")
    wait_response(seconds=60 * 120)

if __name__ == "__main__":
  main()
