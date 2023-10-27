# dilemma_services.py



######################################################################################################
# Utility Functions - getting dilemmas and options for the user                                      #
######################################################################################################

# Function to get viewed dilemmas for a user
def get_viewed_dilemmas(user_id):
    viewed_dilemmas = ViewedDilemma.query.filter_by(user_id=user_id).all()
    viewed_dilemma_ids = [dilemma.dilemma_id for dilemma in viewed_dilemmas]
    logging.info(f"200 OK: Successfully got the list of viewed dilemmas.")
    return viewed_dilemma_ids

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

# Fetch the last dilemma and option chosen by this user from the database.
def get_last_dilemma_and_option(user_id, return_choice_object=False):
    last_choice = UserChoice.query.filter_by(UserID=user_id).order_by(UserChoice.Timestamp.desc()).first()
    if last_choice:
        last_dilemma = Dilemma.query.get(last_choice.DilemmaID)
        last_option = Option.query.get(last_choice.OptionID)
        logging.info(f"200 OK: Successfully fetched the last dilemma and option chosen by the user. User ID: {user_id}")
        
        if return_choice_object:
            return last_dilemma.question, last_option.text, last_choice  # Return the last_choice object as well.
        
        return last_dilemma.question, last_option.text  # Assuming 'question' and 'text' are the relevant fields.
    else:
        if return_choice_object:
            return None, None, None  # Return None for the last_choice object as well.
        
        return None, None

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

