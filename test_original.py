import os
import re
import io
import requests
import pdfplumber
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

TARGET_URL = "https://siuexam.siu.edu.in/forms/resultview.html"

def get_extreme_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return chrome_options

def test_original(prn, seat):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=get_extreme_options())
    wait = WebDriverWait(driver, 5)
    try:
        driver.get(TARGET_URL)
        prn_f = wait.until(EC.element_to_be_clickable((By.ID, "login")))
        prn_f.send_keys(str(prn))
        driver.execute_script("prnverify();")
        
        wait.until(lambda d: len(d.find_element(By.ID, "seatnum").text.strip()) > 5 or 
                             len(d.find_elements(By.ID, "txt3")) > 0)
        
        print("SEATNUM TEXT:", driver.find_element(By.ID, "seatnum").text)
        
        s_f = driver.find_element(By.ID, "txt3")
        s_f.send_keys(str(seat))
        driver.execute_script("viewrslt(3, 'Ff2CU4Z5nA==');")
        
        wait.until(lambda d: "valid" in d.find_element(By.ID, "rslt").text or 
                             len(d.find_elements(By.CLASS_NAME, "btndef")) > 0)
        
        print("RSLT TEXT:", driver.find_element(By.ID, "rslt").text)
        driver.quit()
    except Exception as e: 
        print("Exception:", e)
        driver.quit()

test_original(24070122001, 528501)
