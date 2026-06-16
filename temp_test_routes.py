import os
import sys
sys.path.insert(0, os.path.abspath('pagina-web-sublime'))
from app import app

c = app.test_client()
print('TEST RESULTS')
for p in ['/admin', '/admin-panel/']:
    r = c.get(p, follow_redirects=False)
    print(f'{p} -> {r.status_code} Location={r.headers.get("Location", "")}')
r = c.post('/api/login', json={'usuario': 'admin@sublime.com', 'contrasena': 'admin123'})
print(f'/api/login -> {r.status_code} Body={r.get_data(as_text=True)[:160].replace("\n", " ")}')
