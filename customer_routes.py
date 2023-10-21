# customer_bp.py
from flask import Blueprint, jsonify, request
from models import User, Dilemma, Option, UserChoice, ViewedDilemma, ContextCharacteristic, DilemmasContextCharacteristic,OptionDilemmaRelation
from extensions import db
from flask_cors import CORS
from random import choice
from sqlalchemy import desc # To get the last dilemma and option for a user
from app import limiter, cache  

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
    logging.info(f"200 OK: Successfully got the list of viewed dilemmas.")
    return viewed_dilemma_ids

# Fetch the last dilemma and option chosen by this user from the database.
def get_last_dilemma_and_option(user_id):
    last_choice = UserChoice.query.filter_by(UserID=user_id).order_by(UserChoice.Timestamp.desc()).first()
    if last_choice:
        last_dilemma = Dilemma.query.get(last_choice.DilemmaID)
        last_option = Option.query.get(last_choice.OptionID)
        logging.info(f"200 OK: Successfully fetched the last dilemma and option chosen by the user. User ID: {user_id}")
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
        logging.info(f"200 OK: Successfully got or created a user. User ID: {user}")
    return user

# Function to add a new Option-Dilemma relation
def add_option_dilemma_relation(option_id, dilemma_id, relation_type):
    # Example usage when a new dilemma is generated as a consequence of an option
    # add_option_dilemma_relation(chosen_option_id, new_dilemma_id, 'ConsequenceOf')
    new_relation = OptionDilemmaRelation(
        OptionID=option_id,
        DilemmaID=dilemma_id,
        RelationType=relation_type
    )
    try:
        db.session.add(new_relation)
        db.session.commit()
        logging.info(f"200 OK: Successfully added a new option-dilemma relation. Dilemma ID: {dilemma_id}, Option ID: {option_id}, Relation Type: {relation_type}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"An error occurred when adding a new option dilemma relation: {e}")  


# Function to add a new dilemma and options to the database
def add_new_dilemma_and_options_to_db(context_list, description, options):
    new_dilemma = Dilemma(question=description)
    db.session.add(new_dilemma)
    db.session.commit()
    logging.info(f"200 OK: Successfully added new dilemma.")

    for opt in options:
        # Convert pros and cons lists to comma-separated strings
        new_option = Option(
            text=opt['text'],
            pros=', '.join(opt['pros']),
            cons=', '.join(opt['cons'])
        )
        try:
            db.session.add(new_option)
            db.session.commit()
            logging.info(f"200 OK: Successfully added new option.")
        except Exception as e:
            db.session.rollback()
            logging.error(f"An error occurred when adding a new dilemma and option to the DB: {e}")  

        # Use the utility function to add a new entry in the OptionDilemmaRelation table
        add_option_dilemma_relation(new_option.id, new_dilemma.id, 'OptionFor')

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

        logging.info(f"200 OK: Successfully added new dilemma, context characteristics and options to the database.")
    return new_dilemma


# Function to fetch unviewed dilemmas for a user
def fetch_unviewed_dilemmas(user_id):
    viewed_dilemmas = get_viewed_dilemmas(user_id)
    all_dilemmas = Dilemma.query.all()
    unviewed_dilemmas = [d for d in all_dilemmas if d.id not in viewed_dilemmas]
    
    # If there are no unviewed dilemmas, return None
    if not unviewed_dilemmas:
        return None
    
    # Otherwise, return a random unviewed dilemma
    logging.info(f"200 OK: Successfully fected unviewed dilemmas for the user: {user_id}")
    return choice(unviewed_dilemmas)


# Function to fetch unviewed dilemmas for a user, prioritizing dilemmas that are consequences of the user's last choice
def fetch_priority_unviewed_dilemmas(user_id):
    # Get the last option chosen by the user
    last_choice = UserChoice.query.filter_by(UserID=user_id).order_by(UserChoice.Timestamp.desc()).first()

    # Initialize an empty list to hold the prioritized dilemmas
    priority_dilemmas = []

    if last_choice:
        # If the user has made a choice before, fetch dilemmas that are consequences of that choice
        related_dilemmas = OptionDilemmaRelation.query.filter_by(OptionID=last_choice.OptionID, RelationType='ConsequenceOf').all()
        priority_dilemma_ids = [relation.DilemmaID for relation in related_dilemmas]
        
        # Fetch these dilemmas from the Dilemma table if they haven't been viewed yet
        viewed_dilemmas = get_viewed_dilemmas(user_id)
        priority_dilemmas = [Dilemma.query.get(d_id) for d_id in priority_dilemma_ids if d_id not in viewed_dilemmas]
    
    # Now fetch all unviewed dilemmas for this user
    all_unviewed_dilemmas = fetch_unviewed_dilemmas(user_id)

    # Remove any dilemmas that are already in the priority list to avoid duplication
    all_unviewed_dilemmas = [d for d in all_unviewed_dilemmas if d not in priority_dilemmas]

    # Combine the lists, putting the priority dilemmas at the front
    combined_dilemmas = priority_dilemmas + all_unviewed_dilemmas

    logging.info(f"200 OK: Successfully fetched unviewed priority dilemmas for the user: {user_id}")
    return combined_dilemmas


def call_gpt4_api(full_prompt):
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
        return jsonify({"status": "failure", "message": "Internal Server Error"}), 500
    
    logging.info(f"200 OK: Successfully called GPT-4 API.")
    return generated_text


def parse_gpt4_response(generated_text):
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
        return jsonify({"status": "failure", "message": "Internal Server Error"}), 500

    logging.info(f"200 OK: Successfully parsed the dilemma from GPT-4 as dilemma and options. Dilemma: {dilemma}, Options: {options}")
    return dilemma, options


def generate_new_dilemma_with_gpt4(last_dilemma=None, last_option=None, user_id=None):
    if last_dilemma is None or last_option is None:
        if user_id is None:
            raise ValueError("If last_dilemma and last_option are not provided, user_id must be provided.")
        # Fetch them if they weren't provided (this assumes user.id is accessible from here)
        last_dilemma, last_option = get_last_dilemma_and_option(user_id)

    # Base prompt for GPT-4
    base_prompt = "Please generate an ethical and leadership dilemma related to program management."
    
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
        # API call to GPT-4 (assuming you have a function or method for this)
        response = call_gpt4_api(full_prompt)
        
        # Parsing logic (assuming you have a function or method for this)
        parsed_response = parse_gpt4_response(response)

        # Return the parsed response        
        logging.info(f"200 OK: Successfully generated a new dilemma with GPT-4: {parsed_response}")
        return parsed_response
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None


def fetch_related_options(dilemma_id):
    related_options = []
    try:
        # Fetch the related options from the database
        relations = OptionDilemmaRelation.query.filter_by(DilemmaID=dilemma_id, RelationType='OptionFor').all()
        
        for relation in relations:
            option = Option.query.get(relation.OptionID)
            if option:
                related_options.append(option)

        logging.info(f"200 OK: Successfully fetched the related options to dilemma. Dilemma ID: {dilemma_id}, Options: {related_options}")
        return related_options

    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None


def prepare_dilemma_json_response(dilemma, related_options):
    # Prepare response
    dilemma_data = {
        'id': dilemma.id,
        'question': dilemma.question,
        'options': [
            {
                'id': option.id,
                'text': option.text,
                'pros': option.pros,
                'cons': option.cons
            } for option in related_options
        ]
    }
    logging.info(f"200 OK: Successfully returned the dilemma to the front end: {dilemma_data}")
    return jsonify({'dilemma': dilemma_data}), 200


def fetch_consequential_dilemma(option_id):
    try:
        # Query the OptionDilemmaRelation table to find a dilemma that is a consequence of the given option
        relation = OptionDilemmaRelation.query.filter_by(OptionID=option_id, RelationType='ConsequenceOf').first()
        
        if relation:
            # Fetch the dilemma using the DilemmaID found in the relation
            dilemma = Dilemma.query.get(relation.DilemmaID)
            logging.info(f"200 OK: Successfully fetched the consequential dilemma. Dilemma: {dilemma}, Option ID: {option_id}")
            return dilemma
        else:
            return None
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None


@cache.memoize(60)  # Cache for 60 seconds
def fetch_or_generate_consequential_dilemmas(dilemma_id, user_id):
    try:
        # Fetch all options for the given dilemma
        options = fetch_related_options(dilemma_id)
        
        # Initialize a dictionary to hold the consequential dilemmas for each option
        consequential_dilemmas = {}
        
        for option in options:
            # Check if a consequential dilemma already exists for this option
            consequential_dilemma = fetch_consequential_dilemma(option.id)
       
            # If not, generate a new consequential dilemma using GPT-4
            if not consequential_dilemma:
                last_dilemma, _ = get_last_dilemma_and_option(user_id)  # Assuming user.id is accessible
                generated_dilemma, generated_options = generate_new_dilemma_with_gpt4(last_dilemma, option.text)
                
                # Save the new dilemma and its options in the database
                context_list = generated_dilemma['Context'].split(", ")
                description = generated_dilemma['Description']
                new_dilemma = add_new_dilemma_and_options_to_db(context_list, description, generated_options)
                
                # Mark the new dilemma as a consequence of the current option
                # Use the utility function to add a new entry in the OptionDilemmaRelation table
                add_option_dilemma_relation(option.id, new_dilemma.id, 'ConsequenceOf')

                
                # Add the new dilemma to the dictionary
                consequential_dilemmas[option.id] = new_dilemma
            else:
                # Add the existing consequential dilemma to the dictionary
                consequential_dilemmas[option.id] = consequential_dilemma
 
        logging.info(f"200 OK: Successfully fetched or generated consequential dilemmas for this Dilemma ID: {dilemma_id}")
        return consequential_dilemmas
    
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None


def handle_free_user(user_id):
    unviewed_dilemmas = fetch_unviewed_dilemmas(user_id)

    # If there are no unviewed dilemmas, handle that case
    if not unviewed_dilemmas:
        return None, {"status": "failure", "message": "No new dilemmas available"}, 404

    logging.info(f"200 OK: Successfully selected a dilemma for user  {user_id}.")

    # Pick a random dilemma from the list of unviewed dilemmas
    selected_dilemma = choice(unviewed_dilemmas)
    cache.delete_memoized(fetch_or_generate_consequential_dilemmas, selected_dilemma.id, user_id)

    return selected_dilemma, None, None


def handle_paying_user(user_id):
    # Fetch the last dilemma and option for this user from the database
    last_dilemma, last_option = get_last_dilemma_and_option(user_id)
    # Using utility function to generate a new dilemma in GPT-4
    generated_dilemma, generated_options = generate_new_dilemma_with_gpt4(last_dilemma, last_option, user_id)
    
    # Store this new dilemma and options in your database
    # Insert Context Characteristics and update the many-to-many table
    context_list = generated_dilemma['Context'].split(", ")
    description = generated_dilemma['Description']
    selected_dilemma = add_new_dilemma_and_options_to_db(context_list, description, generated_options)

    logging.info(f"200 OK: Successfully generated and stored a new dilemma for user {user_id}")

    # Invalidate cache here if you add a new dilemma
    cache.delete_memoized(fetch_or_generate_consequential_dilemmas, selected_dilemma.id, user_id)

    # Fetch or generate consequential dilemmas and cache them
    next_dilemmas = fetch_or_generate_consequential_dilemmas(selected_dilemma.id, user_id)
    cache.set(f"consequential_dilemmas_{user_id}", next_dilemmas)

    return selected_dilemma, next_dilemmas, None


def mark_dilemma_as_viewed(user_id, dilemma_id):
    # Check if this dilemma has been viewed by this user before
    viewed = ViewedDilemma.query.filter_by(user_id=user_id, dilemma_id=dilemma_id).first()
    if viewed:
        return "Dilemma has been viewed before by this user", 409
    
    # If not viewed, add to the ViewedDilemmas table
    new_view = ViewedDilemma(user_id=user_id, dilemma_id=dilemma_id)
    try:
        db.session.add(new_view)
        db.session.commit()
        logging.info(f"200 OK: Successfully marked dilemma as viewed. User ID: {user_id}, Dilemma ID: {dilemma_id}")
        return "Dilemma marked as viewed", 201
    except Exception as e:
        logging.error(f"Error while inserting into ViewedDilemmas: {e}")
        db.session.rollback()
        return "Internal Server Error", 500

######################################################################################################
#                                                                                                    #
#                                                                                                    #
#                                        Route Handlers                                              #
#                                                                                                    #
#                                                                                                    #     
######################################################################################################
import logging

logging.basicConfig(level=logging.INFO)  # Sets up basic logging

#####################################################################
#   View Dilemma                                                    # 
#####################################################################

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

    message, status_code = mark_dilemma_as_viewed(user_id, dilemma_id)
    return jsonify({"status": "success" if status_code == 201 else "failure", "message": message}), status_code


#####################################################################
#   Get Options                                                     # 
#####################################################################

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

@limiter.limit("5 per minute") # Limit to 5 requests per minute

@customer_bp.route('/get_random_dilemma', methods=['POST'])  # Changed to POST to get user details
def get_random_dilemma():
    response = {"status": "failure", "message": "Unknown error"}
    status_code = 500
    try:
        data = request.get_json()
        cookie_id = data.get('cookie_id', None)  # Get cookie_id from request

        if not cookie_id:
            logging.warning("Missing cookie_id in the request")
            return jsonify({"status": "failure", 'message': 'Missing cookie_id'}), 400

        user = get_or_create_user(cookie_id) # Get or create the user  
        if not user:
            logging.error("404 Not Found: User could not be created")
            return jsonify({"status": "failure", 'message': 'User not found'}), 404
        
        unviewed_dilemmas = fetch_unviewed_dilemmas(user.id) # Fetch unviewed dilemmas for this user   

        if user.user_type == 'Paying':
            selected_dilemma, next_dilemmas, error_response = handle_paying_user(user.id)
        
        else:   # Free user
            selected_dilemma, _, error_response = handle_free_user(user.id)

        if error_response:
            return jsonify(error_response), 404  # or other status code based on the error

        # Fetch related options using utility function 
        related_options = fetch_related_options(selected_dilemma.id)  

        # Prepare and return JSON response using utility function 
        logging.info(f"200 OK: Successfully returned dilemma for user {user.id}")
        response = prepare_dilemma_json_response(selected_dilemma, related_options)
        status_code = 200

        # Add an entry to the ViewedDilemmas table for this user and dilemma for tracking purposes for free users and paying users
     
        message, status_code = mark_dilemma_as_viewed(user.id, selected_dilemma.id)
        if status_code != 201:
            return jsonify({"status": "failure", "message": message}), status_code
    
        # Invalidate cache here after adding a new viewed dilemma
        cache.delete_memoized(fetch_or_generate_consequential_dilemmas, selected_dilemma.id, user.id)

    except KeyError as e:
        logging.error(f"KeyError: {e}")
        response = {"status": "failure", "message": "Internal Server Error"}
        status_code = 500
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        response = {"status": "failure", "message": "Internal Server Error"}
        status_code = 500
    
    return response  # Directly return the response


#####################################################################
#   Get Option Details API endpoint for ALL users (free and paying) # 
#####################################################################

@customer_bp.route('/get_option_details/<OptionID>', methods=['GET'])
def get_option_details(OptionID):
    option = Option.query.filter_by(id=OptionID).first()
    if not option:
        return jsonify({"status": "failure", 'message': 'Option not found'}), 404

    option_data = {
        'id': option.id,
        'text': option.text,
        'pros': option.pros,
        'cons': option.cons
    }

    return jsonify({'option': option_data})

#####################################################################
#   Store the user's choice                                         # 
#####################################################################

@customer_bp.route('/store_user_choice', methods=['POST'])
def store_user_choice():
    data = request.get_json()
    logging.warning("Data received:", data)
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
        logging.error(f"Database commit failed: {e}")
        return jsonify({"status": "failure", 'message': 'Database commit failed'}), 500

    return jsonify({"status": "failure", 'message': 'User choice stored successfully'}), 200


if __name__ == '__main__':
    app.run()