# Plan capitol 6: Testare si validare

Obiectiv: capitolul trebuie sa demonstreze ca aplicatia implementata functioneaza ca sistem complet, nu doar ca suma de module separate. Testarea trebuie sa acopere clientul desktop `AnnotationEngine`, serviciile backend din `ColaborativeServer`, integrarea modelelor externe, colaborarea in timp real si exportul datelor obtinute.

Recomandare generala: capitolul sa fie scris practic, pe scenarii reale de utilizare. Nu este nevoie de teorie lunga despre testare software; accentul trebuie sa cada pe ce s-a validat in proiect, ce rezultate au fost obtinute si ce limitari raman. Capitolul poate avea aproximativ 10-14 pagini, in functie de numarul de tabele si screenshot-uri incluse.

## 6.1. Obiectivele testarii si metodologia

Tinta: 1 pagina.

Rolul sectiunii este sa explice ce inseamna "validare" pentru acest proiect: verificarea faptului ca utilizatorul poate adnota imagini, poate folosi modele externe, poate salva/exporta rezultatele si poate colabora cu alti utilizatori prin backend.

Continut recomandat:

- prezinta obiectivele principale ale testarii:
  - validarea functionalitatilor clientului desktop;
  - verificarea comunicarii dintre client si backend;
  - validarea fluxurilor asistate de AI prin AutoSeg si AutoMask;
  - verificarea colaborarii in timp real si a sincronizarii adnotarilor;
  - compararea calitativa cu alte instrumente de adnotare;
- separa clar tipurile de testare:
  - testare functionala manuala pentru interfata PyQt;
  - teste automate JUnit pentru servicii backend;
  - testare de integrare pentru REST, WebSocket/STOMP si RabbitMQ;
  - validare calitativa prin comparatie cu tool-uri similare;
- explica faptul ca nu se masoara performanta modelului YOLOE sau Mask2Former ca cercetare AI separata, ci integrarea lor in fluxul aplicatiei.

Tabel recomandat: **Tabel 6.1 - Tipuri de testare utilizate**

Coloane:

| Tip testare | Componenta vizata | Scop | Mod de validare |
| --- | --- | --- | --- |
| Functionala manuala | AnnotationEngine | Verificarea fluxurilor UI | Scenarii executate in aplicatie |
| Integrare backend | Auth, chat, annotation | Verificarea comunicarii intre servicii | REST/STOMP + teste automate |
| AI integration | AutoSeg, AutoMask | Verificarea contractului input/output | Rulare worker + inspectare rezultat |
| Colaborare | Client + annotation-service | Sincronizare multi-user | Doua instante de client |
| Comparatie calitativa | Tool-uri existente | Pozitionarea contributiei | Tabel comparativ |

## 6.2. Mediul de testare

Tinta: 1 pagina.

Sectiunea trebuie sa descrie mediul folosit pentru rularea aplicatiei si pentru verificarea fluxurilor principale. Nu trebuie transformata intr-un manual de instalare; detaliile pas cu pas pot ramane pentru capitolul de instalare/utilizare.

Continut recomandat:

- sistem local Windows, cu proiectul rulat din workspace-ul de dezvoltare;
- client desktop `AnnotationEngine`, pornit din `app.py`;
- backend `ColaborativeServer`, compus din:
  - `auth-service`;
  - `chat-service`;
  - `annotation-service`;
  - `reverse-proxy` Traefik;
  - RabbitMQ;
  - Postgres pentru autentificare;
- modele externe apelate de client:
  - AutoSeg, prin script/executabil extern cu output JSON;
  - AutoMask, prin script/executabil extern cu output JSON;
  - LLM local, prin Ollama sau llama.cpp;
- mentioneaza ca pentru chat si colaborare se folosesc token-uri JWT obtinute prin autentificare.

Comenzi utile de mentionat in text sau intr-un tabel:

```bash
docker compose up -d
```

```bash
python app.py
```

