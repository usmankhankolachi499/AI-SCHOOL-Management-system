// app.js — Ab data BROWSER me nahi, BACKEND (FastAPI) se aata hai
// Flow: UI (button click) → fetch() request → FastAPI → SQLite → JSON → render

const API = {
  token: localStorage.getItem('token') || null,
  user: null,

  // Har request ka common wrapper: header me token lagao, error handle karo
  async request(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (API.token) headers['Authorization'] = 'Bearer ' + API.token;

    const res = await fetch(path, { ...opts, headers });

    // 401 = token khatam/galat → wapas login screen par
    if (res.status === 401 && !path.includes('/auth/login')) {
      doLogout(false);
      throw new Error('Login expire ho gaya');
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Request fail hui');
    }
    return res.json();
  },
};

// In-memory copy of data (sirf dikhane ke liye; asal data DB me hai)
let students = [], teachers = [], classes = [], attendance = [], dashboardData = null;

// ---------- HELPERS ----------
function val(id) { return document.getElementById(id).value.trim(); }
function todayStr() { return new Date().toISOString().slice(0, 10); }
function esc(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ---------- LOGIN / REGISTER / LOGOUT ----------
async function login() {
  const email = val('login-email'), password = val('login-pass');
  if (!email || !password) { alert('Email aur Password daalein'); return; }
  try {
    const data = await API.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    API.token = data.access_token;
    API.user = data.user;
    localStorage.setItem('token', API.token);
    showApp();
  } catch (e) { alert('Login fail: ' + e.message); }
}

async function register() {
  const school = val('login-school'), email = val('login-email'), password = val('login-pass');
  if (!school || !email || !password) { alert('Teenoon fields zaroori hain'); return; }
  try {
    const data = await API.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ school_name: school, email, password }),
    });
    API.token = data.access_token;
    API.user = data.user;
    localStorage.setItem('token', API.token);
    showApp();
  } catch (e) { alert('Register fail: ' + e.message); }
}

function logout() { if (confirm('Logout karna hai?')) doLogout(true); }

function doLogout(reload) {
  localStorage.removeItem('token');
  API.token = null;
  if (reload) location.reload();
  document.getElementById('app').classList.remove('active');
  document.getElementById('login-screen').style.display = 'grid';
}

async function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').classList.add('active');
  document.getElementById('nav-school-name').textContent = API.user?.school_name || 'My School';
  await refreshData();
}

// ---------- DATA LOADING ----------
// Saara data ek saath backend se le aao + dashboard bhi
async function refreshData() {
  const [s, t, c] = await Promise.all([
    API.request('/api/students'),
    API.request('/api/teachers'),
    API.request('/api/classes'),
  ]);
  students = s; teachers = t; classes = c;
  dashboardData = await API.request('/api/dashboard');
  renderStudents();
  renderTeachers();
  renderClasses();
  renderDashboard();
}

async function loadAttendance() {
  const dateInput = document.getElementById('att-date');
  if (!dateInput.value) dateInput.value = todayStr();
  attendance = await API.request('/api/attendance?date=' + dateInput.value);
  renderAttendance();
}

// ---------- NAVIGATION ----------
document.querySelectorAll('.sidebar a').forEach(link => {
  link.addEventListener('click', async () => {
    document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + link.dataset.page).classList.add('active');
    if (link.dataset.page === 'attendance') await loadAttendance();
  });
});

// ---------- MODAL HELPERS ----------
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

// ---------- STUDENTS ----------
function openStudentModal(id) {
  const sel = document.getElementById('student-class');
  sel.innerHTML = classes.length
    ? classes.map(c => `<option value="${c.id}">${esc(c.name)}${c.section ? ' - ' + esc(c.section) : ''}</option>`).join('')
    : '<option value="">No classes — pehle Class add karein</option>';

  if (id) {
    const s = students.find(x => x.id === id);
    document.getElementById('student-modal-title').textContent = 'Edit Student';
    document.getElementById('student-id').value = s.id;
    document.getElementById('student-name').value = s.name;
    document.getElementById('student-class').value = s.class_id || '';
    document.getElementById('student-roll').value = s.roll_no;
    document.getElementById('student-contact').value = s.parent_contact || '';
  } else {
    document.getElementById('student-modal-title').textContent = 'Add Student';
    document.getElementById('student-id').value = '';
    document.getElementById('student-name').value = '';
    document.getElementById('student-class').value = classes[0]?.id || '';
    document.getElementById('student-roll').value = '';
    document.getElementById('student-contact').value = '';
  }
  openModal('student-modal');
}

