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
# 5. add logging

UNCLICABLE_CLASS = "ui-state-disabled"

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
	driver.get(CFG['appointment_page'])    
	time.sleep(3)

def get_to_login_page(driver, CFG):
	driver.get("https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
	#get_page_source(driver)
	time.sleep(2)
	username = driver.find_element(By.ID, "user_email")
	username.clear()
	username.send_keys(CFG['email']) 
	password = driver.find_element(By.ID, "user_password")
	password.clear()
	password.send_keys(CFG['pwd'])
	policy = driver.find_element(By.ID, "policy_confirmed")
	driver.execute_script("arguments[0].click();", policy)
	driver.find_element(By.NAME, "commit").click()
	time.sleep(3)

def is_bookable(month, date_str):
	# change below into the criteria you like
	date_num = int(date_str)
	if month == "September" and date_num >= 10:
		return True
	if month == "October":
		return True
	if month == "November" and date_num >= 13:
		return True
	if month == "December":
		return True
	if month == "January" and date_num <= 13:
		return True
	return False

def main():
	CFG = read_config("./cfg.yaml")
	print("CFG:", CFG)
	# Chrome options to run it in background
	options = webdriver.ChromeOptions()
	options.add_argument("headless")
	scheduled = False
	while True:
		scheduled = False
		reached_daily_limit = False
		no_internet = False
		with webdriver.Chrome("chromedriver",options=options) as driver:
			try:
				get_to_login_page(driver, CFG)
			except selenium.common.exceptions.WebDriverException:
				no_internet = True
				print("no internet connection")
				break
			get_to_appointment_page(driver, CFG)
			try:
				driver.find_element(By.ID,"appointments_consulate_appointment_date_input").click()
			except selenium.common.exceptions.ElementNotInteractableException:
				reached_daily_limit = True
				print("reached daily limit")
			else:
				# check left calendar
				time.sleep(1)
				find_date = False
				while True:
					left_calendar = driver.find_element(By.CSS_SELECTOR, "div.ui-datepicker-group-first")		
					#print("left_calendar.is_displayed()", left_calendar.is_displayed())
					#left_calendar.screenshot("./pic.png")
					month = left_calendar.find_element(By.CSS_SELECTOR, "span.ui-datepicker-month").text.strip()
					print("month:", month)
					if month == "February":
						break
					dates = left_calendar.find_elements(By.CSS_SELECTOR, "td")
					#print("Number of dates: ", len(dates))
					for d in dates:
						d_class = d.get_attribute("class")
						if UNCLICABLE_CLASS in d_class:
							continue
						date_str = d.text.strip()
						if not is_bookable(month, date_str):
							print("{}-{} can be booked but not ideal".format(month, date_str))
							continue
						earliest_bookable_date = month + "-" + date_str
						print("earliest_bookable_date: ", earliest_bookable_date)
						find_date = True
						d.click()
						break
					if find_date:
						break
					driver.find_element(By.CSS_SELECTOR, "a.ui-datepicker-next").click()
					time.sleep(1)
			if find_date and not reached_daily_limit and not no_internet:
				time.sleep(1)
				# get time slots
				driver.find_element(By.CSS_SELECTOR, "#appointments_consulate_appointment_time_input").click()
				time.sleep(1)
				# select time slot
				driver.find_element(By.CSS_SELECTOR, "#appointments_consulate_appointment_time > option:nth-child(2)").click()
				time.sleep(1)
				# schedule
				driver.find_element(By.NAME, "commit").click()
				time.sleep(1)
				# confirmation page
				confirm_botton = driver.find_element(By.CSS_SELECTOR, "body > div.reveal-overlay > div > div > a.button.alert")
				confirmable = confirm_botton.is_displayed()
				print(f"confirmable: {confirmable}.")
				confirm_botton.click()
				message = f"Successfully rescheduled! date {month}-{date_str}"
				print(message)
				# linux system specific sound notification
				# subprocess.call(["spd-say", message])
				scheduled = True
		if scheduled:
			break
		# 12 quota per day
		print("sleep 2 hours and continue")
		time.sleep(60 * 120)

if __name__ == "__main__":
	main()
