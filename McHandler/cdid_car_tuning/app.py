#!/usr/bin/env python3
"""
CDID Car Tuning Assistant - Flask-based web interface
(Roblox CDID car tuning experience)
"""

from flask import Flask, render_template, request, jsonify
import os

from cdid_tuner import CDIDTuner

# Run from this package directory so templates/static are found
APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, 'templates'),
    static_folder=os.path.join(APP_DIR, 'static'),
)
app.secret_key = 'cdid_car_tuning_assistant_secret_key_2024'

# Initialize tuner
tuner = CDIDTuner()

@app.route('/')
def index():
    """Main tuning interface page"""
    return render_template('index.html')

@app.route('/help')
def help_page():
    """Help/documentation page"""
    return render_template('help.html')

@app.route('/api/tune', methods=['POST'])
def get_tuning_suggestions():
    """Get tuning suggestions from AI"""
    try:
        data = request.get_json()
        car_description = data.get('car_description', '')
        tuning_goals = data.get('tuning_goals', '')
        focus_areas = data.get('focus_areas', ['engine', 'suspension'])
        model = data.get('model')
        ecu_available = data.get('ecu_available', False)
        ecu_stage = data.get('ecu_stage')
        internal_electronics_available = data.get('internal_electronics_available', False)
        internal_electronics_stage = data.get('internal_electronics_stage')
        
        if not car_description or not tuning_goals:
            return jsonify({'error': 'Car description and tuning goals are required'}), 400
        
        # Set model if provided
        if model:
            tuner.set_model(model)
        
        # Normalize stage to int 1-3 if provided
        ecu_stage = int(ecu_stage) if ecu_stage is not None and str(ecu_stage).isdigit() and 1 <= int(ecu_stage) <= 3 else None
        internal_electronics_stage = int(internal_electronics_stage) if internal_electronics_stage is not None and str(internal_electronics_stage).isdigit() and 1 <= int(internal_electronics_stage) <= 3 else None
        
        def _opt_num(key):
            v = data.get(key)
            if v is None or v == '':
                return None
            try:
                n = float(v) if not isinstance(v, (int, float)) else v
                return int(n)
            except (TypeError, ValueError):
                return None
        
        turbo_charger = _opt_num('turbo_charger')
        boost_per_turbo = _opt_num('boost_per_turbo')
        super_charger = _opt_num('super_charger')
        super_charger_boost = _opt_num('super_charger_boost')
        front_diff_power = _opt_num('front_diff_power')
        front_diff_coast = _opt_num('front_diff_coast')
        front_diff_preload = _opt_num('front_diff_preload')
        rear_diff_power = _opt_num('rear_diff_power')
        rear_diff_coast = _opt_num('rear_diff_coast')
        rear_diff_preload = _opt_num('rear_diff_preload')
        front_stiffness = _opt_num('front_stiffness')
        front_ride_height = _opt_num('front_ride_height')
        front_damping = _opt_num('front_damping')
        rear_stiffness = _opt_num('rear_stiffness')
        rear_ride_height = _opt_num('rear_ride_height')
        rear_damping = _opt_num('rear_damping')
        
        # Get tuning suggestions
        result = tuner.get_tuning_suggestions(
            car_description,
            tuning_goals,
            focus_areas,
            ecu_available=ecu_available,
            ecu_stage=ecu_stage,
            internal_electronics_available=internal_electronics_available,
            internal_electronics_stage=internal_electronics_stage,
            turbo_charger=turbo_charger,
            boost_per_turbo=boost_per_turbo,
            super_charger=super_charger,
            super_charger_boost=super_charger_boost,
            front_diff_power=front_diff_power,
            front_diff_coast=front_diff_coast,
            front_diff_preload=front_diff_preload,
            rear_diff_power=rear_diff_power,
            rear_diff_coast=rear_diff_coast,
            rear_diff_preload=rear_diff_preload,
            front_stiffness=front_stiffness,
            front_ride_height=front_ride_height,
            front_damping=front_damping,
            rear_stiffness=rear_stiffness,
            rear_ride_height=rear_ride_height,
            rear_damping=rear_damping,
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnose', methods=['POST'])
def diagnose_problem():
    """Diagnose tuning problems"""
    try:
        data = request.get_json()
        problem_description = data.get('problem_description', '')
        current_settings = data.get('current_settings', '')
        model = data.get('model')
        
        if not problem_description:
            return jsonify({'error': 'Problem description is required'}), 400
        
        # Set model if provided
        if model:
            tuner.set_model(model)
        
        # Get diagnosis
        result = tuner.diagnose_tuning_problem(problem_description, current_settings)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ollama/status', methods=['GET'])
def check_ollama_status():
    """Check Ollama connection status"""
    try:
        is_connected = tuner.check_ollama_connection()
        return jsonify({
            'connected': is_connected,
            'model': tuner.model
        })
    except Exception as e:
        return jsonify({'error': str(e), 'connected': False}), 500

@app.route('/api/ollama/models', methods=['GET'])
def get_ollama_models():
    """Get list of available Ollama models"""
    try:
        models = tuner.get_available_models()
        return jsonify({
            'models': models,
            'current_model': tuner.model
        })
    except Exception as e:
        return jsonify({'error': str(e), 'models': []}), 500

if __name__ == '__main__':
    # Create necessary directories (in app dir)
    for name in ('templates', 'static'):
        path = os.path.join(APP_DIR, name)
        os.makedirs(path, exist_ok=True)
    
    CDID_PORT = 5001  # Different from Minecraft web (5000) so both can run
    print("CDID Car Tuning Assistant (Roblox)")
    print("=" * 50)
    print("Starting web application...")
    print("Access at: http://localhost:{}".format(CDID_PORT))
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=CDID_PORT)
