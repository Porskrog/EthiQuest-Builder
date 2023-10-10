from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from random import choice 
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

# Initialize your Flask app here
app = Flask(__name__)
CORS(app)

# Switch to testing mode (This is for demonstration; normally, you'd set this in your test setup)
app.config['TESTING'] = False

# Check if the app is in test mode
if app.config.get('TESTING'):
    app.config.from_pyfile('test_config.py')
else:
    # Your existing production/staging database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flow_camp:ghRta9wBEkr2@mysql28.unoeuro.com:3306/flow_camp_db'

# Database configurationm  -- new comment
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

##################################################################################
# Database tables for the Dilemmas, Options, Users, UserChoices, ViewedDilemmas  #
##################################################################################
class Dilemma(db.Model):
    __tablename__ = 'Dilemmas'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500))

    # Relationship to the Options table
    options = db.relationship('Option', back_populates='dilemma')

class Option(db.Model):
    __tablename__ = 'Options'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))
    pros = db.Column(db.String(500))
    cons = db.Column(db.String(500))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))

    # Relationship to the Dilemmas table
    dilemma = db.relationship('Dilemma', back_populates='options')

# Combined User table
class User(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incrementing ID
    UserID = db.Column(db.String(50), unique=True)  # For registered users
    cookie_id = db.Column(db.String(100), unique=True, nullable=True)  # For anonymous users
    LastVisit = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to UserChoices
    choices = db.relationship('UserChoice', back_populates='user')
    # Relationship to ViewedDilemma
    viewed_dilemmas = db.relationship('ViewedDilemma', back_populates='user')

# UserChoices table
class UserChoice(db.Model):
    __tablename__ = 'UserChoices'
    ChoiceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.id'))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    OptionID = db.Column(db.Integer, db.ForeignKey('Options.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='choices')
    option = db.relationship('Option') 

# Veiwed Dilemmas table 
class ViewedDilemma(db.Model):
    __tablename__ = 'ViewedDilemmas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    dilemma_id = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='viewed_dilemmas')
    dilemma = db.relationship('Dilemma')


# End of Database tables

########################
# Utility Functions    #
########################

# Function to get viewed dilemmas for a user
def get_viewed_dilemmas(user_id):
    viewed_dilemmas = ViewedDilemma.query.filter_by(user_id=user_id).all()
    viewed_dilemma_ids = [dilemma.dilemma_id for dilemma in viewed_dilemmas]
    return viewed_dilemma_ids

#####################
# Route Handlers    #
#####################
import logging

@app.route('/view_dilemma/<int:dilemma_id>', methods=['POST'])
def view_dilemma(dilemma_id):
    logging.info(f"Received request to mark dilemma {dilemma_id} as viewed")

    cookie_id = request.json.get('cookie_id')

    # Try to fetch the user by cookie ID
    user = User.query.filter_by(cookie_id=cookie_id).first()

    # If the user does not exist, create a new one
    if user is None:
        user = User(cookie_id=cookie_id)
        db.session.add(user)
        db.session.commit()

    # Now user.id will contain the ID, whether the user was just created or already existed
    user_id = user.id

    logging.info(f"User ID from request: {user_id}")

    # Check if this dilemma has been viewed by this user before
    viewed = ViewedDilemma.query.filter_by(user_id=user_id, dilemma_id=dilemma_id).first()
    if viewed:
        return jsonify({"message": "Dilemma has been viewed before by this user"}), 409

    # If not viewed, add to the ViewedDilemmas table
    new_view = ViewedDilemma(user_id=user_id, dilemma_id=dilemma_id)
    try:
        db.session.add(new_view)
        db.session.commit()
    except Exception as e:
        logging.error(f"Error while inserting into ViewedDilemmas: {e}")
        db.session.rollback()
        return jsonify({"message": "Internal Server Error"}), 500
    
    return jsonify({"message": "Dilemma marked as viewed"}), 201


@app.route('/add_dilemma', methods=['POST'])
def add_dilemma():
    data = request.get_json()
    new_dilemma = Dilemma(question=data['question'])
    db.session.add(new_dilemma)
    db.session.commit()
    return jsonify({'message': 'New dilemma added'}), 201

