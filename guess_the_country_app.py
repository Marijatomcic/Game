import streamlit as st
import json
import random
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

st.set_page_config(page_title="Guess the Country Game", layout="centered")

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.secrets["OPENAPI_API_KEY"]
 
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
model_key = "openai/gpt-4.1-nano"

@st.cache_data
def load_data():
    with open("countries.json", "r", encoding="utf-8") as f:
        return json.load(f)
raw_data = load_data()

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def set_background(image_file):
    bin_str = get_base64_of_bin_file(image_file)
    css = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.65), rgba(255,255,255,0.65)),
                          url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
set_background("background.png")

st.markdown("""
    <style>
    .custom-answer-box {
        background-color: #2f3b47;
        color: white;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .summary-box {
        background-color: #fdf3c3;
        padding: 1em;
        border-radius: 8px;
        margin-top: 1em;
        font-size: 1.05em;
        color: #333;
    }
    .stSelectbox > div > div {
        background-color: #e4cdb3 !important;
        border-radius: 8px;
    }
    .stButton > button {
        background-color: #3f3f3f;
        color: white;
        padding: 0.8em 2em;
        font-size: 1.1em;
        border-radius: 10px;
        width: 100%;
    }
    input[type="text"] {
        background-color: #2f3b47 !important;
        color: white !important;
        border-radius: 8px;
        padding: 0.5em;
    }

    </style>
""", unsafe_allow_html=True)


def classify_population(pop):
    if pop < 1_000_000: return "small"
    elif pop < 30_000_000: return "medium"
    return "large"

def get_filtered_country_by_difficulty(difficulty):
    target = {"easy": "large", "medium": "medium", "hard": "small"}
    return [c for c in raw_data if classify_population(c.get("population", 0)) == target[difficulty]]

def generate_country_info_with_ai(name):
    prompt = f"""Give me exactly 3 famous foods, 3 famous landmarks, and 3 cultural festivals from {name}.
Respond ONLY in valid compact JSON format like:
{{"food": [...], "landmark": [...], "festival": [...]}}"""
    try:
        res = client.chat.completions.create(model=model_key, messages=[{"role": "user", "content": prompt}])
        return json.loads(res.choices[0].message.content.strip())
    except:
        return {"food": [], "landmark": [], "festival": []}

# Init game state
if "game_started" not in st.session_state:
    st.session_state.game_started = False
    st.session_state.points = 100
    st.session_state.attempts = 0
    st.session_state.previous_hints = []
    st.session_state.answers = []
    st.session_state.asked_questions = []
    st.session_state.leaderboard = []

st.markdown("## 🌍 Guess the Country Game")

# ✅ Custom pastel yellow instruction box
st.markdown("""
<div style="
    background-color: #fdf3c3;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #f1e3a3;
    margin-bottom: 2rem;
">
<h4>🧠 Game Instructions — powered by AI</h4>
<p>Welcome to <strong>Guess the Country!</strong> 🌍<br>
Each round, a secret country is selected and enriched by <strong>AI-generated cultural insights</strong>.</p>

<ul>
  <li>🔍 Ask up to <strong>8 predefined questions</strong>, all answered intelligently by AI</li>
  <li>🎌 One reveals the country's flag (via AI logic)</li>
  <li>❌ Every time you guess wrong, AI gives you a new cultural hint</li>
  <li>🍽️ Hints include iconic <strong>foods, famous landmarks, or festivals</strong> — all AI-generated</li>
  <li>🧠 Everything adapts to your selected difficulty</li>
</ul>

<p>The fewer questions and hints you use, the higher your final score.<br>
Ready to test your global knowledge — and outsmart the AI?</p>
</div>
""", unsafe_allow_html=True)

difficulty = st.selectbox("🔍 Select difficulty", ["easy", "medium", "hard"])

def setup_new_country():
    filtered = get_filtered_country_by_difficulty(difficulty)
    entry = random.choice(filtered)
    name = entry["name"]["common"]
    region = entry.get("region", "Unknown")
    pop = entry.get("population", 0)
    capital = entry.get("capital", ["Unknown"])[0]
    neighbors = len(entry.get("borders", []))
    coast = not entry.get("landlocked", True)
    un = entry.get("unMember", False)
    fifa = entry.get("fifa", "Unknown")
    cca2 = entry.get("cca2", "XX")
    language = list(entry.get("languages", {}).values())[0] if entry.get("languages") else "Unknown"
    culture = generate_country_info_with_ai(name)

    st.session_state.secret = {
        "name": name, "region": region, "population": classify_population(pop),
        "capital": capital, "coastline": coast, "neighbors": neighbors, "un": un,
        "language": language, "fifa": fifa, "cca2": cca2,
        **culture
    }

if st.button("🎮 Start Game") or st.session_state.get("replay_requested", False):
    st.session_state.replay_requested = False
    setup_new_country()
    st.session_state.answers = []
    st.session_state.asked_questions = []
    st.session_state.previous_hints = []
    st.session_state.game_started = True
    st.success("New country loaded!")


# 🔄 Game logic block
if st.session_state.game_started:

# End the game immediately if points are zero or below
    if st.session_state.points <= 0:
        st.error(f"😢 You're out of points! The country was **{st.session_state.secret['name']}**")
        st.session_state.game_started = False
        st.stop()
#Question section
q_map = {
    "Is it in Europe?": lambda c: f"No, it's in {c['region']}" if c["region"].lower() != "europe" else "Yes, it's in Europe",
    "Is its population small, medium, or large?": lambda c: c["population"],
    "Does it have a coastline?": lambda c: "Yes" if c["coastline"] else "No",
    "Does it have more than 3 neighboring countries?": lambda c: "Yes" if c["neighbors"] > 3 else "No",
    "Is it a UN member?": lambda c: "Yes" if c["un"] else "No",
    "What is the country's capital city?": lambda c: c["capital"],
    "What is the country's FIFA code?": lambda c: c["fifa"],
    "What is the flag?": lambda c: "Here is the flag:"
}

