from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from database import db, UserProfile, ChatMessage
from ai_helpers import get_aria_response, get_personalized_greeting
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

load_dotenv()

app = Flask(__name__)

# Use Postgres if provided via DATABASE_URL env var (Render provides this automatically).
# Fallback to local sqlite for dev/testing.
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # SQLAlchemy expects the modern scheme
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///wealth_coach.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

db.init_app(app)

def ensure_user_profile_schema():
    """Backfill missing columns for existing SQLite databases."""
    inspector = inspect(db.engine)
    existing_cols = {col['name'] for col in inspector.get_columns('user_profiles')}
    column_map = {
        'first_name': 'VARCHAR(100)',
        'surname': 'VARCHAR(100)',
        'age': 'INTEGER',
        'email': 'VARCHAR(255)',
        'password_hash': 'VARCHAR(255)',
        'onboarding_completed': 'BOOLEAN DEFAULT 0',
        'last_login_at': 'DATETIME',
        'last_seen_at': 'DATETIME',
        'session_data': "TEXT DEFAULT '{}'",
    }
    with db.engine.begin() as conn:
        for col_name, col_type in column_map.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}"))

# Create database tables
with app.app_context():
    db.create_all()
    ensure_user_profile_schema()

# ==================== HELPER FUNCTIONS ====================

def get_current_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id:
        return UserProfile.query.get(user_id)
    return None

def is_profile_complete(user):
    """Whether onboarding-specific fields are available for dashboard experience."""
    return all([
        user.onboarding_completed,
        user.monthly_surplus is not None,
        user.risk_tolerance,
        user.investment_goals,
        user.investment_horizon is not None,
    ])

def get_session_data_dict(user):
    try:
        return json.loads(user.session_data or '{}')
    except Exception:
        return {}

def merge_session_data(user, updates):
    current = get_session_data_dict(user)
    current.update(updates)
    user.session_data = json.dumps(current)
    user.last_seen_at = datetime.utcnow()

def calculate_sip_growth(monthly_amount, annual_return_pct, years):
    """Calculate SIP growth over time"""
    r = annual_return_pct / 12 / 100
    rows = []
    for year in range(1, years + 1):
        n = year * 12
        if r == 0:
            portfolio_value = monthly_amount * n
        else:
            portfolio_value = monthly_amount * (((1 + r) ** n - 1) / r) * (1 + r)
        invested = monthly_amount * n
        gain = portfolio_value - invested
        rows.append({
            "Year": year,
            "Invested": round(invested, 2),
            "Portfolio_Value": round(portfolio_value, 2),
            "Compounding_Gain": round(gain, 2),
        })
    return rows


def calculate_delay_scenario(monthly_amount, annual_return_pct, total_years, delay_years=5):
    """Compare: start investing today vs start after delay_years years"""
    delay_years = min(delay_years, total_years - 1)

    # Scenario A — start today, invest for total_years
    scenario_a = calculate_sip_growth(monthly_amount, annual_return_pct, total_years)

    # Scenario B — wait delay_years, then invest for remaining time
    effective_years = max(1, total_years - delay_years)
    scenario_b_growth = calculate_sip_growth(monthly_amount, annual_return_pct, effective_years)

    # Pad scenario B with zeros for the waiting period
    padded_b = [0] * delay_years + [row['Portfolio_Value'] for row in scenario_b_growth]
    padded_b = padded_b[:total_years]  # clip to total_years

    final_a_val = scenario_a[-1]['Portfolio_Value']
    final_b_val = scenario_b_growth[-1]['Portfolio_Value'] if scenario_b_growth else 0
    wealth_lost = max(0, final_a_val - final_b_val)

    return {
        'years': list(range(1, total_years + 1)),
        'scenario_a': [row['Portfolio_Value'] for row in scenario_a],
        'scenario_b': padded_b,
        'final_a': format_currency(final_a_val),
        'final_b': format_currency(final_b_val),
        'wealth_lost': format_currency(wealth_lost),
        'delay_years': delay_years,
    }

