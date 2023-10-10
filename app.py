from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
import logging
from customer_routes import customer_bp  # Import your customer Blueprint
from admin_routes import admin_bp  # Import your admin Blueprint

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flow_camp:ghRta9wBEkr2@mysql28.unoeuro.com:3306/flow_camp_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register blueprints
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app

app = create_app()

# Initialize logging
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    app.run()