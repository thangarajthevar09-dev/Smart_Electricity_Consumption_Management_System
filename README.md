
## Requirements
- Python 3.10+
- VS Code (recommended)

## Setup in Windows PowerShell
1. Extract this ZIP.
2. Open the extracted `Smart_Electricity_Consumption_Management_System_JSON` folder in VS Code.
3. Open a terminal in that folder.
4. Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.
5. Install the only dependency:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open http://127.0.0.1:5000 in your browser.

No `.env` file is needed. The app creates `data/database.json` automatically and adds demo readings on first run.

## JSON data and backup
- All readings and the electricity rate are stored in `data/database.json`.
- To back up your data, stop the app and copy `data/database.json` somewhere safe.
- To reset to demo data, stop the app and delete `data/database.json`; the next run recreates it.
- Do not edit the JSON file while the application is running. Keep its JSON structure valid.

## Usage
- Open **Add Reading** and enter a date, building, room, meter ID, actual consumption in kWh and expected consumption in kWh.
- Readings at 120% or more of expected usage show a warning; readings at 150% or more show high usage.
- Open **Settings** to change the illustrative electricity rate. The default ₹8.50/kWh is a demo value; use the rate applicable to your project/location.

## Notes for academic presentation
- This is a software prototype using manually entered/simulated readings, not live smart-meter sensor data.
- An alert identifies a reading worth investigating; it does not prove a physical fault.
- Cost estimates are simplified and do not include taxes, slab pricing, fixed charges or demand charges.
- JSON-file storage is appropriate for a small local academic prototype. It does not provide SQL-style concurrent access or multi-user database management.
