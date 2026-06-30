# TOOL COLABORATIV SEMI-AUTOMAT DE ADNOTARE

Plan si prompt pentru prezentare PPTX de 5 minute.

Student: Grigoras Victor-Andrei  
Tema: PyVisionAnnotator - tool colaborativ semi-automat de adnotare

---

## Timeline 5 minute

- 0:00-0:40 - Introducere / problema
- 0:40-1:20 - Studiu bibliografic scurt
- 1:20-2:00 - Obiective
- 2:00-3:20 - Solutia propusa si arhitectura
- 3:20-4:20 - Evaluare
- 4:20-5:00 - Concluzii si thank you

---

## Slide 1 - Introducere / problema

### Mesaj pe slide
- Adnotarea imaginilor este necesara pentru dataset-uri de Computer Vision.
- Procesul este lent, repetitiv si sensibil la erori intre adnotatori.
- In practica, adnotarea manuala, asistenta AI si colaborarea sunt adesea separate.
- Proiectul propune un flux unic: utilizatorul lucreaza manual, primeste sugestii AI si poate colabora realtime.

### Mini-script
Incep de la problema principala: ca sa antrenam sau sa evaluam modele de Computer Vision, avem nevoie de date etichetate bine.  
Dar adnotarea este consumatoare de timp, mai ales cand obiectele au contururi complexe.  
In plus, daca mai multi oameni lucreaza pe acelasi set de imagini, apar probleme de sincronizare si consistenta.  
De aici vine ideea proiectului: un tool care combina adnotarea manuala, asistenta AI si colaborarea intr-un singur flux.

---

## Slide 2 - Studiu bibliografic scurt, mai casual

### Mesaj pe slide
- CVAT este un reper modern pentru adnotare, colaborare si export dataset.
- LabelMe este un reper clasic pentru adnotare online si contururi/poligoane.
- Mask2Former arata directia moderna pentru segmentare universala.
- YOLOE este relevant pentru detectie open-vocabulary si propuneri vizuale rapide.
- Ideea proiectului: pastram controlul uman, dar adaugam automatizare acolo unde chiar economiseste timp.

### Mini-script
Ca puncte de comparatie, am pornit de la tool-uri cunoscute.  
CVAT este foarte puternic pentru proiecte de adnotare si colaborare. LabelMe este mai clasic, dar ramane un reper pentru adnotarea online.  
Pe partea de modele, Mask2Former este relevant pentru segmentare, iar YOLOE este interesant pentru detectii flexibile, inclusiv pe clase descrise mai liber.  
Proiectul meu nu incearca sa inlocuiasca aceste directii, ci sa combine cateva idei utile intr-un tool desktop controlat de utilizator.

---

## Slide 3 - Obiective

### Mesaj pe slide
- Adnotare manuala: dreptunghiuri, poligoane si masti.
- Asistenta AI: AutoSeg pentru detectii/contururi, AutoMask pentru masti.
- Colaborare: autentificare, sesiuni comune, chat si sincronizare live.
- Export dataset: formate utile pentru fluxuri ML, precum JSON, COCO si YOLO.

### Mini-script
Obiectivul principal a fost sa construiesc o aplicatie completa pentru adnotare vizuala.  
Primul obiectiv a fost partea manuala: utilizatorul trebuie sa poata desena si corecta adnotari.  
Al doilea obiectiv a fost asistenta AI, dar intr-un mod human-in-the-loop: AI-ul propune, utilizatorul valideaza.  
Al treilea obiectiv a fost colaborarea, iar ultimul a fost exportul intr-o forma utila pentru pipeline-uri de Machine Learning.

---

## Slide 4 - Solutia propusa

### Mesaj pe slide
- PyVisionAnnotator este o aplicatie desktop pentru adnotare imagini.
- Canvas central pentru desenare si editare.
- Panouri pentru imagini, proprietati, clase, unelte si setari.
- AutoSeg foloseste YOLOE pentru detectii si contururi/poligoane.
- AutoMask foloseste Mask2Former pentru generarea de masti.
- Utilizatorul pastreaza controlul asupra rezultatului final.

### Mini-script
Solutia propusa este PyVisionAnnotator, o aplicatie desktop construita in jurul unui canvas de adnotare.  
Utilizatorul poate lucra manual cu bounding box-uri, poligoane si masti, iar apoi poate folosi AI-ul ca accelerare.  
Este important de mentionat ca in proiect YOLOE nu este tratat ca generator direct de masti editabile. El este folosit pentru detectii si contururi care devin poligoane.  
Pentru masti editabile, fluxul AutoMask foloseste Mask2Former pornind de la un punct selectat de utilizator.

---

## Slide 5 - Arhitectura

### Mesaj pe slide
- Frontend desktop: Python + PyQt, canvas, toolbar, panouri si setari persistente.
- Worker-e locale: operatii lente mutate in fundal, fara blocarea interfetei.
- AI local: YOLOE pentru AutoSeg, Mask2Former pentru AutoMask, chatbot local prin Ollama / llama.cpp.
- Backend colaborativ: Spring Boot, servicii pentru auth, chat si annotation.
- Comunicare: REST + WebSocket/STOMP, RabbitMQ, PostgreSQL, Docker Compose.
- Include aici figura de arhitectura generala.

### Mini-script
Arhitectura este impartita in trei zone.  
Prima este aplicatia desktop, facuta in Python si PyQt, unde utilizatorul interactioneaza efectiv cu imaginile.  
A doua zona este partea de worker-e si AI local. Aici ruleaza procesele externe, astfel incat interfata sa ramana responsiva.  
A treia zona este backend-ul colaborativ, bazat pe servicii Spring Boot. El gestioneaza autentificarea, chatul si sincronizarea adnotarilor prin WebSocket/STOMP.