```bash
mvn test
```

Tabel recomandat: **Tabel 6.2 - Componente rulate in mediul de testare**

Coloane:

| Componenta | Rol in testare | Observatii |
| --- | --- | --- |
| AnnotationEngine | Client desktop | Interfata de adnotare si colaborare |
| auth-service | Autentificare | Register, login, validate JWT |
| chat-service | Chat si prezenta | STOMP, mesaje private, istoric |
| annotation-service | Sesiuni colaborative | Snapshot, evenimente, chunking |
| RabbitMQ | Evenimente intre servicii | Sincronizare utilizatori |
| Postgres | Persistenta auth | Utilizatori si roluri |

## 6.3. Testarea clientului desktop

Tinta: 2-3 pagini.

Scop: demonstrarea faptului ca utilizatorul poate parcurge fluxul principal de adnotare fara backend si fara modele externe obligatorii.

Continut recomandat:

- testarea incarcarii unui folder de imagini:
  - selectare folder;
  - popularea listei de imagini;
  - selectarea unei imagini;
  - afisarea imaginii in canvas;
- testarea uneltelor de adnotare:
  - creare bounding box;
  - creare polygon;
  - creare mask;
  - selectare, editare si stergere adnotare;
- testarea panoului de proprietati:
  - schimbare label;
  - schimbare culoare/opacitate;
  - verificarea listei de adnotari;
- testarea setarilor vizuale:
  - brightness;
  - contrast;
  - gamma;
  - crosshair;
- testarea salvarii si exportului:
  - salvare JSON local;
  - reincarcare JSON;
  - export YOLO;
  - export COCO;
  - salvare imagine cu masti;
- testarea protectiei la modificari nesalvate:
  - modificare adnotare;
  - selectare alta imagine;
  - verificare optiuni Save / Discard / Cancel.

Tabel recomandat: **Tabel 6.3 - Scenarii de testare pentru clientul desktop**

Coloane:

| ID | Scenariu | Pasi | Rezultat asteptat | Rezultat obtinut |
| --- | --- | --- | --- | --- |
| TC-UI-01 | Incarcare imagine | Selectare folder si imagine | Imaginea apare in canvas | Validat |
| TC-UI-02 | Creare bbox | Selectare tool si drag pe canvas | Apare o adnotare bbox editabila | Validat |
| TC-UI-03 | Creare polygon | Click-uri succesive pe canvas | Apare un polygon inchis | Validat |
| TC-UI-04 | Salvare JSON | Salvare fisier local | Adnotarile sunt serializate | Validat |
| TC-UI-05 | Modificari nesalvate | Schimbare imagine dupa editare | Aplicatia cere confirmare | Validat |

Figuri recomandate:

1. **Figura 6.1 - Validarea incarcarii unei imagini in clientul desktop**
   - screenshot cu lista de imagini, canvas si panou de proprietati;
   - poate reutiliza sau adapta screenshot-ul folosit in capitolul 5, daca se mentioneaza explicit ca aici este folosit pentru validare.

2. **Figura 6.2 - Exemplu de adnotari create manual**
   - screenshot cu bbox, polygon si mask pe aceeasi imagine.

## 6.4. Testarea fluxurilor AutoSeg si AutoMask

Tinta: 2 pagini.

Scop: validarea integrarii modelelor externe in aplicatie. Sectiunea nu trebuie sa repete arhitectura YOLOE sau Mask2Former din capitolul de analiza; aici conteaza daca worker-ele pornesc, daca primesc parametri corecti si daca outputul devine adnotare editabila.

### AutoSeg

Continut recomandat:

- utilizatorul apasa butonul AutoSeg;
- se deschide dialogul de rulare;
- se selecteaza label-urile, pragul de incredere, modul de rulare si device-ul;
- `AutoSegWorker` porneste procesul extern;
- procesul extern returneaza JSON;
- clientul transforma rezultatul in `BoundingBoxItem`, `PolygonItem` sau `MaskItem`, in functie de campurile existente.

