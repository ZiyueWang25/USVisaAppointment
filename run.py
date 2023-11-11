import enum
import datetime
import time
import yaml

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By


# TODO:
# 1. specific time run
# 2. change sleep to clicable condition
# 3. more setting for date and month
# 4. email notification
# 5. logging

CONSULATE_LOCATION_LABEL="appointments_consulate_appointment_facility_id"
CONSULATE_DATE_LABEL = "appointments_consulate_appointment_date"
CONSULATE_TIME_LABEL = "appointments_consulate_appointment_time"
ASC_LOCATION_LABEL="appointments_asc_appointment_facility_id"
ASC_DATE_LABEL = "appointments_asc_appointment_date"
ASC_TIME_LABEL = "appointments_asc_appointment_time"

class LoginSchedule(enum.Enum):
  """
  Each day we can log into the appointment page
  12 times (may not true), and we can use different strategy to
  schedule the appointment.
  """
  Every2Hour = enum.auto() # Every 2 hours
  Every30Min = enum.auto() # Every 30 minutes

def wait_start(choice: LoginSchedule):
  if choice == LoginSchedule.Every2Hour:
    print("Wait 2 hours for the next check")
    wait_response(seconds=60 * 120)
    return True
  elif choice == LoginSchedule.Every30Min:
    print("Wait 30 minutes for the next check")
    wait_response(seconds=60 * 30)


UNCLICABLE_CLASS = "ui-state-disabled"

def wait_response(seconds=1):
  time.sleep(seconds)


def read_config(file_path):
  with open(file_path, "r") as f:
    return yaml.safe_load(f)

def get_to_login_page(driver:webdriver.Chrome, signin_page:str, email:str, pwd:str):
  no_internet = False
  try:
    driver.get(signin_page)
    wait_response(seconds = 2)
    username = driver.find_element(By.ID, "user_email")
    username.clear()
    username.send_keys(email)
    password = driver.find_element(By.ID, "user_password")
    password.clear()
    password.send_keys(pwd)
    policy = driver.find_element(By.ID, "policy_confirmed")
    driver.execute_script("arguments[0].click();", policy)
    driver.find_element(By.NAME, "commit").click()
    wait_response(seconds = 3)
  except selenium.common.exceptions.WebDriverException:
    no_internet = True
    print("no internet connection")
  return no_internet


def get_date_from_calendar(driver:webdriver.Chrome, start_date: str, end_date: str):
  current_year = datetime.datetime.now().year
  current_month = datetime.datetime.now().month
  stop_checking = False
  find_date = False
  got_date = None
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
      date_str = d.text.strip().zfill(2)
      got_date = "{}-{}-{}".format(current_year, month, date_str)
      if got_date > end_date:
        print(f"{got_date} is beyond end_date {end_date}, stop checking")
        stop_checking = True
      elif got_date >= start_date:
        print(f"{got_date} is within desired range, stop checking")
        find_date = True
        d.click()
        break
      else:
        print(f"{got_date} is before start_date {start_date}, continue checking")
        continue
    if stop_checking or find_date:
        break
    # go to next month
    driver.find_element(By.CSS_SELECTOR, "a.ui-datepicker-next").click()
    current_month += 1
    if current_month > 12:
      current_month = 1
      current_year += 1
    wait_response(seconds = 1)
  return find_date, got_date

def get_location(driver:webdriver.Chrome, label:str=CONSULATE_LOCATION_LABEL):
  # select location
  driver.find_element(By.CSS_SELECTOR, f"#{label}_input").click()
  wait_response(seconds = 1)
  # TODO: select Mexico City
  driver.find_element(By.CSS_SELECTOR, f"#{label} > option:nth-child(7)").click()
  wait_response(seconds = 1)

def get_time_slot(driver:webdriver.Chrome, label:str=CONSULATE_TIME_LABEL):
  # get time slots
  driver.find_element(By.CSS_SELECTOR, f"#{label}_input").click()
  wait_response(seconds = 1)
  # select time slot
  driver.find_element(By.CSS_SELECTOR, f"#{label} > option:nth-child(2)").click()
  wait_response(seconds = 1)

