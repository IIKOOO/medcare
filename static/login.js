function login(role) {
    const email = document.querySelector('input[name="email"]').value;
    const password = document.querySelector('input[name="password"]').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email, password: password, role: role }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (role === 'nurse') {
                window.location.href = '/nurse_main';
            } else if (role === 'student') {
                window.location.href = '/student_main';
            }else if (role === 'admin') {
                window.location.href = '/admin_main';
            }
        } else {
            alert(data.message); 
        }
    })
    .catch(error => console.error('Error:', error));

    return false;
}


function submitComment(studentId, table) {
    const comment = document.getElementById(`comment-${studentId}`).value;

    fetch(`/upload_comment/${studentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            comment: comment,
            table: table  
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Comment uploaded successfully!');
        } else {
            alert('Error uploading comment.');
        }
    })
    .catch(error => console.error('Error:', error));
}


function moveToApproved(studentId) {
    fetch(`/move_to_approved/${studentId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Moved to approved successfully.');
            location.reload(); 
        } else {
            alert('Failed to move to approved.');
        }
    });
}

function moveToPending(studentId) {
    fetch(`/move_to_pending/${studentId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Moved to pending successfully.');
            location.reload(); 
        } else {
            alert('Failed to move to pending.');
        }
    });
}

function deleteUser(table, accountId) {
    fetch('/modify_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: table, operation: 'delete', account_id: accountId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) location.reload();
        else alert("Failed to delete user.");
    });
}

function uploadCSV() {
    const formData = new FormData(document.getElementById('csvForm'));
    fetch('/upload_csv', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) alert("CSV uploaded successfully!");
        else alert("Failed to upload CSV.");
        location.reload();
    });
}

document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const formData = new FormData(this);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload();
        } else {
            alert(data.message); 
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while uploading.'); 
    });
});
    
function displayInIframe(studentId, fileType, table) {
    const iframe = document.getElementById('pdfIframe');
    iframe.src = `/display_file/${studentId}/${fileType}/${table}`;

    const fullName = document.getElementById(`student-name-${studentId}`).textContent;
    const nameDisplay = document.getElementById('student-name-display');
    if (nameDisplay) {
        nameDisplay.textContent = fullName;
    }

    if (fileType === 'lab_result') {
        const commentBtn = document.getElementById(`comment-btn-${studentId}`);
        const approvedBtn = document.getElementById(`approved-btn-${studentId}`);
        const pendingBtn = document.getElementById(`pending-btn-${studentId}`);
        const scheduleBtn = document.getElementById(`schedule-btn-${studentId}`);

        if (commentBtn) commentBtn.disabled = false;
        if (approvedBtn) approvedBtn.disabled = false;
        if (pendingBtn) pendingBtn.disabled = false;
        if (scheduleBtn) scheduleBtn.disabled = false;
    }
}

function openScheduleModal(studentId) {
    const studentName = document.querySelector(`#student-name-${studentId}`).textContent; 
    const studentSchoolYear = document.querySelector(`#student-school-year-${studentId}`).textContent;

    document.getElementById('student_id').value = studentId;
    document.getElementById('student_name').value = studentName;
    document.getElementById('student_school_year').value = studentSchoolYear;

    document.getElementById('scheduleModal').style.display = "block";
}


function closeScheduleModal() {
    document.getElementById('scheduleModal').style.display = "none";
}

window.onclick = function(event) {
    if (event.target == document.getElementById('scheduleModal')) {
        closeScheduleModal();
    }
}

function deleteSchedule(scheduleId) {
    alert("Delete functionality for schedule ID: " + scheduleId);
}

function toggleAccountStatus(table, accountId, action) {
    fetch('/toggle_account_status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ table: table, account_id: accountId, action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload(); 
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

function submitSchedule() {
    const form = document.getElementById('scheduleForm');
    const formData = new FormData(form);

    fetch('/set_schedule', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.href = '/nurse_main';
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

document.getElementById('scheduleForm').addEventListener('submit', function(event) {
    event.preventDefault();
    submitSchedule();
});


function searchStudentTable() {
    const input = document.getElementById('searchStudent');
    const filter = input.value.toLowerCase();
    const table = document.getElementById('studentTable');
    const rows = table.getElementsByTagName('tr');

    for (let i = 1; i < rows.length; i++) {
        const fullnameCell = rows[i].getElementsByTagName('td')[3];
        if (fullnameCell) {
            const textValue = fullnameCell.textContent || fullnameCell.innerText;
            rows[i].style.display = textValue.toLowerCase().indexOf(filter) > -1 ? '' : 'none';
        }
    }
}