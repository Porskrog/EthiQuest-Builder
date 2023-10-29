from flask import jsonify
from extensions import db
from app import cache
from models import Dilemma, Option, ContextCharacteristic, DilemmasContextCharacteristic, OptionDilemmaRelation, UserChoice, ViewedDilemma
from sqlalchemy import func, desc
from random import choice
from datetime import datetime
import logging

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_CREATED = 201

logging.basicConfig(level=logging.INFO)

######################################################################################################
# Utility Functions - getting dilemmas and options for the user                                      #
######################################################################################################

# Get viewed dilemmas for a user
def get_viewed_dilemmas(user_id):
    viewed_dilemmas = ViewedDilemma.query.filter_by(user_id=user_id).all()
    viewed_dilemma_ids = [dilemma.dilemma_id for dilemma in viewed_dilemmas]
    logging.info(f"200 OK: Successfully got the list of viewed dilemmas for user id: {user_id}")
    return viewed_dilemma_ids

# Mark a dilemma as viewed by a user
def mark_dilemma_as_viewed(user_id, dilemma_id):
    # Check if this dilemma has been viewed by this user before
    viewed = ViewedDilemma.query.filter_by(user_id=user_id, dilemma_id=dilemma_id).first()
    if viewed:
        logging.warning(f"409 Conflict: Dilemma has been viewed before by this user. User ID: {user_id}, Dilemma ID: {dilemma_id}")
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

# Fetch unviewed dilemmas for a user
def fetch_unviewed_dilemmas(user_id):
    viewed_dilemmas = get_viewed_dilemmas(user_id)
    all_dilemmas = Dilemma.query.all()
    unviewed_dilemmas = [d for d in all_dilemmas if d.id not in viewed_dilemmas]
    
    # If there are no unviewed dilemmas, return None
    if not unviewed_dilemmas:
        logging.warning(f"201 WARNING: There are no unviewed dilemmas for user id: {user_id}")
        return None
    
    # Otherwise, return a random unviewed dilemma
    logging.info(f"200 OK: Successfully fected unviewed dilemmas for user id: {user_id}")
    return choice(unviewed_dilemmas)

# Fetch the last dilemma and option chosen by this user from the database.
def get_last_dilemma_and_option(user_id, return_choice_object=False):
    last_choice = UserChoice.query.filter_by(UserID=user_id).order_by(UserChoice.Timestamp.desc()).first()
    if last_choice:
        last_dilemma = Dilemma.query.get(last_choice.DilemmaID)
        last_option = Option.query.get(last_choice.OptionID)
        logging.info(f"200 OK: Successfully fetched the last dilemma {last_dilemma} and option {last_option} chosen by the user ID: {user_id}")
        
        if return_choice_object:
            return last_dilemma.question, last_option.text, last_choice  # Return the last_choice object as well.
        
        return last_dilemma.question, last_option.text  # Assuming 'question' and 'text' are the relevant fields.
    else:
        if return_choice_object:
            return None, None, None  # Return None for the last_choice object as well.
        
        return None, None

# Fetch unviewed dilemmas for a user, prioritizing dilemmas that are consequences of the user's last choice
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

# Fetch related options for a dilemma
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

# Fetch a dilemma that is a consequence of the given option
def fetch_consequential_dilemma(option_id):
    logging.info(f"200 OK: Fetching consequential dilemma for option ID: {option_id}")
    try:
        # Query the OptionDilemmaRelation table to find a dilemma that is a consequence of the given option
        relation = OptionDilemmaRelation.query.filter_by(OptionID=option_id, RelationType='ConsequenceOf').first()
        logging.info(f"200 OK: Successfully fetched the relation. Relation: {relation}")
        
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

# @cache.memoize(60)  # Cache for 60 seconds
def fetch_or_generate_consequential_dilemmas(dilemma_id, user_id):
    from gpt4_services import generate_new_dilemma_with_gpt4
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

# Add a new Option-Dilemma relation
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

# Add a new dilemma and options to the database
def add_new_dilemma_and_options_to_db(context_list, description, options):
    new_dilemma = Dilemma(question=description)
    try:
        db.session.add(new_dilemma)
        db.session.commit()
        logging.info(f"200 OK: Successfully added new dilemma.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"An error occurred when adding a new dilemma: {e}")  

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
            logging.error(f"An error occurred when adding a new option: {e}")  

        # Use the utility function to add a new entry in the OptionDilemmaRelation table
        add_option_dilemma_relation(new_option.id, new_dilemma.id, 'OptionFor')

    for characteristic in context_list:
        existing_characteristic = ContextCharacteristic.query.filter_by(name=characteristic).first()
        if not existing_characteristic:
            new_characteristic = ContextCharacteristic(name=characteristic)
            try:
                db.session.add(new_characteristic)
                db.session.commit()
                logging.info(f"200 OK: Successfully added new context characteristic.")
                char_id = new_characteristic.id
            except Exception as e:
                db.session.rollback()
                logging.error(f"An error occurred when adding a new context characteristic: {e}")
        else:
            char_id = existing_characteristic.id

        new_dilemma_context = DilemmasContextCharacteristic(DilemmaID=new_dilemma.id, ContextCharacteristicID=char_id)
        try:
            db.session.add(new_dilemma_context)
            db.session.commit()
            logging.info(f"200 OK: Successfully added new dilemma, context characteristics and options to the database.")
        except Exception as e:
            db.session.rollback()
            logging.error(f"An error occurred when adding a new dilemma, context characteristics and options to the database: {e}")
    return new_dilemma

# Prepare a JSON response for the dilemma and related options
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

# Fetch a dilemma and related options for the user
def fetch_random_dilemma():
    try:
        # Fetch a random dilemma from the database
        random_dilemma = Dilemma.query.order_by(func.rand()).first()

        if random_dilemma:
            logging.info(f"200 OK: Successfully fetched a random dilemma: {random_dilemma}")
            return random_dilemma
        else:
            logging.warning(f"404 Not Found: No dilemmas found in the database.")
            return jsonify({"status": "failure", "message": "No dilemmas found in the database."}), 404
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return jsonify({"status": "failure", "message": "Internal Server Error"}), 500