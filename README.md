
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