Contract de output asteptat:

```json
[
  {
    "label": "car",
    "confidence": 0.87,
    "box": [120.0, 80.0, 340.0, 250.0],
    "coordinates": [[130.0, 90.0], [330.0, 95.0], [320.0, 240.0]]
  }
]
```

Criterii de validare:

- procesul extern porneste fara blocarea interfetei;
- outputul JSON este valid;
- campul `box` produce o adnotare de tip bounding box;
- campul `coordinates` produce o adnotare de tip polygon sau mask, in functie de handler;
- adnotarea rezultata poate fi selectata, editata si salvata.

### AutoMask

Continut recomandat:

- utilizatorul selecteaza unealta AutoMask;
- utilizatorul face click pe imagine;
- coordonata punctului este transmisa catre worker;
- `AutoMaskWorker` ruleaza procesul extern;
- outputul contine lista de coordonate pentru masca;
- clientul transforma coordonatele in `MaskItem`.

Contract de output asteptat:

```json
{
  "label": "car",
  "id": 12,
  "point_queried": [180, 140],
  "coordinates": [[130, 90], [131, 90], [132, 91]],
  "bbox": [120, 80, 340, 250]
}
```

Criterii de validare:

- click-ul pe canvas este preluat corect;
- coordonatele sunt transmise in spatiul imaginii;
- outputul include cheia `coordinates`;
- masca este randata pe canvas;
- masca poate fi editata cu brush/eraser si exportata.

Figura recomandata: **Figura 6.3 - Validarea fluxului AutoSeg/AutoMask**

Poza poate contine fie doua capturi separate, fie o captura in care se vede rezultatul unei segmentari automate pe canvas.

## 6.5. Testarea backend-ului

Tinta: 2-3 pagini.

Scop: verificarea serviciilor backend atat separat, cat si in fluxul folosit de clientul desktop.

### Autentificare

Scenarii recomandate:

- register cu utilizator nou;
- register cu email deja existent;
- login cu date corecte;
- login cu parola gresita;
- validate JWT dupa autentificare;
- logout si stergerea token-ului local din client.

Endpoint-uri de mentionat:

```text
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/validate
```

### Chat

Scenarii recomandate:

- conectare STOMP cu token valid;
- trimitere mesaj privat;
- primire mesaj in `/user/queue/private`;
- cerere istoric;
- actualizare prezenta.

Endpoint-uri si destinatii de mentionat:

```text
/app/chat.send
/app/chat.history
/app/chat.presence
/user/queue/private
/user/queue/history
/user/queue/presence
```

### Colaborare

Scenarii recomandate:

- creare sesiune;
- listare sesiuni;
- join la sesiune existenta;
- cerere snapshot;
- trimitere eveniment de adnotare;
- primire eveniment pe topicul sesiunii;
- upload temporar imagine;
- descarcare imagine temporara de catre alt client.

Endpoint-uri si destinatii de mentionat:

```text
/annotation/sessions
/annotation/sessions/{sessionId}/snapshot
/annotation/media/upload-temp
/annotation/ws
/app/collab.event
/topic/sessions/{sessionId}
```

Tabel recomandat: **Tabel 6.4 - Scenarii de testare pentru backend**

Coloane:

| ID | Serviciu | Scenariu | Rezultat asteptat | Tip test |
| --- | --- | --- | --- | --- |
| TC-BE-01 | auth-service | Register utilizator nou | Utilizator creat si JWT emis | Automat/manual |
| TC-BE-02 | auth-service | Login invalid | Raspuns 401 | Automat/manual |
| TC-BE-03 | chat-service | Trimitere mesaj | Mesaj primit pe coada privata | Integrare |
| TC-BE-04 | annotation-service | Creare sesiune | Sesiune listata si accesibila | Integrare |
| TC-BE-05 | annotation-service | Snapshot | Starea sesiunii este returnata | Integrare |

