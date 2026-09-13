# Pordenone Rebel Feed

Aggregatore web responsive per i comunicati (post) e i prossimi eventi di:
- **Iniziativa Libertaria - Pordenone**
- **Circolo Zapata / Amici Zapatisti**

## Caratteristiche
- **Backend**: FastAPI + SQLite (`data/database.db`) con REST API.
- **Frontend**: Interfaccia moderna responsive con Tailwind CSS e Alpine.js.
- **Scraping Agent**: Script Playwright per estrarre e sincronizzare automaticamente post ed eventi da Facebook.
- **Loghi Ufficiali**: Avatar ad alta risoluzione integrati nell'interfaccia.
- **Deploy**: Pronto per Render.com tramite Dockerfile e `render.yaml`.

## Deploy su Render
1. Accedi a [dashboard.render.com](https://dashboard.render.com) tramite GitHub.
2. Clicca su **New +** -> **Blueprint** e seleziona questo repository (`strasp-cyber/pordenone-rebel-feed`).
3. Clicca su **Apply**: Render compilerà ed eseguirà l'applicazione gratuitamente.
