# admin_routes.py
from flask import Blueprint, jsonify

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/get stats')
def get_admin_stats():
    return jsonify({"data": "admin stats"})


#####################
# Route Handlers    #
#####################
import logging

# Add Dilemma       #

@admin_bp.route('/add_dilemma', methods=['POST'])
def add_dilemma():
    data = request.get_json()
    new_dilemma = Dilemma(question=data['question'])
    db.session.add(new_dilemma)
    db.session.commit()
    return jsonify({'message': 'New dilemma added'}), 201

@admin_bp.route('/get_dilemmas', methods=['GET'])
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

@admin_bp.route('/add_option/<DilemmaID>', methods=['POST'])
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

@admin_bp.route('/get_options/<DilemmaID>', methods=['GET'])
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


@admin_bp.route('/get_option_details/<OptionID>', methods=['GET'])
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

if __name__ == '__main__':
    app.run()