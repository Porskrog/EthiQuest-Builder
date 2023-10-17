# customer_bp.py
from flask import Blueprint, jsonify, request
from models import User, Dilemma, Option, UserChoice, ViewedDilemma, ContextCharacteristic, DilemmasContextCharacteristic
from extensions import db
from flask_cors import CORS
from random import choice
from sqlalchemy import desc # To get the last dilemma and option for a user
from app import limiter, cache  # Assuming your app.py is named 'app.py'

import os
import openai
import json

api_key = os.environ.get('OPENAI_API_KEY')
openai.api_key = api_key

customer_bp = Blueprint('customer', __name__)
CORS(customer_bp, origins=["https://flow.camp"])

@customer_bp.route('/get_data')
def get_customer_data():
    return jsonify({"data": "customer data"})

######################################################################################################
# Utility Functions                                                                                  #
######################################################################################################

# Function to get viewed dilemmas for a user
def get_viewed_dilemmas(user_id):
    viewed_dilemmas = ViewedDilemma.query.filter_by(user_id=user_id).all()
    viewed_dilemma_ids = [dilemma.dilemma_id for dilemma in viewed_dilemmas]
    return viewed_dilemma_ids

# Fetch the last dilemma and option chosen by this user from the database.
def get_last_dilemma_and_option(user_id):
    last_choice = UserChoice.query.filter_by(UserID=user_id).order_by(UserChoice.Timestamp.desc()).first()
    if last_choice:
        last_dilemma = Dilemma.query.get(last_choice.DilemmaID)
        last_option = Option.query.get(last_choice.OptionID)
        return last_dilemma.question, last_option.text  # Assuming 'question' and 'text' are the relevant fields.
    else:
        return None, None

# Function to get or create a user
def get_or_create_user(cookie_id):
    user = User.query.filter_by(cookie_id=cookie_id).first()
    if not user:
        user = User(cookie_id=cookie_id)
        db.session.add(user)
        db.session.commit()
    return user

# Function to add a new dilemma and options to the database
def add_new_dilemma_and_options_to_db(context_list, description, options):
    new_dilemma = Dilemma(question=description)
    db.session.add(new_dilemma)
    db.session.commit()

    for opt in options:
        # Convert pros and cons lists to comma-separated strings
        new_option = Option(
            text=opt['text'],
            pros=', '.join(opt['pros']),
            cons=', '.join(opt['cons']),
            DilemmaID=new_dilemma.id
        )
        try:
            db.session.add(new_option)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")

    for characteristic in context_list:
        existing_characteristic = ContextCharacteristic.query.filter_by(name=characteristic).first()
        if not existing_characteristic:
            new_characteristic = ContextCharacteristic(name=characteristic)
            db.session.add(new_characteristic)
            db.session.commit()
            char_id = new_characteristic.id
        else:
            char_id = existing_characteristic.id

        new_dilemma_context = DilemmasContextCharacteristic(DilemmaID=new_dilemma.id, ContextCharacteristicID=char_id)
        db.session.add(new_dilemma_context)
        db.session.commit()
    return new_dilemma

# Function to fetch unviewed dilemmas for a user
def fetch_unviewed_dilemmas(user_id):
    viewed_dilemmas = get_viewed_dilemmas(user_id)
    all_dilemmas = Dilemma.query.all()
    unviewed_dilemmas = [d for d in all_dilemmas if d.id not in viewed_dilemmas]
    return unviewed_dilemmas


######################################################################################################
# Route Handlers                                                                                     #
######################################################################################################
import logging

logging.basicConfig(level=logging.INFO)  # Sets up basic logging

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

#####################################################################
#   Get Random Dilemma API endpoint for ALL users (free and paying) # 
#####################################################################

