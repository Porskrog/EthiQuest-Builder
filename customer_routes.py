# customer_bp.py
from flask import Blueprint, jsonify, request
from models import User, Dilemma, Option, UserChoice, ViewedDilemma, ContextCharacteristic, DilemmasContextCharacteristic,OptionDilemmaRelation
from extensions import db
from flask_cors import CORS
from random import choice
from app import limiter, cache  
from gpt4_services import generate_new_dilemma_with_gpt4, call_gpt4_api, parse_gpt4_response
from dilemma_services import prepare_dilemma_json_response, add_new_dilemma_and_options_to_db, mark_dilemma_as_viewed, get_last_dilemma_and_option, fetch_related_options, fetch_consequential_dilemma, fetch_unviewed_dilemmas, fetch_or_generate_consequential_dilemmas
import os
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)  # Sets up basic logging

customer_bp = Blueprint('customer', __name__)
CORS(customer_bp, origins=["https://flow.camp"])


######################################################################################################
#                                                                                                    #
#                                          Utility Functions                                         #
#                                                                                                    #
######################################################################################################


@customer_bp.route('/get_data')
def get_customer_data():
    return jsonify({"data": "customer data"})


# Function to get or create a user
def get_or_create_user(cookie_id):
    try:
        user = User.query.filter_by(cookie_id=cookie_id).first()
        if not user:
            user = User(cookie_id=cookie_id)
            db.session.add(user)
            db.session.commit()
            logging.info(f"200 OK: Successfully got or created a user. User ID: {user.id}")
    except Exception as e:
        logging.error(f"Database error: {e}")
        db.session.rollback()
        return None
    return user


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

######################################################################################################
#                                                                                                    #
#                                                                                                    #
#                                        Route Handlers                                              #
#                                                                                                    #
# Sequence of functions:                                                                             #
# 1. get_toggle_setting                                                                              #
# 2. update_toggle_setting                                                                           #
# 3. get_unviewed_dilemmas(user_id)                                                                  #
# 4. get_dilemma                                                                                     #
# 5. view_dilemma (mark dilemmaas viewed)                                                            #
# 6. get_option_details                                                                              #     
# 7. store_user_choice                                                                               #
######################################################################################################

######################################################################################################
#  1. Get Toggle Setting                                                                             #
######################################################################################################

@customer_bp.route('/get_toggle_settings', methods=['GET'])
def get_toggle_settings():
    logging.info("200 OK: Received request to get toggles")

    # Fetch the cookie ID from query parameters
    # cookie_id = request.args.get('user_id')

    # NEW: Fetch the cookie ID from query parameters
    cookie_id = request.args.get('cookie_id', None)

    if not cookie_id:
        logging.warning("Missing cookie_id in the request")
        return jsonify({"status": "failure", 'message': 'Missing cookie_id'}), 400

    user = get_or_create_user(cookie_id) # Get or create the user  
    if not user:
        logging.error("404 Not Found: User could not be created")
        return jsonify({"status": "failure", 'message': 'User not found'}), 404

    # Fetch the random and consequential fields from the user model
    Random = user.Random
    Consequential = user.Consequential

    logging.info(f"200 OK: Successfully returned toggles for user {user.id}, Random: {Random}, Consequential: {Consequential}")
    return jsonify({'random': Random, 'consequential': Consequential})


######################################################################################################
#  2. Update Toggle Setting                                                                          #
######################################################################################################

@customer_bp.route('/update_toggle_settings', methods=['POST'])
def update_toggle_settings():
    # Log the incoming request
    logging.info("200 OK: Received request to update toggles")

    # Fetch the cookie ID from query parameters
    cookie_id = request.args.get('user_id')

    user = get_or_create_user(cookie_id) # Get or create the user  
    if not user:
        logging.error("404 Not Found: User could not be created")
        return jsonify({"status": "failure", 'message': 'User not found'}), 404
    
    # Fetch the random and consequential fields from the request
    data = request.get_json()
    Random = data.get('random')
    Consequential = data.get('consequential')

    # Update the user model
    user.Random = Random
    user.Consequential = Consequential
    try:
        db.session.commit()
    except Exception as e:
        logging.error(f"Database commit failed: {e}")
        return jsonify({"status": "failure", 'message': 'Database commit failed'}), 500

    logging.info(f"200 OK: Successfully updated toggles for user {user.id}, Random: {user.Random}, Consequential: {user.Consequential}")
    return jsonify({'random': Random, 'consequential': Consequential})

