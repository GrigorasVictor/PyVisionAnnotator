Benchmarking pentru modele alternative: analizarea unor modele open‑vocabulary (ex. YOLO‑World, LLMDet, SAM2) pentru a observa potențialul de generalizare și pentru a justifica alegerea finală.
Validarea unui suport local de tip VLM/LLM: compararea mai multor modele rulate local (Ollama) pentru a susține componenta de chatbot și a stabili un compromis calitate‑viteză. Chatbotul are rolul de a ajuta utilizatorul cu întrebări și de a oferi sugestii pentru remedieri ale erorilor întâlnite.
Experiență de utilizare și prevenirea erorilor: confirmare la schimbarea imaginii și la închidere pentru a evita pierderea adnotărilor.
Persistența setărilor vizuale: salvarea preferințelor (grosime contur, dimensiune font, opacitate mască) între sesiuni.
Îmbunătățirea vizuală a imaginii: ajustări de luminozitate, contrast și gamma fără a altera datele originale.
Încărcare inteligentă a adnotărilor: asocierea automată a fișierelor JSON cu imaginea corespunzătoare.
Optimizarea serializării măștilor: compresie și reducerea volumului de date pentru fișiere mari.
Reducerea traficului în colaborare: trimiterea pe bucăți a actualizărilor pentru măști și deduplicarea evenimentelor.
Crosshair și ghidaj vizual: indicatori pentru precizie în adnotare și selectare.