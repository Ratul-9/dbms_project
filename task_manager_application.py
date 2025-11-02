from flask import Flask, request, redirect, url_for, render_template_string, g, jsonify
import sqlite3
import os
from datetime import datetime
app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')

TEMPLATE_BASE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Task Manager</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>:root{--primary:#6366f1;--secondary:#8b5cf6;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--dark:#1e293b;--light:#f8fafc}body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}.container{max-width:1400px}.glass-card{background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-radius:20px;border:1px solid rgba(255,255,255,0.3);box-shadow:0 8px 32px rgba(0,0,0,0.1)}.header-card{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border-radius:20px;padding:2rem;margin-bottom:2rem;box-shadow:0 10px 40px rgba(102,126,234,0.3)}.task-card{background:white;border-radius:16px;border:none;margin-bottom:1rem;transition:all 0.3s ease;box-shadow:0 2px 8px rgba(0,0,0,0.08)}.task-card:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,0.15)}.btn-custom{border-radius:12px;padding:0.6rem 1.5rem;font-weight:600;transition:all 0.3s ease;border:none}.btn-custom:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.2)}.btn-primary-custom{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white}.btn-success-custom{background:linear-gradient(135deg,#10b981 0%,#059669 100%);color:white}.form-control-custom{border-radius:12px;border:2px solid #e2e8f0;padding:0.75rem 1rem;transition:all 0.3s ease}.form-control-custom:focus{border-color:#667eea;box-shadow:0 0 0 3px rgba(102,126,234,0.1)}.badge-custom{padding:0.5rem 1rem;border-radius:8px;font-weight:600;font-size:0.75rem}.user-card{background:white;border-radius:16px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.08)}.priority-high{border-left:4px solid #ef4444}.priority-medium{border-left:4px solid #f59e0b}.priority-low{border-left:4px solid #10b981}.deadline-badge{background:#fef3c7;color:#92400e;padding:0.4rem 0.8rem;border-radius:8px;font-size:0.75rem;font-weight:600}.deadline-overdue{background:#fee2e2;color:#991b1b}.filter-section{background:white;border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.08)}h1,h2,h5{font-weight:700}@media(max-width:768px){.header-card{padding:1.5rem}}</style></head><body><div class="container py-4">{% block body %}{% endblock %}</div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script></body></html>'''

TEMPLATE_INDEX = '''{% extends "base" %}{% block body %}<div class="header-card"><div class="d-flex justify-content-between align-items-center"><div><h1 class="mb-2"><i class="fas fa-tasks me-3"></i>Task Manager</h1><p class="mb-0 opacity-75">Organize and track your team's work efficiently</p></div><a class="btn btn-light btn-custom" href="/new_task"><i class="fas fa-plus me-2"></i>New Task</a></div></div><div class="row"><div class="col-lg-8"><div class="filter-section"><form class="row g-3 align-items-end" method="get" action="/"><div class="col-md-4"><label class="form-label small fw-bold text-muted"><i class="fas fa-user me-2"></i>Filter by User</label><select name="filter_user" class="form-select form-control-custom"><option value="">All users</option>{% for u in users %}<option value="{{u.id}}" {% if filter_user and filter_user==u.id %}selected{% endif %}>{{u.name}}</option>{% endfor %}</select></div><div class="col-md-4"><label class="form-label small fw-bold text-muted"><i class="fas fa-info-circle me-2"></i>Status</label><select name="status" class="form-select form-control-custom"><option value="">Any status</option><option value="open" {% if status=='open' %}selected{% endif %}>Open</option><option value="in_progress" {% if status=='in_progress' %}selected{% endif %}>In Progress</option><option value="done" {% if status=='done' %}selected{% endif %}>Done</option></select></div><div class="col-md-4"><label class="form-label small fw-bold text-muted opacity-0">.</label><button class="btn btn-primary-custom btn-custom w-100"><i class="fas fa-filter me-2"></i>Apply Filters</button></div></form></div>{% if tasks %}{% for t in tasks %}<div class="task-card priority-{{t.priority}}"><div class="card-body"><div class="row align-items-start"><div class="col-lg-8"><h5 class="mb-2">{{t.title}}</h5><p class="text-muted mb-3">{{t.description or 'No description'}}</p><div class="d-flex flex-wrap gap-2 align-items-center"><span class="badge badge-custom bg-{{'success' if t.status=='done' else 'primary' if t.status=='in_progress' else 'secondary'}}"><i class="fas fa-{{'check-circle' if t.status=='done' else 'spinner' if t.status=='in_progress' else 'circle'}} me-1"></i>{{t.status.replace('_',' ').title()}}</span><span class="badge badge-custom bg-{{'danger' if t.priority=='high' else 'warning' if t.priority=='medium' else 'info'}}"><i class="fas fa-flag me-1"></i>{{t.priority.title()}}</span>{% if t.deadline %}<span class="deadline-badge {% if t.is_overdue %}deadline-overdue{% endif %}"><i class="fas fa-calendar-alt me-1"></i>Due: {{t.deadline_formatted}}{% if t.is_overdue %} <i class="fas fa-exclamation-triangle ms-1"></i>{% endif %}</span>{% endif %}</div></div><div class="col-lg-4 text-lg-end mt-3 mt-lg-0"><div class="mb-3"><i class="fas fa-user-circle text-muted me-2"></i><span class="fw-semibold">{{t.assignee_name or 'Unassigned'}}</span><br><small class="text-muted"><i class="far fa-clock me-1"></i>{{t.created_at}}</small></div><div class="d-flex gap-2 justify-content-lg-end"><a class="btn btn-sm btn-outline-primary btn-custom" href="/edit/{{t.id}}"><i class="fas fa-edit me-1"></i>Edit</a><a class="btn btn-sm btn-outline-danger btn-custom" href="/delete/{{t.id}}" onclick="return confirm('Delete this task?')"><i class="fas fa-trash me-1"></i>Delete</a></div></div></div></div></div>{% endfor %}{% else %}<div class="glass-card text-center py-5"><i class="fas fa-inbox fa-3x text-muted mb-3"></i><h4 class="text-muted">No tasks found</h4><p class="text-muted">Create your first task to get started!</p><a href="/new_task" class="btn btn-primary-custom btn-custom mt-3"><i class="fas fa-plus me-2"></i>Create Task</a></div>{% endif %}</div><div class="col-lg-4"><div class="user-card mb-3"><h5 class="mb-3"><i class="fas fa-users me-2 text-primary"></i>Team Members</h5><ul class="list-group list-group-flush mb-3">{% for u in users %}<li class="list-group-item d-flex justify-content-between align-items-center border-0 px-0"><span><i class="fas fa-user-circle text-muted me-2"></i>{{u.name}}</span><span class="badge bg-primary rounded-pill">{{u.count}}</span></li>{% endfor %}{% if not users %}<li class="list-group-item border-0 px-0 text-muted text-center">No users yet</li>{% endif %}</ul><form method="post" action="/new_user" class="d-flex gap-2"><input name="name" placeholder="Add team member" class="form-control form-control-custom" required><button class="btn btn-success-custom btn-custom"><i class="fas fa-plus"></i></button></form></div><div class="user-card"><h5 class="mb-3"><i class="fas fa-chart-pie me-2 text-success"></i>Quick Stats</h5><div class="d-flex justify-content-between mb-2"><span class="text-muted">Total Tasks:</span><span class="fw-bold">{{stats.total}}</span></div><div class="d-flex justify-content-between mb-2"><span class="text-muted">Completed:</span><span class="fw-bold text-success">{{stats.done}}</span></div><div class="d-flex justify-content-between mb-2"><span class="text-muted">In Progress:</span><span class="fw-bold text-primary">{{stats.in_progress}}</span></div><div class="d-flex justify-content-between"><span class="text-muted">Overdue:</span><span class="fw-bold text-danger">{{stats.overdue}}</span></div></div></div></div>{% endblock %}'''

TEMPLATE_NEW_TASK = '''{% extends "base" %}{% block body %}<div class="row justify-content-center"><div class="col-lg-8"><div class="glass-card p-4"><div class="mb-4"><h2><i class="fas fa-plus-circle me-2 text-primary"></i>Create New Task</h2><p class="text-muted">Fill in the details below to create a new task</p></div><form method="post" action="/new_task"><div class="mb-3"><label class="form-label fw-bold"><i class="fas fa-heading me-2"></i>Title</label><input name="title" placeholder="Enter task title" class="form-control form-control-custom" required></div><div class="mb-3"><label class="form-label fw-bold"><i class="fas fa-align-left me-2"></i>Description</label><textarea name="description" placeholder="Enter task description" class="form-control form-control-custom" rows="4"></textarea></div><div class="row"><div class="col-md-6 mb-3"><label class="form-label fw-bold"><i class="fas fa-user me-2"></i>Assign To</label><select name="assignee" class="form-select form-control-custom"><option value="">-- Unassigned --</option>{% for u in users %}<option value="{{u.id}}">{{u.name}}</option>{% endfor %}</select></div><div class="col-md-6 mb-3"><label class="form-label fw-bold"><i class="fas fa-flag me-2"></i>Priority</label><select name="priority" class="form-select form-control-custom"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></div></div><div class="mb-4"><label class="form-label fw-bold"><i class="fas fa-calendar-alt me-2"></i>Deadline (Optional)</label><input type="date" name="deadline" class="form-control form-control-custom"></div><div class="d-flex gap-2"><button class="btn btn-primary-custom btn-custom"><i class="fas fa-save me-2"></i>Create Task</button><a class="btn btn-outline-secondary btn-custom" href="/"><i class="fas fa-times me-2"></i>Cancel</a></div></form></div></div></div>{% endblock %}'''

TEMPLATE_EDIT_TASK = '''{% extends "base" %}{% block body %}<div class="row justify-content-center"><div class="col-lg-8"><div class="glass-card p-4"><div class="mb-4"><h2><i class="fas fa-edit me-2 text-primary"></i>Edit Task</h2><p class="text-muted">Update the task details below</p></div><form method="post" action="/edit/{{task.id}}"><div class="mb-3"><label class="form-label fw-bold"><i class="fas fa-heading me-2"></i>Title</label><input name="title" value="{{task.title}}" class="form-control form-control-custom" required></div><div class="mb-3"><label class="form-label fw-bold"><i class="fas fa-align-left me-2"></i>Description</label><textarea name="description" class="form-control form-control-custom" rows="4">{{task.description}}</textarea></div><div class="row"><div class="col-md-4 mb-3"><label class="form-label fw-bold"><i class="fas fa-user me-2"></i>Assign To</label><select name="assignee" class="form-select form-control-custom"><option value="">-- Unassigned --</option>{% for u in users %}<option value="{{u.id}}" {% if task.assignee_id==u.id %}selected{% endif %}>{{u.name}}</option>{% endfor %}</select></div><div class="col-md-4 mb-3"><label class="form-label fw-bold"><i class="fas fa-info-circle me-2"></i>Status</label><select name="status" class="form-select form-control-custom"><option value="open" {% if task.status=='open' %}selected{% endif %}>Open</option><option value="in_progress" {% if task.status=='in_progress' %}selected{% endif %}>In Progress</option><option value="done" {% if task.status=='done' %}selected{% endif %}>Done</option></select></div><div class="col-md-4 mb-3"><label class="form-label fw-bold"><i class="fas fa-flag me-2"></i>Priority</label><select name="priority" class="form-select form-control-custom"><option value="low" {% if task.priority=='low' %}selected{% endif %}>Low</option><option value="medium" {% if task.priority=='medium' %}selected{% endif %}>Medium</option><option value="high" {% if task.priority=='high' %}selected{% endif %}>High</option></select></div></div><div class="mb-4"><label class="form-label fw-bold"><i class="fas fa-calendar-alt me-2"></i>Deadline (Optional)</label><input type="date" name="deadline" value="{{task.deadline or ''}}" class="form-control form-control-custom"></div><div class="d-flex gap-2"><button class="btn btn-primary-custom btn-custom"><i class="fas fa-save me-2"></i>Save Changes</button><a class="btn btn-outline-secondary btn-custom" href="/"><i class="fas fa-times me-2"></i>Cancel</a></div></form></div></div></div>{% endblock %}'''

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    if os.path.exists(DB_PATH):
        # Check if deadline column exists, if not add it
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cur.fetchall()]
        if 'deadline' not in columns:
            cur.execute('ALTER TABLE tasks ADD COLUMN deadline TEXT')
            conn.commit()
        conn.close()
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, assignee_id INTEGER, status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', deadline TEXT, created_at TEXT, updated_at TEXT, FOREIGN KEY(assignee_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    filter_user = request.args.get('filter_user', type=int)
    status = request.args.get('status', '')
    db = get_db()
    cur = db.cursor()
    q = 'SELECT t.*, u.name as assignee_name FROM tasks t LEFT JOIN users u ON t.assignee_id=u.id'
    params = []
    where = []
    if filter_user:
        where.append('t.assignee_id=?')
        params.append(filter_user)
    if status:
        where.append('t.status=?')
        params.append(status)
    if where:
        q += ' WHERE ' + ' AND '.join(where)
    q += ' ORDER BY CASE priority WHEN "high" THEN 0 WHEN "medium" THEN 1 ELSE 2 END, created_at DESC'
    cur.execute(q, params)
    rows = cur.fetchall()
    tasks = []
    today = datetime.utcnow().date()
    for r in rows:
        is_overdue = False
        deadline_formatted = None
        if r['deadline']:
            try:
                deadline_date = datetime.fromisoformat(r['deadline']).date()
                deadline_formatted = deadline_date.strftime('%b %d, %Y')
                if deadline_date < today and r['status'] != 'done':
                    is_overdue = True
            except:
                pass
        tasks.append({
            'id': r['id'],
            'title': r['title'],
            'description': r['description'],
            'assignee_id': r['assignee_id'],
            'assignee_name': r['assignee_name'],
            'status': r['status'],
            'priority': r['priority'],
            'deadline': r['deadline'],
            'deadline_formatted': deadline_formatted,
            'is_overdue': is_overdue,
            'created_at': r['created_at']
        })
    cur.execute('SELECT u.id, u.name, COUNT(t.id) as count FROM users u LEFT JOIN tasks t ON t.assignee_id=u.id GROUP BY u.id')
    users = cur.fetchall()
    users_list = [{'id': u['id'], 'name': u['name'], 'count': u['count']} for u in users]
    
    # Calculate stats
    cur.execute('SELECT COUNT(*) as total FROM tasks')
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as done FROM tasks WHERE status='done'")
    done = cur.fetchone()['done']
    cur.execute("SELECT COUNT(*) as in_progress FROM tasks WHERE status='in_progress'")
    in_progress = cur.fetchone()['in_progress']
    cur.execute("SELECT COUNT(*) as overdue FROM tasks WHERE deadline < date('now') AND status != 'done'")
    overdue = cur.fetchone()['overdue']
    
    stats = {'total': total, 'done': done, 'in_progress': in_progress, 'overdue': overdue}
    
    return render_template_string(TEMPLATE_INDEX, tasks=tasks, users=users_list, filter_user=filter_user, status=status, stats=stats)

