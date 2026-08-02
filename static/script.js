let currentScheduleResults = [];
let selectedPreferences = [];
let twoShiftPreferences = [];  // NEW: Store 2-shift preferences
let teacherList = [];
let staffList = [];
let loadedScheduleId = null; // Track the currently loaded routine

// Calendar variables
let selectedDates = [];
const today = new Date();
let currentMonth = today.getMonth();
let currentYear = today.getFullYear();
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Initialize calendar when page loads
document.addEventListener('DOMContentLoaded', function() {
    renderCalendar();
    populateYearSelect();
    loadRoutines();
});

async function loadTeacherData() {
    if (teacherList.length > 0 && staffList.length > 0) {
        return;
    }

    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        if (data.success) {
            teacherList = data.data.teachers || [];
            staffList = data.data.staff || [];
        }
    } catch (error) {
        console.error('Failed to load teacher data:', error);
    }
}

function toggleSavedRoutines() {
    const panel = document.getElementById('savedRoutinesPanel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadRoutines();
    } else {
        panel.style.display = 'none';
    }
}

async function loadRoutines() {
    const list = document.getElementById('routinesList');
    try {
        const response = await fetch('/api/routines');
        const data = await response.json();
        
        if (data.success && data.routines && data.routines.length > 0) {
            let html = '';
            data.routines.forEach(routine => {
                const dateObj = new Date(routine.created_at);
                const options = {
                    timeZone: 'Asia/Kolkata',
                    day: 'numeric', month: 'short', year: 'numeric',
                    hour: '2-digit', minute: '2-digit', hour12: true
                };
                const dateStr = dateObj.toLocaleString('en-IN', options);
                const safeName = routine.version_name.replace(/'/g, "\\'");
                html += `
                    <div class="routine-item" id="routine-${routine.id}" onclick="restoreRoutine(${routine.id}, '${safeName}')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="routine-name">${routine.version_name}</div>
                                <div class="routine-date">${dateStr}</div>
                            </div>
                            <div style="display: flex; gap: 5px;">
                                <button onclick="renameRoutine(event, ${routine.id}, '${safeName}')" class="btn btn-secondary" title="Rename" style="padding: 2px 5px; font-size: 0.7rem;">✏️</button>
                                <button onclick="deleteRoutine(event, ${routine.id})" class="btn btn-warning" title="Delete" style="padding: 2px 5px; font-size: 0.7rem; background: rgba(231, 76, 60, 0.7); border: none; color: white;">🗑️</button>
                            </div>
                        </div>
                    </div>
                `;
            });
            list.innerHTML = html;
        } else {
            list.innerHTML = '<p class="no-dates" style="width: 100%;">No routines saved yet.</p>';
        }
    } catch (error) {
        console.error('Failed to load routines:', error);
        list.innerHTML = '<p class="no-dates" style="width: 100%;">Failed to load routines.</p>';
    }
}

async function deleteRoutine(event, id) {
    event.stopPropagation();
    if (!confirm('Are you sure you want to delete this routine?')) return;

    try {
        const response = await fetch(`/api/routine/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            loadRoutines();
            if (loadedScheduleId === id) {
                loadedScheduleId = null;
                currentScheduleResults = [];
                document.getElementById('resultsSection').style.display = 'none';
            }
        } else {
            alert('Failed to delete routine: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to delete routine:', error);
    }
}

async function renameRoutine(event, id, currentName) {
    event.stopPropagation();
    const newName = prompt('Enter new routine name:', currentName);
    if (!newName || newName.trim() === '' || newName === currentName) return;

    try {
        const response = await fetch(`/api/routine/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: newName.trim() })
        });
        const data = await response.json();
        if (data.success) {
            loadRoutines();
            // Optional: update the heading if this routine is currently loaded
        } else {
            alert('Failed to rename routine: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to rename routine:', error);
    }
}

