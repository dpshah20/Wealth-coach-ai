import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are ARIA — a warm, patient AI wealth mentor for first-time investors in India.

YOUR PERSONALITY:
- Friendly, encouraging, non-judgmental — like a knowledgeable older sibling
- You use simple everyday analogies (chai, cricket, travel, Zomato delivery)
- You never use jargon without defining it
- If someone seems anxious about money, address the emotion first

EXACT RESPONSE FORMAT — always follow this structure:

Line 1: A short, punchy hook sentence (plain text, no markdown)

One or two sentences of core explanation. Use **bold** for key terms or important numbers. Keep it simple and conversational.

- Bullet point one — short and punchy
- Bullet point two — practical or memorable
- Bullet point three — optional, only if needed

One thoughtful follow-up question that deepens their understanding?

📌 Educational only — not personal financial advice.

STRICT RULES:
1. Always use the exact format above — hook, body, bullets (2-3), one follow-up question, disclaimer
2. Keep total response under 150 words
3. Never recommend specific funds, stocks, or fund houses by name
4. Never guarantee returns or predict markets
5. Bold (**text**) only key terms and important figures
6. The follow-up question must be on its own line, end with a ?
7. Use ₹ for amounts

FOLLOW-UP QUESTION BANK (pick the most relevant):
- "Are you planning to use this money within 2–3 years, or can you invest for longer?"
- "How many years can you stay invested without touching this money?"
- "On a scale of 1–10, how okay are you with your money going up and down sometimes?"
- "What's the one financial goal you want this money to help you reach?"
- "Do you currently have 3–6 months of expenses saved as an emergency fund?"
- "Would you prefer steady but slower growth, or are you okay with some ups and downs for better returns?"

SCOPE:
- SIP, mutual funds, FD, ELSS, index funds, compounding, diversification, asset allocation
- Trade-offs: safety vs growth, liquidity vs returns
- Emergency funds, risk tolerance, surplus allocation

DO NOT:
- Give specific portfolio or fund recommendations
- Provide tax or legal advice
- Predict future returns
"""

def get_aria_response(user_message, chat_history, user_profile=None):
    """
    Get response from ARIA based on message and history
    
    Args:
        user_message: User's input message
        chat_history: List of previous chat messages
        user_profile: Optional user profile dict for context
        
    Returns:
        str: ARIA's response
    """
    try:
        # Build context from chat history
        conversation_context = []

        # Add system prompt as first message
        system_message = SYSTEM_PROMPT
        if user_profile:
            system_message += f"\n\nUSER CONTEXT:\n"
            system_message += f"- Monthly Surplus: ₹{user_profile.get('monthly_surplus', 'Unknown')}\n"
            system_message += f"- Risk Tolerance: {user_profile.get('risk_tolerance', 'Unknown')}\n"
            system_message += f"- Investment Horizon: {user_profile.get('investment_horizon', 'Unknown')} years\n"
            system_message += f"- Knowledge Level: {user_profile.get('knowledge_level', 'Beginner')}\n"

        conversation_context.append({
            "role": "user",
            "parts": [{"text": system_message}]
        })

        conversation_context.append({
            "role": "model",
            "parts": [{"text": "I understand. I'm ARIA, your wealth coach. I'll help you learn about investing in a simple, encouraging way. Ask me anything!"}]
        })

        # Add chat history
        for msg in chat_history[-8:]:  # Last 8 messages to leave room for system
            conversation_context.append({
                "role": msg['role'],
                "parts": [{"text": msg['content']}]
            })

        # Add current message
        conversation_context.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        # Generate response
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=conversation_context
        )
        
        return response.text
    except Exception as e:
        return f"❌ Error connecting to ARIA: {str(e)}\n\nPlease check your Gemini API key and try again."

def get_personalized_greeting(user_profile):
    """Get personalized greeting based on user profile"""
    try:
        surplus  = user_profile.get('monthly_surplus', 5000)
        goal     = user_profile.get('investment_goals', 'your goals')
        horizon  = user_profile.get('investment_horizon', 10)
        risk     = user_profile.get('risk_tolerance', 'medium')

        risk_label = {'low': 'conservative', 'medium': 'balanced', 'high': 'growth-focused'}.get(risk, 'balanced')

        prompt = f"""Generate a warm, personalized welcome message for a first-time investor with these details:
- Monthly surplus: ₹{surplus}
- Goal: {goal}
- Investment horizon: {horizon} years
- Risk style: {risk_label}

Follow this EXACT format:
Line 1: Warm, personal welcome hook (1 sentence, plain text)

One sentence acknowledging their goal and what's possible in {horizon} years. Use **bold** for key terms.

- One encouraging fact about their situation
- One quick win they could focus on first

What's the first thing about investing you'd like to understand better?

📌 Educational only — not personal financial advice.

Keep it under 120 words. Warm, encouraging, like a knowledgeable friend."""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        return response.text
    except Exception as e:
        return "Welcome back! I'm ARIA, your AI wealth mentor.\n\nReady to help you make your money work harder — ask me anything about investing, SIP, mutual funds, or where to start.\n\nWhat's one investing concept you've always wanted to understand?\n\n📌 Educational only — not personal financial advice."

def get_learning_recommendations(user_profile, completed_topics=None):
    """Get recommended learning topics based on user profile"""
    try:
        completed_str = ", ".join(completed_topics) if completed_topics else "None yet"
        prompt = f"""Based on this investor profile, suggest 3 MOST RELEVANT learning topics:
        
        Profile:
        - Monthly Surplus: ₹{user_profile['monthly_surplus']}
        - Risk Tolerance: {user_profile['risk_tolerance']}
        - Investment Horizon: {user_profile['investment_horizon']} years
        - Completed Topics: {completed_str}
        
        Return as JSON array with exactly 3 topics. Format:
        [
          {{"topic": "Topic Name", "reason": "Why this matters for them"}},
          ...
        ]
        
        Available topics: Emergency Fund Basics, Understanding SIP, Mutual Funds 101, 
        Risk vs Return, Diversification, Index Funds, Compounding Power, Asset Allocation"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        import json
        try:
            # Extract JSON from response
            response_text = response.text
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                recommendations = json.loads(json_str)
                return recommendations
        except:
            pass
        
        # Fallback recommendations
        return [
            {"topic": "Emergency Fund Basics", "reason": "Foundation before investing"},
            {"topic": "Understanding SIP", "reason": "Perfect for your monthly surplus"},
            {"topic": "Risk vs Return", "reason": "Align with your risk tolerance"}
        ]
    except Exception as e:
        return [
            {"topic": "Emergency Fund Basics", "reason": "Foundation before investing"},
            {"topic": "Understanding SIP", "reason": "Perfect for your monthly surplus"},
            {"topic": "Risk vs Return", "reason": "Align with your risk tolerance"}
        ]