@app.route('/new_user', methods=['POST'])
def new_user():
    name = request.form.get('name','').strip()
    if name:
        db = get_db()
        db.execute('INSERT INTO users(name) VALUES(?)', (name,))
        db.commit()
    return redirect(url_for('index'))

@app.route('/new_task', methods=['GET','POST'])
def new_task():
    db = get_db()
    cur = db.cursor()
    if request.method=='POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        assignee = request.form.get('assignee')
        priority = request.form.get('priority','medium')
        deadline = request.form.get('deadline','').strip()
        created_at = datetime.utcnow().isoformat()
        assignee_id = int(assignee) if assignee else None
        if title:
            cur.execute('INSERT INTO tasks(title, description, assignee_id, priority, deadline, created_at, updated_at) VALUES(?,?,?,?,?,?,?)', (title, description, assignee_id, priority, deadline if deadline else None, created_at, created_at))
            db.commit()
        return redirect(url_for('index'))
    cur.execute('SELECT id, name FROM users')
    users = cur.fetchall()
    users_list = [{'id': u['id'], 'name': u['name']} for u in users]
    return render_template_string(TEMPLATE_NEW_TASK, users=users_list)

@app.route('/edit/<int:task_id>', methods=['GET','POST'])
def edit(task_id):
    db = get_db()
    cur = db.cursor()
    if request.method=='POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        assignee = request.form.get('assignee')
        status = request.form.get('status','open')
        priority = request.form.get('priority','medium')
        deadline = request.form.get('deadline','').strip()
        assignee_id = int(assignee) if assignee else None
        updated_at = datetime.utcnow().isoformat()
        cur.execute('UPDATE tasks SET title=?, description=?, assignee_id=?, status=?, priority=?, deadline=?, updated_at=? WHERE id=?', (title, description, assignee_id, status, priority, deadline if deadline else None, updated_at, task_id))
        db.commit()
        return redirect(url_for('index'))
    cur.execute('SELECT id, name FROM users')
    users = cur.fetchall()
    cur.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
    r = cur.fetchone()
    if not r:
        return redirect(url_for('index'))
    task = {k: r[k] for k in r.keys()}
    users_list = [{'id': u['id'], 'name': u['name']} for u in users]
    return render_template_string(TEMPLATE_EDIT_TASK, task=task, users=users_list)

@app.route('/delete/<int:task_id>')
def delete(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    db.commit()
    return redirect(url_for('index'))

@app.route('/api/tasks')
def api_tasks():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT t.*, u.name as assignee_name FROM tasks t LEFT JOIN users u ON t.assignee_id=u.id')
    rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users')
def api_users():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM users')
    rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

if __name__=='__main__':
    init_db()
    from jinja2 import DictLoader
    app.jinja_loader = DictLoader({
        'base': TEMPLATE_BASE
    })
    app.run(debug=True, host='0.0.0.0', port=5000)