def get_appointment_date(
    driver:webdriver.Chrome,
    start_date: str,
    end_date: str,
    date_label:str=CONSULATE_DATE_LABEL,
    time_label:str=CONSULATE_TIME_LABEL,
):
  reached_daily_limit = False
  find_date = False
  got_date = None
  try:
    driver.find_element(By.ID, f"{date_label}_input").click()
    wait_response(seconds = 1)
  except selenium.common.exceptions.ElementNotInteractableException:
    reached_daily_limit = True
    print("reached daily limit")
  if reached_daily_limit:
    return reached_daily_limit, find_date, got_date
  find_date, got_date = get_date_from_calendar(driver, start_date, end_date)
  if find_date:
    get_time_slot(driver, label=time_label)
  return reached_daily_limit, find_date, got_date

def get_appointment(driver:webdriver.Chrome, start_date: str, end_date: str, is_mexico: bool):
  if is_mexico:
    find_asc_date = False
    while not find_asc_date:
      print(f"Using date range: {start_date} - {end_date}")
      get_location(driver, CONSULATE_LOCATION_LABEL)
      reached_daily_limit, find_date, got_date = get_appointment_date(driver, start_date, end_date)
      if reached_daily_limit or not find_date:
        return reached_daily_limit, find_date, got_date
      get_location(driver, ASC_LOCATION_LABEL)
      reached_daily_limit, find_asc_date, got_asc_date = get_appointment_date(driver, start_date, end_date, ASC_DATE_LABEL, ASC_TIME_LABEL)
      if not find_asc_date:
        print("Find consulate date but not find appropriate asc date.")
        print("Increase start date by 1 day and try again.")
        next_date = datetime.datetime.strptime(start_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        start_date = next_date.strftime("%Y-%m-%d")
        if start_date > end_date:
          print("No date available")
          return reached_daily_limit, find_asc_date, got_asc_date
    return reached_daily_limit, find_asc_date, got_date
  else:
    return get_appointment_date(driver, start_date, end_date)

def schedule_appointment(driver, got_date, debug):
  # schedule
  driver.find_element(By.NAME, "commit").click()
  wait_response(seconds = 1)
  # confirmation page
  confirm_botton = driver.find_element(By.CSS_SELECTOR, "body > div.reveal-overlay > div > div > a.button.alert")
  confirmable = confirm_botton.is_displayed()
  print(f"confirmable: {confirmable}.")
  if not debug:
    confirm_botton.click()
    message = f"Successfully rescheduled! date {got_date}"
  else:
    message = f"In debug mode, can schedule date {got_date} but won't schedule."
  print(message)
  # linux system specific sound notification
  # subprocess.call(["spd-say", message])
  return True

def main():
  CFG = read_config("./cfg.yaml")
  print("CFG:", CFG)
  signin_page = CFG["signin_page"]
  email = CFG["email"]
  pwd = CFG["pwd"]
  appointment_page = CFG["appointment_page"]
  start_date = CFG["start_date"]
  end_date = CFG["end_date"]
  debug = CFG["debug"]
  is_mexico = CFG["is_mexico"]
  check_schedule = CFG["check_schedule"]
  if check_schedule == "Every30Min":
    check_schedule = LoginSchedule.Every30Min
  elif check_schedule == "Every2Hour":
    check_schedule = LoginSchedule.Every2Hour
  else:
    raise ValueError("check_schedule should be either Every30min or Every2hour, got {}".format(check_schedule))

  options = webdriver.ChromeOptions()
  options.add_argument("headless")
  scheduled = False
  first_time = True
  while True:
    if not first_time:
      wait_start(check_schedule)
    first_time = False
    with webdriver.Chrome(options=options) as driver:
      no_internet = get_to_login_page(driver, signin_page, email, pwd)
      if no_internet:
        continue
      driver.get(appointment_page)
      wait_response(seconds = 3)
      reached_daily_limit, find_date, got_date = get_appointment(driver, start_date, end_date, is_mexico)
      if reached_daily_limit:
        continue
      if not find_date:
        continue
      scheduled = schedule_appointment(driver, got_date, debug)

    if scheduled:
      break

if __name__ == "__main__":
  main()
