import os
import requests
import io
import re
import pdfplumber
import concurrent.futures
import threading
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app) # Allow React frontend to access

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

START_PRN = 24070122001
END_PRN = 24070122200
MASTER_POOL = list(range(528501, 530000))
BASE_URL = "https://siuexam.siu.edu.in"
SEASON = "April 2026"
YEAR = 2026
DEPARTMENT = "CSE"
SEMESTER = 3
WORKER_COUNT = 50

# Global State
state = {
    "is_running": False,
    "should_stop": False,
    "current_prn": 0,
    "total_prns": END_PRN - START_PRN + 1,
    "logs": []
}

USED_SEATS = set()

def log_msg(msg):
    print(msg)
    state["logs"].append(msg)
    if len(state["logs"]) > 100:
        state["logs"].pop(0)

def extract_from_memory(pdf_content):
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text = pdf.pages[0].extract_text()
            name = "Unknown"
            if text:
                match = re.search(r"NAME\s*:\s*([^\n\r]*)", text, re.IGNORECASE)
                name = match.group(1).strip() if match else "Unknown"
            gpa = "N/A"
            nums = re.findall(r"(\d+\.\d+)", text)
            for num in reversed(nums):
                if 0.1 <= float(num) <= 10.0:
                    gpa = num
                    break
            return name, gpa
    except: 
        return "Error", "N/A"

def check_seat(prn, seat):
    if state["should_stop"]: return None
    try:
        session = requests.Session()
        verify_url = f"{BASE_URL}/rsstd/DspSeatnum"
        verify_params = {"dbnm": "siucore", "prn": prn, "mksea": SEASON}
        res = session.get(verify_url, params=verify_params, timeout=10)
        
        if "Please contact your institute" in res.text:
            return {"status": "TNG", "seat": seat}
        
        view_url = f"{BASE_URL}/rsstd/viewrslt"
        view_params = {"dbnm": "siucore", "mrkexmid": 3, "siudbnm": "Ff2CU4Z5nA==", "seatno": seat, "p": prn, "se": SEASON}
        res_view = session.get(view_url, params=view_params, timeout=10)
        
        if "Enter valid Seat No.!!" not in res_view.text:
            soup = BeautifulSoup(res_view.text, "html.parser")
            btn = soup.find("a", class_="btndef")
            if btn and "href" in btn.attrs:
                pdf_url = btn["href"].replace("../../", BASE_URL + "/")
                pdf_res = session.get(pdf_url, timeout=10)
                name, gpa = extract_from_memory(pdf_res.content)
                return {"status": "SUCCESS", "name": name, "gpa": gpa, "seat": seat}
    except Exception as e:
        pass
    return None

def save_to_supabase(record):
    if not supabase: return
    try:
        supabase.table("results").upsert(record).execute()
    except Exception as e:
        log_msg(f"Failed to save {record['prn']} to DB: {e}")

def scraper_loop():
    log_msg(f"Started Turbo API Scraper with {WORKER_COUNT} workers...")
    for prn in range(START_PRN, END_PRN + 1):
        if state["should_stop"]:
            log_msg("Scraper stopped by user.")
            break

        state["current_prn"] = prn - START_PRN + 1
        found = False
        search_index = 0
        
        while not found and search_index < len(MASTER_POOL):
            if state["should_stop"]: break
            batch = []
            temp_idx = search_index
            while len(batch) < WORKER_COUNT and temp_idx < len(MASTER_POOL):
                s = MASTER_POOL[temp_idx]
                if s not in USED_SEATS:
                    batch.append(s)
                temp_idx += 1
            
            if not batch: break
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {executor.submit(check_seat, prn, batch[i]): i for i in range(len(batch))}
                results = []
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res: results.append(res)
                
                results = sorted(results, key=lambda x: x["seat"] if "seat" in x and isinstance(x["seat"], int) else 999999)
                
                for res in results:
                    if res["status"] == "TNG":
                        log_msg(f"PRN: {prn} | SKIP")
                        save_to_supabase({"prn": prn, "name": "N/A", "seat": "SKIP", "gpa": "TNG", "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER})
                        found = True
                        break 
                    elif res["status"] == "SUCCESS":
                        log_msg(f"PRN: {prn} | Seat: {res['seat']} | Name: {res['name']} | GPA: {res['gpa']}")
                        USED_SEATS.add(res['seat'])
                        save_to_supabase({"prn": prn, "name": res['name'], "seat": str(res['seat']), "gpa": res['gpa'], "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER})
                        found = True
                        break
            
            if not found:
                search_index = temp_idx 
        
        if not found and not state["should_stop"]:
            log_msg(f"PRN: {prn} | FAIL")

    state["is_running"] = False
    if not state["should_stop"]:
        log_msg("[FINISH] Scraping Complete.")

@app.route('/api/start', methods=['POST'])
def start_scraper():
    if state["is_running"]:
        return jsonify({"message": "Already running"}), 400
    
    state["is_running"] = True
    state["should_stop"] = False
    state["logs"] = []
    
    thread = threading.Thread(target=scraper_loop)
    thread.start()
    return jsonify({"message": "Scraper started"})

@app.route('/api/stop', methods=['POST'])
def stop_scraper():
    if not state["is_running"]:
        return jsonify({"message": "Not running"}), 400
    
    state["should_stop"] = True
    return jsonify({"message": "Stopping..."})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(state)

if __name__ == '__main__':
    log_msg("API Server initialized. Waiting for commands...")
    app.run(port=5000)
