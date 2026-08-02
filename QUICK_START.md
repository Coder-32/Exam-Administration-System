# Quick Start Guide

## Option 1: Docker (Recommended)

### Prerequisites
- Docker installed ([Download Docker Desktop](https://www.docker.com/products/docker-desktop))

### 1. Clone or navigate to the project
```bash
cd ExamAdministrationSystem
```

### 2. Create environment file (optional - uses defaults)
```bash
cp .env.example .env
```
Edit `.env` if you want to customize database credentials or port numbers.

### 3. Start the application with Docker Compose
```bash
docker-compose up -d
```

The first run will build the image and start both the PostgreSQL database and Flask application.

### 4. Access the application
- **Web Application**: http://localhost:10000
- **Database**: localhost:5432

### 5. View logs
```bash
docker-compose logs -f exam-admin
```

### 6. Stop the application
```bash
docker-compose down
```

To also remove the database volume:
```bash
docker-compose down -v
```

---

## Option 2: Local Installation (Development)

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### 1. Navigate to project directory
```bash
cd ExamAdministrationSystem
```

### 2. Create virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start PostgreSQL
Ensure PostgreSQL is running and create the database:
```sql
CREATE DATABASE exam_db;
```

### 5. Run the Flask application
```bash
python app.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### 6. Open in browser
Navigate to: `http://localhost:5000` or `http://localhost:10000`

---

## Sample Data for Testing

### Example Configuration:
- Faculty Members: 3 (F1, F2, F3)
- Staff Members: 2 (S1, S2)
- Rooms: 3 (R1, R2, R3)
- Dates: 2 (D1, D2)

### Example Faculty Preferences:
**F1**
- Priority Dates: D1,D2
- Exclusions: D1-Afternoon

**F2**
- Priority Dates: D2
- Exclusions: D2-Morning

**F3**
- Priority Dates: D1
- Exclusions: none (leave empty)

### Example Staff Preferences:
**S1**
- Priority Dates: D1,D2
- Exclusions: D2-Afternoon

**S2**
- Priority Dates: D2
- Exclusions: D1-Morning

---

## Features Demonstrated

✅ Dynamic form generation based on input numbers
✅ Intelligent preference handling
✅ Optimized schedule generation using network algorithms
✅ Real-time results display in formatted table
✅ One-click Excel export with timestamp
✅ Responsive design for all devices
✅ Error handling and validation

---

## Expected Results

The system will:
1. Create a bipartite graph of personnel, dates, shifts, and rooms
2. Apply cost minimization algorithm for optimal assignment
3. Display a complete deployment chart showing:
   - Which faculty member is assigned to each room
   - Which staff member supports each shift
   - Any unfilled positions (if constraints don't allow 100% coverage)

---

## Troubleshooting

**Issue**: Port 5000 is already in use
- **Solution**: Change port in `app.py` line: `app.run(debug=True, port=8000)`

**Issue**: ModuleNotFoundError
- **Solution**: Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

**Issue**: Excel export fails
- **Solution**: Ensure openpyxl is installed: `pip install openpyxl --upgrade`

**Issue**: JavaScript errors in browser console
- **Solution**: Check browser console (F12 → Console tab) for specific errors
- Clear browser cache (Ctrl+Shift+Delete) and refresh

---

## File Structure Explained

```
project_1_did/
│
├── app.py                      # Flask web server & API endpoints
├── schedule.py                 # Scheduling algorithm & logic
├── requirements.txt            # Python package dependencies
├── README.md                   # Full documentation
├── QUICK_START.md             # This file
│
├── templates/                  # HTML templates
│   └── index.html             # Main web interface
│
├── static/                     # Static assets
│   ├── style.css              # Styling (CSS)
│   └── script.js              # Frontend logic (JavaScript)
│
└── service/                    # (Placeholder for services)
```

---

## API Endpoints

### POST /api/schedule
Generates the invigilation schedule

**Request Body**:
```json
{
  "faculties_count": 3,
  "staff_count": 2,
  "rooms_count": 3,
  "dates_count": 2,
  "facultyData": {
    "F1": {"priority_dates": ["D1"], "emergency_shifts": ["D1-Afternoon"]}
  },
  "staffData": {
    "S1": {"priority_dates": ["D1"], "emergency_shifts": []}
  }
}
```

### POST /api/download-excel
Downloads schedule as Excel file

**Request Body**:
```json
{
  "results": [...]  // Array of schedule results
}
```

---

## Next Steps

1. ✅ Run the application
2. ✅ Test with sample data
3. ✅ Export results to Excel
4. ✅ Customize CSS for your institution's branding
5. ✅ Integrate with your college management system

Enjoy your invigilation scheduling system! 🎓