available = [q for q in q_map if q not in st.session_state.asked_questions]

# Store the selected question in session state
st.session_state.selected_question = st.selectbox(
    "❓ Choose a question:",
    available,
    key="question_selector"
)

if st.button("Submit Question"):
    selected = st.session_state.selected_question
    if selected in available:
        answer = q_map[selected](st.session_state.secret)
        st.session_state.answers.append((selected, answer))
        st.session_state.asked_questions.append(selected)
        st.session_state.points -= 2
    else:
        st.warning("⚠️ This question is no longer available.")



    for q, a in st.session_state.answers:
        st.markdown(f"<div class='custom-answer-box'><strong>{q}</strong><br>{a}</div>", unsafe_allow_html=True)
        if q == "What is the flag?":
            code = st.session_state.secret.get("cca2", "XX")
            st.image(f"https://flagsapi.com/{code}/flat/64.png", width=100)

    st.markdown("🎯 **Your Guess:**")
    guess = st.text_input("Enter your country guess")
    if st.button("Submit Guess"):
        if guess.strip().lower() == st.session_state.secret["name"].lower():
            st.success(f"🎉 Correct! It was **{st.session_state.secret['name']}**")
            st.balloons()
            st.session_state.game_started = False

            c = st.session_state.secret
            summary = f"""
            <div class="summary-box">
            <b>Continent:</b> {c['region']}<br>
            <b>Capital:</b> {c['capital']}<br>
            <b>Language:</b> {c['language']}<br>
            <b>Population:</b> {c['population']}<br>
            <b>FIFA Code:</b> {c['fifa']}<br>
            <b>Foods:</b> 🍽️ {', '.join(c['food'])}<br>
            <b>Landmarks:</b> 🏰 {', '.join(c['landmark'])}<br>
            <b>Festivals:</b> 🎉 {', '.join(c['festival'])}
            </div>
            """
            st.markdown("### 📚 Country Summary")
            st.markdown(summary, unsafe_allow_html=True)

        else:
            st.error("❌ Wrong guess.")
            st.session_state.attempts += 1
            st.session_state.points -= 20

            if st.session_state.points <= 0:
                st.error(f"😢 You're out of points! The country was **{st.session_state.secret['name']}**")
                st.session_state.game_started = False

            if st.session_state.attempts >= 5:
                st.error(f"😢 Game Over! The country was **{st.session_state.secret['name']}**")
                st.session_state.game_started = False
            else:
                country = st.session_state.secret["name"]
                used_hints = st.session_state.previous_hints
                prompt = f"""

            
Give ONE unique cultural clue about the country '{country}' that matches the difficulty '{difficulty}'.

Pick only from these categories:
- Famous foods
- Major landmarks
- Cultural festivals

Rules:
- For 'easy', choose very famous foods or major landmarks; country must have population > 30M
- For 'medium', pick well-known festivals or traditions; country must have population < 30M
- For 'hard', give obscure festivals, lesser-known landmarks, or traditional foods; country must have population < 1M

Warnings:
- Do NOT mention the country name '{country}' or its capital
- Avoid repeating previous hints: {used_hints}
- Try to rotate topics (if last hint was a food, give a landmark or festival next)
- Return ONLY in this JSON format: {{ "hint": "..." }}
"""
                try:
                    res = client.chat.completions.create(
                        model=model_key,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    hint = json.loads(res.choices[0].message.content.strip())["hint"]
                    if hint not in st.session_state.previous_hints:
                        st.session_state.previous_hints.append(hint)
                        st.info(f"💡 Hint: {hint}")
                    else:
                        st.warning("You've already seen this hint.")
                except:
                    st.warning("⚠️ Could not fetch hint.")

    # ✅ DISPLAY updated after processing
    st.markdown(f"🧠 **Guesses left:** {5 - st.session_state.attempts} | 🏆 **Points:** {st.session_state.points}")

# Leaderboard + Play Again
if not st.session_state.game_started and "secret" in st.session_state:
    player = st.text_input("🏅 Enter your name for the leaderboard:", key="player_name")
    
    if st.button("Submit Score") and player:
        current_score = st.session_state.points

        # Check if player already has an entry and if the new score is better
        existing = [s for s in st.session_state.leaderboard if s[0] == player]
        if existing:
            best_prev = max(s[1] for s in existing)
            if current_score > best_prev:
                # Remove old entry and add updated score
                st.session_state.leaderboard = [s for s in st.session_state.leaderboard if s[0] != player]
                st.session_state.leaderboard.append((player, current_score))
        else:
            st.session_state.leaderboard.append((player, current_score))

        # Sort leaderboard in descending order of score
        st.session_state.leaderboard = sorted(st.session_state.leaderboard, key=lambda x: x[1], reverse=True)[:5]


if st.button("🎯 Play Again"):
    # Reset only if game was lost
    if st.session_state.points <= 0 or st.session_state.attempts >= 5:
        st.session_state.points = 100
        st.session_state.attempts = 0
    # Otherwise: keep points and attempts

    st.session_state.secret = None
    st.session_state.replay_requested = True
    st.session_state.game_started = False
    st.rerun()

if st.session_state.leaderboard:
    st.markdown("### 🏆 Leaderboard")
    for i, (name, score) in enumerate(st.session_state.leaderboard, 1):
        st.markdown(f"**{i}. {name}** — {score} points")

















































