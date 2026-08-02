# Exam Invigilation Scheduling System

A web-based application for managing exam invigilation schedules with automatic optimization using network flow algorithms.

---

## ✨ Features

### Modern Web Interface
- Intuitive form-based data entry with dynamic form generation
- Real-time schedule generation and display
- Responsive design for desktop, tablet, and mobile
- Professional gradient UI with smooth animations
- Loading indicators and clear error messages

### Advanced Scheduling Algorithm
- Optimized faculty and staff deployment using NetworkX
- Preference-based assignment with cost minimization
- Emergency exclusion handling
- Automatic capacity management
- Guaranteed optimal solution

### Export Options
- **CSV Export** — Grouped schedules (Main, Faculty, Staff, Rooms)
- **PDF Reports** — Faculty invigilation reports
- **ZIP Download** — All CSVs bundled in one file

### Preference System with Shifts
- Set preferences per shift (Morning / Afternoon)
- Emergency exclusions — hard constraints
- Preferred assignments — soft constraints (optimization objective)

---

## 📁 Project Structure

```
Exam Administration System/
├── app.py                          # Flask backend with API endpoints
├── CONFIG.py                       # Configuration reference
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
│
├── database/                       # Data files
│   ├── teachers.txt                # Faculty names
│   ├── staffs.txt                  # Staff names
│   ├── rooms.txt                   # Room list
│   └── namesProf.pdf               # Professor names reference
│
├── service/                        # Backend services
│   ├── schedule.py                 # Scheduling algorithm & network flow logic
│   ├── createTable.py              # PDF report generation
│   ├── export_service.py           # Excel/CSV export utilities
│   └── db.py                       # Database utilities
│
├── templates/                      # HTML templates
│   ├── index.html                  # Main web interface
│   ├── calender.html               # Calendar view
│   └── register.html               # Registration page
│
├── static/                         # Static assets
│   ├── style.css                   # CSS styling & animations
│   └── script.js                   # Frontend JavaScript logic
│
├── schedule_storage/               # Generated CSV/ZIP output
│   ├── exam_schedule.csv
│   ├── teacher_schedule.csv
│   ├── staff_schedule.csv
│   ├── room_schedule.csv
│   └── exam_schedules.zip          # Created on demand
│
├── README.md                       # This file
├── QUICK_START.md                  # Quick setup guide (merged into README)
├── DEPLOYMENT.md                   # Cloud deployment guide
└── render.yaml                     # Render deployment configuration
```

---

## 🚀 Quick Start

### Local Development

#### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Run the Application
```bash
python app.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

#### 3. Open in Browser
Navigate to: `http://localhost:5000`

---

## 🐳 Docker Deployment

### Using Docker Compose
```bash
docker-compose up
```
Visit: `http://localhost:5000`

### Using Docker Directly
```bash
# Pull from DockerHub
docker pull satwik006/exam-administration-system:latest

# Run the container
docker run -p 5000:5000 satwik006/exam-administration-system:latest
```

### If Port 5000 is Already in Use
```bash
# Use a different port
docker run -p 8080:5000 satwik006/exam-administration-system:latest
# Visit: http://localhost:8080
```

### Export as .tar File
```bash
docker save exam-administration-system:latest -o exam-system.tar
```

To use the .tar file:
```bash
docker load -i exam-system.tar
docker run -p 5000:5000 exam-administration-system:latest
```

---

## 📦 Production Deployment

### Local Server
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Cloud Deployment (Render)
See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.

**Your DockerHub Repository:** https://hub.docker.com/r/satwik006/exam-administration-system

---

## 📖 How to Use

### Step 1: System Configuration
- Enter the number of faculty members, staff members, examination rooms, and dates
- Click **"Generate Input Forms"**

### Step 2: Faculty & Staff Preferences
For each faculty/staff member:
- Enter priority dates (e.g., `D1,D2,D3`)
- Enter emergency exclusions (e.g., `D1-Morning,D2-Afternoon`)

