# RFID Smart Water Supply Monitoring & Billing System

A full-featured Streamlit web application that simulates an RFID-based smart water supply network with user authentication, water usage monitoring, slab billing, admin controls, analytics, alerts, and basic ML forecasting.

## Features
- RFID user authentication simulation
- Water usage tracking with historical logs
- Slab-based smart billing
- Downloadable PDF bills and CSV reports
- Admin panel for users, RFID IDs, and billing rates
- Leak detection logic for abnormal usage
- 7-day water consumption prediction using linear regression
- Role-based login (Admin / User)
- Dark mode toggle
- SQLite backend for persistence
- Future-ready notes for IoT and QR integration

## Project Structure
- `app.py` – main Streamlit app
- `database.py` – SQLite initialization and CRUD helpers
- `utils.py` – billing, forecasting, anomaly detection, exports
- `auth.py` – login and logout helpers
- `requirements.txt` – dependencies

## Demo Credentials
- Admin: `admin` / `admin123`
- User: `shreya` / `user123`

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- The database file `smart_water.db` is created automatically on first run.
- Dummy users and 120+ days of usage logs are auto-generated.
- The app is designed to be beginner-friendly but follows modular practices suitable for future scaling.
