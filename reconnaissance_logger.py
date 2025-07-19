import cv2
import face_recognition
import numpy as np
import csv
import sqlite3
from datetime import datetime
import os
import time
import threading  # Pour la gestion des threads
import pygame  # Pour l'alarme sonore
from threading import Thread

# Initialiser pygame pour le son
pygame.mixer.init()

def generate_beep_sound():
    # Créer un son court (0.3 secondes) à 1000 Hz en stéréo
    sample_rate = 44100
    duration = 0.3  # secondes
    frequency = 1000  # Hz
    
    # Générer les échantillons mono
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * frequency * t) * 0.5  # Volume à 50%
    
    # Convertir en stéréo (2 canaux)
    stereo_samples = np.column_stack((tone, tone))
    
    # Convertir en format 16-bit
    samples = (stereo_samples * 32767).astype(np.int16)
    
    # Créer le son
    sound = pygame.sndarray.make_sound(samples)
    return sound

alarm_sound = generate_beep_sound()

# Chemin absolu vers le fichier des signatures
script_dir = os.path.dirname(os.path.abspath(__file__))
chemin = os.path.join(script_dir, 'SignaturesAll.npy')

# Vérifier si le fichier existe
if not os.path.exists(chemin):
    # Essayer un autre emplacement si le fichier n'est pas trouvé
    autre_chemin = os.path.abspath(os.path.join(script_dir, '..', 'SignaturesAll.npy'))
    if os.path.exists(autre_chemin):
        chemin = autre_chemin
    else:
        raise FileNotFoundError(f"Fichier SignaturesAll.npy introuvable. J'ai cherché ici :\n1. {chemin}\n2. {autre_chemin}")

try:
    signature_nom = np.load(chemin)
except Exception as e:
    raise Exception(f"Erreur lors du chargement du fichier {chemin}: {str(e)}")

# Séparer caractéristiques et noms
signature = signature_nom[:, :-1].astype('float')
noms = signature_nom[:, -1]

# Initialisation de la base de données
def init_db():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect('surveillance.db')
    c = conn.cursor()
    
    # Création de la table des détections si elle n'existe pas
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
    conn.commit()
    return conn

# Initialiser la base de données
db = init_db()

