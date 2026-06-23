import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'pagina-web-sublime'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import app, seed_default_admin  # noqa: E402

if __name__ == '__main__':
    app.run(debug=True, port=5000)

seed_default_admin()
