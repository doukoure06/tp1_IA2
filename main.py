import subprocess
import sys
import os
import time
import webbrowser

def run_streamlit_app(script_name, port):
    """Lance une application Streamlit dans un sous-processus"""
    cmd = [sys.executable, "-m", "streamlit", "run", script_name, "--server.port", str(port)]
    subprocess.Popen(cmd, shell=True)
    webbrowser.open_new_tab(f"http://localhost:{port}")

def main():
    print("Démarrage des applications...")
    
    # Chemins des scripts (dans le même dossier)
    dashboard_script = 'dashboard.py'
    reco_script = 'reconnaissance_logger.py'
    
    # Vérifier que les fichiers existent
    if not os.path.exists(dashboard_script):
        print(f"Erreur: Impossible de trouver {dashboard_script}")
        return
    if not os.path.exists(reco_script):
        print(f"Erreur: Impossible de trouver {reco_script}")
        return
    
    # Lancer les applications sur des ports différents
    print("1. Démarrage du tableau de bord sur http://localhost:8501")
    run_streamlit_app(dashboard_script, 8501)
    
    # Petit délai pour laisser le temps au premier serveur de démarrer
    time.sleep(2)
    
    print("2. Démarrage de la reconnaissance faciale sur http://localhost:8502")
    run_streamlit_app(reco_script, 8502)
    
    print("\nLes applications ont été lancées avec succès!")
    print("- Tableau de bord: http://localhost:8501")
    print("- Reconnaissance faciale: http://localhost:8502")
    print("\nAppuyez sur Ctrl+C pour arrêter les applications.")
    
    try:
        # Garder le script en cours d'exécution
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt des applications...")

if __name__ == "__main__":
    main()