async function restoreRoutine(id, name) {
    document.getElementById('loadingSpinner').style.display = 'flex';
    
    // Highlight selected routine
    document.querySelectorAll('.routine-item').forEach(item => item.classList.remove('active'));
    const selectedItem = document.getElementById(`routine-${id}`);
    if (selectedItem) selectedItem.classList.add('active');

    try {
        const response = await fetch(`/api/routine/${id}`);
        const data = await response.json();
        
        if (data.success) {
            currentScheduleResults = data.results;
            loadedScheduleId = id;
            
            // Reconstruct selected dates
            selectedDates = data.dates;
            updateSelectedDatesDisplay();
            
            // Re-render calendar so it highlights the restored dates
            if (selectedDates.length > 0) {
                const firstDate = new Date(selectedDates[0]);
                currentMonth = firstDate.getMonth();
                currentYear = firstDate.getFullYear();
                document.getElementById("yearSelect").value = currentYear;
            }
            renderCalendar();
            
            // Display results table
            displayResults(data.results, {message: `Restored Routine: ${name}`});
            
            // Show preference panel so they can access Emergency Reschedule
            showPreferencePanel();
            
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to restore routine: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

function updatePreferenceSelects() {
    const teacherSelect = document.getElementById('preferenceTeacherSelect');
    const dateSelect = document.getElementById('preferenceDateSelect');
    const twoShiftsSelect = document.getElementById('twoShiftsTeacherSelect');
    
    const staffSelect = document.getElementById('preferenceStaffSelect');
    const staffDateSelect = document.getElementById('preferenceStaffDateSelect');

    teacherSelect.innerHTML = '<option value="">Select teacher</option>';
    teacherList.forEach(teacher => {
        teacherSelect.innerHTML += `<option value="${teacher}">${teacher}</option>`;
    });

    staffSelect.innerHTML = '<option value="">Select staff</option>';
    staffList.forEach(staff => {
        staffSelect.innerHTML += `<option value="${staff}">${staff}</option>`;
    });
    
    // NEW: Also populate the two-shifts teacher select (Faculty Only)
    twoShiftsSelect.innerHTML = '<option value="">Select faculty member</option>';
    teacherList.forEach(teacher => {
        twoShiftsSelect.innerHTML += `<option value="${teacher}">${teacher}</option>`;
    });

    const emPersonSelect = document.getElementById('emergencyPersonSelect');
    if (emPersonSelect) {
        emPersonSelect.innerHTML = '<option value="">Select Absentee...</option>';
        teacherList.forEach(teacher => {
            emPersonSelect.innerHTML += `<option value="${teacher}">${teacher}</option>`;
        });
        staffList.forEach(staff => {
            emPersonSelect.innerHTML += `<option value="${staff}">${staff}</option>`;
        });
    }

    dateSelect.innerHTML = '<option value="">Select date</option>';
    selectedDates.slice().sort().forEach(date => {
        dateSelect.innerHTML += `<option value="${date}">${date}</option>`;
    });

    staffDateSelect.innerHTML = '<option value="">Select date</option>';
    selectedDates.slice().sort().forEach(date => {
        staffDateSelect.innerHTML += `<option value="${date}">${date}</option>`;
    });

    const emDateSelect = document.getElementById('emergencyDateSelect');
    if (emDateSelect) {
        emDateSelect.innerHTML = '<option value="">Absence Effective From...</option>';
        selectedDates.slice().sort().forEach(date => {
            emDateSelect.innerHTML += `<option value="${date}">${date}</option>`;
        });
    }
}

function showPreferencePanel() {
    if (selectedDates.length === 0) {
        alert('Select exam dates first before adding preferences.');
        return;
    }
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('preferenceSection').style.display = 'block';
    
    // Only show Emergency Reschedule if a DB routine is currently loaded
    const emSec = document.getElementById('emergencySection');
    if (emSec) {
        emSec.style.display = loadedScheduleId ? 'block' : 'none';
    }
    
    loadTeacherData().then(updatePreferenceSelects);
    updatePreferenceRulesList();
    updateTwoShiftsList();  // NEW: Update the two-shifts list
}

function hidePreferencePanel() {
    document.getElementById('preferenceSection').style.display = 'none';
    const emSec = document.getElementById('emergencySection');
    if (emSec) emSec.style.display = 'none';
    document.getElementById('uploadSection').style.display = 'block';
}

function addPreferenceRule(type = 'teacher') {
    let person, date, status, shift;

    if (type === 'teacher') {
        person = document.getElementById('preferenceTeacherSelect').value;
        date = document.getElementById('preferenceDateSelect').value;
        status = document.getElementById('preferenceStatusSelect').value;
        shift = document.getElementById('preferenceShiftSelect').value;
    } else {
        person = document.getElementById('preferenceStaffSelect').value;
        date = document.getElementById('preferenceStaffDateSelect').value;
        status = document.getElementById('preferenceStaffStatusSelect').value;
        shift = document.getElementById('preferenceStaffShiftSelect').value;
    }

    if (!person || !date) {
        alert('Please choose both person and date.');
        return;
    }

    const existingIndex = selectedPreferences.findIndex(rule => (rule.person === person || rule.teacher === person) && rule.date === date && rule.shift === shift);
    if (existingIndex !== -1) {
        selectedPreferences[existingIndex].status = status;
    } else {
        selectedPreferences.push({ person, date, shift, status });
    }

    updatePreferenceRulesList();
}

function updatePreferenceRulesList() {
    const list = document.getElementById('preferenceRulesList');
    if (selectedPreferences.length === 0) {
        list.innerHTML = '<p class="no-dates">No preference rules added yet.</p>';
        return;
    }
    let html = '';
    selectedPreferences.forEach((rule, index) => {
        // Create compact identifier format: person_date_shift
        const dateOnly = rule.date ? rule.date.split('-').slice(2).join('-') : 'unknown'; // Extract day from date
        const shiftLower = (rule.shift || 'morning').toLowerCase();
        const personName = rule.person || rule.teacher || 'unknown';
        const identifier = `${personName}_${dateOnly}_${shiftLower}`;
        
        html += `
            <div class="preference-item">
                <div>
                    <strong>${identifier}</strong> — <span style="color: #666;">${rule.status === 'emergency' ? '🚨 Emergency' : '⭐ Preferred'}</span>
                </div>
                <button onclick="removePreferenceRule(${index})">Remove</button>
            </div>
        `;
    });
    list.innerHTML = html;
}

function removePreferenceRule(index) {
    selectedPreferences.splice(index, 1);
    updatePreferenceRulesList();
}

// NEW: Functions for managing 2-shift preferences
function addTwoShiftPreference() {
    const teacher = document.getElementById('twoShiftsTeacherSelect').value;
    const permission = document.getElementById('twoShiftsPermissionSelect').value;

    if (!teacher) {
        alert('Please select a faculty member.');
        return;
    }

    // Check if preference already exists and update it
    const existingIndex = twoShiftPreferences.findIndex(p => p.person === teacher);
    if (existingIndex !== -1) {
        twoShiftPreferences[existingIndex].allowTwoShifts = (permission === 'yes');
    } else {
        twoShiftPreferences.push({
            person: teacher,
            allowTwoShifts: (permission === 'yes')
        });
    }

    updateTwoShiftsList();
}

function updateTwoShiftsList() {
    const list = document.getElementById('twoShiftsList');
    if (twoShiftPreferences.length === 0) {
        list.innerHTML = '<p class="no-dates">No 2-shift preferences set yet.</p>';
        return;
    }
    let html = '';
    twoShiftPreferences.forEach((pref, index) => {
        const status = pref.allowTwoShifts ? '✅ Allow' : '❌ Restrict';
        const statusColor = pref.allowTwoShifts ? 'green' : 'red';
        
        html += `
            <div class="preference-item">
                <div>
                    <strong>${pref.person}</strong> — <span style="color: ${statusColor};">${status}</span>
                </div>
                <button onclick="removeTwoShiftPreference(${index})">Remove</button>
            </div>
        `;
    });
    list.innerHTML = html;
}

function removeTwoShiftPreference(index) {
    twoShiftPreferences.splice(index, 1);
    updateTwoShiftsList();
}

async function applyPreferences() {
    if (selectedPreferences.length === 0 && twoShiftPreferences.length === 0) {
        alert('No preference rules added yet.');
        return;
    }
    await processSchedule(true);
}


// Calendar functions
function populateYearSelect() {
    const yearSelect = document.getElementById("yearSelect");
    for (let y = 2024; y <= 2030; y++) {
        let option = document.createElement("option");
        option.value = y;
        option.text = y;
        if (y === currentYear) option.selected = true;
        yearSelect.appendChild(option);
    }
}

function renderCalendar() {
    const daysContainer = document.getElementById("days");
    const monthYear = document.getElementById("monthYear");
    
    daysContainer.innerHTML = "";
    monthYear.innerText = `${monthNames[currentMonth]} ${currentYear}`;

    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const totalDays = new Date(currentYear, currentMonth + 1, 0).getDate();

    // Empty spaces for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
        daysContainer.innerHTML += "<div></div>";
    }

    for (let day = 1; day <= totalDays; day++) {
        const paddedDay = String(day).padStart(2, '0');
        const paddedMonth = String(currentMonth + 1).padStart(2, '0');
        const dateStr = `${currentYear}-${paddedMonth}-${paddedDay}`;

        const div = document.createElement("div");
        div.classList.add("day");
        div.innerText = day;

        // Highlight today
        if (
            day === today.getDate() &&
            currentMonth === today.getMonth() &&
            currentYear === today.getFullYear()
        ) {
            div.classList.add("today");
        }

        if (selectedDates.includes(dateStr)) {
            div.classList.add("selected");
        }

        div.onclick = () => toggleDate(dateStr, div);
        daysContainer.appendChild(div);
    }
}

function toggleDate(dateStr, element) {
    if (selectedDates.includes(dateStr)) {
        selectedDates = selectedDates.filter(d => d !== dateStr);
        element.classList.remove("selected");
    } else {
        selectedDates.push(dateStr);
        element.classList.add("selected");
    }
    updateSelectedDatesDisplay();
}

function updateSelectedDatesDisplay() {
    const selectedDatesDiv = document.getElementById("selectedDatesList");
    
    if (selectedDates.length === 0) {
        selectedDatesDiv.innerHTML = '<p class="no-dates">No dates selected yet</p>';
        return;
    }
    
    // Sort dates for better display
    const sortedDates = [...selectedDates].sort();
    
    let html = '';
    sortedDates.forEach(dateStr => {
        const date = new Date(dateStr);
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        
        html += `
            <div class="selected-date-item">
                <span class="selected-date-text">${formattedDate}</span>
                <button class="remove-date-btn" onclick="removeDate('${dateStr}')">×</button>
            </div>
        `;
    });
    
    selectedDatesDiv.innerHTML = html;
}

function removeDate(dateStr) {
    selectedDates = selectedDates.filter(d => d !== dateStr);
    updateSelectedDatesDisplay();
    renderCalendar(); // Update calendar display
}

function clearAllDates() {
    if (selectedDates.length === 0) return;
    
    if (confirm(`Are you sure you want to clear all ${selectedDates.length} selected dates?`)) {
        selectedDates = [];
        updateSelectedDatesDisplay();
        renderCalendar(); // Update calendar display
    }
}

function changeMonth(direction) {
    currentMonth += direction;

    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    } else if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }

    document.getElementById("yearSelect").value = currentYear;
    renderCalendar();
}

