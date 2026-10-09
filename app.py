import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Fikirakirana ny pejy Streamlit
st.set_page_config(page_title="Projet SBI", page_icon="🔐", layout="wide")

# Ampifandraisina amin'ny Supabase amin'ny alalan'ny Streamlit Secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Fiarovana ny Session state ho an'ny connexion
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

def login():
    st.title("🔐 Projet SBI - Pejy fidirana")
    st.subheader("Mampidira ny IM sy ny Mot de passe")

    with st.form("login_form"):
        im_input = st.number_input("Immatriculation (IM):", value=277485, step=1)
        password_input = st.text_input("Mot de passe:", type="password")
        submit_button = st.form_submit_button("Miditra (Se connecter)")

        if submit_button:
            # Rehetra momba ny UTILISATEUR avy amin'ny Supabase
            response = supabase.table("utilisateur").select("*").eq("im", im_input).execute()
            data = response.data

            if data and len(data) > 0:
                user = data[0]
                # Fanamarinana ny mot de passe
                if user.get("password") == password_input:
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = user
                    st.success("Tafiditra soa aman-tsara!")
                    st.rerun()
                else:
                    st.error("Diso ny mot de passe!")
            else:
                st.error("Tsy hita io IM io ao amin'ny banky angona (Supabase)!")

def main_app():
    user = st.session_state["user_info"]
    
    # Barra lateral misy ny mombamomba ny mpampiasa
    st.sidebar.title("👤 Konty tafiditra")
    st.sidebar.write(f"**Anarana:** {user['nom']}")
    st.sidebar.write(f"**IM:** {user['im']}")
    st.sidebar.write(f"**Corps:** {user['corps']}")
    
    if st.sidebar.button("Hiboaka (Se déconnecter)"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.rerun()

    st.title("📊 Projet SBI - Dashboard")
    st.write(f"Tongasoa eto amin'ny sehatra, **{user['nom']}**!")

    tab1, tab2 = st.tabs(["📁 Angona UO", "👥 Angona UTILISATEUR"])

    with tab1:
        st.subheader("Tabilao UO (Unité Organisationnelle)")
        uo_response = supabase.table("uo").select("*").execute()
        df_uo = pd.DataFrame(uo_response.data)
        st.dataframe(df_uo, use_container_width=True)

    with tab2:
        st.subheader("Tabilao UTILISATEUR")
        user_response = supabase.table("utilisateur").select("*").execute()
        df_user = pd.DataFrame(user_response.data)
        # Afatotra tsy haseho ny mot de passe eo amin'ny tabilao ankapobeny mba ho fiarovana
        if "password" in df_user.columns:
            df_user = df_user.drop(columns=["password"])
        st.dataframe(df_user, use_container_width=True)

# Famaritana ny pejy haseho
if not st.session_state["authenticated"]:
    login()
else:
    main_app()