### Step 3: Set Shift Preferences (Optional)
1. Select exam dates from the calendar
2. Click **"Set Preferences"**
3. Fill in the preference form:
   - Select Teacher/Staff name
   - Select Date
   - Select Shift (Morning or Afternoon)
   - Select Status (Preferred or Emergency)
4. Click **"Add Rule"** to add the preference
5. Click **"Apply Preferences"** to save

### Step 4: Generate Schedule
- Click **"Generate Schedule"**
- View the optimized invigilation deployment chart
- Review the assignment status

### Step 5: Export Results
- Download individual CSVs or all as ZIP
- Generate PDF reports

### Testing with Sample Data

#### Example Configuration:
- Faculty Members: 3 (F1, F2, F3)
- Staff Members: 2 (S1, S2)
- Rooms: 3 (R1, R2, R3)
- Dates: 2 (D1, D2)

#### Example Faculty Preferences:
**F1**
- Priority Dates: D1,D2
- Exclusions: D1-Afternoon

**F2**
- Priority Dates: D2
- Exclusions: D2-Morning

**F3**
- Priority Dates: D1
- Exclusions: (leave empty)

#### Example Staff Preferences:
**S1**
- Priority Dates: D1,D2
- Exclusions: D2-Afternoon

**S2**
- Priority Dates: D2
- Exclusions: D1-Morning

---

## ✨ Features Demonstrated

✅ Dynamic form generation based on input numbers
✅ Intelligent preference handling
✅ Optimized schedule generation using network algorithms
✅ Real-time results display in formatted table
✅ Multi-format export (CSV, PDF, ZIP)
✅ Calendar-based preference management
✅ Responsive design for all devices
✅ Error handling and validation

---

## 📊 CSV Export System

### Constant Filenames
All CSV files use fixed filenames and **overwrite** with each new generation (no timestamp bloat):

| File | Description |
|------|-------------|
| `exam_schedule.csv` | Main schedule with all assignments |
| `teacher_schedule.csv` | Faculty assignments grouped by teacher |
| `staff_schedule.csv` | Staff assignments grouped by staff member |
| `room_schedule.csv` | Assignments grouped and sorted by room |

### CSV File Formats

**exam_schedule.csv (Main)**
```
Date, Room, Shift, Faculty1, Faculty2, Staff
2026-04-16, Room101, Morning, Dr. Ahmed, John, Sarah
```

**teacher_schedule.csv (Grouped by Faculty)**
```
Teacher, Date, Shift, Room, Role
Dr. Ahmed, 2026-04-16, Morning, Room101, Faculty 1
```

**staff_schedule.csv (Grouped by Staff)**
```
Staff, Date, Shift, Room, Faculty1, Faculty2
Sarah, 2026-04-16, Morning, Room101, Dr. Ahmed, John
```

**room_schedule.csv (Grouped by Room)**
```
Date, Room, Shift, Faculty1, Faculty2, Staff
2026-04-16, Room101, Morning, Dr. Ahmed, John, Sarah
```

### Download Options

| Button | Action |
|--------|--------|
| 📋 Main Schedule | Download main schedule CSV |
| 👨‍🏫 Faculty Schedule | Download faculty-grouped CSV |
| 👥 Staff Schedule | Download staff-grouped CSV |
| 🏛️ Rooms Schedule | Download room-grouped CSV |
| 📦 Download All (ZIP) | All 4 CSVs as `exam_schedules.zip` |

### API Endpoints for CSV

```
POST /api/download-csv
Body: {"results": [...], "type": "main|teacher|staff|room"}
Returns: CSV file with constant name

POST /api/download-all-csv
Body: {"results": [...]}
Returns: ZIP file with all 4 CSVs
```

---

## 🔧 Troubleshooting

### Port Already in Use
**Error**: `Address already in use`

**Solution 1 - Use Different Port**:
```bash
docker run -p 8080:5000 exam-administration-system:latest
# Visit: http://localhost:8080
```

