import streamlit as st
import sqlite3
import os
import pandas as pd
import requests
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AI Code Review System", page_icon="🛠️", layout="wide")

# إعدادات الـ API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DB_PATH = "execution_tracking.db"

# --- قراءة المفتاح بشكل آمن جداً من إعدادات Streamlit ---
try:
    HIDDEN_REAL_KEY = st.secrets["GROQ_API_KEY"]
except:
    HIDDEN_REAL_KEY = ""

# --- الشريط الجانبي لإدخال المفتاح (Sidebar) ---
st.sidebar.title("🔑 Security settings")

# تهيئة ذاكرة حفظ المفتاح داخل الموقع
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- ميزة الباسوورد السريع للتيم واللجنة ---
with st.sidebar.expander("⚡ Show the API key"):
    st.write("Enter the password to automatically populate and activate the key:")
    quick_pass = st.text_input("Password:", type="password", placeholder="Enter Password here...")
    if st.button("Automatically fill in the key 🚀", use_container_width=True):
        if quick_pass == "2006":
            st.session_state.api_key = HIDDEN_REAL_KEY
            st.success("The key has been successfully called and activated! 🎉")
            st.rerun()
        else:
            st.error("❌ The password is incorrect!")

# مربع النص لإدخال المفتاح
raw_key = st.sidebar.text_input("Groq API Key:", type="password", placeholder="gsk_...", value=st.session_state.api_key)

# زرار التفعيل اليدوي
if st.sidebar.button("Activating and approving the key 🔑", use_container_width=True):
    st.session_state.api_key = raw_key
    if raw_key.strip():
        st.sidebar.success("The key has been successfully activated! 🎉")
    else:
        st.sidebar.error("Please enter the key first!")

# المفتاح الفعلي الذي سيستخدمه النظام
user_api_key = st.session_state.api_key

# وظيفة استدعاء الـ API
def call_groq_api(prompt, api_key):
    if not api_key.strip():
        return "❌ Error: The API key has not been activated. Please use Quick Login or enter the key and click the Activate button first."
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

# بناء البرومبت 
def build_prompt(code_content, file_type="python"):
    return f"""
You are an expert code reviewer analyzing {file_type} code.
Your response MUST be concise, practical, and directly proportional to the complexity of the input code.

STRICT INSTRUCTIONS:
1. DO NOT over-engineer the code. If the user submits a simple print statement or a short script, fix ONLY the syntax/logic errors. Do NOT add unnecessary wrapper functions, classes, logging, or complex boilerplate unless the original code already has them.
2. Keep your explanation simple, direct, and easy to read. Avoid long essays or generic clichés.
3. Use the following exact markdown format:

### 🐞 (Key Issues Identified):
* Mention only the actual errors or bottlenecks concisely in 2-4 brief bullet points.

### 💡 (Quick Tip):
* One concise sentence on how to write this better.

### ✅ (Corrected Code):
Provide the exact, clean, fixed code directly inside a code block without over-complicating it.

Code to review:
{code_content}
"""

# تسجيل العملية في الداتابيز
def log_to_db(file_name, status, result):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT, execution_status TEXT, ai_analysis_result TEXT, timestamp TEXT
        )
    """)
    cursor.execute("INSERT INTO code_review_logs VALUES (NULL, ?, ?, ?, ?)",
                   (file_name, status, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- واجهة المستخدم الرئيسية ---
st.title("🛡️ Automated AI Code Review & Refactoring System")
st.write("منصة تفاعلية لمراجعة وتحسين أكواد هندسة البيانات باستخدام الذكاء الاصطناعي")

tab1, tab2 = st.tabs(["⚡ (Live Review)", "📊 (Dashboard)"])

# --- التبويبة الأولى: التجربة الحية ---
with tab1:
    input_method = st.radio("Choose the method of entering the code:", ("(File Upload)", "(Paste Code)"), horizontal=True)
    
    code_to_review = ""
    file_name = "Direct_Paste.py"
    file_type = "python"

    # تم تصليح الشرط هنا ليتطابق مع الـ Radio Button
    if input_method == "(File Upload)":
        uploaded_file = st.file_uploader("Upload the code file (.py, .sql)", type=["py", "sql"])
        if uploaded_file is not None:
            code_to_review = uploaded_file.read().decode("utf-8")
            file_name = uploaded_file.name
            file_type = "python" if file_name.endswith(".py") else "sql"
    else:
        file_type = st.selectbox("Select the programming language:", ["python", "sql"])
        code_to_review = st.text_area("Paste the broken code here:", height=200)

    if st.button("🔍 Code Review and Optimization", type="primary"):
        if code_to_review.strip() == "":
            st.warning("Please enter the code first!")
        elif not user_api_key.strip():
            st.error("Please enter the API key or use the quick login in the sidebar first!")
        else:
            with st.spinner("Analyzing the code via Groq AI..."):
                prompt = build_prompt(code_to_review, file_type)
                ai_response = call_groq_api(prompt, user_api_key)
                
                if "❌ Error" in ai_response or "Error:" in ai_response:
                    st.error(ai_response)
                else:
                    log_to_db(file_name, "SUCCESS", ai_response)
                    st.success("The analysis has been successfully completed!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📝 Original code (the problem)")
                        st.code(code_to_review, language=file_type)
                    
                    with col2:
                        st.subheader("🤖 Artificial Intelligence and Correction Report")
                        st.markdown(ai_response)

# --- التبويبة الثانية: التحليلات ---
with tab2:
    st.subheader("Past Operations Log and Statistics")
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT id, file_name, execution_status, timestamp FROM code_review_logs ORDER BY id DESC", conn)
        conn.close()
        
        c1, c2 = st.columns(2)
        c1.metric("Total files scanned", len(df))
        c2.metric("Success Rate", "100%")
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("There are no records in the database yet.")
