from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

opts = Options()
opts.add_argument("--headless")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)
driver.get("https://siuexam.siu.edu.in/forms/resultview.html")
time.sleep(2)
try:
    print("dbnm:", driver.execute_script("return $('#dbnm').val()"))
    print("grp:", driver.execute_script("return $('#grp').val()"))
except Exception as e:
    print(e)
driver.quit()
