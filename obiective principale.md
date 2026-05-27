Interfață de adnotare completă: realizarea unui canvas interactiv cu zoom/pan și unelte pentru bounding box, poligon și mască, astfel încât utilizatorul să poată adnota rapid și precis.
Gestionarea coerentă a adnotărilor: păstrarea unei structuri clare pentru etichete și elemente (ID unic, listare, editare, ștergere), pentru a evita erorile și a facilita modificările.
Export standardizat al datelor: suport pentru COCO și YOLO, cu organizare predictibilă a fișierelor, astfel încât dataset‑urile să fie reutilizabile în antrenare fără conversii suplimentare.
Integrare AI semi‑automată: folosirea AutoSeg și AutoMask pentru propuneri rapide de segmentare, cu posibilitate de corectare manuală imediată.
Modularizarea execuției AI: rularea modelelor ca aplicații separate, prin procese dedicate, pentru a izola erorile și a permite actualizări independente.
Colaborare în timp real: sesiuni comune, sincronizare create/update/delete, și actualizare a imaginii între utilizatori prin REST + WebSocket, pentru a evita duplicarea muncii.
Securitate și acces controlat: autentificare pe bază de JWT și păstrarea locală a token‑ului pentru o experiență de lucru fluidă, fără relogare frecventă.
Evaluarea și selecția modelelor AI externe: testarea Mask2Former și YOLOE pe imagini de referință, cu măsurarea timpului de procesare și a calității rezultatelor.

Ambalarea și integrarea backend‑urilor de inferență: pregătirea executabilelor și a configurărilor necesare pentru a facilita rularea locală și integrarea în aplicație.