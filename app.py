import streamlit as st
import pandas as pd
from datetime import datetime
import io
import pypdf
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Manifeste Maritime - Extraction Propre (N/A)",
    page_icon="🚢",
    layout="wide"
)

# --- BLOC DE SÉCURITÉ ET D'AUTHENTIFICATION ---
def check_password():
    """Vérifie le mot de passe avant de donner accès à l'application."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Connexion Sécurisée")
        st.markdown("Veuillez saisir le mot de passe pour accéder à la plateforme de gestion du manifeste.")
        
        with st.form("login_form"):
            password_input = st.text_input("Mot de passe", type="password")
            submit_login = st.form_submit_button("Se connecter")
            
            if submit_login:
                if password_input == "Admin2026!":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect. Accès refusé.")
        return False
    return True

# --- FONCTION D'EXTRACTION AVEC RETOUR N/A SI ABSENT ---
def parse_manifest_with_na(pdf_file):
    """Analyse chaque page et met N/A si une information n'est pas trouvée."""
    extracted_rows = []
    
    try:
        reader = pypdf.PdfReader(pdf_file)
        total_pages = len(reader.pages)
        
        if total_pages == 0:
            return []

        # Parcourt chaque page du PDF une par une (jusqu'à 200 pages)
        for page_num in range(min(total_pages, 200)):
            page = reader.pages[page_num]
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            if not lines:
                lines = [f"Page {page_num + 1}"]

            # 1. Navire (N/A si introuvable)
            vessel = "N/A"
            vessel_match = re.search(r'(?:Vessel|Navire|Voyage)\s*[:\-]?\s*([A-Z0-9\s\-]+)', text, re.IGNORECASE)
            if vessel_match:
                vessel = vessel_match.group(1).strip()[:30]
            else:
                for l in lines[:5]:
                    l_up = l.upper()
                    if "GAMA" in l_up or "MAERSK" in l_up or "MSC" in l_up:
                        vessel = l[:30]
                        break

            # 2. Port de chargement (N/A si introuvable)
            loading_port = "N/A"
            port_match = re.search(r'(?:Port of Loading|Loading Port|POL|Port)\s*[:\-]?\s*([A-Za-z\s]+)', text, re.IGNORECASE)
            if port_match:
                loading_port = port_match.group(1).strip()[:25]
            else:
                ports_connus = ["ENNORE", "JEBEL ALI", "TUTICORIN", "GDANSK", "TUNIS", "MUNDRA", "ROTTERDAM", "NANSHA", "XINGANG", "CASABLANCA", "QINGDAO", "NINGBO", "SHENZHEN", "JAKARTA", "NAPLES", "NEWARK", "BUSAN", "SHEKOU"]
                for p in ports_connus:
                    if p in text.upper():
                        loading_port = p.title()
                        break

            # 3. Consignataire / Client (N/A si introuvable)
            consignee = "N/A"
            for l in lines:
                l_up = l.upper()
                if any(kw in l_up for kw in ["ETS", "SARL", " SA ", "GROUP", "COMPAGNIE", "ENTREPRISE", "DIALLO", "BARRY", "SOCIETE", "TOURE", "KONE", "MAMADOU", "AMADOU", "ALPHA", "COVAL", "AFRICA"]):
                    if len(l) > 3 and not "MANIFEST" in l_up and not "VESSEL" in l_up:
                        consignee = l[:40]
                        break

            # 4. Quantités de conteneurs 20' et 40' (0 ou N/A si absents)
            c_20 = 0
            c_40 = 0
            
            match_20 = re.search(r'\b(\d{1,2})\s*(?:20\s*[\'"]?\s*DV|20DV|20\s*FT|20\'GP|20)\b', text, re.IGNORECASE)
            if match_20:
                c_20 = int(match_20.group(1))
                
            match_40 = re.search(r'\b(\d{1,2})\s*(?:40\s*[\'"]?\s*HC|40HC|40\s*FT|40\'HQ|40)\b', text, re.IGNORECASE)
            if match_40:
                c_40 = int(match_40.group(1))

            teus = (c_20 * 1) + (c_40 * 2)

            # 5. Marchandise principale unique (N/A si introuvable)
            commodity = "N/A"
            for l in lines:
                l_up = l.upper()
                if any(kw in l_up for kw in ["MOTORCYCLE", "BAGS", "CARTONS", "CLOTHES", "TILES", "SPARE PARTS", "SHOES", "CIGARETTES", "DRUMS", "PALLETS", "FROZEN", "RICE", "SUGAR", "TEXTILES", "TEA", "CHICKEN", "GENERAL", "HOUSEGOODS"]):
                    commodity = l[:45]
                    break

            # 6. Trade et Catégorie
            trade = "N/A"
            text_up = text.upper()
            if "FAR EAST" in text_up or "NINGBO" in text_up or "NANSHA" in text_up or "QINGDAO" in text_up or "XINGANG" in text_up or "MAWEI" in text_up or "JAKARTA" in text_up or "BUSAN" in text_up or "SHEKOU" in text_up:
                trade = "21-FAR EAST"
            elif "EUROPE" in text_up or "GDANSK" in text_up or "ROTTERDAM" in text_up or "NAPLES" in text_up:
                trade = "04-NORTH EUROPE"
            elif "INDIA" in text_up or "ENNORE" in text_up or "MUNDRA" in text_up or "TUTICORIN" in text_up:
                trade = "14-INDIA & PAKISTAN"
            elif "USA" in text_up or "NEWARK" in text_up or "HOUSTON" in text_up:
                trade = "01-USA"
            elif "AFRICA" in text_up or "CASABLANCA" in text_up or "TUNIS" in text_up:
                trade = "17-NORTH AFRICA"

            category = "N/A"
            comm_up = commodity.upper()
            if "MOTORCYCLE" in comm_up:
                category = "Motorbike & Tricycles"
            elif "CLOTHES" in comm_up or "TISSUES" in comm_up or "SHOES" in comm_up:
                category = "Tissues,clothes & accesoires"
            elif "PARTS" in comm_up:
                category = "SPARE PARTS"
            elif "CIGARETTES" in comm_up:
                category = "cigarettes / Tobacco"
            elif "TILES" in comm_up:
                category = "Tiles & Ceramics"
            elif "FOOD" in comm_up or "CHICKEN" in comm_up:
                category = "Food-Meat-Poultry"
            elif "TEA" in comm_up:
                category = "Food - Tea / Coffee"
            elif "PLASTIC" in comm_up:
                category = "plastic stuffs"

            # Ligne maritime
            line_name = "MAERSK"
            if "MSC" in text_up:
                line_name = "MSC"
            elif "CMA CGM" in text_up:
                line_name = "CMA CGM"

            # Ajout de la ligne pour cette page
            extracted_rows.append({
                "MONTHS": "Jan-26",
                "Ligne": line_name,
                "VESSEL": vessel,
                "LOADING PORT": loading_port,
                "consignee": consignee,
                "COMMODITIES": commodity,
                "20'DV": c_20 if c_20 > 0 else "N/A",
                "40'HC": c_40 if c_40 > 0 else "N/A",
                "TEU's": teus if teus > 0 else "N/A",
                "Trade": trade,
                "Commodity-category": category,
                "Document_Source": f"{pdf_file.name} (Page {page_num + 1})"
            })

    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier : {e}")

    return extracted_rows