## 6.6. Testarea colaborarii si a trimiterii in N pachete

Tinta: 2 pagini.

Scop: validarea celui mai important flux distribuit: mai multi clienti lucreaza pe aceeasi imagine si vad aceleasi modificari.

Scenariu principal:

- se pornesc doua instante ale clientului desktop;
- ambii utilizatori se autentifica;
- primul utilizator creeaza o sesiune colaborativa;
- imaginea activa este incarcata temporar pe server;
- al doilea utilizator se alatura sesiunii;
- al doilea client descarca imaginea temporara si cere snapshot-ul sesiunii;
- primul utilizator creeaza o adnotare;
- al doilea utilizator primeste evenimentul live;
- al doilea utilizator modifica adnotarea;
- primul utilizator vede modificarea.

Validarea payload-urilor mici:

- pentru bbox si polygon simple, evenimentul se trimite direct;
- serverul versionaza evenimentul;
- evenimentul este publicat catre topicul sesiunii;
- clientii il aplica local fara sa il retrimita.

Validarea trimiterii in N pachete:

- pentru masti sau payload-uri mari, clientul serializeaza evenimentul initial;
- payload-ul este encodat base64;
- datele sunt impartite in bucati;
- fiecare bucata este transmisa ca `annotation.chunk`;
- serverul reasambleaza pachetele dupa `chunkId`, `sessionId`, `index`, `total` si `originalType`;
- la final serverul emite `annotation.chunk.ack`;
- in caz de eroare, serverul emite `annotation.chunk.error`;
- clientul poate reincerca trimiterea de maximum doua ori.

Payload de mentionat:

```json
{
  "chunkId": "chunk_001",
  "sessionId": "sess_01",
  "index": 0,
  "total": 3,
  "originalType": "annotation.update",
  "encoding": "base64-json",
  "data": "..."
}
```

Figura recomandata: **Figura 6.4 - Validarea colaborarii si a trimiterii in pachete**

Diagrama ar trebui sa arate:

```text
Client A -> annotation.chunk -> annotation-service
Client A <- annotation.chunk.ack <- annotation-service
annotation-service -> eveniment reasamblat -> Client B
```

## 6.7. Teste automate existente

Tinta: 1-2 pagini.

Scop: prezentarea testelor automate deja existente in backend si a zonelor pe care acestea le acopera. Trebuie mentionat clar ca partea desktop este validata in principal manual, in timp ce backend-ul are teste automate JUnit.

Teste existente de mentionat:

- `auth_module`:
  - `UserServiceTest`;
  - `AuthServiceApplicationTests`;
- `chat_module`:
  - `ChatServiceTest`;
  - teste de incarcare context Spring;
- `annotation_module`:
  - `SessionsApiIT`;
  - `AnnotationSyncIT`;
  - `MediaEventsIT`;
  - `CollaborationServiceRoomLifecycleTest`;
  - `CollaborationServiceMaskPointsTest`;
  - `AnnotationChunkAssemblyServiceTest`.

Tabel recomandat: **Tabel 6.5 - Teste automate disponibile in backend**

Coloane:

| Modul | Test | Functionalitate verificata | Observatii |
| --- | --- | --- | --- |
| auth_module | UserServiceTest | Register, login, credentiale invalide | Teste de serviciu |
| chat_module | ChatServiceTest | Mesaje, istoric, validari | Teste de serviciu |
| annotation_module | SessionsApiIT | API sesiuni | Test de integrare |
| annotation_module | AnnotationSyncIT | Evenimente WebSocket | Test de integrare |
| annotation_module | MediaEventsIT | Upload imagine si `image.available` | Test de integrare |
| annotation_module | AnnotationChunkAssemblyServiceTest | Reasamblare pachete | Test unitar |

Comenzi de rulare:

```bash
cd ColaborativeServer/auth_module
mvn test
```