@limiter.limit("5 per minute")
@customer_bp.route('/get_random_dilemma', methods=['POST'])  # Changed to POST to get user details
def get_random_dilemma():
    try:
        data = request.get_json()
        cookie_id = data.get('cookie_id', None)  # Get cookie_id from request

        if not cookie_id:
            logging.warning("Missing cookie_id in the request")
            return jsonify({'message': 'Missing cookie_id'}), 400

        # Get or create the user   
        user = get_or_create_user(cookie_id)

        if user.user_type == 'Paying':
            # Generate new dilemma using GPT-4

            # Fetch the last dilemma and option for this user from the database
            last_dilemma, last_option = get_last_dilemma_and_option(user.id)

            # Decide whether to make the new dilemma consequential of the former dilemma
            make_consequential = choice([True, False])

            # Generate the prompt for GPT-4
            base_prompt = "Please generate an ethical and leadership dilemma related to program management."
            if make_consequential and last_dilemma and last_option:
                full_prompt = f"{base_prompt} It must be a direct consequence of the previous dilemma was: {last_dilemma} and the chosen option which was: {last_option}"
            else:
                full_prompt = base_prompt

            # Add the standard format to the prompt
            full_prompt += """
            Format the dilemma as follows:
            Context: {Comma separated important context characteristics as for example Public Sector, Private Sector, Fixed Price, Variable Costs, Fixed Scope, Waterfall, Agile, etc., max 10 words}
            Description: {Brief description, max 60 words}
            Option A: {Option A, max 20 words}
            - Pros: {Pros for Option A, max 20 words}
            - Cons: {Cons for Option A, max 20 words}
            Option B: {Option B, max 20 words}
            - Pros: {Pros for Option B, max 20 words}
            - Cons: {Cons for Option B, max 20 words}
            """

            print(f"GPT-4 Prompt text: {full_prompt}")  # Debugging line
            # API call to GPT-4 to generate the new dilemma
            try:

                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a leadership dilemma generator."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=250
                )
                generated_text = response['choices'][0]['message']['content']
                print(f"Generated text: {generated_text}")  # Debugging line
            except Exception as e:
                print(f"An error occurred: {e}")
                return jsonify({"message": "Internal Server Error"}), 500

            # Parsing logic to extract the dilemma, options, pros, and cons from the generated_text
            try:
                # Split the generated text into lines
                lines = generated_text.strip().split("\n")

                # Initialize empty dictionaries to hold the parsed information
                dilemma = {}
                options = []

                # Loop over the lines and parse them
                for line in lines:
                    if "Context:" in line:
                        dilemma['Context'] = line.split(":", 1)[1].strip()
                    elif "Description:" in line:
                        dilemma['Description'] = line.split(":", 1)[1].strip()
                    elif "Option " in line:
                        option = {}
                        option['text'] = line.split(":", 1)[1].strip()
                    elif "- Pros:" in line:
                        option['pros'] = line.split(":", 1)[1].strip().split(", ")
                    elif "- Cons:" in line:
                        option['cons'] = line.split(":", 1)[1].strip().split(", ")
                        options.append(option)  # Only append the option once it's fully formed

                # Validate that we have all the necessary components
                if 'Context' not in dilemma or 'Description' not in dilemma:
                    raise Exception("Missing context, or description in the generated text.")
                if len(options) < 2:
                    raise Exception("At least two options are required in the generated text.")

                # Now you can use `dilemma` and `options` as needed
            except Exception as e:
                print(f"Error while parsing the generated text: {e}")
                return jsonify({"message": "Internal Server Error"}), 500

            # Store this new dilemma and options in your database
            # Insert Context Characteristics and update the many-to-many table
            context_list = dilemma['Context'].split(", ")
            description = dilemma['Description']
            new_dilemma = add_new_dilemma_and_options_to_db(context_list, description, options)

            # Prepare to add an entry to the ViewedDillemmas table before preparing the response
            selected_dilemma = new_dilemma

        else:  # Free user
            # Get the list of viewed dilemmas for this user
            viewed_dilemmas = get_viewed_dilemmas(user.id)
        
            # Get all dilemmas from the database
            all_dilemmas = Dilemma.query.all()
        
            # Filter out the viewed dilemmas
            unviewed_dilemmas = fetch_unviewed_dilemmas(user.id)

            # If there are no unviewed dilemmas, handle that case
            if not unviewed_dilemmas:
                return jsonify({"message": "No new dilemmas available"}), 404
        
            # Pick a random dilemma from the unviewed dilemmas
            selected_dilemma = choice(unviewed_dilemmas)

        # Add an entry to the ViewedDilemmas table for this user and dilemma for tracking purposes for free users and paying users
        try:
            new_view = ViewedDilemma(user_id=user.id, dilemma_id=selected_dilemma.id)
            db.session.add(new_view)
            db.session.commit()
        except Exception as e:
            print(f"An error occurred when updating ViewedDilemma: {e}")
            return jsonify({"message": "Internal Server Error when updating ViewedDilemma"}), 500

        options = Option.query.filter_by(DilemmaID=selected_dilemma.id).all()

        # Prepare response
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

        return jsonify({'dilemma': dilemma_data}), 200
    
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        return jsonify({"message": "Internal Server Error"}), 500
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


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
    print("Data received:", data)
    cookie_id = data.get('user_cookie', None)  # Shpip install openaiould this be 'user_cookie'?
    OptionID = data.get('option_id', None)
    DilemmaID = data.get('dilemma_id', None)  # Get the dilemma ID from the request

    if not all([cookie_id, OptionID, DilemmaID]):
        missing_params = [k for k, v in {"cookie_id": cookie_id, "OptionID": OptionID, "DilemmaID": DilemmaID}.items() if v is None]
        return jsonify({'message': f'Missing parameters: {missing_params}'}), 400

    # Check if user exists
    user = User.query.filter_by(cookie_id=cookie_id).first()
    
    # If user doesn't exist, create a new user
    if not user:
        new_user = User(cookie_id=cookie_id)
        db.session.add(new_user)
        db.session.commit()
        user = new_user
    
    # Store the user's choice
    new_choice = UserChoice(OptionID=OptionID, UserID=user.id, DilemmaID=DilemmaID)

    try:
        db.session.add(new_choice)
        db.session.commit()
    except Exception as e:
        print(f"Database commit failed: {e}")
        return jsonify({'message': 'Database commit failed'}), 500

    return jsonify({'message': 'User choice stored successfully'}), 200


if __name__ == '__main__':
    app.run()