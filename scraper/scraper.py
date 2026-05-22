import os
import requests
import io
import re
import pdfplumber
import concurrent.futures
from supabase import create_client, Client
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("WARNING: Supabase credentials not found in .env. Data will not be saved.")

START_PRN = 24070122001
END_PRN = 24070122200
MASTER_POOL = list(range(528501, 530000))
BASE_URL = "https://siuexam.siu.edu.in"
SEASON = "April 2026"

# Database Categories
YEAR = 2026
DEPARTMENT = "CSE"
SEMESTER = 3

# High concurrency for pure HTTP requests
WORKER_COUNT = 50

# Track seats
USED_SEATS = set()

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
    try:
        session = requests.Session()
        # Verify PRN
        verify_url = f"{BASE_URL}/rsstd/DspSeatnum"
        verify_params = {
            "dbnm": "siucore",
            "prn": prn,
            "mksea": SEASON
        }
        res = session.get(verify_url, params=verify_params, timeout=10)
        if "Please contact your institute" in res.text:
            return {"status": "TNG", "seat": seat}
        
        # Check Seat
        view_url = f"{BASE_URL}/rsstd/viewrslt"
        view_params = {
            "dbnm": "siucore",
            "mrkexmid": 3,
            "siudbnm": "Ff2CU4Z5nA==",
            "seatno": seat,
            "p": prn,
            "se": SEASON
        }
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
        # Upsert based on PRN to avoid duplicates
        supabase.table("results").upsert(record).execute()
    except Exception as e:
        print(f"Failed to save PRN {record['prn']} to DB: {e}")

def process_batch():
    print(f"Starting Turbo API Scraper with {WORKER_COUNT} workers...")
    print("-" * 60)
    for prn in range(START_PRN, END_PRN + 1):
        found = False
        search_index = 0
        
        while not found and search_index < len(MASTER_POOL):
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
                        print(f"PRN: {prn:<15} | SKIP")
                        save_to_supabase({
                            "prn": prn, "name": "N/A", "seat": "SKIP", "gpa": "TNG",
                            "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER
                        })
                        found = True
                        break 
                    elif res["status"] == "SUCCESS":
                        print(f"PRN: {prn:<15} | Seat: {res['seat']:<10} | Name: {res['name'][:20]:<20} | GPA: {res['gpa']}")
                        USED_SEATS.add(res['seat'])
                        save_to_supabase({
                            "prn": prn, "name": res['name'], "seat": str(res['seat']), "gpa": res['gpa'],
                            "year": YEAR, "department": DEPARTMENT, "semester": SEMESTER
                        })
                        found = True
                        break
            
            if not found:
                search_index = temp_idx 
        
        if not found:
            print(f"PRN: {prn:<15} | FAIL")

    print("\n[FINISH] Scraping Complete.")

if __name__ == "__main__":
    process_batch()