async function saveStudent() {
  const id = document.getElementById('student-id').value;
  const name = val('student-name');
  const classVal = document.getElementById('student-class').value;
  const roll_no = val('student-roll');
  const parent_contact = val('student-contact');
  if (!name || !classVal || !roll_no) { alert('Name, Class aur Roll No zaroori hain'); return; }

  const body = JSON.stringify({
    name, roll_no, parent_contact,
    class_id: classVal ? Number(classVal) : null,
  });
  try {
    if (id) {
      await API.request('/api/students/' + id, { method: 'PUT', body });
    } else {
      await API.request('/api/students', { method: 'POST', body });
    }
    closeModal('student-modal');
    await refreshData(); // Students + Classes ka count + Dashboard fresh ho jata hai
  } catch (e) { alert(e.message); }
}

async function deleteStudent(id) {
  if (!confirm('Delete this student?')) return;
  try {
    await API.request('/api/students/' + id, { method: 'DELETE' });
    await refreshData();
  } catch (e) { alert(e.message); }
}

function renderStudents() {
  const tbody = document.getElementById('students-body');
  if (!students.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">No students yet.</td></tr>';
    return;
  }
  tbody.innerHTML = students.map(s => `
    <tr>
      <td>${esc(s.name)}</td>
      <td>${esc(s.class_name || '—')}</td>
      <td>${esc(s.roll_no)}</td>
      <td>${esc(s.parent_contact || '—')}</td>
      <td class="actions">
        <button class="btn btn-ghost btn-sm" onclick="openStudentModal(${s.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteStudent(${s.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

// ---------- TEACHERS ----------
function openTeacherModal(id) {
  const title = document.getElementById('teacher-modal-title');
  if (id) {
    const t = teachers.find(x => x.id === id);
    title.textContent = 'Edit Teacher';
    document.getElementById('teacher-id').value = t.id;
    document.getElementById('teacher-name').value = t.name;
    document.getElementById('teacher-subject').value = t.subject;
    document.getElementById('teacher-email').value = t.email;
  } else {
    title.textContent = 'Add Teacher';
    document.getElementById('teacher-id').value = '';
    document.getElementById('teacher-name').value = '';
    document.getElementById('teacher-subject').value = '';
    document.getElementById('teacher-email').value = '';
  }
  openModal('teacher-modal');
}

async function saveTeacher() {
  const id = document.getElementById('teacher-id').value;
  const name = val('teacher-name');
  const subject = val('teacher-subject');
  const email = val('teacher-email');
  if (!name || !subject) { alert('Name aur Subject zaroori hain'); return; }

  const body = JSON.stringify({ name, subject, email });
  try {
    if (id) {
      await API.request('/api/teachers/' + id, { method: 'PUT', body });
    } else {
      await API.request('/api/teachers', { method: 'POST', body });
    }
    closeModal('teacher-modal');
    await refreshData();
  } catch (e) { alert(e.message); }
}

async function deleteTeacher(id) {
  if (!confirm('Delete this teacher?')) return;
  try {
    await API.request('/api/teachers/' + id, { method: 'DELETE' });
    await refreshData();
  } catch (e) { alert(e.message); }
}

function renderTeachers() {
  const tbody = document.getElementById('teachers-body');
  if (!teachers.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty">No teachers yet.</td></tr>';
    return;
  }
  tbody.innerHTML = teachers.map(t => `
    <tr>
      <td>${esc(t.name)}</td>
      <td>${esc(t.subject)}</td>
      <td>${esc(t.email || '—')}</td>
      <td class="actions">
        <button class="btn btn-ghost btn-sm" onclick="openTeacherModal(${t.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteTeacher(${t.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

// ---------- CLASSES ----------
function openClassModal(id) {
  const title = document.getElementById('class-modal-title');
  if (id) {
    const c = classes.find(x => x.id === id);
    title.textContent = 'Edit Class';
    document.getElementById('class-id').value = c.id;
    document.getElementById('class-name').value = c.name;
    document.getElementById('class-section').value = c.section || '';
  } else {
    title.textContent = 'Add Class';
    document.getElementById('class-id').value = '';
    document.getElementById('class-name').value = '';
    document.getElementById('class-section').value = '';
  }
  openModal('class-modal');
}

async function saveClass() {
  const id = document.getElementById('class-id').value;
  const name = val('class-name');
  const section = val('class-section');
  if (!name) { alert('Class name zaroori hai'); return; }

  const body = JSON.stringify({ name, section });
  try {
    if (id) {
      await API.request('/api/classes/' + id, { method: 'PUT', body });
    } else {
      await API.request('/api/classes', { method: 'POST', body });
    }
    closeModal('class-modal');
    await refreshData();
  } catch (e) { alert(e.message); }
}

async function deleteClass(id) {
  if (!confirm('Delete this class?')) return;
  try {
    await API.request('/api/classes/' + id, { method: 'DELETE' });
    await refreshData();
  } catch (e) { alert(e.message); }
}

function renderClasses() {
  const tbody = document.getElementById('classes-body');
  if (!classes.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty">No classes yet.</td></tr>';
    return;
  }
  tbody.innerHTML = classes.map(c => `
    <tr>
      <td>${esc(c.name)}</td>
      <td>${esc(c.section || '—')}</td>
      <td>${c.student_count}</td>
      <td class="actions">
        <button class="btn btn-ghost btn-sm" onclick="openClassModal(${c.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteClass(${c.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

// ---------- ATTENDANCE ----------
function renderAttendance() {
  const list = document.getElementById('attendance-list');
  if (!students.length) {
    list.innerHTML = '<p class="empty">No students to mark attendance.</p>';
    return;
  }
  list.innerHTML = students.map(s => {
    const rec = attendance.find(a => a.student_id === s.id);
    const status = rec ? rec.status : '';
    return `
      <div class="attendance-row">
        <div class="name">${esc(s.name)} <small>${esc(s.class_name || '')} • Roll ${esc(s.roll_no)}</small></div>
        <div class="att-toggle">
          <button class="present ${status === 'present' ? 'active' : ''}"
            onclick="markAttendance(${s.id}, 'present')">Present</button>
          <button class="absent ${status === 'absent' ? 'active' : ''}"
            onclick="markAttendance(${s.id}, 'absent')">Absent</button>
        </div>
      </div>
    `;
  }).join('');
}

async function markAttendance(studentId, status) {
  const date = document.getElementById('att-date').value;
  try {
    await API.request('/api/attendance', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId, status, date }),
    });
    await loadAttendance();
    dashboardData = await API.request('/api/dashboard');
    renderDashboard();
  } catch (e) { alert(e.message); }
}

document.getElementById('att-date').addEventListener('change', loadAttendance);

// ---------- DASHBOARD ----------
function renderDashboard() {
  if (!dashboardData) return;
  document.getElementById('stat-students').textContent = dashboardData.students;
  document.getElementById('stat-teachers').textContent = dashboardData.teachers;
  document.getElementById('stat-classes').textContent = dashboardData.classes;
  document.getElementById('stat-attendance').textContent =
    dashboardData.marked ? `${dashboardData.present}/${dashboardData.marked}` : '—';

  const recentBody = document.getElementById('recent-students-body');
  if (!dashboardData.recent_students.length) {
    recentBody.innerHTML = '<tr><td colspan="3" class="empty">No students yet. Add one from Students page.</td></tr>';
  } else {
    recentBody.innerHTML = dashboardData.recent_students.map(s => `
      <tr><td>${esc(s.name)}</td><td>${esc(s.class_name || '—')}</td><td>${esc(s.roll_no)}</td></tr>
    `).join('');
  }
}

// ---------- INIT (page load hote hi) ----------
(async function init() {
  // Purana token hai? Backend se poocho — "yeh banda logged-in hai?"
  if (API.token) {
    try {
      API.user = await API.request('/api/auth/me');
      await showApp();
      return;
    } catch (e) { /* token invalid — login screen dikhegi */ }
  }
})();
