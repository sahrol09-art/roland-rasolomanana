import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

# Fikirakirana ny pejy Streamlit
st.set_page_config(page_title="Projet SBI", page_icon="🔐", layout="wide")

# Ampifandraisina amin'ny Supabase amin'ny alalan'ny Streamlit Secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Session State ho an'ny connexion sy ny importation
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None
if "import_pending" not in st.session_state:
    st.session_state["import_pending"] = None

def login():
    st.title("🔐 Projet SBI - Pejy fidirana")
    st.subheader("Mampidira ny IM sy ny Mot de passe")

    with st.form("login_form"):
        im_input = st.number_input("Immatriculation (IM):", value=277485, step=1)
        password_input = st.text_input("Mot de passe:", type="password")
        submit_button = st.form_submit_button("Miditra (Se connecter)")

        if submit_button:
            response = supabase.table("utilisateur").select("*").eq("im", im_input).execute()
            data = response.data

            if data and len(data) > 0:
                user = data[0]
                if user.get("password") == password_input:
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = user
                    st.success("Tafiditra soa aman-tsara!")
                    st.rerun()
                else:
                    st.error("Diso ny mot de passe!")
            else:
                st.error("Tsy hita io IM io ao amin'ny banky angona!")

def execute_btt_insert(records_to_insert, user_uo, action="insert", existing_criteria=None):
    try:
        # Raha misy mise à jour (remplacer), fafana aloha ny efa ao araka ny taona sy volana
        if action == "update" and existing_criteria:
            for crit in existing_criteria:
                supabase.table("btt").delete()\
                    .eq("uo_id", user_uo)\
                    .eq("annee", crit["annee"])\
                    .eq("mois", crit["mois"])\
                    .execute()

        # Fampidirana ny angona vaovao
        supabase.table("btt").insert(records_to_insert).execute()
        st.success(f"✅ Vita ny importation ho an'ny UO {user_uo}!")
        st.session_state["import_pending"] = None
        st.rerun()
    except Exception as e:
        st.error(f"Nisy olana teo am-pampidirana: {e}")

