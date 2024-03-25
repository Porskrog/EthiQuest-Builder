from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
from flask_caching import Cache
from redis import Redis
import logging
import os

# Initialize Limiter and Cache
# First, adjust the Limiter creation to include the storage_uri
redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_uri)
# limiter = Limiter(key_func=get_remote_address)    # Taking this out for now
cache = Cache(config={'CACHE_TYPE': 'simple'})

def create_app():
    app = Flask(__name__)
    # CORS(app, origins=["https://ethiquest.ai"])
    # CORS(app, resources={r"/customer/*": {"origins": "https://ethiquest.ai"}})

    # Define allowed origins including both your production domain and any development/testing origins
    origins_allowed = ["https://ethiquest.ai", "http://localhost:8080", "http://localhost:*", "https://*.flutterflow.io"]
    # Apply CORS configuration to all routes with the specified list of origins
    CORS(app, supports_credentials=True, origins=origins_allowed)
    # Your additional setup continues here...

    limiter.init_app(app)  # Initialize Limiter
    cache.init_app(app)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flow_camp:ghRta9wBEkr2@mysql28.unoeuro.com:3306/flow_camp_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register blueprints
    from customer_routes import customer_bp  # Import your customer Blueprint
    from admin_routes import admin_bp  # Import your admin Blueprint
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app

app = create_app()

# Initialize logging
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    app.run()