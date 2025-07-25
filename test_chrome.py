from selenium import webdriver

# Ouvre une fenêtre Chrome et va sur Google
try:
    driver = webdriver.Chrome()
    driver.get("https://www.google.com")
    input("Appuie sur Entrée pour fermer le navigateur...")
finally:
    driver.quit() 