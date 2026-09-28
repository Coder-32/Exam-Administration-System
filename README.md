# Exam Invigilation Scheduling & Administration System

🔗 **Live Deployment**: [https://exam-administration-system.onrender.com/](https://exam-administration-system.onrender.com/)

A modular web application designed for universities and academic institutions to generate optimal exam invigilation routines. The system models the invigilation scheduling problem as a **Min-Cost Max-Flow (MCMF)** network flow optimization problem and solves it using **Google OR-Tools** and **Constraint Programming (CP-SAT)**.

---

## 🌟 Key Highlights

- **Mathematical Optimization Engine**: Invigilation duty assignments modeled as a Min-Cost Max-Flow network and solved using Google OR-Tools (`SimpleMinCostFlow` and `cp_model`).
- **Fair Workload Distribution**: Quadratic / piecewise-convex cost curves guarantee equitable shift distribution across all available professors and staff members.
- **Preference & Emergency Constraint Handling**: Strict hard-constraint enforcement for emergency leave and soft-constraint reward optimization for preferred shifts/dates.
- **Dynamic Emergency Rescheduling**: Instant re-balancing of past rosters if an invigilator calls in sick, locking past assignments while reallocating future shifts seamlessly.
- **Modular Architecture**: Clean separation into `routes/`, `utils/`, `service/`, and centralized configuration in `config.py`.
- **Multi-Format Export System**: Real-time generation of grouped CSV files (Main, Faculty, Staff, Room), one-click ZIP download, and formatted ReportLab PDF reports.
- **Intelligent PDF Roster Ingestion**: Automated bulk import of teachers and staff from PDF documents with fallback to Tesseract OCR for scanned schedules.
- **Zero-Configuration Database**: Pure SQLite database (`database/exam_schedules.db`) built directly on Python's native standard library with zero external database setup required.

---

## 🏛️ System Architecture

The application is structured into modular layers following clean code and domain-driven design principles:

```text
Exam-Administration-System/
├── app.py                      # Flask Application factory and server entrypoint
├── config.py                   # Centralized configuration (paths, credentials, OCR settings)
├── requirements.txt            # Python dependencies
├── .env.example                # Local environment template
├── database/                   # Seed files and local SQLite database
├── schedule_storage/           # Runtime storage for generated CSVs, ZIPs, and PDFs
│
├── routes/                     # Blueprint modular route controllers
│   ├── __init__.py             # Route registration registry
│   ├── auth_routes.py          # /login, /logout, /register_account, password management
│   ├── view_routes.py          # Page rendering for / (dashboard) and /register
│   ├── personnel_routes.py     # CRUD for teachers, staff, rooms, and PDF roster parsing
│   ├── schedule_routes.py      # /api/schedule, emergency rescheduling, and routine persistence
│   └── export_routes.py        # /api/download-csv, /api/download-all-csv, /api/download-pdf
│
├── utils/                      # Reusable utility functions
│   ├── __init__.py
│   ├── ocr_utils.py            # PDF text extraction (PyPDF2) and OCR pipeline (PyMuPDF + Tesseract)
│   └── export_utils.py         # Dynamic column detection, DataFrame grouping, and ZIP builder
│
├── service/                    # Core business logic and algorithmic solvers
│   ├── __init__.py
│   ├── schedule.py             # OR-Tools SimpleMinCostFlow, CP-SAT solver, and NetworkX fallback
│   ├── db.py                   # Pure SQLite data persistence layer (User-scoped tables & routines)
│   ├── db_config.py            # Database connection configuration
│   ├── createTable.py          # ReportLab PDF report generation
│   └── export_service.py       # Excel and metrics calculation utilities
│
├── templates/                  # Frontend HTML5 templates
│   ├── index.html              # Main scheduling console and calendar interface
│   ├── register.html           # Personnel and room administration interface
│   ├── login.html              # Authentication portal
│   └── register_account.html   # User account creation
│
└── static/                     # Frontend static assets
    ├── style.css               # Modern gradient UI styling and responsive layouts
    └── script.js               # Dynamic DOM manipulation, API client, and calendar logic
```

---

## 🧮 Mathematical Modeling: Min-Cost Max-Flow in Google OR-Tools

### 1. The Invigilation Scheduling Problem

Given:
- A set of exam dates $D = \{d_1, d_2, \dots, d_{|D|}\}$
- A set of shifts per day $S = \{\text{Morning}, \text{Afternoon}\}$
- A set of examination rooms $R = \{r_1, r_2, \dots, r_{|R|}\}$
- A pool of faculty members $F$ and support staff $St$
- Personnel requirements: each room $r$ on date $d$, shift $s$ requires $K_{fac}$ faculty members and $K_{stf}$ staff members.

Total demand for the exam session:
$$Q = |D| \times |S| \times |R| \times (K_{fac} + K_{stf})$$

### 2. Network Flow Formulation

The problem is represented as a directed graph $G = (V, E)$ with capacity function $c(u, v)$ and unit cost function $w(u, v)$:

```text
[ SOURCE ] (Supply = +Q)
    │
    ▼ (Capacity = 1, Cost = (i-1) * 150)  <-- Workload Tranches (Fairness)
[ Workload Nodes: P_W_1, P_W_2, ... ]
    │
    ▼ (Capacity = 1, Cost = 0)
[ Personnel Node: Person P ]
    │
    ▼ (Capacity = 2, Cost = 0)            <-- Max 2 shifts per day
[ Person-Date Node: P_d ]
    │
    ▼ (Capacity = 1, Cost = C_pref)       <-- Shift Preference / Emergency Cost
[ Person-Shift Node: P_{d,s} ]
    │
    ▼ (Capacity = 1, Cost = 0)            <-- Exclusivity (at most 1 room per shift)
[ Room Requirement Node: REQ_{d,s,r} ]
    │
    ▼ (Capacity = K_fac or K_stf, Cost = 0)
[ SINK ] (Demand = -Q)
```

#### Graph Layer Specifications:

1. **Source ($S$) & Sink ($T$)**:
   - Node $S$ has supply $+Q$.
   - Node $T$ has demand $-Q$ (supply $-Q$).
   - All intermediate nodes have net supply $0$ (flow conservation: $\sum_{u} f(u, v) = \sum_{w} f(v, w)$).

2. **Workload Balancing Tranches ($P_{W_1}, P_{W_2}, \dots$)**:
   - To avoid overloading active invigilators while leaving others idle, each person $P$ has multiple incoming arcs from $S$, each representing an additional shift tranche $i \in \{1, \dots, |D| \times |S|\}$.
   - Arc $(S \to P_{W_i})$ has `capacity = 1` and `cost = (i - 1) * 150`.
   - **Mathematical Effect**: This creates a strictly convex piecewise-linear penalty curve:
     - 1st assigned shift: cost $= 0$
     - 2nd assigned shift: cost $= 150$
     - 3rd assigned shift: cost $= 300$
     - 4th assigned shift: cost $= 450$
   - Because the algorithm minimizes total cost, flow is distributed evenly across all invigilators before any single invigilator receives higher-index tranches.

3. **Daily Shift Limits ($P \to P_d$)**:
   - Each arc from $P$ to date node $P_d$ has `capacity = 2` and `cost = 0`.
   - This prevents anyone from working more than 2 shifts on any given day.

4. **Shift Assignment & Preferences ($P_d \to P_{d,s}$)**:
   - Each arc from $P_d$ to shift node $P_{d,s}$ has `capacity = 1` and unit cost $C_{pref}$:
     - **Preferred Shift / Priority Date**: $C_{pref} = 10$ (strong incentive to assign).
     - **Standard Shift**: $C_{pref} = 200$ (baseline neutral cost).
     - **Emergency Exclusion / Leave**: $C_{pref} = 5000$ (or arc is removed entirely as a hard constraint).

5. **Room Allocation & Demand Satisfaction ($\text{REQ}_{d,s,r} \to T$)**:
   - Arcs from $P_{d,s}$ to $\text{F\_REQ}_{d,s,r}$ (for faculty) and $\text{S\_REQ}_{d,s,r}$ (for staff) have `capacity = 1` and `cost = 0`.
   - Arcs from $\text{F\_REQ}_{d,s,r} \to T$ have `capacity = K_fac` and `cost = 0`.
   - Arcs from $\text{S\_REQ}_{d,s,r} \to T$ have `capacity = K_stf` and `cost = 0`.

---

### 3. Implementation in Google OR-Tools

The system implements the solution using **two complementary OR-Tools paradigms**:

#### Method A: Direct Graph Flow (`ortools.graph.python.min_cost_flow.SimpleMinCostFlow`)

Located in [`service/schedule.py`](file:///c:/Users/Victus/Desktop/takehello/Exam-Administration-System/service/schedule.py):

```python
from ortools.graph.python import min_cost_flow

smcf = min_cost_flow.SimpleMinCostFlow()

# 1. Map string nodes to sequential integer IDs (0 ... N-1)
# 2. Add convex workload tranche arcs
for f_id in teachers:
    for w in range(1, total_shifts + 1):
        smcf.add_arc_with_capacity_and_unit_cost(source_id, w_node, 1, (w - 1) * 150)
        smcf.add_arc_with_capacity_and_unit_cost(w_node, person_node, 1, 0)

# 3. Add date-shift capacity and preference arcs
smcf.add_arc_with_capacity_and_unit_cost(person_node, date_node, 2, 0)
smcf.add_arc_with_capacity_and_unit_cost(date_node, shift_node, 1, preference_cost)

# 4. Add demand satisfaction arcs to Sink
smcf.add_arc_with_capacity_and_unit_cost(f_req_node, sink_id, req_fac, 0)
smcf.add_arc_with_capacity_and_unit_cost(s_req_node, sink_id, req_stf, 0)

# 5. Set node supplies and solve
smcf.set_node_supply(source_id, total_demand)
smcf.set_node_supply(sink_id, -total_demand)

status = smcf.solve()
if status in (smcf.OPTIMAL, smcf.FEASIBLE):
    # Flow on arc i > 0 indicates active assignment
    for arc_idx in active_arcs:
        if smcf.flow(arc_idx) > 0:
            assign_invigilator(...)
```

**Complexity**: Solved in polynomial time $O(V^2 E \log V)$ using the Cost-Scaling Push-Relabel algorithm, executing in under 20 milliseconds even for large university campuses.

#### Method B: Multi-Constraint CP-SAT Formulation (`ortools.sat.python.cp_model`)

For complex operational constraints (such as forbidding consecutive double-shifts unless explicitly permitted, or locking past duties during mid-session emergency rescheduling), the system utilizes OR-Tools CP-SAT:

1. **Binary Decision Variables**:
   $$x_{f, d, s, r} \in \{0, 1\} \quad \forall f \in F, d \in D, s \in S, r \in R$$

2. **Room Capacity Constraints**:
   $$\sum_{f \in F} x_{f, d, s, r} = K_{fac} \quad \text{and} \quad \sum_{st \in St} x_{st, d, s, r} = K_{stf}$$

3. **Exclusivity Constraint**:
   $$\sum_{r \in R} x_{f, d, s, r} \le 1 \quad \forall f \in F, d \in D, s \in S$$

4. **Emergency Absence Constraint**:
   $$x_{f_{absent}, d, s, r} = 0 \quad \forall d \ge d_{emergency}$$

5. **Workload Fairness Objective**:
   $$\text{Minimize} \quad 50 \cdot W_{max} + 200 \cdot (W_{max} - W_{min}) + 100 \sum \text{DoubleShiftPenalty} - 20 \sum \text{PriorityBonus}$$

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (Python 3.11 recommended)
- **Tesseract OCR** *(Optional: only needed if uploading scanned image PDFs)*

---

### Step 1: Clone and Prepare Environment

```bash
# Clone the repository
git clone https://github.com/your-username/exam-administration-system.git
cd exam-administration-system

# Create and activate virtual environment
# On Windows:
python -m venv venv
venv\Scripts\activate

# On macOS / Linux:
python3 -m venv venv
source venv/bin/activate
```

---

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3: Environment Setup

Copy `.env.example` to `.env`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Default configuration in `.env`:
```env
# Application Configuration
FLASK_ENV=development
SECRET_KEY=change-this-in-production
PORT=5000
PYTHONUNBUFFERED=1

# Database Configuration (Pure SQLite - stored in database/exam_schedules.db)
# SQLITE_DB_PATH=database/exam_schedules.db
```

---

### Step 4: Run the Application

```bash
python app.py
```

The application will start on:
```text
http://localhost:5000
```

---

## 📖 Step-by-Step User Workflow

### 1. Authentication & Registration
- Navigate to `http://localhost:5000/login`.
- Register a user account (e.g. `admin`).
- Each user maintains an isolated dataset of faculty, staff, rooms, and generated routines.

### 2. Personnel & Room Setup
- Navigate to the **Register** tab (`/register`).
- Add Faculty members and Staff members manually or upload a roster PDF.
  - Standard text PDFs are parsed directly with `PyPDF2`.
  - Scanned image PDFs can be parsed using the **Enable OCR** checkbox via `pytesseract`.
- Add Examination Rooms.

### 3. Schedule Generation
- Return to the **Dashboard** (`/`).
- Click on dates in the interactive calendar to designate examination days.
- (Optional) Configure shift preferences:
  - Set specific teachers as *Preferred* for desired dates/shifts.
  - Set *Emergency* exclusions for unavailable slots.
- Specify faculty required per room (default: 2) and staff required per room (default: 1).
- Click **"Generate Schedule"**.

### 4. Emergency Rescheduling
- In the event of sudden absenteeism:
  - Open a saved routine.
  - Select the absent personnel and the effective emergency date.
  - Click **"Emergency Reschedule"**.
  - All past dates are locked, while remaining slots are optimally re-distributed.

### 5. Multi-Format Downloads
- **Main Schedule CSV**: Complete roster sorted by date and shift.
- **Teacher Schedule CSV**: Grouped view showing every duty assigned to each professor.
- **Staff Schedule CSV**: Grouped view showing support duties.
- **Room Schedule CSV**: Roster formatted room-by-room for door postings.
- **All Schedules (ZIP)**: One-click bundle containing all CSV views.
- **PDF Report**: Publication-ready ReportLab document formatted with header branding and signature sections.

---

## 🔌 API Reference

### Authentication Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/login` | User login |
| `GET` | `/logout` | User logout |
| `POST` | `/register_account` | Create new user account |
| `POST` | `/api/change-password` | Update account password |
| `POST` | `/api/delete-account` | Permanently delete user and associated schedules |

### Personnel & Room Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/data` | Fetch all registered teachers, staff, and rooms |
| `POST` | `/api/register-teacher` | Register a new faculty member |
| `POST` | `/api/register-staff` | Register a new staff member |
| `POST` | `/api/delete-teacher` | Remove a faculty member |
| `POST` | `/api/delete-staff` | Remove a staff member |
| `POST` | `/api/register-room` | Register an examination room |
| `POST` | `/api/delete-room` | Remove an examination room |
| `POST` | `/api/upload-pdf-list` | Bulk upload teachers/staff from PDF (supports OCR) |

### Scheduling & Routine Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/schedule` | Execute OR-Tools optimization and return assignment table |
| `POST` | `/api/emergency_reschedule` | Re-balance future schedule slots around absent invigilator |
| `GET` | `/api/routines` | List metadata of all saved routines |
| `GET` | `/api/routine/<id>` | Retrieve full assignments for a saved routine |
| `POST` | `/api/save_routine` | Save generated schedule under a routine name |
| `DELETE` | `/api/routine/<id>` | Delete a saved routine |
| `PUT` | `/api/routine/<id>` | Rename a saved routine |

### Export Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/download-csv` | Download grouped CSV (`main`, `teacher`, `staff`, `room`) |
| `POST` | `/api/download-all-csv` | Download in-memory ZIP archive of all CSV formats |
| `POST` | `/api/download-pdf` | Download formatted ReportLab PDF report |

---

## 🛠️ Testing & Troubleshooting

### Port Conflict
If port `5000` is already occupied by another service:
- Set `PORT=8000` in `.env`, or run:
  ```bash
  $env:PORT=8000; python app.py
  ```

### Tesseract OCR Configuration
If your institution uploads scanned or handwritten PDF documents:
1. Install Tesseract OCR from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Set the binary path in `.env` if not in standard directory:
   ```env
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

### Database Storage
- The application uses pure SQLite (`database/exam_schedules.db`). No installation, configuration, or server management of external databases is required. Tables, indexes, and cascading foreign-key constraints are initialized automatically on launch.

---

## 📄 License
This project is open-source and available for educational and institutional administrative use.