---

## Slide 6 - Evaluare

### Mesaj pe slide
- Clientul a fost validat prin scenarii manuale in interfata.
- Backend-ul are teste JUnit pentru servicii si scenarii de integrare.
- Endpoint-urile au fost verificate si cu Postman.
- Fluxuri testate: autentificare, chat, colaborare, AutoSeg, AutoMask, export.
- Criterii urmarite: corectitudine, sincronizare, robustete si export fara pierderi.

### Mini-script
Evaluarea a combinat mai multe tipuri de verificare.  
Pentru client, multe lucruri tin de interactiuni vizuale, deci am folosit scenarii manuale: desenare, selectie, editare, setari si export.  
Pentru backend, validarea este mai tehnica: exista teste JUnit pentru servicii, scenarii de integrare si verificari prin Postman pentru endpoint-uri.  
Am urmarit ca autentificarea, chatul, sincronizarea si exportul sa functioneze coerent end-to-end.

---

## Slide 7 - Concluzii / Thank you

### Mesaj pe slide
- Proiectul combina adnotare manuala, asistenta AI si colaborare realtime.
- Fluxul ramane human-in-the-loop: utilizatorul decide rezultatul final.
- Arhitectura este modulara si permite integrarea de modele noi.
- Exportul face rezultatele utile pentru dataset-uri si antrenare ML.
- Thank you.

### Mini-script
In concluzie, proiectul trateaza o problema practica din pregatirea dataset-urilor vizuale.  
Contributia principala este integrarea intr-un singur tool a adnotarii manuale, asistentei AI si colaborarii.  
AI-ul nu inlocuieste utilizatorul, ci reduce timpul pentru pasii repetitivi.  
Pe viitor, aplicatia poate fi extinsa cu modele noi, persistenta mai avansata pentru proiecte si evaluari comparative mai detaliate.  
Thank you.

---

## Prompt pentru generare PPTX

Genereaza o prezentare PowerPoint in limba romana pentru o sustinere de licenta de 5 minute.

Titlul prezentarii este:
TOOL COLABORATIV SEMI-AUTOMAT DE ADNOTARE

Context:
Proiectul se numeste PyVisionAnnotator si este o aplicatie desktop pentru adnotarea imaginilor. Combina adnotarea manuala, asistenta AI, colaborarea realtime, chatul si exportul dataset-urilor. Tonul trebuie sa fie clar, academic, dar natural, nu prea incarcat si nu prea rigid.

Constrangeri:
- Maximum 7 slide-uri.
- Durata totala: 5 minute.
- Bullets scurte, usor de prezentat.
- Design curat, academic, cu mult spatiu liber.
- Include spatiu vizual pentru o figura de arhitectura pe slide-ul de arhitectura.
- Nu transforma prezentarea intr-un poster aglomerat.
- Nu spune ca YOLOE returneaza direct masti editabile in proiect.
- Mentioneaza corect: YOLOE este folosit pentru detectii si contururi/poligoane in AutoSeg; Mask2Former este folosit pentru generarea de masti in AutoMask.

Structura slide-uri:
1. Introducere / problema
   - Adnotarea imaginilor este lenta si repetitiva.
   - Colaborarea si asistenta AI sunt adesea separate de adnotarea manuala.
   - Scopul proiectului este un flux unic pentru adnotare, AI si colaborare.

2. Studiu bibliografic scurt
   - CVAT ca reper modern pentru adnotare si colaborare.
   - LabelMe ca reper clasic pentru adnotare online.
   - Mask2Former ca model relevant pentru segmentare.
   - YOLOE ca model relevant pentru detectii open-vocabulary si propuneri vizuale.
   - Ton casual-academic: "am pornit de la aceste repere si am construit o solutie adaptata proiectului".

3. Obiective
   - Adnotare manuala: box, poligon, masca.
   - Asistenta AI: AutoSeg si AutoMask.
   - Colaborare: sesiuni, chat, sincronizare live.
   - Export dataset: JSON, COCO, YOLO.

4. Solutia propusa
   - PyVisionAnnotator ca aplicatie desktop.
   - Canvas si panouri pentru editare.
   - AutoSeg cu YOLOE pentru detectii/contururi.
   - AutoMask cu Mask2Former pentru masti.
   - Flux human-in-the-loop.

5. Arhitectura
   - Frontend: Python + PyQt.
   - Worker-e: procese externe si operatii asincrone.
   - Backend: Spring Boot, auth, chat, annotation.
   - Comunicare: REST + WebSocket/STOMP.
   - Infrastructura: RabbitMQ, PostgreSQL, Docker Compose.
   - Include placeholder pentru figura de arhitectura.

6. Evaluare
   - Testare manuala pentru clientul PyQt.
   - Teste JUnit pentru serviciile Spring Boot.
   - Scenarii de integrare.
   - Verificari Postman pentru endpoint-uri.
   - Testare export/import si flux colaborativ.

7. Concluzii
   - Sistemul unifica adnotarea manuala, AI-ul si colaborarea.
   - Utilizatorul ramane in control.
   - Arhitectura este modulara si extensibila.
   - Rezultatele pot fi exportate pentru pipeline-uri ML.
   - Inchide cu "Thank you".

Adauga pentru fiecare slide speaker notes de 30-50 de secunde, cu fraze naturale, potrivite pentru o prezentare de licenta.