```bash
cd ColaborativeServer/chat_module
mvn test
```

```bash
cd ColaborativeServer/annotation_module
mvn test
```

Observatie importanta: daca in capitol se includ rezultate concrete, acestea trebuie rulate inainte si trecute in tabel cu status real: trecut, esuat sau neexecutat.

## 6.8. Compararea cu alte instrumente de adnotare

Tinta: 2-3 pagini.

Acesta trebuie sa fie un subcapitol separat. Scopul nu este sa se declare ca aplicatia este "mai buna" decat toate tool-urile existente, ci sa se pozitioneze contributia proiectului in raport cu directiile observate in literatura si in instrumentele studiate in `conspecte/Contributii/Conspecte.md`.

Tool-uri reprezentative de comparat:

- LabelMe: instrument online clasic pentru adnotare de imagini;
- CVAT-BWV: platforma web pentru adnotare video, orientata pe body-worn video;
- Annotation Web: tool web pentru imagini medicale cu ultrasunete;
- BRIMA: tool browser-only, cu instalare minima;
- V-RSIR: platforma web pentru remote sensing image retrieval;
- SegBuilder: tool semi-automat pentru segmentare;
- PiPo-Net: metoda semi-automata polygon-based pentru imagini patologice;
- AI-Enhanced Annotation Tool for Aneurysm Medical Image Labeling: exemplu de tool medical asistat de AI;
- A Cost-Effective, Fast, and Robust Annotation Tool: exemplu de adnotare semi-automata pentru imagini/video.

Atentie: intrarea `Lymphocyte Annotator` din `Conspecte.md` trebuie verificata inainte de folosire, deoarece textul pare duplicat din sectiunea LabelMe. Pana la corectare, nu trebuie folosita ca sursa principala in tabelul comparativ.

Criterii de comparatie:

- tip aplicatie: web, desktop, browser-only, pipeline experimental;
- tipuri de adnotari: bbox, polygon, mask, landmarks, clasificare;
- asistenta AI: inexistenta, semi-automata, model dedicat, model generalist;
- colaborare: individuala, colaborare web, sesiuni multi-user;
- export dataset: JSON, COCO, YOLO sau format specific;
- domeniu tinta: general, medical, remote sensing, video, pathology;
- instalare: locala, web hosted, Docker, browser-only;
- extensibilitate: modele externe, plugin-uri, backend modular.

Tabel recomandat: **Tabel 6.6 - Comparatie intre PyVisionAnnotator si alte instrumente de adnotare**

Coloane:

| Tool | Tip | Adnotari | AI-assisted | Colaborare | Export | Observatii |
| --- | --- | --- | --- | --- | --- | --- |
| PyVisionAnnotator | Desktop + backend | BBox, polygon, mask | Da, prin worker-e externe | Da, STOMP/WebSocket | JSON, YOLO, COCO | Integrare locala + colaborativa |
| LabelMe | Web | Polygon, obiecte | Nu in varianta clasica | Limitata | Dataset specific | Tool clasic, online |
| CVAT-BWV | Web | Video/object annotation | Partial, in functie de extensii | Da | Formate dataset | Orientat pe video |
| Annotation Web | Web medical | BBox, segmentare, landmarks | Nu ca element central | Posibil prin platforma | Date medicale | Ultrasunete |
| BRIMA | Browser-only | Image annotation | Nu ca element central | Nu accent principal | Export dataset | Instalare minima |
| V-RSIR | Web | Etichetare imagini satelitare | Nu ca element central | Da, voluntari/inspectori | Dataset RSIR | Remote sensing |
| SegBuilder | Semi-automat | Segmentare | Da | Nu accent principal | Segmentari | Focus pe segmentare |
| PiPo-Net | Semi-automat | Polygon | Da | Nu accent principal | Date patologice | Focus medical |

Concluzie recomandata pentru subcapitol:

