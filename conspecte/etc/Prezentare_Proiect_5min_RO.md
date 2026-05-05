# Prezentare proiect - 5 minute (puncte de vorbire)

## 0:00 - 0:40 | Problema si motivatia
- Adnotarea imaginilor este lenta, repetitiva si adesea inconsistenta intre adnotatori.
- In practica, tool-urile pentru lucru local si colaborare online sunt separate.
- Asta creste timpul de iteratie pentru dataset-uri de Computer Vision.

## 0:40 - 1:20 | Obiectivul lucrarii
- Scop: o platforma unica pentru adnotare manuala + asistare AI + colaborare realtime.
- Rezultat urmarit: mai putin timp pe imagine, dar cu control uman pastrat.
- Abordare: flux human-in-the-loop, unde utilizatorul valideaza propunerile AI.

## 1:20 - 2:10 | Solutia propusa (ce am construit)
- Aplicatia desktop `PyVisionAnnotator` pentru lucrul pe canvas (`Rect`, `Poly`, `Mask`).
- Asistare AI locala prin scripturi externe:
  - `mask2former.py`: punct -> segmentul obiectului + bbox.
  - `yoloe.py`: detectii multi-clasa cu scor + segment/bbox.
- Export in formate uzuale: `JSON`, `COCO`, `YOLO`.
- Modul Chatbot integrat cu asistent LLM pentru intrebari despre aplicatie.

## 2:10 - 3:10 | Arhitectura tehnica (in ce e facut)
- Frontend/Desktop: `Python` + `PyQt6` (UI, canvas, setari persistente).
- AI local: pipeline Python (`torch`, `transformers`, `ultralytics`) rulat asincron in subprocess.
- Backend colaborativ: microservicii `Java` + `Spring Boot` (`auth`, `chat`, `annotation`).
- Comunicatie: `REST` + `WebSocket/STOMP`, mesagerie `RabbitMQ`, reverse proxy `Traefik`.
- Persistenta autentificare: `PostgreSQL`; orchestrare: `Docker Compose`.

## 3:10 - 4:00 | Date + evaluare
- Date structurate: utilizatori, roluri, token-uri, metadata sesiune (auth DB).
- Date semi-structurate: adnotari `rect/poly/mask` (inclusiv mask compactata).
- Date nestructurate: imagini (`JPG`, `PNG`, `BMP`, `TIFF`, `WEBP`).
- Evaluare propusa:
  - timp mediu de adnotare (manual vs asistat AI),
  - consistenta adnotarilor,
  - latenta sincronizarii colaborative,
  - corectitudine export/import fara pierderi.

## 4:00 - 4:40 | Rezultate asteptate si contributii
- Reducerea timpului de etichetare prin propuneri automate validate de utilizator.
- Productivitate mai buna in echipe prin colaborare realtime.
- Interoperabilitate cu pipeline-uri ML datorita exportului standardizat.
- Contributie: integrare unificata adnotare + AI + colaborare intr-un sistem modular.

## 4:40 - 5:00 | Inchidere
- Mesaj final: proiectul adreseaza un blocaj real din pregatirea dataset-urilor CV.
- Este fezabil tehnic pe stack matur si poate fi extins cu modele noi.
- Concluzie: platforma accelereaza etichetarea, dar mentine controlul uman.

---

## Intrebari probabile (pregatire rapida)
- De ce e problema non-triviala fata de tool-urile existente?
- De ce ai ales `Mask2Former` + `YOLOE`?
- Ce metrici arata clar castigul fata de varianta fara AI?
- Care sunt limitarile curente si pasii urmatori?