**Solution 2 - Find and Kill Process**:
```bash
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Module Not Found Error
**Error**: `ModuleNotFoundError`

**Solution**: Reinstall dependencies
```bash
pip install -r requirements.txt --force-reinstall
```

### Excel/PDF Export Fails
**Error**: Export functions not working

**Solution**: Ensure required packages are installed
```bash
pip install openpyxl --upgrade
pip install PyPDF2 --upgrade
```

### JavaScript Errors in Browser
**Error**: Errors in browser console

**Solution**:
- Open browser console: `F12 → Console tab`
- Check for specific errors
- Clear browser cache: `Ctrl+Shift+Delete`
- Refresh the page

### Docker Image Not Found
**Error**: `docker pull` fails

**Solution**: Build image locally
```bash
docker build -t exam-administration-system .
docker run -p 5000:5000 exam-administration-system:latest
```

---

## 📋 API Endpoints Reference

### Core Endpoints

```
POST /api/schedule
POST /api/download-csv
POST /api/download-all-csv
POST /api/create-pdf
GET  /api/data
```

### Full Request/Response Examples

**POST /api/schedule** — Generate schedule
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

---

## 🎓 Expected Results

The system will:
1. Create a bipartite graph of personnel, dates, shifts, and rooms
2. Apply cost minimization algorithm for optimal assignment
3. Display a complete deployment chart showing:
   - Which faculty member is assigned to each room
   - Which staff member supports each shift
   - Any unfilled positions (if constraints don't allow 100% coverage)

---

## 📚 Additional Resources

- [DEPLOYMENT.md](DEPLOYMENT.md) - Cloud deployment guide
- [CONFIG.py](CONFIG.py) - Configuration reference
- [Dockerfile](Dockerfile) - Docker configuration

---

## 📝 License & Support

For issues, feature requests, or contributions, please refer to the project repository.

**DockerHub**: https://hub.docker.com/r/satwik006/exam-administration-system
Returns: ZIP file with all 4 CSVs
```

---

## 🔀 Preference System Details

### Preference Naming Convention
Preferences are displayed in a compact identifier format:
```
{teacher}_{dd}_{shift}
```
**Examples:**
- `Dr. Ahmed_16_morning` — Dr. Ahmed, 16th day, morning shift
- `John_17_afternoon` — John, 17th day, afternoon shift

### Preference Types
- **Preferred** — Teacher/Staff prefers this shift on this date
- **Emergency** — Teacher/Staff cannot work this shift on this date

### Backend Format
```json
{
  "teacher": "Dr. Ahmed",
  "date": "2026-04-16",
  "shift": "Morning",
  "status": "emergency"
}
```

### How Preferences Are Processed
- **Emergency shifts** → Hard constraint: person is excluded from that date-shift combination
- **Preferred shifts** → Soft constraint: scheduler gives bonus for assigning to that date-shift combination

### Preference Propagation Flow
```
User UI → script.js → app.py (/api/schedule)
  → schedule.py (formal_scheduler_api)
  → Constraint Model
  → Hard/Soft Constraints Applied
```

> **Note:** If no shift is specified in preferences sent via API, it defaults to 'All' shifts. The scheduler respects hard emergency constraints strictly and uses soft constraints for preferred assignments as an optimization objective.

---

## ⚙️ Technical Details

### Technologies Used

| Layer | Technology |
|-------|------------|
| Backend Framework | Flask |
| Scheduling Algorithm | NetworkX (Min-Cost Max-Flow) |
| Data Processing | Pandas |
| Excel Export | OpenPyXL |
| PDF Reports | ReportLab |
| Frontend | HTML5, CSS3, Vanilla JavaScript |

### Algorithm Overview
1. **Graph Construction** — Creates a network with nodes for personnel, dates, shifts, and rooms
2. **Cost Assignment:**
   - Emergency exclusion: `5000` (maximum penalty)
   - Priority dates: `index × 10` (lower is better)
   - Auto-drafted: `200` (moderate penalty)
3. **Flow Optimization** — Minimum cost maximum flow algorithm with polynomial time complexity O(V²E²)
4. **Assignment** — Extracts faculty and staff assignments from the flow solution

