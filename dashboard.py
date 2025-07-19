import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import sqlite3

# Configuration de la page (doit être la première commande Streamlit)
st.set_page_config(
    page_title="Tableau de Bord Personnel",
    layout="wide"
)

# ---------- CONFIGURATION DE LA BASE DE DONNÉES ----------
def init_db():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect('surveillance.db')
    c = conn.cursor()
    
    # Création de la table des utilisateurs
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Création de la table des détections
    c.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type_detection TEXT NOT NULL,
            date TEXT NOT NULL,
            heure TEXT NOT NULL,
            image_path TEXT
        )
    ''')
    
    # Créer un utilisateur admin par défaut si aucun utilisateur n'existe
    c.execute("SELECT * FROM users")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin")
        )
    
    conn.commit()
    return conn

# Initialiser la base de données
db = init_db()

# ---------- AUTHENTIFICATION ----------
def check_login():
    """Vérifie les identifiants de l'utilisateur"""
    st.sidebar.title("🔒 Authentification")
    
    # Formulaire de connexion
    with st.sidebar.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit_button = st.form_submit_button("Se connecter")
    
    if submit_button:
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        
        if user:
            st.session_state['logged_in'] = True
            st.session_state['username'] = user[1]
            st.session_state['role'] = user[3]
            st.sidebar.success(f"Connecté en tant que {username}")
            st.experimental_rerun()
        else:
            st.sidebar.error("Identifiants invalides")
    
    return st.session_state.get('logged_in', False)

# ---------- FONCTIONS UTILITAIRES ----------
def get_detections():
    """Récupère les détections depuis la base de données"""
    try:
        # Rafraîchir la connexion à la base de données
        db = sqlite3.connect('surveillance.db')
        query = """
        SELECT 
            id, nom, type_detection, 
            date, heure, image_path
        FROM detections
        ORDER BY date DESC, heure DESC
        """
        df = pd.read_sql_query(query, db)
        db.close()
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return pd.DataFrame()

def save_detection(nom, type_detection, image=None):
    """Enregistre une nouvelle détection"""
    now = datetime.now()
    date = now.strftime('%Y-%m-%d')
    heure = now.strftime('%H:%M:%S')
    
    # Sauvegarder l'image si fournie
    image_path = None
    if image is not None:
        os.makedirs('detection_images', exist_ok=True)
        image_path = f"detection_images/{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(image_path, image)
    
    # Insérer dans la base de données
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO detections 
        (nom, type_detection, date, heure, image_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (nom, type_detection, date, heure, image_path)
    )
    db.commit()

# ---------- DASHBOARD ----------
@st.cache_data(ttl=5)  # Mise en cache pour 5 secondes
def load_data():
    return get_detections()

def afficher_dashboard():
    st.title("Tableau de Bord Personnel")
    
    # Charger les données avec mise en cache
    df = load_data()
    
    # Afficher des informations de débogage
    with st.expander("Débogage - Afficher les données brutes"):
        st.write("Données chargées:", df)
        st.write("Dernière mise à jour:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Charger les données
    df = get_detections()
    
    if df.empty:
        st.warning("Aucune donnée de détection disponible.")
        return
    
    # Filtres dans la barre latérale
    st.sidebar.header("Filtres")
    
    # Filtre par date
    min_date = pd.to_datetime(df['date']).min().date()
    max_date = pd.to_datetime(df['date']).max().date()
    
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtre par type de détection
    types_detection = ["Tous"] + sorted(df["type_detection"].unique().tolist())
    selected_type = st.sidebar.selectbox("Type de détection", types_detection)
    
    # Filtre par nom
    noms = ["Tous"] + sorted(df["nom"].unique().tolist())
    selected_nom = st.sidebar.selectbox("Personne", noms)
    
    # Appliquer les filtres
    if len(date_range) == 2:
        df_filtered = df[
            (pd.to_datetime(df['date']).dt.date >= date_range[0]) & 
            (pd.to_datetime(df['date']).dt.date <= date_range[1])
        ]
    else:
        df_filtered = df.copy()
    
    if selected_type != "Tous":
        df_filtered = df_filtered[df_filtered["type_detection"] == selected_type]
    
    if selected_nom != "Tous":
        df_filtered = df_filtered[df_filtered["nom"] == selected_nom]
    
    # Afficher les indicateurs clés de sécurité
    col1, col2, col3, col4 = st.columns(4)
    
    # Détections d'intrus
    df_intrus = df_filtered[df_filtered["nom"] == "Inconnu"]
    
    with col1:
        total_intrus = len(df_intrus)
        st.metric("Intrus détectés", 
                 total_intrus,
                 help="Nombre total d'intrus détectés")
    
    with col2:
        intrus_aujourdhui = len(df_intrus[
            pd.to_datetime(df_intrus['date']).dt.date == pd.Timestamp.today().date()
        ])
        st.metric("Intrus aujourd'hui", 
                 intrus_aujourdhui,
                 help="Nombre d'intrus détectés aujourd'hui")
    
    with col3:
        try:
            derniere_detection = pd.to_datetime(df_intrus['date'] + ' ' + df_intrus['heure']).max()
            derniere_detection_str = derniere_detection.strftime('%d/%m %H:%M')
        except:
            derniere_detection_str = "Aucune détection"
            
        st.metric("Dernier intrus", 
                 derniere_detection_str,
                 help="Dernière détection d'un intrus")
    
    with col4:
        # Calculer le nombre d'intrus ce mois-ci
        mois_courant = pd.Timestamp.today().month
        intrus_mois = len(df_intrus[
            pd.to_datetime(df_intrus['date']).dt.month == mois_courant
        ])
        st.metric(
            "Intrus ce mois",
            intrus_mois,
            help="Nombre d'intrus détectés ce mois-ci"
        )
    
    # Graphique d'activité personnalisé
    st.subheader("Activité récente")
    if not df_filtered.empty:
        # Préparer les données pour l'utilisateur actuel
        df_user = df_filtered[df_filtered["nom"] == "Utilisateur"]
        df_daily = df_user.groupby('date').size().reset_index(name='count')
        
        # Créer un graphique d'activité
        fig = px.bar(
            df_daily, 
            x='date', 
            y='count',
            labels={'date': 'Date', 'count': 'Nombre de visites'},
            title='Vos visites par jour',
            color_discrete_sequence=['#4e79a7']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='lightgray')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Graphique des détections par personne
    st.subheader(" Détections par personne")
    if not df_filtered.empty:
        df_person = df_filtered['nom'].value_counts().reset_index()
        df_person.columns = ['Personne', 'Nombre de détections']
        
        fig = px.bar(
            df_person,
            x='Personne',
            y='Nombre de détections',
            color='Personne',
            title='Nombre de détections par personne'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tableau des détections
    st.subheader(" Historique des détections")
    
    # Options d'affichage
    col1, col2 = st.columns([3, 1])
    with col2:
        page_size = st.selectbox("Lignes par page", [10, 25, 50, 100])
    
    # Pagination
    if not df_filtered.empty:
        total_pages = (len(df_filtered) // page_size) + (1 if len(df_filtered) % page_size > 0 else 0)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Afficher le tableau paginé
        st.dataframe(
            df_filtered.iloc[start_idx:end_idx].reset_index(drop=True),
            column_config={
                "image_path": st.column_config.ImageColumn("Image", help="Image de la détection")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Afficher les informations de pagination
        st.caption(f"Page {page} sur {total_pages} | {len(df_filtered)} détections au total")
    
    # Bouton d'export
    if st.button(" Exporter les données"):
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name=f'detections_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv'
        )

# ---------- EXÉCUTION ----------
if check_login():
    afficher_dashboard()