@app.route('/get_dilemmas', methods=['GET'])
def get_dilemmas():
    all_dilemmas = Dilemma.query.all()
    output = []

    for dilemma in all_dilemmas:
        dilemma_data = {}
        dilemma_data['id'] = dilemma.id
        dilemma_data['question'] = dilemma.question

        options = Option.query.filter_by(DilemmaID=dilemma.id).all()
        options_list = []

        for option in options:
            option_data = {}
            option_data['id'] = option.id
            option_data['text'] = option.text
            option_data['pros'] = option.pros
            option_data['cons'] = option.cons
            options_list.append(option_data)

        dilemma_data['options'] = options_list
        output.append(dilemma_data)

    return jsonify({'dilemmas': output})

@app.route('/add_option/<DilemmaID>', methods=['POST'])
def add_option(DilemmaID):
    data = request.get_json()
    new_option = Option(
        text=data['text'], 
        pros=data['pros'], 
        cons=data['cons'], 
        DilemmaID=DilemmaID
    )
    db.session.add(new_option)
    db.session.commit()
    return jsonify({'message': 'New option added'}), 201

@app.route('/get_options/<DilemmaID>', methods=['GET'])
def get_options(DilemmaID):
    options = Option.query.filter_by(DilemmaID=DilemmaID).all()
    output = []

    for option in options:
        option_data = {}
        option_data['id'] = option.id
        option_data['text'] = option.text
        option_data['pros'] = option.pros
        option_data['cons'] = option.cons
        output.append(option_data)

    return jsonify({'options': output})

@app.route('/get_random_dilemma', methods=['POST'])  # Changed to POST to get user details
def get_random_dilemma():
    data = request.get_json()
    cookie_id = data.get('cookie_id', None)  # Get cookie_id from request
    
    # Fetch the user from the database
    user = User.query.filter_by(cookie_id=cookie_id).first()
    
    # If user doesn't exist, create a new user
    if not user:
        new_user = User(cookie_id=cookie_id)
        db.session.add(new_user)
        db.session.commit()
        user = new_user
    
    # After fetching or creating a user  ######################## Take out again when finished debugging
    print(f"Fetched or created user with ID: {user.id}")

    # Get the list of viewed dilemmas for this user
    viewed_dilemmas = get_viewed_dilemmas(user.id)
    
    # Get all dilemmas from the database
    all_dilemmas = Dilemma.query.all()
    
    # Filter out the viewed dilemmas
    unviewed_dilemmas = [d for d in all_dilemmas if d.id not in viewed_dilemmas]
    
    # If there are no unviewed dilemmas, handle that case
    if not unviewed_dilemmas:
        return jsonify({"message": "No new dilemmas available"}), 404
    
    # Pick a random dilemma from the unviewed dilemmas
    selected_dilemma = choice(unviewed_dilemmas)
    
    # Before inserting into ViewedDilemmas ################# Take out again when finished debugging
    print(f"Inserting with user_id: {user.id}, dilemma_id: {selected_dilemma.id}")

    # Add an entry to the ViewedDilemmas table
    new_view = ViewedDilemma(user_id=user.id, dilemma_id=selected_dilemma.id)
    db.session.add(new_view)
    db.session.commit()

    options = Option.query.filter_by(DilemmaID=selected_dilemma.id).all()

    dilemma_data = {
        'id': selected_dilemma.id,
        'question': selected_dilemma.question,
        'options': [
            {
                'id': option.id,
                'text': option.text,
                'pros': option.pros,
                'cons': option.cons
            } for option in options
        ]
    }
    
    return jsonify({'dilemma': dilemma_data})


@app.route('/get_option_details/<OptionID>', methods=['GET'])
def get_option_details(OptionID):
    option = Option.query.filter_by(id=OptionID).first()
    if not option:
        return jsonify({'message': 'Option not found'}), 404

    option_data = {
        'id': option.id,
        'text': option.text,
        'pros': option.pros,
        'cons': option.cons
    }

    return jsonify({'option': option_data})

# Store user's choice
@app.route('/store_user_choice', methods=['POST'])
def store_user_choice():
    data = request.get_json()
    cookie_id = data['cookie_id']
    option_id = data['option_id']

    # Check if user exists
    user = User.query.filter_by(cookie_id=cookie_id).first()
    
    # If user doesn't exist, create a new user
    if not user:
        new_user = User(cookie_id=cookie_id)
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    # Store the user's choice
    new_choice = UserChoice(option_id=option_id, user_id=user.id)
    db.session.add(new_choice)
    db.session.commit()

    return jsonify({'message': 'User choice stored successfully'}), 200


@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()