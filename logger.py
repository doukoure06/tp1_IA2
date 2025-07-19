import csv
from datetime import datetime
import os

# Ruta del archivo de detección
FICHIER_CSV = "data/detections.csv"

def enregistrer_detection(nom):
    """Agrega una nueva detección al archivo CSV"""
    date = datetime.now().date()
    heure = datetime.now().time().strftime("%H:%M:%S")

    ligne = [nom, str(date), heure]

    # Crear archivo si no existe, con encabezados
    if not os.path.exists(FICHIER_CSV) or os.stat(FICHIER_CSV).st_size == 0:
        with open(FICHIER_CSV, mode="w", newline='', encoding="utf-8") as fichier:
            writer = csv.writer(fichier)
            writer.writerow(["Nom", "Date", "Heure"])
            writer.writerow(ligne)
    else:
        with open(FICHIER_CSV, mode="a", newline='', encoding="utf-8") as fichier:
            writer = csv.writer(fichier)
            writer.writerow(ligne)
