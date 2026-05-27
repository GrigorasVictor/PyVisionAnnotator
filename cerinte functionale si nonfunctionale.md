# Cerinte functionale

- Incarcarea imaginilor dintr-un folder si navigarea rapida intre ele.
- Afisarea imaginilor pe un canvas interactiv cu zoom si pan.
- Crearea adnotarilor de tip bounding box, poligon si masca (image segmentation).
- Selectarea, editarea si stergerea adnotarilor existente.
- Asocierea etichetelor si culorilor pentru adnotari.
- Exportul adnotarilor in formate standard (COCO si YOLO).
- Salvarea si incarcarea adnotarilor in format intern (JSON).
- Integrarea AutoSeg si AutoMask pentru propuneri semi-automate.
- Rularea modelelor AI ca procese separate (modularizare).
- Colaborare in timp real: sesiuni, sincronizare create/update/delete prin REST si WebSocket.
- Autentificare cu JWT si acces controlat la sesiuni.
- Interfata de chat pentru comunicare intre utilizatori.
- Chatbot local pentru asistenta si sugestii la erori.
- Setari vizuale persistente (grosime contur, font, opacitate masca).
- Confirmare la schimbarea imaginii sau inchidere pentru prevenirea pierderilor.

# Cerinte non-functionale

- Usabilitate: interfata clara, operatii frecvente accesibile rapid.
- Performanta: interfata ramane responsiva in timpul rularii AI (procesare asincrona).
- Fiabilitate: validari pentru cai inexistente si mesaje clare de eroare.
- Securitate: autentificare pe baza de token si protejarea sesiunilor.
- Integritate date: exporturi consistente, fara pierderi de date.
- Scalabilitate: mai multi utilizatori pot lucra in aceeasi sesiune.
- Mentenabilitate: arhitectura modulara (client + server + procese AI separate).
- Extensibilitate: posibilitatea de a adauga noi modele sau formate de export.
- Portabilitate: rulare locala pe Windows, cu configurare minima.