if check_password():
    with st.sidebar:
        st.write("👤 **Session Active**")
        st.info("📌 **Mode N/A Actif** : Les données absentes sont automatiquement signalées par N/A.")
        if st.button("🔴 Se déconnecter"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚢 Manifeste Maritime - Extraction Propre (N/A si vide)")
    st.markdown("Importez votre manifeste PDF : chaque page génère sa ligne et affiche N/A en l'absence de données.")

    if "manifeste_df" not in st.session_state:
        st.session_state.manifeste_df = pd.DataFrame(columns=[
            "MONTHS", "Ligne", "VESSEL", "LOADING PORT", "consignee", 
            "COMMODITIES", "20'DV", "40'HC", "TEU's", "Trade", "Commodity-category", "Document_Source"
        ])

    tab1, tab2, tab3 = st.tabs(["📄 Import & Validation", "📊 Rapports Mensuels", "📁 Base de Données / Export"])

    # --- ONGLET 1 : IMPORTATION ET VALIDATION ---
    with tab1:
        st.header("1. Chargement et Traitement du PDF")
        
        uploaded_pdf = st.file_uploader(
            "Glissez-déposez votre manifeste PDF (jusqu'à 200 pages)", 
            type=["pdf"]
        )

        preview_data = []
        if uploaded_pdf is not None:
            with st.spinner("🔍 Analyse de toutes les pages du document..."):
                preview_data = parse_manifest_with_na(uploaded_pdf)
                st.success(f"✨ Succès ! **{len(preview_data)} lignes** générées.")

        if preview_data:
            st.subheader("Aperçu du Tableau :")
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)

            if st.button("💾 Valider et Enregistrer dans le Manifeste Global"):
                st.session_state.manifeste_df = pd.concat(
                    [st.session_state.manifeste_df, preview_df], 
                    ignore_index=True
                )
                st.balloons()
                st.success("Toutes les lignes ont été ajoutées avec succès !")

    # --- ONGLET 2 : RAPPORTS MENSUELS ---
    with tab2:
        st.header("📊 Rapports Mensuels & Statistiques")
        
        df = st.session_state.manifeste_df
        
        if df.empty:
            st.warning("Aucune donnée disponible. Importez un document dans le premier onglet.")
        else:
            # Conversion sécurisée pour les calculs métriques
            numeric_teus = pd.to_numeric(df["TEU's"], errors='coerce').fillna(0)
            numeric_20 = pd.to_numeric(df["20'DV"], errors='coerce').fillna(0)
            numeric_40 = pd.to_numeric(df["40'HC"], errors='coerce').fillna(0)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total TEU's", int(numeric_teus.sum()))
            col2.metric("Total 20'DV", int(numeric_20.sum()))
            col3.metric("Total 40'HC", int(numeric_40.sum()))
            col4.metric("Nombre d'expéditions", len(df))
            
            st.markdown("---")
            
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("Volume TEUs par Ligne Maritime")
                trade_chart = df.groupby("Ligne")[df["TEU's"].apply(lambda x: pd.to_numeric(x, errors='coerce')).name].sum() if "TEU's" in df else pd.Series()
                st.bar_chart(numeric_teus)
                
            with g2:
                st.subheader("Répartition par Trade")
                trade_summary = df.groupby("Trade").size()
                st.bar_chart(trade_summary)
                
            st.subheader("Top Consignataires (Consignees)")
            top_consignees = df.groupby("consignee").size().reset_index(name="Nombre").sort_values(by="Nombre", ascending=False)
            st.dataframe(top_consignees, use_container_width=True)

    # --- ONGLET 3 : EXPORT EXCEL ---
    with tab3:
        st.header("📁 Base de Données du Manifeste & Export Excel")
        
        st.dataframe(st.session_state.manifeste_df, use_container_width=True)
        
        if not st.session_state.manifeste_df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.manifeste_df.to_excel(writer, sheet_name='Manifest', index=False)
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Télécharger le Manifeste en Excel (.xlsx)",
                data=processed_data,
                file_name=f"MANIFESTE_EXPORT_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
