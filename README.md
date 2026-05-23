# ResultScout

ResultScout is a full-stack application designed to automate the retrieval and visualization of examination results from the SIU (Symbiosis International University) exam portal. 

By leveraging a Python-based Selenium scraper and a modern React frontend, it streamlines the process of checking results, completely bypassing the manual login and navigation hurdles.

## Features

- **Automated Web Scraping:** Headless Chrome-based Selenium scraper for fast and reliable data extraction from the university portal.
- **RESTful API Backend:** A Python API layer that acts as a bridge between the scraper and the frontend, exposing endpoints to fetch user-specific results.
- **Modern User Interface:** A fast, responsive, and intuitive web interface built with React and Vite.
- **Seamless Integration:** Designed to query result data dynamically based on `PRN` and other necessary credentials.

## Technology Stack

### Backend (Scraper & API)
- **Python 3.x**
- **Selenium & WebDriver Manager:** For browser automation and HTML parsing.
- **Flask / FastAPI:** (Dependent on `api.py` implementation) for serving REST endpoints.

### Frontend
- **React 18**
- **Vite:** Next-generation frontend tooling for ultra-fast development.
- **Tailwind CSS** (if applicable) for styling.

## Repository Structure

```text
ResultScout/
├── frontend/             # React (Vite) User Interface
├── scraper/              # Python Selenium Scraper & API
│   ├── api.py            # API Server
│   ├── scraper.py        # Core scraping logic
│   ├── requirements.txt  # Python dependencies
│   └── .env              # Environment configurations
├── test.py               # Headless browser testing script
└── test_original.py      # Original prototype testing script
```

## Setup & Installation

### 1. Backend (Scraper) Setup

```bash
cd scraper

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add any required environment variables
# Run the API server
python api.py
```

### 2. Frontend Setup

In a new terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open `http://localhost:5173` (or the port specified by Vite) in your browser to interact with the application.

## Testing

You can run the headless browser tests to ensure the scraper is correctly identifying elements on the target university website.

```bash
python test.py
```

## Disclaimer

This project is for educational and personal use only. It interacts with the university's result portal. Please ensure you are compliant with the university's terms of service regarding automated scripts and web scraping.
