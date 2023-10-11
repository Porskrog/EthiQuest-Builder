# customer_bp.py
from flask import Blueprint, jsonify
from flask_cors import CORS

customer_bp = Blueprint('customer', __name__)
CORS(customer_bp, origins=["https://flow.camp"])

@customer_bp.route('/get_data')
def get_customer_data():
    return jsonify({"data": "customer data"})

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

@customer_bp.route('/view_dilemma/<int:dilemma_id>', methods=['POST'])
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


@customer_bp.route('/get_options/<DilemmaID>', methods=['GET'])
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

@customer_bp.route('/get_random_dilemma', methods=['POST'])  # Changed to POST to get user details
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


@customer_bp.route('/get_option_details/<OptionID>', methods=['GET'])
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
@customer_bp.route('/store_user_choice', methods=['POST'])
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

if __name__ == '__main__':
    app.run()