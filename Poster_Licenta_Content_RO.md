# Poster Licenta - Continut Pregatit (1 slide)

## Date autor
- **Student:** [Nume Prenume]
- **Coordonator:** [Titlu, Nume Prenume]
- **Lucrare:** *PyVisionAnnotator - Platforma de adnotare imagini asistata de AI cu colaborare realtime*

---

## 1) Enuntul problemei (context + motivatie)
Adnotarea dataset-urilor vizuale este consumatoare de timp, predispusa la inconsistente intre adnotatori si dificil de sincronizat in echipe distribuite. Instrumentele clasice separa adesea adnotarea locala de colaborarea online, ceea ce creste costul operational si timpul de iteratie.

**Problema cercetata:** cum poate fi realizata o aplicatie unica ce combina adnotare manuala precisa, asistare AI (segmentare automata) si colaborare realtime, pastrand in acelasi timp performanta, claritatea UX si integrarea usoara in fluxuri de ML.

---

## 2) Obiectiv principal si obiective secundare
### Obiectiv principal
Dezvoltarea unui sistem complet de adnotare vizuala, cu functionalitati locale si colaborative, care accelereaza crearea de date etichetate pentru Computer Vision.

### Obiective secundare
- Implementarea uneltelor de adnotare `Rect`, `Poly`, `Mask` cu editare intuitiva.
- Integrarea modelelor AI externe pentru segmentare asistata:
  - `mask2former.py` (point query pentru segment la un punct selectat).
  - `yoloe.py` (detectie + segmentare multi-clasa).
- Integrarea unui asistent LLM in aplicatie pentru intrebari despre functionalitati, fluxuri de lucru si setari.
- Export/import in formate uzuale (`JSON`, `COCO`, `YOLO`).
- Suport colaborativ realtime (REST + WebSocket/STOMP) cu autentificare JWT.
- Robustete in executia proceselor externe (timeout, validare cai, parsare JSON toleranta la loguri).

---

## 3) Solutia propusa
- Dezvoltarea unei platforme unificate de adnotare care combina lucru manual, asistare AI si colaborare realtime.
- Integrarea modelelor `mask2former.py` (segmentare la punct) si `yoloe.py` (detectie + segmentare multi-clasa) pentru accelerarea etichetarii.
- Sincronizarea adnotarilor intre utilizatori prin evenimente WebSocket, cu control de versiune pe sesiune.
- Suport contextual prin asistent LLM integrat, pentru intrebari despre functionalitati si utilizarea aplicatiei.

**Ideea cheie:** un flux "human-in-the-loop" in care utilizatorul valideaza rezultatele AI, iar sistemul reduce timpul de adnotare fara a sacrifica controlul.

---

## 4) Arhitectura conceptuala / tehnica
### Frontend/Desktop
- `PyVisionAnnotator`: aplicatie desktop in `Python` + `PyQt6` pentru adnotare (canvas + sidebar + setari persistente).
- Include integrare WebSocket/chat si asistent LLM (`Ollama`) pentru suport rapid in aplicatie.

### AI local (subprocess)
- Executie asincrona a inferentei prin `mask2former.py` si `yoloe.py`.
- Pipeline `Python` (`transformers`, `ultralytics`, `torch`) cu conversie in adnotari editabile.

### Backend colaborativ (microservicii)
- Arhitectura cu microservicii `Java` + `Spring Boot` (`auth`, `chat`, `annotation`) in spatele `Traefik`.
- Comunicatie `REST` + `WebSocket/STOMP`, mesagerie `RabbitMQ`, persistenta auth in `PostgreSQL`, orchestrare `Docker Compose`.

---

## 5) Metoda / Solutia propusa
1. Incarcare imagine si adnotare manuala pe canvas.
2. Optional, asistare AI:
   - click punct + `mask2former.py` -> segmentul obiectului, coordonate, bbox;
   - selectie etichete + `yoloe.py` -> detectii multiple cu scor + segment/bbox.
3. Asistare conversationala prin LLM pentru ghidare rapida in utilizarea aplicatiei.
4. Post-procesare geometrica si integrare in model intern de adnotare.
5. Salvare/export dataset (`JSON`, `COCO`, `YOLO`).
6. In mod colaborativ, sincronizare prin WS cu control de versiune pe sesiune si deduplicare de evenimente.

**Intrare:** imagini si configuratii de model.