def save_detection(nom, type_detection, image=None):
    """Enregistre une détection dans la base de données"""
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    heure = now.strftime("%H:%M:%S")
    image_path = None
    
    if image is not None:
        # Créer le dossier 'detection_images' s'il n'existe pas
        os.makedirs('detection_images', exist_ok=True)
        image_path = f'detection_images/detection_{now.strftime("%Y%m%d_%H%M%S")}.jpg'
        cv2.imwrite(image_path, image)
    
    c = db.cursor()
    c.execute('''
        INSERT INTO detections (nom, type_detection, date, heure, image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (nom, type_detection, date, heure, image_path))
    db.commit()

# Configuration de la capture vidéo
def init_camera():
    # Essayer différents backends et paramètres
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_ANY, "Any available backend")
    ]
    
    for backend, name in backends:
        try:
            print(f"Tentative d'ouverture de la caméra avec {name}...")
            cap = cv2.VideoCapture(backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Vérifier si la caméra est ouverte
            if cap.isOpened():
                print(f"Caméra ouverte avec succès en utilisant {name}")
                return cap
            else:
                print(f"Échec de l'ouverture avec {name}")
                cap.release()
        except Exception as e:
            print(f"Erreur avec {name}: {str(e)}")
    
    # Si aucun backend ne fonctionne, essayer avec l'index 0
    print("Tentative avec le backend par défaut...")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        return cap
    
    raise RuntimeError("Impossible d'ouvrir la caméra avec aucun des backends disponibles")

# Initialiser la caméra
capture = None
try:
    capture = init_camera()
    # Donner un peu de temps à la caméra pour s'initialiser
    time.sleep(2)
except Exception as e:
    print(f"Erreur critique lors de l'initialisation de la caméra: {e}")
    exit(1)

while True:
    reponse, image = capture.read()

    if reponse:
        # Reducción de tamaño y conversión de color
        image_reduite = cv2.resize(image, (0, 0), None, 0.25, 0.25)
        image_RGB = cv2.cvtColor(image_reduite, cv2.COLOR_BGR2RGB)

        # Localización y codificación de rostros
        emplacement_face = face_recognition.face_locations(image_RGB)
        carac_face = face_recognition.face_encodings(image_RGB, emplacement_face)

        for encode, loc in zip(carac_face, emplacement_face):
            
            tab = face_recognition.compare_faces(signature, encode)
            distance_face = face_recognition.face_distance(signature, encode)
            minDist = np.argmax(distance_face)  
            
            # Conserver le calcul de la distance minimale pour les fonctionnalités avancées
            minDistance = np.min(distance_face) if len(distance_face) > 0 else 1.0
            
            # Seuils pour les fonctionnalités avancées
            TOLERANCE = 0.5
            MATCH_THRESHOLD = 0.4
            
            y1, x2, y2, x1 = loc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4

          
            if tab[minDist] == True:
                nom = noms[minDist]
                # Calculer la confiance pour l'affichage
                confidence = (1 - minDistance) * 100
                type_detection = f'Reconnu ({confidence:.1f}%)'
                
                # Réinitialiser le compteur d'alertes si une personne reconnue
                if hasattr(threading, '_alarm_triggered'):
                    threading._alarm_triggered = False
                color = (0, 255, 0)  # Vert pour une reconnaissance valide
            else:
                # Si la distance est trop grande, considérer comme inconnu
                nom = 'Inconnu'
                confidence = (1 - minDistance) * 100
                # Afficher la meilleure correspondance même pour les inconnus
                if len(distance_face) > 0:
                    best_match = np.argmin(distance_face)
                    type_detection = f'Inconnu (ressemble à {noms[best_match]} à {confidence:.1f}%)'
                else:
                    type_detection = 'Inconnu'
                
                # Ne déclencher l'alarme que pour les visages avec une certaine qualité de détection
                if minDistance < 0.7:  # Seuil plus permissif pour l'alarme
                    type_detection = 'Alerte: Intrus détecté!'
                    
                    # Vérifier si une alerte est déjà en cours
                    if not hasattr(threading, '_alarm_playing'):
                        threading._alarm_playing = False
                    
                    # Déclencher l'alarme si pas déjà en cours de lecture
                    if not threading._alarm_playing:
                        threading._alarm_playing = True
                        
                        # Démarrer l'alarme dans un thread séparé
                        def play_alarm():
                            try:
                                for _ in range(3):  # 3 bips d'alarme
                                    alarm_sound.play()
                                    time.sleep(0.4)  # Délai entre les bips
                            finally:
                                # Réinitialiser l'état de l'alarme une fois terminée
                                threading._alarm_playing = False
                        
                        alarm_thread = Thread(target=play_alarm)
                        alarm_thread.daemon = True
                        alarm_thread.start()
                
                color = (0, 0, 255)  # Rouge pour les inconnus

            # Changer la couleur en fonction du type de détection
            color = (0, 255, 0)  # Vert par défaut (reconnu)
            if type_detection.startswith('Alerte'):
                color = (0, 0, 255)  # Rouge pour les inconnus
                
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            cv2.rectangle(image, (x1, y2 - 20), (x2, y2), color, cv2.FILLED)
            cv2.putText(image, f"{nom} - {type_detection}", (x1 + 6, y2 - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

            # Enregistrer la détection dans la base de données
            save_detection(nom, type_detection, image[y1:y2, x1:x2])

        cv2.imshow('Capture', image)
        if cv2.waitKey(1) == ord('q'):
            break
    else:
        break

capture.release()
cv2.destroyAllWindows()