function changeYear() {
    currentYear = parseInt(document.getElementById("yearSelect").value);
    renderCalendar();
}

// Process schedule with selected dates
async function processSchedule() {
    if (selectedDates.length === 0) {
        alert('Please select at least one exam date');
        return;
    }

    // Show loading spinner
    document.getElementById('loadingSpinner').style.display = 'flex';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('processBtn').innerText = 'Processing...';

    const reqFac = parseInt(document.getElementById('reqFacInput').value) || 2;
    const reqStf = parseInt(document.getElementById('reqStfInput').value) || 1;
    
    // This is a new schedule — clear any previously loaded DB routine
    loadedScheduleId = null;
    const emSec = document.getElementById('emergencySection');
    if (emSec) emSec.style.display = 'none';

    try {
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                exam_dates: selectedDates,
                preferences: selectedPreferences,
                two_shift_preferences: twoShiftPreferences,
                req_fac: reqFac,
                req_stf: reqStf
            })
        });

        const data = await response.json();

        if (data.success) {
            currentScheduleResults = data.results;
            displayResults(data.results, data.status);
            // Don't loadRoutines because we haven't saved it to DB yet
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to generate schedule: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('processBtn').disabled = false;
        document.getElementById('processBtn').innerText = 'Generate Schedule';
    }
}

