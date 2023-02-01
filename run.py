import enum
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

class LoginSchedule(enum.Enum):
  """
  Each day we can log into the appointment page
  12 times, and we can use different strategy to
  schedule the appointment.
  """
  CheckEvery2Hour = enum.auto()

def login_schedule(choice: LoginSchedule):
  if choice == LoginSchedule.CheckEvery2Hour:
    print("Wait 2 hours for the next check")
    wait_response(seconds=60 * 120)



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

def is_ideal(month, date_str):
  """Checks whether a given clickable month and date is ideal
  
  Suppose you run this script at Feb 1st, and you want to book any date between
  Feb 13th to April 20th. The program will check each month starting from Feburary.
  Each bookable date will be judged by this function. Three scenarios:
  1. Feb 10th is the earliest bookable date, not ideal and we continue checking other dates.
  2. March 1st is the earliest bookable date, perfect and we are done.
  3. April 24th is the earliest bookable date, not ideal and it goes beyond our desired range
     so we stop checking.
     
  Also, suppose you booked April 15th but you want to make it earlier. You need to change the
  function again to make the ideal date narrower in order to achieve that, otherwise you may
  book April 20th if it is available next time.
  """
  ideal = False
  stop_checking = False
  # change below into the criteria you like
  date_num = int(date_str)
  if month == "Feburary" and date_num < 13:
    ideal = False
  if month == "Feburary" and date_num >= 13:
    ideal = True
  elif month == "March":
    ideal = True
  elif month == "April" and date_num <= 20:
    ideal = True
  else:
    stop_checking = True
  return ideal, stop_checking


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
      ideal, stop_checking = is_ideal(month, date_str)

      if stop_checking:
        print("reached {}-{}, stop checking".format(month, date_str))
        break

      if not ideal:
        print("{}-{} can be booked but not ideal".format(month, date_str))
        continue

      earliest_ideal_date = month + "-" + date_str
      print("earliest_ideal_date: ", earliest_ideal_date)
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
  first_time = True
  while True:
    if not first_time:
      login_schedule(LoginSchedule.CheckEvery2Hour)
    first_time = False
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

if __name__ == "__main__":
  main()