### Performance
- Schedule generation: < 5 seconds for typical inputs
- Max capacity: 50 faculty, 50 staff, 50 rooms, 30 dates
- Memory efficient: works with in-memory data structures

---

## 📋 Input Format Reference

### Priority Dates Format
- Single date: `D1`
- Multiple dates: `D1,D2,D3`
- Dates are listed in order of preference

### Emergency Exclusions Format
- Single exclusion: `D1-Morning`
- Multiple exclusions: `D1-Morning,D2-Afternoon,D3-Morning`
- Format: `Date-Shift` where Shift is `Morning` or `Afternoon`

---

## 🔗 API Reference

### Generate Schedule
```http
POST /api/schedule
Content-Type: application/json

{
  "faculties_count": 3,
  "staff_count": 2,
  "rooms_count": 3,
  "dates_count": 2,
  "facultyData": {
    "F1": {"priority_dates": ["D1"], "emergency_shifts": ["D1-Afternoon"]},
    "F2": {"priority_dates": ["D2"], "emergency_shifts": []},
    "F3": {"priority_dates": ["D1","D2"], "emergency_shifts": ["D2-Morning"]}
  },
  "staffData": {
    "S1": {"priority_dates": ["D1"], "emergency_shifts": ["D1-Afternoon"]},
    "S2": {"priority_dates": ["D2"], "emergency_shifts": []}
  }
}
```

### Download Excel
```http
POST /api/download-excel
Content-Type: application/json

{
  "results": [
    {"Date": "D1", "Shift": "Morning", "Room": "R1", ...}
  ]
}
```

---

## 🔒 Error Handling

The system validates:
- ✓ Positive integer inputs for counts
- ✓ Valid date format in preferences
- ✓ Sufficient capacity for assignments
- ✓ Network flow feasibility
- ✓ Empty or malformed preference data
- ✓ API errors with descriptive messages

---

## 🛠️ Troubleshooting

### Port Already in Use
```python
# Change port in app.py:
if __name__ == '__main__':
    app.run(debug=True, port=8000)
```

### Missing Dependencies
```bash
pip install -r requirements.txt --force-reinstall --upgrade
```

### Excel Export Not Working
```bash
pip install openpyxl --upgrade
```

### Browser Console Errors
- Press **F12** to open developer tools
- Check **Console** tab for JavaScript errors
- Clear cache and reload (**Ctrl+Shift+Delete**)

---

## 🧪 Testing Checklist

- [ ] Run `pip install -r requirements.txt`
- [ ] Execute `python app.py`
- [ ] Verify Flask server starts without errors
- [ ] Open `http://localhost:5000` in browser
- [ ] Test with sample configuration (3 faculty, 2 staff, 3 rooms, 2 dates)
- [ ] Enter test preferences
- [ ] Generate schedule and verify results
- [ ] Export to CSV/Excel and verify file contents
- [ ] Test **"Start Over"** functionality
- [ ] Verify responsive design on mobile
- [ ] Check browser console for JS errors

---

## 🚢 Deployment Checklist

- [ ] Set `debug=False` in `app.py`
- [ ] Test with production WSGI server (Gunicorn)
- [ ] Configure CORS if needed
- [ ] Set up environment variables
- [ ] Enable HTTPS certificates
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Test backup/recovery

---

## 🎓 Future Enhancements

### Development
- Add database integration (SQLAlchemy)
- Implement user authentication
- Add schedule history tracking

### Production
- Deploy using Gunicorn + Nginx
- Add SSL certificates
- Set up monitoring and logging
- Implement backup strategies

### Features
- Email notifications for assignments
- Conflict detection and resolution
- Calendar integration
- Mobile app using Flask-CORS
- Analytics dashboard

---

## 📞 Support

For issues or questions, refer to the codebase documentation or check the browser console for JavaScript errors.

| Resource | Location |
|----------|----------|
| Main Interface | `http://localhost:5000` |
| API Base | `http://localhost:5000/api/` |
| Quick Setup | `QUICK_START.md` |
| Configuration | `CONFIG.py` |