def format_currency(amount):
    """Format amount in Indian Rupees with Cr/L shorthand"""
    if amount >= 1_00_00_000:
        return f"₹{amount/1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"₹{amount/1_00_000:.2f} L"
    elif amount >= 1_000:
        return f"₹{amount/1_000:.1f}K"
    return f"₹{amount:,.0f}"

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Landing page / Onboarding"""
    user = get_current_user()
    if user and is_profile_complete(user):
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/api/auth/signup', methods=['POST'])
def api_auth_signup():
    """Create user account and start onboarding."""
    try:
        data = request.json or {}
        first_name = (data.get('first_name') or '').strip()
        surname = (data.get('surname') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        age_raw = data.get('age')

        if not all([first_name, surname, email, password, age_raw]):
            return jsonify({'status': 'error', 'message': 'All signup fields are required'}), 400
        if '@' not in email:
            return jsonify({'status': 'error', 'message': 'Please enter a valid email'}), 400
        if len(password) < 6:
            return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters'}), 400

        age = int(age_raw)
        if age < 18 or age > 100:
            return jsonify({'status': 'error', 'message': 'Age must be between 18 and 100'}), 400

        existing = UserProfile.query.filter_by(email=email).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Email already registered. Please login.'}), 409

        user = UserProfile(
            clerk_user_id=f'local:{email}',
            first_name=first_name,
            surname=surname,
            age=age,
            email=email,
            password_hash=generate_password_hash(password),
            knowledge_level='beginner',
            risk_tolerance='medium',
            onboarding_completed=False,
            last_login_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        merge_session_data(user, {
            'auth_email': email,
            'auth_provider': 'local',
            'last_auth_action': 'signup',
        })
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['email'] = user.email

        return jsonify({
            'status': 'success',
            'needs_onboarding': True,
            'user': user.to_dict(),
        })
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Age must be a valid number'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """Login with email and password."""
    try:
        data = request.json or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

        user = UserProfile.query.filter_by(email=email).first()
        if not user or not user.password_hash:
            return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401
        if not check_password_hash(user.password_hash, password):
            return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401

        user.last_login_at = datetime.utcnow()
        merge_session_data(user, {
            'auth_email': email,
            'auth_provider': 'local',
            'last_auth_action': 'login',
        })
        db.session.commit()

        session['user_id'] = user.id
        session['email'] = user.email

        return jsonify({
            'status': 'success',
            'needs_onboarding': not is_profile_complete(user),
            'user': user.to_dict(),
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/onboard', methods=['POST'])
def api_onboard():
    """Handle user onboarding"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'status': 'error', 'message': 'Please login first'}), 401

        data = request.json or {}

        incoming_monthly = int(data.get('monthly_surplus', 5000))
        incoming_risk = data.get('risk_tolerance', 'medium')
        incoming_goals = data.get('investment_goals', '')
        incoming_horizon = int(data.get('investment_horizon', 5))

        # Keep user profile up to date for future personalized conversations.
        user.monthly_surplus = max(100, min(incoming_monthly, 500000))
        user.risk_tolerance = incoming_risk
        user.investment_goals = incoming_goals.strip()
        user.investment_horizon = max(1, min(incoming_horizon, 40))
        user.onboarding_completed = True
        merge_session_data(user, {
            'onboarding_completed_at': datetime.utcnow().isoformat(),
            'monthly_surplus': user.monthly_surplus,
            'risk_tolerance': user.risk_tolerance,
            'investment_goals': user.investment_goals,
            'investment_horizon': user.investment_horizon,
        })

        db.session.commit()

        # Get personalized greeting
        greeting = get_personalized_greeting(user.to_dict())

        # Store greeting as first AI message
        greeting_msg = ChatMessage(
            user_id=user.id,
            role='assistant',
            content=greeting
        )
        db.session.add(greeting_msg)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'user_id': user.id,
            'greeting': greeting
        })
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Please enter valid numeric values'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message.strip():
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        
        # Save user message
        user_msg = ChatMessage(
            user_id=user.id,
            role='user',
            content=user_message
        )
        db.session.add(user_msg)
        db.session.commit()
        
        # Get recent history for better continuity across ongoing conversations.
        history = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.id.desc()).limit(30).all()
        history.reverse()
        chat_history = [{'role': msg.role, 'content': msg.content} for msg in history]
        
        # Get ARIA response
        ai_response = get_aria_response(
            user_message,
            chat_history[:-1],  # Exclude current user message
            user.to_dict()
        )
        
        # Save AI response
        ai_msg = ChatMessage(
            user_id=user.id,
            role='assistant',
            content=ai_response
        )
        db.session.add(ai_msg)

        merge_session_data(user, {
            'last_user_message': user_message,
            'last_ai_response': ai_response,
            'last_chat_at': datetime.utcnow().isoformat(),
        })
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'response': ai_response
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calculator', methods=['POST'])
def api_calculator():
    """SIP Compounding Calculator"""
    try:
        data = request.json
        monthly_amount = int(data.get('monthly_amount', 5000))
        annual_return = float(data.get('annual_return', 12.0))
        years = int(data.get('years', 10))

        # Clamp inputs to safe ranges
        monthly_amount = max(100, min(monthly_amount, 500000))
        annual_return  = max(1.0, min(annual_return, 30.0))
        years          = max(1, min(years, 40))

        # Calculate growth
        growth_data = calculate_sip_growth(monthly_amount, annual_return, years)

        # Prepare chart data
        years_list     = [row['Year'] for row in growth_data]
        invested_list  = [row['Invested'] for row in growth_data]
        portfolio_list = [row['Portfolio_Value'] for row in growth_data]

        # Final values
        final = growth_data[-1]
        summary = {
            'total_invested':  format_currency(final['Invested']),
            'portfolio_value': format_currency(final['Portfolio_Value']),
            'compounding_gain': format_currency(final['Compounding_Gain']),
            'gain_percentage': f"{(final['Compounding_Gain'] / final['Invested'] * 100):.1f}%"
        }

        # Delay scenario (start today vs start 5 years later)
        delay_data = calculate_delay_scenario(monthly_amount, annual_return, years, delay_years=5)

        return jsonify({
            'status': 'success',
            'chart': {
                'years':     years_list,
                'invested':  invested_list,
                'portfolio': portfolio_list
            },
            'delay_chart': delay_data,
            'summary':    summary,
            'table_data': growth_data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/user/profile', methods=['GET'])
def api_user_profile():
    """Get user profile"""
    user = get_current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    return jsonify({
        'status': 'success',
        'profile': user.to_dict()
    })

@app.route('/api/user/session', methods=['GET'])
def api_user_session_get():
    """Get persisted session memory for the logged-in user."""
    user = get_current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    return jsonify({
        'status': 'success',
        'session_data': get_session_data_dict(user),
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
        'last_seen_at': user.last_seen_at.isoformat() if user.last_seen_at else None,
    })

@app.route('/api/user/session', methods=['POST'])
def api_user_session_update():
    """Persist small UI/session state updates for returning sessions."""
    user = get_current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    payload = request.json or {}
    allowed_keys = {'active_tab', 'calculator_inputs', 'notes'}
    safe_updates = {k: v for k, v in payload.items() if k in allowed_keys}

    if not safe_updates:
        return jsonify({'status': 'error', 'message': 'No valid session fields provided'}), 400

    merge_session_data(user, safe_updates)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'session_data': get_session_data_dict(user),
    })

@app.route('/api/chat/history', methods=['GET'])
def api_chat_history():
    """Get chat history"""
    user = get_current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    messages = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.id).all()
    chat_history = [msg.to_dict() for msg in messages]
    
    return jsonify({
        'status': 'success',
        'history': chat_history
    })

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    user = get_current_user()
    if not user:
        return redirect(url_for('index'))
    if not is_profile_complete(user):
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=user.to_dict())

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
