import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage
import time
import zipfile
import io
import os
import sqlite3
import datetime
import requests

# Set page config
st.set_page_config(page_title="PTU E-Certificate Generator", layout="wide", page_icon="🎓", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
def local_css():
    st.markdown("""
    <style>
    /* Streamlit native configuration used in config.toml to hide toolbar */

    /* Stunning Dark Glassmorphism Theme */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* Apply animation to main elements */
    .block-container {
        animation: fadeIn 0.8s ease-out;
    }
    
    /* Headers with gradient text */
    h1, h2, h3 {
        background: linear-gradient(to right, #00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Inputs - Glass style */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
        color: #f8fafc !important;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus, .stTextArea > div > textarea:focus, .stSelectbox > div > div:focus {
        border-color: #00f2fe !important;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.3) !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Standard Buttons */
    .stButton > button {
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.05);
        color: white;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 12px 28px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton > button:hover {
        transform: scale(1.05);
        border-color: rgba(255,255,255,0.3);
        box-shadow: 0 0 20px rgba(255,255,255,0.1);
    }
    
    /* Primary Action Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #00c6ff, #0072ff);
        border: none;
        box-shadow: 0 4px 15px rgba(0, 114, 255, 0.4);
        font-weight: bold;
        letter-spacing: 0.5px;
    }
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.05) translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 114, 255, 0.6);
    }
    
    /* Tabs - Glassmorphic */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background: rgba(0, 0, 0, 0.2);
        padding: 10px;
        border-radius: 16px;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #00f2fe !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* File Uploaders */
    .stFileUploader > div > div {
        background: rgba(255, 255, 255, 0.03);
        border: 2px dashed rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        transition: all 0.3s ease;
    }
    .stFileUploader > div > div:hover {
        border-color: #00f2fe;
        background: rgba(0, 242, 254, 0.05);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Image preview constraint with neon glow */
    .preview-img-container img {
        max-height: 550px;
        width: auto !important;
        margin: 0 auto;
        display: block;
        border-radius: 12px;
        box-shadow: 0 0 30px rgba(0, 242, 254, 0.2);
        transition: transform 0.3s ease;
    }
    .preview-img-container img:hover {
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
def setup_database():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS run_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT,
         action_type TEXT,
         record_count INTEGER,
         status TEXT)
    ''')
    conn.commit()
    return conn

def log_history(action_type, record_count, status):
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO run_history (timestamp, action_type, record_count, status) VALUES (?, ?, ?, ?)",
              (timestamp, action_type, record_count, status))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect('history.db')
    df = pd.read_sql_query("SELECT * FROM run_history ORDER BY id DESC", conn)
    conn.close()
    return df

# --- FONT SETUP ---
FONTS_DIR = "fonts"
FONT_URLS = {
    "Lato (Sans-Serif)": "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf",
    "Crimson Text (Serif)": "https://github.com/google/fonts/raw/main/ofl/crimsontext/CrimsonText-Regular.ttf",
    "Great Vibes (Cursive)": "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf",
    "Pacifico (Display)": "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf"
}

def setup_fonts():
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)
    
    for font_name, url in FONT_URLS.items():
        file_path = os.path.join(FONTS_DIR, f"{font_name.split(' ')[0]}.ttf")
        if not os.path.exists(file_path):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                print(f"Failed to download {font_name}: {e}")

# --- AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had a correct password."""
    def password_entered():
        if st.session_state["username"] == "admin" and st.session_state["password"] == "admin123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.header("Admin Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.header("Admin Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        st.error("😕 User not known or password incorrect")
        return False
    else:
        return True

@st.cache_data
def load_dataframe(file_bytes, file_name):
    if file_name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    else:
        return pd.read_excel(io.BytesIO(file_bytes))

def load_template_image(file_bytes):
    return Image.open(io.BytesIO(file_bytes))

def get_font(font_choice, custom_font_bytes, size):
    if custom_font_bytes:
        return ImageFont.truetype(io.BytesIO(custom_font_bytes), size)
    
    if font_choice and font_choice in FONT_URLS:
        file_path = os.path.join(FONTS_DIR, f"{font_choice.split(' ')[0]}.ttf")
        if os.path.exists(file_path):
            return ImageFont.truetype(file_path, size)
    
    # Fallback
    try:
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        return ImageFont.load_default()

def apply_formatting(text, fmt):
    if fmt == "Title Case":
        return str(text).title()
    elif fmt == "UPPERCASE":
        return str(text).upper()
    return str(text)

def generate_certificate_image(
    name, college, template,
    name_x, name_y, name_size, name_color, name_align, name_fmt,
    col_x, col_y, col_size, col_color, col_align, col_fmt,
    font_choice, custom_font_bytes
):
    img_copy = template.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Draw Name
    name_font = get_font(font_choice, custom_font_bytes, name_size)
    formatted_name = apply_formatting(name, name_fmt)
    if name_align:
        bbox = draw.textbbox((0, 0), formatted_name, font=name_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        pos_x = name_x - text_width / 2
        pos_y = name_y - text_height / 2
    else:
        pos_x = name_x
        pos_y = name_y
    draw.text((pos_x, pos_y), formatted_name, fill=name_color, font=name_font)
    
    # Draw College
    if college and pd.notna(college):
        col_font = get_font(font_choice, custom_font_bytes, col_size)
        formatted_col = apply_formatting(college, col_fmt)
        if col_align:
            bbox = draw.textbbox((0, 0), formatted_col, font=col_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            c_pos_x = col_x - text_width / 2
            c_pos_y = col_y - text_height / 2
        else:
            c_pos_x = col_x
            c_pos_y = col_y
        draw.text((c_pos_x, c_pos_y), formatted_col, fill=col_color, font=col_font)
        
    return img_copy

def main():
    local_css()
    setup_database()
    setup_fonts()
    
    # Header Section with Logo
    col1, col2 = st.columns([1, 6])
    with col1:
        if os.path.exists("ptu_logo.png"):
            st.image("ptu_logo.png", width=120)
        else:
            st.info("Logo missing (ptu_logo.png)")
    with col2:
        st.title("PTU E-CERTIFICATE GENERATOR")
        st.markdown("##### 🎓 Professional Certificate Generation & Dispatch System")
        
    st.markdown("---")
    
    # --- SIDEBAR: SMTP CONFIGURATION ---
    st.sidebar.header("✉️ SMTP Configuration")
    smtp_server = st.sidebar.text_input("SMTP Server", value="smtp.gmail.com")
    smtp_port = st.sidebar.number_input("SMTP Port", value=587, step=1)
    sender_email = st.sidebar.text_input("Sender Email")
    sender_password = st.sidebar.text_input("Sender App Password", type="password")

    st.sidebar.subheader("Email Template")
    email_subject = st.sidebar.text_input("Email Subject", value="Your Certificate")
    email_body = st.sidebar.text_area(
        "Email Body", 
        value="Hello {Name},\n\nPlease find your certificate attached.\n\nBest Regards,\nThe Team",
        height=150
    )

    # TABS LAYOUT
    tab1, tab2, tab3 = st.tabs(["🖌️ Generator Studio", "🚀 Bulk Dispatcher", "📜 History Logs"])

    with tab1:
        # --- MAIN AREA: UPLOADS ---
        st.header("1. Data & Templates")
        col_u1, col_u2 = st.columns(2)

        with col_u1:
            data_file = st.file_uploader("Upload Student Data (CSV/Excel)", type=["csv", "xlsx"])
        with col_u2:
            template_file = st.file_uploader("Upload Certificate Template (PNG/JPG)", type=["png", "jpg", "jpeg"])

        # Load Data
        df = None
        if data_file:
            try:
                df = load_dataframe(data_file.getvalue(), data_file.name)
                
                if 'Name' not in df.columns or 'Email' not in df.columns or 'College' not in df.columns:
                    st.error("Uploaded file MUST contain 'Name', 'Email', and 'College' columns.")
                    df = None
                else:
                    st.success(f"Data loaded successfully. {len(df)} records found.")
            except Exception as e:
                st.error(f"Error loading data: {e}")

        # Load Image
        template_img = None
        if template_file:
            try:
                template_img = load_template_image(template_file.getvalue())
                st.success("Template loaded successfully.")
            except Exception as e:
                st.error(f"Error loading template image: {e}")

        if df is not None and template_img is not None:
            st.header("2. Styling & Fonts")
            
            # Font Selection
            st.markdown("#### Font Selection")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                font_choice = st.selectbox("Select Built-in Font", list(FONT_URLS.keys()))
            with col_f2:
                font_file = st.file_uploader("OR Upload Custom Font (TTF)", type=["ttf"])
                custom_font_bytes = font_file.read() if font_file else None

            # Image dimensions for slider limits
            img_width, img_height = template_img.size
            
            st.markdown("#### Name Configuration")
            col_n1, col_n2, col_n3 = st.columns(3)
            with col_n1:
                name_x = st.slider("Name X-Coord", min_value=0, max_value=img_width, value=img_width//2)
                name_y = st.slider("Name Y-Coord", min_value=0, max_value=img_height, value=img_height//3)
                name_align = st.checkbox("Center Align Name", value=True)
            with col_n2:
                name_size = st.slider("Name Font Size", min_value=10, max_value=200, value=60)
                name_color = st.color_picker("Name Font Color", value="#000000")
            with col_n3:
                name_fmt = st.selectbox("Name Formatting", ["Title Case", "UPPERCASE", "Original"])
                
            st.markdown("#### College Name Configuration")
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                col_x = st.slider("College X-Coord", min_value=0, max_value=img_width, value=img_width//2)
                col_y = st.slider("College Y-Coord", min_value=0, max_value=img_height, value=(img_height//3)*2)
                col_align = st.checkbox("Center Align College", value=True)
            with col_c2:
                col_size = st.slider("College Font Size", min_value=10, max_value=200, value=40)
                col_color = st.color_picker("College Font Color", value="#333333")
            with col_c3:
                col_fmt = st.selectbox("College Formatting", ["Title Case", "UPPERCASE", "Original"], index=1)

            st.header("3. Live Preview")
            first_row = df.iloc[0]
            first_name = first_row['Name']
            first_college = first_row['College']
            
            preview_img = generate_certificate_image(
                first_name, first_college, template_img,
                name_x, name_y, name_size, name_color, name_align, name_fmt,
                col_x, col_y, col_size, col_color, col_align, col_fmt,
                font_choice, custom_font_bytes
            )
            
            st.markdown('<div class="preview-img-container">', unsafe_allow_html=True)
            st.image(preview_img, caption=f"Preview for: {first_name} - {first_college}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.header("4. Bulk Generate (ZIP Download)")
            if st.button("📦 Generate All Certificates (ZIP)", type="primary"):
                progress_bar = st.progress(0)
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for i, row in df.iterrows():
                        name = row['Name']
                        college = row['College']
                        
                        cert_img = generate_certificate_image(
                            name, college, template_img,
                            name_x, name_y, name_size, name_color, name_align, name_fmt,
                            col_x, col_y, col_size, col_color, col_align, col_fmt,
                            font_choice, custom_font_bytes
                        )
                        
                        # Convert to PDF and resize to keep it light (under 2-3MB)
                        img_pdf_buffer = io.BytesIO()
                        cert_img_rgb = cert_img.convert('RGB')
                        cert_img_rgb.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                        cert_img_rgb.save(img_pdf_buffer, format='PDF', resolution=100)
                        
                        # Add to ZIP
                        zip_file.writestr(f"{name}_Certificate.pdf", img_pdf_buffer.getvalue())
                        
                        progress_bar.progress((i + 1) / len(df))
                
                log_history("Bulk ZIP Generation", len(df), "Success")
                st.success("Certificates generated successfully!")
                st.download_button(
                    label="⬇️ Download All Certificates (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="certificates.zip",
                    mime="application/zip"
                )

        else:
            st.info("👆 Please upload both Student Data and a Certificate Template to proceed.")

    with tab2:
        st.header("Bulk Email Dispatcher")
        st.write("Send generated certificates directly to students' emails.")
        
        if df is not None and template_img is not None:
            if st.button("🚀 Verify & Send Emails", type="primary"):
                if not sender_email or not sender_password:
                    st.error("Please provide SMTP Sender Email and App Password in the sidebar.")
                else:
                    status_placeholder = st.empty()
                    progress_bar_email = st.progress(0)
                    
                    # Initialize status table
                    status_df = pd.DataFrame(columns=["Name", "College", "Email", "Status", "Error Reason"])
                    
                    # Setup SMTP
                    try:
                        server = smtplib.SMTP(smtp_server, int(smtp_port))
                        server.starttls()
                        server.login(sender_email, sender_password)
                        
                        success_count = 0
                        for i, row in df.iterrows():
                            name = row['Name']
                            college = row['College']
                            recipient_email = row['Email']
                            
                            try:
                                # Generate PDF for this user
                                cert_img = generate_certificate_image(
                                    name, college, template_img,
                                    name_x, name_y, name_size, name_color, name_align, name_fmt,
                                    col_x, col_y, col_size, col_color, col_align, col_fmt,
                                    font_choice, custom_font_bytes
                                )
                                # Convert to PDF and resize to keep it light
                                img_pdf_buffer = io.BytesIO()
                                cert_img_rgb = cert_img.convert('RGB')
                                cert_img_rgb.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                                cert_img_rgb.save(img_pdf_buffer, format='PDF', resolution=100)
                                pdf_data = img_pdf_buffer.getvalue()
                                
                                # Prepare Email
                                msg = EmailMessage()
                                msg['Subject'] = email_subject
                                msg['From'] = sender_email
                                msg['To'] = recipient_email
                                
                                # Format body
                                body = email_body.replace("{Name}", str(name))
                                msg.set_content(body)
                                
                                # Attach PDF
                                msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f"{name}_Certificate.pdf")
                                
                                # Send
                                server.send_message(msg)
                                success_count += 1
                                
                                # Update status
                                new_row = {"Name": name, "College": college, "Email": recipient_email, "Status": "Sent", "Error Reason": ""}
                                status_df = pd.concat([status_df, pd.DataFrame([new_row])], ignore_index=True)
                                
                            except Exception as e:
                                new_row = {"Name": name, "College": college, "Email": recipient_email, "Status": "Failed", "Error Reason": str(e)}
                                status_df = pd.concat([status_df, pd.DataFrame([new_row])], ignore_index=True)
                            
                            # Update UI
                            status_placeholder.dataframe(status_df, use_container_width=True)
                            progress_bar_email.progress((i + 1) / len(df))
                            
                            # Rate limiting (delay to prevent spam flagging)
                            if i < len(df) - 1:
                                time.sleep(2)
                        
                        server.quit()
                        log_history("Email Dispatch", success_count, "Success")
                        st.success(f"Email dispatch completed. Sent {success_count}/{len(df)} emails.")
                        
                    except Exception as smtp_e:
                        log_history("Email Dispatch", 0, f"Failed: {smtp_e}")
                        st.error(f"SMTP Connection Error: {smtp_e}")
        else:
             st.info("👆 Please upload Data and Template in the Generator Studio tab first.")

    with tab3:
        st.header("History Logs")
        st.write("Overview of all past generations and email dispatches.")
        
        if st.button("🔄 Refresh History"):
            pass # Streamlit reruns on button click anyway
            
        try:
            history_df = get_history()
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else:
                st.info("No history logs found yet. Generate some certificates to see logs here.")
        except Exception as e:
            st.error(f"Could not load history: {e}")

if check_password():
    main()