######################################################################################################
#  3. Get Unviewed Dilemmas                                                                          #
######################################################################################################

@customer_bp.route('/get_unviewed_dilemmas', methods=['POST'])
def get_unviewed_dilemmas():
    data = request.get_json()
    user_id = data.get('user_id', None)
    cookie_id = data.get('cookie_id', None)
    
    # Log the incoming request
    logging.info(f"200 OK: Received request to get unviewed dilemmas for user {user_id}")

    if not user_id and not cookie_id:
        return jsonify({"status": "failure", 'message': 'Missing user_id or cookie_id'}), 400

    if user_id:
        # Fetch the unviewed dilemmas for this user
        unviewed_dilemmas = fetch_unviewed_dilemmas(user_id)
    elif cookie_id:
        # Fetch the unviewed dilemmas for this user
        unviewed_dilemmas = fetch_unviewed_dilemmas(cookie_id)
        
    # If there are no unviewed dilemmas, handle that case
    if not unviewed_dilemmas:
        return jsonify({"status": "failure", "message": "No new dilemmas available"}), 404

    if user_id:
        logging.info(f"200 OK: Successfully selected a dilemma for the user with user id: {user_id}.")
    elif cookie_id:
        logging.info(f"200 OK: Successfully selected a dilemma for the user with cookie id: {cookie_id}.")
    
    # No need to pick a random dilemma here, as fetch_unviewed_dilemmas already returns a random dilemma
    selected_dilemma = unviewed_dilemmas

    return jsonify({"status": "success", "message": "Successfully selected a dilemma", "dilemma_id": selected_dilemma.id}), 200

######################################################################################################
#  4. Get Dilemma                                                                                    #
######################################################################################################

@limiter.limit("5 per minute") # Limit to 5 requests per minute
@customer_bp.route('/get_dilemma', methods=['POST'])  # Changed to POST to get user details
def get_dilemma():
    response = {"status": "failure", "message": "Unknown error"}
    status_code = 500
    try:
        # NEW: Fetch the last choice made by this user
        last_dilemma, last_option, last_choice = get_last_dilemma_and_option(user.id, return_choice_object=True)

        # NEW: Initialize as None
        selected_dilemma = None
        error_response = None

        # NEW: If a last choice exists, look for a consequential dilemma
        consequential_dilemma = None
        if last_choice:
            logging.info("Fetching for consequential dilemma")
            consequential_dilemma = fetch_consequential_dilemma(last_choice.OptionID)

        # The existing logic to fetch a random dilemma
        if user.user_type == 'Paying':
            logging.info("Call handle paying user")
            if consequential_dilemma is None:
                 selected_dilemma, next_dilemmas, error_response = handle_paying_user(user.id)
        
        else:   # Free user
            logging.info("Call handle free user")
            selected_dilemma, _, error_response = handle_free_user(user.id)

        # If a consequential dilemma was found, overwrite the selected_dilemma
        if consequential_dilemma:
            selected_dilemma = consequential_dilemma

        if error_response:
            return jsonify(error_response), 404  # or other status code based on the error

        # Fetch related options using utility function 
        related_options = fetch_related_options(selected_dilemma.id)  

        # Prepare and return JSON response using utility function 
        logging.info(f"200 OK: Successfully returned dilemma for user {user.id}")
        response = prepare_dilemma_json_response(selected_dilemma, related_options)
        status_code = 200

        # Add an entry to the ViewedDilemmas table for this user and dilemma for tracking purposes
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

######################################################################################################
#  5. Mark dilemma as viewed                                                                         # 
######################################################################################################

@customer_bp.route('/view_dilemma/<int:dilemma_id>', methods=['POST'])
def view_dilemma(dilemma_id):
    logging.info(f"200 OK: Received request to mark dilemma {dilemma_id} as viewed")
    
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

    logging.info(f"200 OK: User ID from request: {user_id}")

    message, status_code = mark_dilemma_as_viewed(user_id, dilemma_id)
    return jsonify({"status": "success" if status_code == 201 else "failure", "message": message}), status_code

######################################################################################################
#  6. Get Option Details API endpoint for ALL users (free and paying)                                # 
######################################################################################################

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

######################################################################################################
#  7. Store the user's choice                                                                        # 
######################################################################################################

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

    return jsonify({"status": "success", 'message': 'User choice stored successfully'}), 200

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



if __name__ == '__main__':
    app.run()