**Iesire:** adnotari structurale (rect/poly/mask), exportabile pentru antrenare ML.

---

## 6) Date (model de date / set de date)
### Date structurate
- `auth-service` / `PostgreSQL`: utilizatori, roluri, credentiale hash-uite, token-uri si metadata de sesiune.
- Date colaborative: metadate sesiune/proiect/imagine, versiuni si evenimente sincronizate (`REST`/`WebSocket`).

### Date nestructurate / semi-structurate
- Intrari nestructurate: imagini multi-format (`JPG`, `PNG`, `BMP`, `TIFF`, `WEBP`).
- Adnotari semi-structurate: `rect` (bbox), `poly` (puncte), `mask` (compactata `bitset_v1` + `zlib` + `base64`), cu serializare/export in `JSON`, `COCO`, `YOLO`.
- Seturi de lucru: imagini locale de test (ex. `sample/cat_dog`) + imagini incarcate in sesiuni colaborative.

---

## 7) Evaluare (metrici, cazuri de test, validare)
### Metrici
- Timp mediu de adnotare / imagine (manual vs asistat AI).
- Consistenta adnotarilor (intra/inter-annotator).
- Latenta colaborativa (emitere eveniment -> randare client remote).
- Succes export/import (`JSON`, `COCO`, `YOLO`) fara pierderi.

### Cazuri + validare
- Teste pe obiecte simple si contururi complexe, inclusiv sesiuni multi-utilizator.
- Verificare rezilienta la reconectare, evenimente WS duplicate/stale, timeout/cancel AI.
- Validare comparativa: fara AI vs cu AI, plus flux end-to-end (adnotare -> sincronizare -> export).

---

## 8) Rezultate asteptate
- Reducerea timpului de etichetare prin asistare AI.
- Productivitate mai mare in echipe prin colaborare realtime.
- Suport rapid in aplicatie prin asistentul LLM.
- Interoperabilitate cu pipeline-uri ML prin export standardizat.
- Baza extensibila pentru persistenta sesiunilor si integrarea de modele noi.

---

## 9) Contributii si fezabilitate
### Contributii
- Integrare unificata: adnotare manuala + inferenta AI + colaborare realtime.
- Design practic pentru fluxuri de lucru CV, cu focus pe UX si robustete.
- Arhitectura modulara (desktop + microservicii) usor de extins.

### Fezabilitate
- Functionalitati implementate in proiectul curent (conform modulelor existente).
- Stack tehnologic matur: Python + modele CV, Spring Boot, Docker Compose, Traefik, RabbitMQ, PostgreSQL.

### Riscuri + plan de rezerva
- Latenta sau caderi in servicii colaborative -> fallback local + snapshot recovery.
- Cost computational AI pe CPU -> configurare device (`cuda/cpu`) si praguri de inferenta.

---

## 10) Intrebari clasice (pregatire aparare)
- De ce problema este non-triviala?
- Care este diferenta fata de lucrari/tool-uri existente?
- De ce aceasta alegere de algoritmi/modele?
- Ce alternative au fost evaluate?
- Ce metrici demonstreaza succesul?
- Ce limitari are MVP-ul si ce pasi urmeaza?

---

## 11) Script scurt pentru prezentare (4 minute)
- **0:00 - 0:40** Problema + motivatie.
- **0:40 - 1:20** Obiective si contributii.
- **1:20 - 2:20** Arhitectura sistemului (desktop + backend colaborativ).
- **2:20 - 3:10** Metoda si fluxul AI (Mask2Former / YOLOE).
- **3:10 - 3:40** Evaluare si rezultate asteptate.
- **3:40 - 4:00** Concluzie + directii viitoare.

---

## 12) Cuvinte cheie (footer poster)
`Computer Vision` · `Image Annotation` · `AI-assisted Labeling` · `Realtime Collaboration` · `WebSocket` · `Dataset Export` · `YOLOE` · `Mask2Former`

---

## 13) Checklist predare
- [ ] Poster final intr-un singur slide (`PDF` / `PPT` / `DOCX`).
- [ ] Include nume student + coordonator.
- [ ] Structura completa (problema, obiective, metoda, date, evaluare, rezultate).
- [ ] Incarcat in Teams cu cel putin 1 zi inainte.
- [ ] Repetitie prezentare in limita de `4 min` + `1 min` intrebari.