async function saveCurrentRoutine() {
    if (!currentScheduleResults || currentScheduleResults.length === 0) {
        alert('There is no schedule generated to save.');
        return;
    }
    
    const inputField = document.getElementById('saveRoutineNameInput');
    const routineName = inputField.value.trim();
    if (!routineName) {
        alert('Please enter a name for this routine.');
        return;
    }
    
    try {
        const response = await fetch('/api/save_routine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentScheduleResults,
                version_name: routineName
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Routine saved successfully!');
            inputField.value = '';
            loadRoutines();
        } else {
            alert('Failed to save routine: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to save routine:', error);
        alert('Failed to save routine: ' + error.message);
    }
}

async function triggerEmergencyReschedule() {
    const person = document.getElementById('emergencyPersonSelect').value;
    const date = document.getElementById('emergencyDateSelect').value;
    
    if (!person || !date) {
        alert('Please select both the absentee and the effective date.');
        return;
    }
    
    if (!loadedScheduleId) {
        alert('You must restore a routine first before you can run an Emergency Reschedule on it.');
        return;
    }
    
    if (!confirm(`This will read the selected schedule from the PostgreSQL database, LOCK all assignments prior to ${date}, remove ${person} from all assignments on or after ${date}, and rebalance the rest. Proceed?`)) {
        return;
    }
    
    document.getElementById('loadingSpinner').style.display = 'flex';
    
    try {
        const response = await fetch('/api/emergency_reschedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ person: person, emergency_date: date, schedule_id: loadedScheduleId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentScheduleResults = data.results;
            hidePreferencePanel();
            displayResults(data.results, data.status);
            alert("Emergency Database Reschedule Complete!\nThe past has been locked and the future has been re-optimized.");
            loadRoutines(); // Refresh routines to show the newly saved emergency schedule
        } else {
            showError(data.error);
        }
    } catch (e) {
        showError("Emergency reschedule request failed: " + e.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Display results in table
function displayResults(results, status) {
    const resultsHead = document.getElementById('resultsHead');
    const resultsBody = document.getElementById('resultsBody');
    
    // Determine max faculties and staffs
    let maxFac = 0;
    let maxStf = 0;
    if (results.length > 0) {
        maxFac = results[0].faculties ? results[0].faculties.length : (results[0].faculty1 ? 2 : 0);
        maxStf = results[0].staffs ? results[0].staffs.length : (results[0].staff ? 1 : 0);
    }
    
    // Generate Header
    let headHtml = `<tr>
        <th>Date</th>
        <th>Shift</th>
        <th>Room</th>`;
    for(let i=0; i<maxFac; i++) {
        headHtml += `<th>Faculty ${i+1}</th>`;
    }
    for(let i=0; i<maxStf; i++) {
        headHtml += `<th>Staff ${i+1}</th>`;
    }
    headHtml += `</tr>`;
    resultsHead.innerHTML = headHtml;

    resultsBody.innerHTML = '';
    results.forEach(row => {
        const tr = document.createElement('tr');
        let html = `
            <td>${row.date}</td>
            <td>${row.shift}</td>
            <td>${row.room}</td>
        `;
        
        if (row.faculties) {
            for(let i=0; i<maxFac; i++) {
                html += `<td>${row.faculties[i] || '---'}</td>`;
            }
            for(let i=0; i<maxStf; i++) {
                html += `<td>${row.staffs[i] || '---'}</td>`;
            }
        } else {
            // Fallback for legacy format
            html += `
                <td>${row.faculty1}</td>
                <td>${row.faculty2}</td>
                <td>${row.staff}</td>
            `;
        }
        
        tr.innerHTML = html;
        resultsBody.appendChild(tr);
    });

    // Display status message
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = status.message || 'Schedule generated successfully';
    statusDiv.className = 'status-message';
    
    if (status.empty_positions > 0) {
        statusDiv.classList.add('warning');
    } else {
        statusDiv.classList.add('success');
    }

    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Export to CSV (main, teacher, staff, or room grouped)
async function exportToCSV(csvType = 'main') {
    if (currentScheduleResults.length === 0) {
        alert('No results to export');
        return;
    }

    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentScheduleResults,
                type: csvType
            })
        });

        if (response.ok) {
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `schedule_${csvType}.csv`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            // Download the file synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log(`✓ Downloaded: ${filename}`);
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to export CSV: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Export all CSVs as ZIP
async function exportAllAsZip() {
    if (currentScheduleResults.length === 0) {
        alert('No results to export');
        return;
    }

    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-all-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentScheduleResults
            })
        });

        if (response.ok) {
            // Download the ZIP file synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'exam_schedules.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log('✓ Downloaded: exam_schedules.zip');
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to export ZIP: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Download PDF for schedule
async function downloadPDF(pdfType = 'main') {
    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: pdfType
            })
        });

        if (response.ok) {
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `schedule_${pdfType}.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            // Download the PDF synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log(`✓ Downloaded: ${filename}`);
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to download PDF: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// View Grouped Schedules (display in main results table)
function viewAndDownloadSchedule(scheduleType) {
    if (currentScheduleResults.length === 0) {
        alert('No results to display');
        return;
    }

    const resultsTable = document.getElementById('resultsTable');
    const tableHead = resultsTable.querySelector('thead');
    const tableBody = document.getElementById('resultsBody');

    let headers = [];
    let rows = [];

    // Determine max faculty/staff counts across all rows
    let maxFac = 0, maxStf = 0;
    currentScheduleResults.forEach(row => {
        maxFac = Math.max(maxFac, (row.faculties || []).length);
        maxStf = Math.max(maxStf, (row.staffs || []).length);
    });
    if (maxFac === 0) maxFac = 2; // legacy fallback
    if (maxStf === 0) maxStf = 1;

    const facCols = Array.from({length: maxFac}, (_, i) => `Faculty ${i + 1}`);
    const stfCols = Array.from({length: maxStf}, (_, i) => `Staff ${i + 1}`);

    // Helper: get faculty/staff name at index from row (supports both formats)
    const getFac = (row, i) => {
        if (row.faculties) return row.faculties[i] || '---';
        if (i === 0) return row.faculty1 || '---';
        if (i === 1) return row.faculty2 || '---';
        return '---';
    };
    const getStf = (row, i) => {
        if (row.staffs) return row.staffs[i] || '---';
        if (i === 0) return row.staff || '---';
        return '---';
    };

    if (scheduleType === 'room') {
        headers = ['Date', 'Room', 'Shift', ...facCols, ...stfCols];
        rows = currentScheduleResults.map(row => [
            row.date, row.room, row.shift,
            ...Array.from({length: maxFac}, (_, i) => getFac(row, i)),
            ...Array.from({length: maxStf}, (_, i) => getStf(row, i))
        ]);
        rows.sort((a, b) => a[1].localeCompare(b[1]) || a[0].localeCompare(b[0]));
    }
    else if (scheduleType === 'teacher') {
        headers = ['Teacher', 'Date', 'Shift', 'Room', 'Role'];
        const teacherMap = {};

        currentScheduleResults.forEach(row => {
            const facs = row.faculties || [row.faculty1, row.faculty2].filter(Boolean);
            facs.forEach((name, i) => {
                if (!name || name === 'N/A' || name === '---') return;
                if (!teacherMap[name]) teacherMap[name] = [];
                teacherMap[name].push([name, row.date, row.shift, row.room, `Faculty ${i + 1}`]);
            });
        });

        rows = Object.values(teacherMap).flat();
        rows.sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
    }
    else if (scheduleType === 'staff') {
        headers = ['Staff', 'Date', 'Shift', 'Room', ...facCols];
        const staffMap = {};

        currentScheduleResults.forEach(row => {
            const stfs = row.staffs || [row.staff].filter(Boolean);
            stfs.forEach((name, si) => {
                if (!name || name === 'N/A' || name === '---') return;
                if (!staffMap[name]) staffMap[name] = [];
                const facNames = Array.from({length: maxFac}, (_, i) => getFac(row, i));
                staffMap[name].push([name, row.date, row.shift, row.room, ...facNames]);
            });
        });

        rows = Object.values(staffMap).flat();
        rows.sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
    }
    else { // main
        headers = ['Date', 'Shift', 'Room', ...facCols, ...stfCols];
        rows = currentScheduleResults.map(row => [
            row.date, row.shift, row.room,
            ...Array.from({length: maxFac}, (_, i) => getFac(row, i)),
            ...Array.from({length: maxStf}, (_, i) => getStf(row, i))
        ]);
    }

    // Update table headers
    tableHead.innerHTML = '';
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);

    // Update table body
    tableBody.innerHTML = '';
    rows.forEach(rowData => {
        const tr = document.createElement('tr');
        rowData.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell ?? '---';
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });

    // Scroll to table
    resultsTable.scrollIntoView({ behavior: 'smooth' });
}





// Show error message
function showError(message) {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = '❌ Error: ' + message;
    statusDiv.className = 'status-message error';
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Reset form
function resetForm() {
    document.getElementById('examDatesFile').value = '';
    document.getElementById('resultsSection').style.display = 'none';
    currentScheduleResults = [];
    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}
