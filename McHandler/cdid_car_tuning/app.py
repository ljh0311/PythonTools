#!/usr/bin/env python3
"""
CDID Car Tuning Assistant - Flask-based web interface
(Roblox CDID car tuning experience)
"""

import os
import sys
from flask import Flask, render_template, request, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MCHANDLER_ROOT = os.path.dirname(APP_DIR)
if MCHANDLER_ROOT not in sys.path:
    sys.path.insert(0, MCHANDLER_ROOT)

from cdid_tuner import CDIDTuner
from settings_manager import SettingsManager
from flask_config import get_secret_key, get_run_kwargs
from web_components import register_layout

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, 'templates'),
    static_folder=os.path.join(APP_DIR, 'static'),
)
app.secret_key = get_secret_key('cdid-car-tuning')
register_layout(app, 'cdid')

settings_manager = SettingsManager(os.path.join(MCHANDLER_ROOT, 'config.json'))
tuner = CDIDTuner.from_settings(settings_manager)


def apply_ollama_settings() -> None:
    tuner.configure(
        url=settings_manager.get_setting('ollama.url'),
        model=settings_manager.get_setting('ollama.model'),
        timeout=settings_manager.get_setting('ollama.timeout', 120),
    )


SUSPENSION_FIELDS = (
    'front_stiffness', 'front_ride_height', 'front_damping',
    'rear_stiffness', 'rear_ride_height', 'rear_damping',
)
NON_NEGATIVE_FIELDS = (
    'turbo_charger', 'boost_per_turbo', 'super_charger', 'super_charger_boost',
    'front_diff_power', 'front_diff_coast', 'front_diff_preload',
    'rear_diff_power', 'rear_diff_coast', 'rear_diff_preload',
) + SUSPENSION_FIELDS


def _parse_optional_number(value):
    if value is None or value == '':
        return None
    try:
        number = float(value) if not isinstance(value, (int, float)) else value
        if number != int(number):
            return number
        return int(number)
    except (TypeError, ValueError):
        return 'invalid'


