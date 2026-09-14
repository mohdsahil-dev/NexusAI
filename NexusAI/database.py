import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app and ensure data directory exists."""
    data_dir = os.path.abspath(os.path.join(app.root_path, 'data'))
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'invoices'), exist_ok=True)
    
    db_file = os.path.join(data_dir, 'nexusai.db').replace('\\', '/')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
    
    db.init_app(app)
    with app.app_context():
        db.create_all()
