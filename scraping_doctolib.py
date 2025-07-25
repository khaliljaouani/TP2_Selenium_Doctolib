import argparse
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# =============================
# 1. Gestion des arguments CLI
# =============================
def get_args():
    parser = argparse.ArgumentParser(description="Scraping Doctolib avec Selenium")
    parser.add_argument('--max', type=int, default=10, help='Nombre de résultats maximum à afficher')
    parser.add_argument('--date_debut', type=str, required=True, help='Date de début (JJ/MM/AAAA)')
    parser.add_argument('--date_fin', type=str, required=True, help='Date de fin (JJ/MM/AAAA)')
    parser.add_argument('--requete', type=str, required=True, help='Requête médicale (ex: dermatologue)')
    parser.add_argument('--secteur', type=str, choices=['1', '2', 'non conventionné'], help='Type d’assurance')
    parser.add_argument('--consultation', type=str, choices=['visio', 'sur place'], help='Type de consultation')
    parser.add_argument('--prix_min', type=int, help='Prix minimum (€)')
    parser.add_argument('--prix_max', type=int, help='Prix maximum (€)')
    parser.add_argument('--adresse', type=str, help='Mot-clé dans l’adresse (ex: 75015, Boulogne)')
    parser.add_argument('--exclure', type=str, nargs='*', help='Zones à exclure (liste de mots-clés)')
    return parser.parse_args()

# =============================
# 2. Initialisation Selenium
# =============================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    # options.add_argument('--headless')  # Décommente si tu veux sans interface graphique
    driver = webdriver.Chrome(options=options)
    return driver

# =============================
# 3. Recherche sur Doctolib
# =============================
def recherche_doctolib(driver, args):
    # Aller sur la page d'accueil de Doctolib
    driver.get("https://www.doctolib.fr/")
    wait = WebDriverWait(driver, 10)

    # Gérer le pop-up cookies si présent
    try:
        # Essaye de cliquer sur "Tout refuser" si présent
        bouton_refuser = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Refuser')]"))
        )
        bouton_refuser.click()
        time.sleep(1)
    except:
        try:
            # Sinon, essaye de cliquer sur "Tout accepter"
            bouton_accepter = driver.find_element(By.XPATH, "//button[contains(., 'Accepter')]")
            bouton_accepter.click()
            time.sleep(1)
        except:
            pass  # Aucun pop-up cookies visible

    # Remplir la barre de recherche de spécialité
    champ_recherche = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchbar-input.searchbar-query-input"))
    )
    champ_recherche.clear()
    champ_recherche.send_keys(args.requete)
    time.sleep(1)  # Laisser l'autocomplétion apparaître
    champ_recherche.send_keys("\n")  # Valider la spécialité
    time.sleep(1)

    # Remplir le champ de localisation si fourni
    if args.adresse:
        champ_lieu = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchbar-input.searchbar-place-input"))
        )
        champ_lieu.clear()
        champ_lieu.send_keys(args.adresse)
        time.sleep(1)
        champ_lieu.send_keys("\n")  # Valider l'adresse
        time.sleep(1)

    # Cliquer sur le bouton de recherche si besoin
    bouton_recherche = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.searchbar-submit-button"))
    )
    bouton_recherche.click()
    time.sleep(3)  # Laisser la page de résultats charger

# =============================
# 4. Extraction des résultats
# =============================
def extraire_medecins(driver, args):
    medecins = []
    blocs = driver.find_elements(By.CSS_SELECTOR, "div.dl-card.dl-card-bg-white.dl-card-variant-default.dl-card-border")
    for bloc in blocs[:args.max]:
        try:
            nom = bloc.find_element(By.CSS_SELECTOR, "h2.dl-text.dl-text-body.dl-text-bold.dl-text-s.dl-text-primary-110").text
        except:
            nom = ""
        try:
            specialite = bloc.find_element(By.CSS_SELECTOR, "div.flex > p").text
        except:
            specialite = ""
        try:
            rue = bloc.find_element(By.CSS_SELECTOR, "p.p8ZDI8v1UHoMdXI35XEt").text
        except:
            rue = ""
        try:
            cp_ville = bloc.find_elements(By.CSS_SELECTOR, "div.flex.flex-wrap.gap-x-4 > p")[1].text
            code_postal, ville = cp_ville.split(' ', 1)
        except:
            code_postal, ville = "", ""
        # Extraction du secteur
        try:
            secteur = ""
            p_tags = bloc.find_elements(By.CSS_SELECTOR, "p.p8ZDI8v1UHoMdXI35XEt")
            for p in p_tags:
                if "secteur" in p.text.lower():
                    secteur = p.text
        except:
            secteur = ""
        # Extraction de la prochaine disponibilité (plus robuste)
        try:
            dispo = ""
            spans = bloc.find_elements(By.CSS_SELECTOR, "div[data-test-id='availabilities-container'] span")
            for s in spans:
                txt = s.text.strip()
                if txt and any(mois in txt.lower() for mois in ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]):
                    dispo = txt
                    break
        except:
            dispo = ""
        medecins.append({
            'Nom': nom,
            'Prochaine disponibilité': dispo,
            'Type de consultation': "",  # à compléter
            'Secteur': secteur,
            'Prix': "",                  # à compléter
            'Adresse': rue,
            'Code postal': code_postal,
            'Ville': ville
        })
    return medecins

# =============================
# 5. Génération du CSV
# =============================
def generer_csv(liste_medecins, nom_fichier="resultats_doctolib.csv"):
    champs = [
        'Nom', 'Prochaine disponibilité', 'Type de consultation', 'Secteur',
        'Prix', 'Adresse', 'Code postal', 'Ville'
    ]
    with open(nom_fichier, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        for med in liste_medecins:
            writer.writerow(med)
    print(f"CSV généré : {nom_fichier}")

# =============================
# 6. Main
# =============================
def main():
    args = get_args()
    driver = init_driver()
    try:
        recherche_doctolib(driver, args)
        medecins = extraire_medecins(driver, args)
        generer_csv(medecins)
        input("Appuie sur Entrée pour fermer la fenêtre Chrome...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 