def validate_tune_payload(data: dict):
    """Validate tuning request fields. Returns (errors, parsed_values)."""
    errors = []
    parsed = {}

    for field in NON_NEGATIVE_FIELDS:
        raw = data.get(field)
        if raw is None or raw == '':
            parsed[field] = None
            continue
        number = _parse_optional_number(raw)
        if number == 'invalid':
            errors.append(f'{field.replace("_", " ")} must be a number')
            continue
        if number < 0:
            errors.append(f'{field.replace("_", " ")} must be zero or greater')
            continue
        parsed[field] = number

    for field in SUSPENSION_FIELDS:
        value = parsed.get(field)
        if value is not None and (value < 0 or value > 1500):
            errors.append(f'{field.replace("_", " ")} must be between 0 and 1500')

    ecu_available = bool(data.get('ecu_available', False))
    ie_available = bool(data.get('internal_electronics_available', False))

    ecu_stage = data.get('ecu_stage')
    ie_stage = data.get('internal_electronics_stage')

    if ecu_available:
        if ecu_stage is None or str(ecu_stage) == '':
            errors.append('ECU stage is required (1-3) when ECU tuning is available')
        else:
            try:
                ecu_stage = int(ecu_stage)
                if ecu_stage not in (1, 2, 3):
                    errors.append('ECU stage must be 1, 2, or 3')
            except (TypeError, ValueError):
                errors.append('ECU stage must be 1, 2, or 3')
    else:
        ecu_stage = None

    if ie_available:
        if ie_stage is None or str(ie_stage) == '':
            errors.append('Internal Electronics stage is required (1-3) when IE tuning is available')
        else:
            try:
                ie_stage = int(ie_stage)
                if ie_stage not in (1, 2, 3):
                    errors.append('Internal Electronics stage must be 1, 2, or 3')
            except (TypeError, ValueError):
                errors.append('Internal Electronics stage must be 1, 2, or 3')
    else:
        ie_stage = None

    parsed['ecu_stage'] = ecu_stage
    parsed['internal_electronics_stage'] = ie_stage
    return errors, parsed


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/api/tune', methods=['POST'])
def get_tuning_suggestions():
    try:
        data = request.get_json() or {}
        car_description = data.get('car_description', '')
        tuning_goals = data.get('tuning_goals', '')

        if not car_description or not tuning_goals:
            return jsonify({'error': 'Car description and tuning goals are required'}), 400

        errors, parsed = validate_tune_payload(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400

        model = data.get('model')
        if model:
            tuner.set_model(model)

        result = tuner.get_tuning_suggestions(
            car_description,
            tuning_goals,
            data.get('focus_areas', ['engine', 'suspension']),
            ecu_available=bool(data.get('ecu_available', False)),
            ecu_stage=parsed['ecu_stage'],
            internal_electronics_available=bool(data.get('internal_electronics_available', False)),
            internal_electronics_stage=parsed['internal_electronics_stage'],
            turbo_charger=parsed.get('turbo_charger'),
            boost_per_turbo=parsed.get('boost_per_turbo'),
            super_charger=parsed.get('super_charger'),
            super_charger_boost=parsed.get('super_charger_boost'),
            front_diff_power=parsed.get('front_diff_power'),
            front_diff_coast=parsed.get('front_diff_coast'),
            front_diff_preload=parsed.get('front_diff_preload'),
            rear_diff_power=parsed.get('rear_diff_power'),
            rear_diff_coast=parsed.get('rear_diff_coast'),
            rear_diff_preload=parsed.get('rear_diff_preload'),
            front_stiffness=parsed.get('front_stiffness'),
            front_ride_height=parsed.get('front_ride_height'),
            front_damping=parsed.get('front_damping'),
            rear_stiffness=parsed.get('rear_stiffness'),
            rear_ride_height=parsed.get('rear_ride_height'),
            rear_damping=parsed.get('rear_damping'),
        )

        if 'error' in result:
            return jsonify(result), 500

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/diagnose', methods=['POST'])
def diagnose_problem():
    try:
        data = request.get_json() or {}
        problem_description = data.get('problem_description', '')
        current_settings = data.get('current_settings', '')
        model = data.get('model')

        if not problem_description:
            return jsonify({'error': 'Problem description is required'}), 400

        if model:
            tuner.set_model(model)

        result = tuner.diagnose_tuning_problem(problem_description, current_settings)

        if 'error' in result:
            return jsonify(result), 500

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ollama/status', methods=['GET'])
def check_ollama_status():
    try:
        return jsonify({
            'connected': tuner.check_ollama_connection(),
            'model': tuner.model,
        })
    except Exception as e:
        return jsonify({'error': str(e), 'connected': False}), 500


@app.route('/api/ollama/models', methods=['GET'])
def get_ollama_models():
    try:
        models = tuner.get_available_models()
        return jsonify({
            'models': models,
            'current_model': tuner.model,
        })
    except Exception as e:
        return jsonify({'error': str(e), 'models': []}), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    try:
        if request.method == 'GET':
            return jsonify(settings_manager.settings)

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        if 'ollama' in data and isinstance(data['ollama'], dict):
            for key, value in data['ollama'].items():
                settings_manager.set_setting(f'ollama.{key}', value)

        if not settings_manager.save_settings():
            return jsonify({'error': 'Failed to save settings'}), 500

        apply_ollama_settings()
        return jsonify({'success': True, 'settings': settings_manager.settings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    for name in ('templates', 'static'):
        os.makedirs(os.path.join(APP_DIR, name), exist_ok=True)

    run_kwargs = get_run_kwargs(default_port=5001)
    print("CDID Car Tuning Assistant (Roblox)")
    print("=" * 50)
    print("Starting web application...")
    print(f"Access at: http://{run_kwargs['host']}:{run_kwargs['port']}")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    app.run(**run_kwargs)
