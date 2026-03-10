# PyVisionAnnotator - Lista de Funcționalități

## 1. Canvas & Navigare
- [x] Zoom In/Out (Rotiță Mouse)
- [x] Pan/Deplasare (Click-Mijloc sau Space + Click-Stânga)
- [x] Încărcare imagini din folder (Sidebar navigabil)
- [x] Suport formate: JPG, PNG, BMP, TIFF, WEBP

## 2. Unelte de Adnotare (Tools)
- [x] **Rect (Dreptunghi)**: Bounding Box
  - Desenare prin drag-and-drop
  - Redimensionare prin colțuri/laturi (Handles)
- [x] **Poly (Poligon)**: Segmentare Semantică
  - Click-Stânga pentru adăugare puncte
  - Click-Dreapta sau Enter pentru închidere contur
  - Afișare etichetă deasupra poligonului
- [x] **AutoSeg Tool**: Segmentare automată prin model extern
  - Configurare model din toolbar → 🤖 AutoSeg (acceptă .py sau .exe)
  - Click pe obiect → rulează subprocess → rezultat afișat ca poligon
  - Progress dialog cu opțiune de anulare
  - Suport JSON output cu coordonate de tip mască (simplificate automat cu Douglas-Peucker)

## 3. Gestionare Date & Proprietăți
- [x] **Panou Proprietăți (Sidebar Dreapta)**:
  - Modificare Etichetă (Label) pentru elementul selectat
  - Modificare Culoare (Color Picker)
  - Afișare coordonate exacte
- [x] **Lista Adnotări**: Vizualizare ID și coordonate
- [x] **Existing Labels**: Reutilizare rapidă a etichetelor deja existente în imagine (cu contorizare)
- [x] **Ștergere**: Tasta Delete sau buton dedicat

## 4. Export & Import Inteligent
- [x] **Formate**: JSON și CSV
- [x] **Structură Dataset Automată**:
  - Salvează automat în subfoldere `/rectangle` sau `/poly` în directorul imaginii
  - Numește fișierul după numele imaginii
- [x] **Smart Load**: La încărcarea unui JSON/CSV, aplicația găsește și deschide automat imaginea aferentă
- [x] **Protecție Date**: Prompt de confirmare "Save changes?" la schimbarea imaginii dacă există modificări nesalvate

## 5. Configurare (Settings)
- [x] Dialog dedicat pentru setări vizuale persistente:
  - Grosime linie contur (px)
  - Dimensiune font etichetă (pt)
  - Înălțime fundal etichetă (Badge Height px)

## 7. Ajustări Imagine (Visual Only)
- [x] Slider Brightness (-100 la +100)
- [x] Slider Contrast (0.1× la 3.0×)
- [x] Slider Gamma (0.1 la 3.0)
- [x] Buton Reset pentru a reveni la valorile neutre
- [x] Adnotările se salvează pe coordonatele **originale** — ajustările sunt strict vizuale

## 8. Crosshair Cursor
- [x] Două linii infinite (orizontală + verticală) care urmăresc mouse-ul în timp real
- [x] Desenat deasupra oricărei adnotări (viewport overlay), fără a interfera cu scena
- [x] Toggle ON/OFF printr-un checkbox în sidebar

## 9. AutoSeg — Segmentare Automată (Model Extern)
- [x] **Configurare persistentă** (QSettings): un singur fișier model (.py sau .exe standalone)
  - Dacă .py: se cere și calea către interpretorul Python (auto-detectat dacă e gol)
  - Dacă .exe: se rulează direct, fără interpret
- [x] **Dialog dedicat** (🤖 AutoSeg în toolbar) cu:
  - Browse model file + Browse Python interpreter
  - Spinner timeout (5–600 s)
  - Buton 🧪 Test Connection
- [x] **Execuție asincronă** în QThread (AutoSegWorker) — GUI rămâne responsiv
- [x] **Progress dialog** cu buton Cancel (termină procesul)
- [x] **Marker vizual** pe canvas (cerc verde) la click, dispare după rezultat
- [x] **Conversie automată** coordonate mască → poligon simplificat:
  - Sortare angulară de la centroid
  - Simplificare Douglas-Peucker (epsilon = 2px)
  - Suport convex hull opțional
- [x] **Subprocess securizat** (shell=False, validare căi, timeout, argument list)

## 10. SubprocessHandler — Execuție Securizată Procese Externe
- [x] `shell=False` — previne injecția de comenzi
- [x] Validare existență cale executabil / script
- [x] Timeout configurabil
- [x] Parsare automată JSON din stdout (tolerant la log-uri suplimentare)
- [x] Suport variabile de mediu custom

