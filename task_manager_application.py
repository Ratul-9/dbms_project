from flask import Flask, request, redirect, url_for, render_template_string, g, jsonify
import sqlite3
import os
from datetime import datetime
app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')
TEMPLATE_BASE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Task Manager</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><div class="container py-4">{% block body %}{% endblock %}</div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script></body></html>'''
TEMPLATE_INDEX = '''{% extends "base" %}{% block body %}<div class="d-flex justify-content-between align-items-center mb-3"><h1>Task Manager</h1><a class="btn btn-primary" href="/new_task">New Task</a></div><div class="row"><div class="col-md-8"><div class="card mb-3"><div class="card-body"><form class="row g-2" method="get" action="/"> <div class="col-auto"><select name="filter_user" class="form-select"><option value="">All users</option>{% for u in users %}<option value="{{u.id}}" {% if filter_user and filter_user==u.id %}selected{% endif %}>{{u.name}}</option>{% endfor %}</select></div><div class="col-auto"><select name="status" class="form-select"><option value="">Any status</option><option value="open" {% if status=='open' %}selected{% endif %}>Open</option><option value="in_progress" {% if status=='in_progress' %}selected{% endif %}>In Progress</option><option value="done" {% if status=='done' %}selected{% endif %}>Done</option></select></div><div class="col-auto"><button class="btn btn-secondary">Filter</button></div></form></div></div>{% for t in tasks %}<div class="card mb-2"><div class="card-body"><div class="d-flex justify-content-between"><div><h5>{{t.title}}</h5><p class="mb-1">{{t.description}}</p><small>Assigned to: {{t.assignee_name or 'Unassigned'}} • Created: {{t.created_at}}</small></div><div class="text-end"><span class="badge bg-{{'success' if t.status=='done' else 'warning' if t.status=='in_progress' else 'secondary'}}">{{t.status.replace('_',' ').title()}}</span><div class="mt-2"><a class="btn btn-sm btn-outline-primary" href="/edit/{{t.id}}">Edit</a> <a class="btn btn-sm btn-outline-danger" href="/delete/{{t.id}}">Delete</a></div></div></div></div></div>{% endfor %}</div><div class="col-md-4"><div class="card"><div class="card-body"><h5>Users</h5><ul class="list-group mb-3">{% for u in users %}<li class="list-group-item d-flex justify-content-between align-items-center">{{u.name}}<span class="badge bg-primary rounded-pill">{{u.count}}</span></li>{% endfor %}</ul><form method="post" action="/new_user" class="d-flex"><input name="name" placeholder="New user" class="form-control me-2"><button class="btn btn-success">Add</button></form></div></div></div></div>{% endblock %}'''
TEMPLATE_NEW_TASK = '''{% extends "base" %}{% block body %}<h2>New Task</h2><form method="post" action="/new_task"><div class="mb-3"><input name="title" placeholder="Title" class="form-control"></div><div class="mb-3"><textarea name="description" placeholder="Description" class="form-control"></textarea></div><div class="mb-3"><select name="assignee" class="form-select"><option value="">-- unassigned --</option>{% for u in users %}<option value="{{u.id}}">{{u.name}}</option>{% endfor %}</select></div><div class="mb-3"><select name="priority" class="form-select"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div><button class="btn btn-primary">Create</button> <a class="btn btn-link" href="/">Cancel</a></form>{% endblock %}'''
TEMPLATE_EDIT_TASK = '''{% extends "base" %}{% block body %}<h2>Edit Task</h2><form method="post" action="/edit/{{task.id}}"><div class="mb-3"><input name="title" value="{{task.title}}" class="form-control"></div><div class="mb-3"><textarea name="description" class="form-control">{{task.description}}</textarea></div><div class="mb-3"><select name="assignee" class="form-select"><option value="">-- unassigned --</option>{% for u in users %}<option value="{{u.id}}" {% if task.assignee_id==u.id %}selected{% endif %}>{{u.name}}</option>{% endfor %}</select></div><div class="mb-3"><select name="status" class="form-select"><option value="open" {% if task.status=='open' %}selected{% endif %}>Open</option><option value="in_progress" {% if task.status=='in_progress' %}selected{% endif %}>In Progress</option><option value="done" {% if task.status=='done' %}selected{% endif %}>Done</option></select></div><div class="mb-3"><select name="priority" class="form-select"><option value="low" {% if task.priority=='low' %}selected{% endif %}>Low</option><option value="medium" {% if task.priority=='medium' %}selected{% endif %}>Medium</option><option value="high" {% if task.priority=='high' %}selected{% endif %}>High</option></select></div><button class="btn btn-primary">Save</button> <a class="btn btn-link" href="/">Cancel</a></form>{% endblock %}'''
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
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, assignee_id INTEGER, status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', created_at TEXT, updated_at TEXT, FOREIGN KEY(assignee_id) REFERENCES users(id))''')
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
    for r in rows:
        tasks.append({
            'id': r['id'],
            'title': r['title'],
            'description': r['description'],
            'assignee_id': r['assignee_id'],
            'assignee_name': r['assignee_name'],
            'status': r['status'],
            'priority': r['priority'],
            'created_at': r['created_at']
        })
    cur.execute('SELECT u.id, u.name, COUNT(t.id) as count FROM users u LEFT JOIN tasks t ON t.assignee_id=u.id GROUP BY u.id')
    users = cur.fetchall()
    users_list = [{'id': u['id'], 'name': u['name'], 'count': u['count']} for u in users]
    return render_template_string(TEMPLATE_INDEX, tasks=tasks, users=users_list, filter_user=filter_user, status=status)
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
        created_at = datetime.utcnow().isoformat()
        assignee_id = int(assignee) if assignee else None
        if title:
            cur.execute('INSERT INTO tasks(title, description, assignee_id, priority, created_at, updated_at) VALUES(?,?,?,?,?,?)', (title, description, assignee_id, priority, created_at, created_at))
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
        assignee_id = int(assignee) if assignee else None
        updated_at = datetime.utcnow().isoformat()
        cur.execute('UPDATE tasks SET title=?, description=?, assignee_id=?, status=?, priority=?, updated_at=? WHERE id=?', (title, description, assignee_id, status, priority, updated_at, task_id))
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