def main_app():
    user = st.session_state["user_info"]
    user_uo_id = str(user.get('id_uo', '')).strip()
    
    st.sidebar.title("👤 Konty tafiditra")
    st.sidebar.write(f"**Anarana:** {user['nom']}")
    st.sidebar.write(f"**IM:** {user['im']}")
    st.sidebar.write(f"**Corps:** {user['corps']}")
    st.sidebar.write(f"**UO ID:** {user_uo_id}")
    
    if st.sidebar.button("Hiboaka (Se déconnecter)"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.session_state["import_pending"] = None
        st.rerun()

    st.title("📊 Projet SBI - Sehetra Fitantanana")
    st.write(f"Tongasoa, **{user['nom']}**!")

    tab_btt, tab_uo, tab_user = st.tabs(["📄 Angona BTT", "📁 Angona UO", "👥 Angona UTILISATEUR"])

    # --- TAB BTT ---
    with tab_btt:
        st.subheader("📄 Fitantanana ny BTT")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📊 Mijery Angona", "📤 Ampiakatra Fichier Excel", "✍️ Hampiditra An-tanana"])

        # 1. Mijery ny angona BTT
        with sub_tab1:
            st.write(f"### Lisitry ny BTT voasoratra ao amin'ny Supabase (UO: {user_uo_id})")
            btt_res = supabase.table("btt").select("*").eq("uo_id", user_uo_id).order("id", desc=True).execute()
            df_btt = pd.DataFrame(btt_res.data)
            
            if not df_btt.empty:
                st.dataframe(df_btt, use_container_width=True)
            else:
                st.info(f"Mbola tsy misy angona BTT ho an'ny UO {user_uo_id} aloha hatreto.")

        # 2. Ampiakatra Fichier Excel
        with sub_tab2:
            st.write("### 📤 Fampakarana Fichier Excel (Importation BTT)")
            st.caption(f"Ny angona mifanaraka amin'ny **UO = {user_uo_id}** ihany no ho ampiakarina.")
            
            uploaded_file = st.file_uploader("Fidio ny fichier Excel (.xlsx):", type=["xlsx", "xls"], key="excel_btt")
            
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file, sheet_name="BTT")
                    
                    # Clean column names for matching
                    df_upload.columns = df_upload.columns.astype(str).str.strip()

                    # Fampifanarahana ny anaran'ny column amin'ny Supabase
                    col_mapping = {
                        "UO_ID": "uo_id",
                        "Agent": "agent",
                        "UO": "uo",
                        "Année": "annee",
                        "Mois": "mois",
                        "N°_BTT": "num_btt",
                        "Lieu_dégagement (TG/TP; BFM;BP)": "lieu_degagement",
                        "Date_période_début": "date_periode_debut",
                        "Date_période_Fin": "date_periode_fin",
                        "Date_Dégagement": "date_degagement",
                        "Numéraire=Espèce (**12)": "numeraire_espece",
                        "Chèque (**22)": "cheque",
                        "Virement (*3)": "virement",
                        "BTT_Total": "btt_total",
                        "BTT_Cumul": "btt_cumul",
                        "OBSERVATION": "observation"
                    }
                    
                    df_upload = df_upload.rename(columns=col_mapping)

                    if "uo_id" not in df_upload.columns:
                        st.error("Tsy hita ilay columna 'UO_ID' na 'uo_id' ao anaty fichier Excel!")
                    else:
                        # Convert column UO_ID to string
                        df_upload["uo_id"] = df_upload["uo_id"].astype(str).str.strip()

                        # 1. Filtre par ID_UO
                        df_user_data = df_upload[df_upload["uo_id"] == user_uo_id].copy()

                        # CRITÈRE: Raha tsy misy donnée ho an'io ID_UO io
                        if df_user_data.empty:
                            st.warning(f"⚠️ Tsy misy ID_UO = {user_uo_id} sy UO ao anatin'ilay fichier emporté-na!")
                        else:
                            st.success(f"Hita ao anaty fichier: Android/Andalana {len(df_user_data)} mifanaraka amin'ny UO = {user_uo_id}")
                            st.dataframe(df_user_data.head(), use_container_width=True)

                            if st.button("🚀 Hanomboka ny Importation", key="btn_check_import"):
                                # Format Dates
                                for d_col in ["date_periode_debut", "date_periode_fin", "date_degagement"]:
                                    if d_col in df_user_data.columns:
                                        df_user_data[d_col] = pd.to_datetime(df_user_data[d_col], errors='coerce').dt.strftime('%Y-%m-%d')

                                df_user_data = df_user_data.where(pd.notnull(df_user_data), None)
                                records = df_user_data.to_dict(orient="records")

                                # 2. Check for Existing Data in Supabase (ID_UO, Année, Mois)
                                existing_criteria = []
                                conflicts_found = False

                                for r in records:
                                    annee_val = r.get("annee")
                                    mois_val = r.get("mois")

                                    if annee_val and mois_val:
                                        check_res = supabase.table("btt").select("id")\
                                            .eq("uo_id", user_uo_id)\
                                            .eq("annee", int(annee_val))\
                                            .eq("mois", str(mois_val))\
                                            .execute()
                                        
                                        if check_res.data and len(check_res.data) > 0:
                                            conflicts_found = True
                                            crit = {"annee": int(annee_val), "mois": str(mois_val)}
                                            if crit not in existing_criteria:
                                                existing_criteria.append(crit)

                                if conflicts_found:
                                    # Store pending state to prompt the user
                                    st.session_state["import_pending"] = {
                                        "records": records,
                                        "existing_criteria": existing_criteria
                                    }
                                else:
                                    # Pure Insert
                                    execute_btt_insert(records, user_uo_id, action="insert")

                except Exception as e:
                    st.error(f"Nisy olana teo am-pamakiana ilay fichier: {e}")

            # Modal / Prompts for Conflict Resolution
            if st.session_state.get("import_pending"):
                pending = st.session_state["import_pending"]
                st.write("---")
                st.warning("⚠️ **Efa misy angona mifanaraka amin'io ID_UO, Année, ary Mois io ao amin'ny Supabase:**")
                for c in pending["existing_criteria"]:
                    st.write(f"- **Année:** {c['annee']} | **Mois:** {c['mois']}")

                st.write("### Safidio ny zavatra tianao atao:")
                col_act1, col_act2 = st.columns(2)

                with col_act1:
                    if st.button("🔄 Hanao Mise à jour (Remplacer)"):
                        execute_btt_insert(
                            pending["records"], 
                            user_uo_id, 
                            action="update", 
                            existing_criteria=pending["existing_criteria"]
                        )

                with col_act2:
                    if st.button("🛡️ Tazomina ihany ny efa ao (Conserver)"):
                        st.session_state["import_pending"] = None
                        st.info("Nocancel-na ny importation. Nitazona ny angona efa teo aloha.")
                        st.rerun()

        # 3. Hampiditra An-tanana (Saisie)
        with sub_tab3:
            st.write("### ✍️ Formulaire Fampidirana BTT Vaovao")
            with st.form("form_btt_saisie"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    uo_id_in = st.text_input("UO ID", value=user_uo_id, disabled=True)
                    agent_in = st.text_input("Agent", value=user.get('nom', ''))
                    uo_in = st.text_input("Libellé UO")
                    annee_in = st.number_input("Année", value=2026, step=1)
                    mois_in = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])

                with col2:
                    num_btt_in = st.text_input("N° BTT")
                    lieu_in = st.text_input("Lieu de dégagement")
                    date_debut_in = st.date_input("Date période début", value=date.today())
                    date_fin_in = st.date_input("Date période fin", value=date.today())
                    date_deg_in = st.date_input("Date dégagement", value=date.today())

                with col3:
                    numeraire_in = st.number_input("Numéraire / Espèce", value=0.0)
                    cheque_in = st.number_input("Chèque", value=0.0)
                    virement_in = st.number_input("Virement", value=0.0)
                    observation_in = st.text_area("Observation")

                submit_btt = st.form_submit_button("Hampiditra (Enregistrer BTT)")

                if submit_btt:
                    btt_total_val = numeraire_in + cheque_in + virement_in
                    new_btt = {
                        "uo_id": user_uo_id,
                        "agent": agent_in,
                        "uo": uo_in,
                        "annee": int(annee_in),
                        "mois": mois_in,
                        "num_btt": num_btt_in,
                        "lieu_degagement": lieu_in,
                        "date_periode_debut": str(date_debut_in),
                        "date_periode_fin": str(date_fin_in),
                        "date_degagement": str(date_deg_in),
                        "numeraire_espece": numeraire_in,
                        "cheque": cheque_in,
                        "virement": virement_in,
                        "btt_total": btt_total_val,
                        "observation": observation_in
                    }
                    supabase.table("btt").insert(new_btt).execute()
                    st.success("Tafiditra soa aman-tsara ny BTT vaovao!")
                    st.rerun()

    # --- TAB UO ---
    with tab_uo:
        st.subheader("Tabilao UO (Unité Organisationnelle)")
        uo_response = supabase.table("uo").select("*").execute()
        df_uo = pd.DataFrame(uo_response.data)
        st.dataframe(df_uo, use_container_width=True)

    # --- TAB UTILISATEUR ---
    with tab_user:
        st.subheader("Tabilao UTILISATEUR")
        user_response = supabase.table("utilisateur").select("*").execute()
        df_user = pd.DataFrame(user_response.data)
        if "password" in df_user.columns:
            df_user = df_user.drop(columns=["password"])
        st.dataframe(df_user, use_container_width=True)

if not st.session_state["authenticated"]:
    login()
else:
    main_app()