- aplicatia dezvoltata combina mai multe directii care apar separat in tool-urile studiate:
  - client desktop pentru control local;
  - exporturi utile pentru dataset-uri;
  - asistenta AI prin procese externe interschimbabile;
  - backend colaborativ;
  - sincronizare in timp real;
  - suport pentru adnotari mari prin chunking;
- contributia nu este un model AI nou, ci integrarea acestor componente intr-un flux coerent de adnotare.

## 6.9. Limitari si validare finala

Tinta: 1 pagina.

Sectiunea trebuie sa inchida capitolul printr-o concluzie sincera: sistemul este functional si validat pe scenarii reprezentative, dar exista limitari naturale pentru un proiect de licenta.

Limitari de mentionat:

- testarea clientului desktop este in principal manuala;
- nu exista benchmark extins pentru viteza pe dataset-uri foarte mari;
- performanta AutoSeg/AutoMask depinde de modelul extern configurat;
- colaborarea a fost validata pe scenarii locale/controlate, nu pe un numar mare de utilizatori simultani;
- persistenta colaborarii este in memorie, deci nu inlocuieste un sistem complet de productie;
- comparatia cu alte tool-uri este calitativa, pe baza functionalitatilor si a literaturii, nu o evaluare experimentala directa.

Validare finala:

- utilizatorul poate adnota manual;
- utilizatorul poate folosi AutoSeg si AutoMask;
- rezultatele pot fi editate si exportate;
- utilizatorul se poate autentifica;
- chatul si colaborarea functioneaza prin backend;
- evenimentele mari pot fi transmise in pachete;
- sistemul este comparabil functional cu tool-uri existente, dar aduce o combinatie proprie de client desktop, backend colaborativ si worker-e AI externe.

## Figuri si tabele recomandate

Figuri:

1. **Figura 6.1 - Validarea incarcarii unei imagini in clientul desktop**
2. **Figura 6.2 - Exemplu de adnotari create manual**
3. **Figura 6.3 - Validarea fluxului AutoSeg/AutoMask**
4. **Figura 6.4 - Validarea colaborarii si a trimiterii in pachete**
5. **Figura 6.5 - Fluxul complet de validare end-to-end**

Tabele:

1. **Tabel 6.1 - Tipuri de testare utilizate**
2. **Tabel 6.2 - Componente rulate in mediul de testare**
3. **Tabel 6.3 - Scenarii de testare pentru clientul desktop**
4. **Tabel 6.4 - Scenarii de testare pentru backend**
5. **Tabel 6.5 - Teste automate disponibile in backend**
6. **Tabel 6.6 - Comparatie intre PyVisionAnnotator si alte instrumente de adnotare**

## Ordine recomandata pentru scriere

1. Inlocuieste placeholder-ul din `templateLaTeX-Rom-2026/chapters/testare_validare.tex` cu introducerea capitolului.
2. Scrie 6.1 si 6.2 ca fundatie scurta.
3. Scrie 6.3 si 6.4 pe baza clientului desktop si a fluxurilor AI.
4. Scrie 6.5 si 6.6 pe baza backend-ului si a colaborarii.
5. Adauga 6.7 cu testele automate existente.
6. Scrie 6.8 folosind `conspecte/Contributii/Conspecte.md` si tabelul comparativ.
7. Inchide cu 6.9 si cu o concluzie de validare.

## Test plan pentru implementarea capitolului in LaTeX

- verifica faptul ca `testare_validare.tex` compileaza dupa inlocuirea placeholder-ului;
- verifica toate referintele la figuri si tabele;
- verifica daca figurile folosite apar si in anexa cu provenienta corecta;
- ruleaza sau mentioneaza explicit statusul testelor JUnit folosite in capitol;
- nu introduce rezultate numerice daca nu au fost masurate;
- nu folosi `Lymphocyte Annotator` ca sursa comparativa pana cand conspectul nu este corectat;
- pastreaza comparatia cu alte tool-uri la nivel calitativ, nu ca benchmark experimental.
