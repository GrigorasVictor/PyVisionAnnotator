**V-RSIR An Open Access Web-Based Image Annotation Tool for Remote Sensing Image Retrieval**



Lucrarea propune V-RSIR, un instrument web deschis pentru adnotarea imaginilor satelitare, destinat creării de seturi de date pentru remote sensing image retrieval. Contribuția principală este introducerea unui sistem colaborativ bazat pe voluntari, care permite etichetarea imaginilor direct în browser, fără instalări sau cunoștințe tehnice avansate.



Autorii oferă și o analiză a metodelor existente de creare a dataset-urilor, evidențiind limitările acestora (complexitate, acces redus, scalabilitate mică).

Un alt aport important este integrarea mai multor surse de imagini online, ceea ce duce la o diversitate mai mare a datelor colectate.



Tool-ul include funcții complete: etichetare, decupare, editare, verificare și statistici, contribuind la creșterea calității datelor.

Se introduce și un mecanism de control al calității prin inspectori care validează imaginile etichetate.

Lucrarea demonstrează practic utilitatea sistemului prin crearea unui dataset mare (peste 59.000 imagini, 38 clase).

Dataset-ul obținut este distribuit global, ceea ce crește dificultatea și relevanța evaluării algoritmilor.

Autorii validează datele folosind metode clasice și deep learning, arătând superioritatea celor din urmă.

Rezultatele confirmă că platforma poate genera benchmark-uri valide și utile.

În concluzie, contribuția majoră este oferirea unei soluții scalabile și accesibile pentru crearea de dataset-uri mari în domeniul imaginilor satelitare.



**A Cost-Effective, Fast, and Robust Annotation Tool**



Lucrarea prezintă un tool de adnotare pentru imagini/video, conceput pentru a reduce costul și timpul necesar creării dataset-urilor folosite în deep learning. Problema principală identificată este că adnotarea manuală este lentă, costisitoare și predispusă la erori, mai ales în cazul videoclipurilor unde fiecare cadru trebuie etichetat.

Contribuția majoră este propunerea unui sistem semi-automat care combină adnotarea manuală inițială cu urmărirea automată a obiectelor în cadrele următoare.



Utilizatorul marchează obiectele doar în primul cadru, iar algoritmul le urmărește automat pe parcursul videoclipului.

Lucrarea introduce și compară mai multe metode de tracking (template matching, histogram-based, keypoints, KCF), alegând o variantă optimizată.

Cea mai importantă contribuție tehnică este adaptarea metodei Kernelized Correlation Filter pentru tracking robust, multi-obiect și multi-clasă.

Sistemul reduce drastic intervenția umană și automatizează mare parte din procesul de etichetare.



Tool-ul permite și exportul datelor în formate utile pentru antrenarea modelelor de deep learning.

Rezultatele experimentale arată o îmbunătățire majoră a vitezei, de aproximativ 50x până la 200x față de metodele manuale.

În același timp, se obține și o acuratețe mai bună datorită reducerii erorilor umane.

În concluzie, contribuția principală este un sistem rapid, robust și eficient care face posibilă generarea de dataset-uri mari cu efort minim.



**AI-Enhanced Annotation Tool for Aneurysm Medical Image Labeling**



Lucrarea propune un tool de adnotare asistat de inteligență artificială pentru imagini medicale, axat pe detectarea anevrismelor cerebrale. Problema principală este că adnotarea manuală realizată de radiologi este lentă, obositoare și poate varia între experți.

Contribuția majoră este integrarea unui model deep learning (YOLO v11) într-un sistem care ajută automat la identificarea și etichetarea anevrismelor.

Tool-ul nu înlocuiește medicul, ci îl asistă, oferind sugestii rapide pentru zonele suspecte.

Un aport important este creșterea consistenței și reducerea variațiilor dintre adnotările diferiților specialiști.

Lucrarea prezintă și un pipeline complet: colectare date, preprocesare, adnotare și antrenare model.

Modelul YOLO este optimizat pentru detecție rapidă în timp real pe imagini medicale.

Rezultatele arată performanțe ridicate (precizie și recall mari), comparabile sau mai bune decât alte metode.

Un avantaj major este reducerea timpului de adnotare și a efortului depus de radiologi.

Tool-ul permite și îmbunătățirea continuă prin antrenare pe date noi.

În concluzie, contribuția principală este un sistem inteligent care accelerează și îmbunătățește procesul de adnotare medicală, sprijinind dezvoltarea modelelor AI.



**Annotation Web - An open-source web-based annotation tool for ultrasound images**



Lucrarea propune Annotation Web (AW), un instrument web pentru adnotarea imaginilor medicale de tip ultrasunete, folosit la crearea dataset-urilor pentru deep learning.

Contribuția principală este un sistem accesibil direct în browser, fără instalări sau transfer manual de date.

Platforma rezolvă limitările metodelor existente, care sunt greoaie și neadaptate datelor video.

Un aport tehnic important este folosirea HTML canvas pentru redare rapidă și navigare eficientă între cadre.

Tool-ul permite mai multe tipuri de adnotare: clasificare, segmentare, bounding box și landmarks.

Arhitectura modulară bazată pe Django permite extinderea ușoară a funcționalităților.

Se introduce un mecanism de eficientizare prin utilizarea cadrelor-cheie (key frames).

Platforma include și măsuri de securitate, precum autentificarea multifactor.

Sistemul a fost validat în aplicații reale din imagistică medicală, cu rezultate bune.

În concluzie, contribuția majoră este o soluție rapidă, scalabilă și ușor de folosit pentru adnotarea datelor medicale.



**Brima: Low-Overhead Browser-Only Image Annotation Tool (Preprint)**



Lucrarea propune BRIMA, un instrument de adnotare a imaginilor care funcționează exclusiv în browser, destinat creării rapide de dataset-uri pentru computer vision.

Contribuția principală este eliminarea completă a instalării și configurării, adnotarea făcându-se direct în browser.

Sistemul introduce conceptul de „annotate-while-browsing”, unde utilizatorul poate eticheta imagini direct de pe web.

Se elimină necesitatea descărcării și organizării manuale a imaginilor înainte de adnotare.

Un aport important este suportul pentru crowdsourcing, facilitând colaborarea la scară mare.

Tool-ul suportă formate standard (ex. COCO), fiind compatibil cu pipeline-uri de machine learning.

Arhitectura este simplă, cu componentă client (browser extension) și server minimal.

Platforma permite trasabilitatea datelor prin stocarea informațiilor despre sursa imaginilor (URL).

Rezultatele experimentale arată că sistemul permite colectarea rapidă a unor dataset-uri mari și de calitate.

În concluzie, contribuția majoră este o soluție flexibilă, rapidă și ușor de folosit pentru adnotarea imaginilor direct din browser.



**Image browsing for efficient image annotation**



Lucrarea propune un sistem de navigare și vizualizare a bazelor de imagini pentru a face adnotarea mai eficientă.

Problema abordată este că adnotarea manuală este lentă, iar metodele automate nu sunt încă suficient de bune.

Contribuția principală este organizarea imaginilor pe baza similarității vizuale, astfel încât imagini asemănătoare să fie apropiate.

Se introduce o reprezentare vizuală pe o „sferă de culori” (hue sphere), bazată pe caracteristici simple precum culoarea.

Sistemul folosește o structură ierarhică care permite explorarea eficientă a dataset-urilor mari.

Imaginile sunt organizate pe un grid pentru a evita suprapunerea și a îmbunătăți claritatea vizuală.

Un avantaj major este posibilitatea de a adnota simultan grupuri de imagini similare.

Aceasta reduce numărul de interacțiuni necesare față de parcurgerea liniară a imaginilor.

Rezultatele experimentale arată că metoda este mai rapidă decât metodele clasice de tip listă.

În concluzie, contribuția majoră este un sistem de browsing inteligent care accelerează adnotarea prin organizarea vizuală a datelor.



**Tool for image annotation in context of modern object detection**



Lucrarea propune un tool pentru adnotarea imaginilor în contextul detecției moderne de obiecte, destinat creării de dataset-uri pentru deep learning.

Problema abordată este că adnotarea cu bounding box este un proces lent, repetitiv și predispus la erori.

Contribuția principală este dezvoltarea unui sistem cu două interfețe: management de proiect și adnotare efectivă.

Interfața de management permite configurarea proiectelor, claselor și organizarea dataset-urilor.

Interfața de adnotare oferă instrumente intuitive pentru desenarea și editarea bounding box-urilor.

Un aport important este suportul pentru mai multe formate standard (COCO, PASCAL VOC, YOLO).

Tool-ul introduce și automatizare prin integrarea modelului YOLOv5 pentru pre-adnotare.

Aceasta reduce efortul manual și accelerează procesul de etichetare.

Sistemul permite gestionarea eficientă a mai multor proiecte și dataset-uri simultan.

În concluzie, contribuția majoră este un instrument flexibil și eficient care combină adnotarea manuală cu automatizarea pentru detecția obiectelor.



**WebAnnoCV: A Lightweight OpenCV-Based Annotation Tool for Interactive Web Applications**



Lucrarea propune WebAnnoCV, un instrument web pentru adnotarea imaginilor, utilizat în detecție, segmentare și clasificare.

Contribuția principală este procesarea completă în browser, fără servere externe sau instalări suplimentare.

Această abordare elimină problemele de latență și îmbunătățește confidențialitatea datelor.

Autorii evidențiază limitările soluțiilor existente, în special cele legate de cloud și aplicațiile desktop.

Un aport tehnic important este integrarea OpenCV.js pentru procesare rapidă în timp real.

Tool-ul oferă funcții variate: bounding box, segmentare poligonală și puncte-cheie.

Se introduce un mecanism AI care asistă utilizatorul și reduce efortul manual.

Platforma este optimizată pentru mai multe dispozitive, inclusiv mobile și tablete.

Rezultatele arată o acuratețe ridicată și o reducere semnificativă a timpului de adnotare.

În concluzie, contribuția majoră este o soluție sigură, eficientă și accesibilă pentru adnotare direct în browser.



**Annotate-Lab: Simplifying Image Annotation**



Lucrarea prezintă Annotate-Lab, un instrument open-source pentru adnotarea imaginilor, utilizat în machine learning și computer vision.

Problema abordată este că adnotarea manuală este lentă și predispusă la erori.

Contribuția principală este un sistem client-server care combină flexibilitatea cu scalabilitatea.

Interfața client, bazată pe React, oferă un mod intuitiv de realizare a adnotărilor.

Serverul, bazat pe Flask, gestionează stocarea datelor și configurarea proiectelor.

Un aport important este integrarea Segment Anything Model (SAM) pentru selecție automată.

Aceasta reduce semnificativ efortul manual și crește eficiența procesului.

Tool-ul suportă mai multe tipuri de adnotare și export în format YOLO și JSON.

Platforma este open-source, permițând extindere și contribuții din partea comunității.

În concluzie, contribuția majoră este un sistem flexibil și semi-automat care îmbunătățește viteza și acuratețea adnotării



**3D Markup of Radiological Images in ePAD, a Web-Based Image Annotation Tool**



Lucrarea prezintă extinderea platformei ePAD pentru adnotarea imaginilor radiologice prin introducerea suportului 3D.

Problema abordată este că sistemele existente folosesc rapoarte text nestructurate și suportă doar adnotare 2D.

Contribuția principală este dezvoltarea unui plugin web care permite vizualizarea și adnotarea volumetrică a imaginilor.

Se introduce o interfață 3D bazată pe trei planuri (axial, frontal, sagital) pentru explorarea datelor.

Un aport important este utilizarea WebGL pentru procesare rapidă și randare eficientă în browser.

Lucrarea propune și compară mai multe metode de selecție a regiunilor 3D (ROI).

Cea mai importantă contribuție este introducerea cursorului sferic 3D pentru adnotare intuitivă.

Această metodă permite marcarea simultană a mai multor straturi de imagini.

Rezultatele arată că această abordare este preferată de radiologi și îmbunătățește precizia.

În concluzie, contribuția majoră este extinderea adnotării medicale de la 2D la 3D într-un mod eficient și ușor de utilizat.



**A Tool for Thermal Image Annotation and Automatic Temperature Extraction around Orthopedic Pin Sites**



Lucrarea propune un instrument pentru adnotarea imaginilor termice și extragerea automată a temperaturii în zona de interes.

Problema abordată este că tool-urile existente sunt lente, manuale și nu sunt optimizate pentru imagini termice.

Contribuția principală este un sistem de adnotare „single-click” pentru identificarea rapidă a zonelor relevante.

Un aport important este maparea adnotărilor de pe imagini vizibile pe cele termice pentru a reduce erorile.

Tool-ul extrage automat temperatura maximă și distribuția temperaturii din ROI.

Se introduce și analiza contururilor de temperatură pentru vizualizarea variațiilor termice.

Datele sunt salvate în formate structurate (CSV) pentru utilizare în machine learning.

Sistemul reduce semnificativ efortul manual și crește consistența adnotării.

Este validat în aplicații medicale, în special pentru monitorizarea infecțiilor post-operatorii.

În concluzie, contribuția majoră este un tool eficient și automatizat pentru analiza imaginilor termice în medicină.



**Annio: A Web-Based Tool for Annotating Medical Images with Ontologies**



Lucrarea propune Annio, un instrument web pentru adnotarea imaginilor medicale volumetrice.

Problema abordată este dificultatea integrării adnotărilor cu date medicale standardizate și lipsa unor tool-uri web complete.

Contribuția principală este un sistem de adnotare complet în browser, fără instalare sau descărcare de date.

Un aport major este integrarea ontologiilor medicale pentru etichetare standardizată.

Utilizatorii pot adnota puncte, cercuri și poligoane în imagini 2D și 3D.

Sistemul permite navigare avansată (zoom, pan, ajustare intensitate) în imagini volumetrice.

Etichetele sunt generate automat prin sugestii din ontologii pe baza textului introdus.

Datele sunt stocate împreună cu coordonate și identificatori standardizați.

Tool-ul a fost validat pe imagini pulmonare și cardiace, fiind util în practică.

În concluzie, contribuția majoră este combinarea adnotării web cu etichetare semantică standardizată.



**CVAT-BWV: A Web-Based Video Annotation Platform for Police Body-Worn Video**



Lucrarea propune CVAT-BWV, o platformă web pentru adnotarea videoclipurilor provenite din body-worn cameras (BWV).

Problema abordată este dificultatea analizării volumului mare de date video sensibile și lipsa dataset-urilor annotate.

Contribuția principală este un sistem securizat, local, pentru adnotarea datelor multimodale (video, audio, text).

Platforma integrează AI pentru asistarea adnotării: detecție obiecte, recunoaștere vocală și diarizare.

Un aport important este suportul complet pentru adnotări multimodale și multi-perspectivă.

Tool-ul permite crearea de bounding box-uri, etichete audio și corectarea transcripturilor.

Integrarea modelelor AI reduce semnificativ efortul manual și crește calitatea datelor.

Sistemul este bazat pe CVAT și oferă flexibilitate și extensibilitate ridicată.

Platforma este open-source și adaptată pentru date sensibile, cu control al accesului.

În concluzie, contribuția majoră este o platformă completă pentru adnotare video multimodală asistată de AI.



**LabelMe: Online Image Annotation and Applications**



Lucrarea propune LabelMe, o bază de date și un instrument web pentru adnotarea imaginilor digitale.

Abordează lipsa seturilor de date masive, diversificate și etichetate necesare pentru recunoașterea obiectelor.

Contribuția tehnică constă într-o interfață online care permite adnotarea prin poligoane detaliate.

Sistemul facilitează partajarea datelor între cercetători, asigurând o creștere continuă a volumului de imagini.

Utilizatorii pot adăuga, edita și interoga obiecte în timp real, folosind instrumente de desenare intuitive.

Lucrarea analizează distribuția etichetelor, observând un model heavy-tailed conform legii lui Zipf.

Datele colectate includ clase frecvente (ferestre, mașini) și o multitudine de categorii rare.

Implementarea permite vizualizarea și descărcarea seturilor pentru antrenarea algoritmilor de viziune artificială.

Rezultatele demonstrează eficiența colaborării deschise în construirea unei resurse bogate pentru cercetare.

Concluzia subliniază că LabelMe este un cadru sustenabil pentru scalarea calitativă a adnotării.



**Lymphocyte\_Annotator\_CD3\_and\_CD8\_IHC\_Stained\_Patch\_Image\_Annotation\_Tool**



Lucrarea propune LabelMe, o bază de date și un instrument web pentru adnotarea imaginilor digitale.

Abordează lipsa seturilor de date masive, diversificate și etichetate necesare pentru recunoașterea obiectelor.

Contribuția tehnică constă într-o interfață online care permite adnotarea prin poligoane detaliate.

Sistemul facilitează partajarea datelor între cercetători, asigurând o creștere continuă a volumului de imagini.

Utilizatorii pot adăuga, edita și interoga obiecte în timp real, folosind instrumente de desenare intuitive.

Lucrarea analizează distribuția etichetelor, observând un model heavy-tailed conform legii lui Zipf.

Datele colectate includ clase frecvente (ferestre, mașini) și o multitudine de categorii rare.

Implementarea permite vizualizarea și descărcarea seturilor pentru antrenarea algoritmilor de viziune artificială.

Rezultatele demonstrează eficiența colaborării deschise în construirea unei resurse bogate pentru cercetare.

Concluzia subliniază că LabelMe este un cadru sustenabil pentru scalarea calitativă a adnotării.



**MammoApplet: An interactive Java applet tool for manual annotation in medical imaging**



Articolul propune MammoApplet, o interfață Java tip applet pentru adnotarea manuală a imaginilor medicale prin web.

Problema vizată este necesitatea gestionării volumelor mari de date și instruirea radiologilor prin baze de date adnotate.

Sistemul utilizează o arhitectură client-server bazată pe soclu TCP/IP pentru comunicarea cu serverul Apache.

Interfața permite interogarea ierarhică a sistemelor PACS prin protocolul DICOM 3.0 la nivel de pacient, studiu și serie.

Contribuția tehnică include instrumente de procesare (zoom, contrast, luminozitate) și de desenare poligonală a leziunilor.

Adnotările sunt salvate sub formă de fișiere XML, permițând stocarea atributelor morfologice și a lexicului BIRADS.

Platforma suportă accesul simultan al mai multor experți, identificând autorul fiecărei adnotări prin coduri de culori.

Informațiile de tip overlay includ calcularea automată a ariei și centrului de masă pentru regiunile marcate.

Extensibilitatea tool-ului a fost demonstrată prin adaptarea acestuia pentru imagini MRI și spectroscopie de prostată.

Concluzia subliniază eficiența instrumentului în crearea bazei de date MammoDB pentru e-learning și suport decizional.



**Markup\_SVGAn\_Online\_Content-Aware\_Image\_Abstraction\_and\_Annotation\_Tool**



Markup SVG propune un cadru de lucru pentru colectarea și structurarea asistată a datelor de imagine adnotate.

Abordează ineficiența proceselor manuale de segmentare și lipsa unei structuri unificate pentru metadate complexe.

Utilizează un strat de abstracție bazat pe SVG pentru a integra caracteristicile numerice cu etichetele semantice.

Implementează patru clase de module: procesare de bază, semantice, date eterogene și agenți de acțiune.

Include extracție automată de trăsături prin histograme de culoare, filtre Gabor și descriptori de tip SIFT.

Utilizează algoritmi Active Contours și Interactive Graph Cuts pentru segmentarea precisă a regiunilor.

Sugerează etichete folosind o formulare Bayesiană ce corelează trăsăturile regiunii cu contextul imaginii.

Optimizează viteza de procesare prin accelerare NVIDIA GPU (CUDA), facilitând interacțiunea în timp real.

Garantează scalabilitatea prin tehnici de compresie SVG bazate pe ajustări polinomiale pentru seturi de date mari.

Contribuția majoră constă în reducerea efortului de adnotare manuală printr-un sistem interactiv, căutabil și extensibil.



**Semi-automatic\_image\_annotation\_of\_street\_scenes**



Lucrarea propune un instrument de adnotare semi-automată pentru scene rutiere folosite în conducerea autonomă.

Problema abordată este timpul mare și efortul necesar pentru etichetarea manuală la nivel de pixel.

Contribuția principală este un cadru care combină superpixeli, CRF dens și corecții manuale.

Se utilizează algoritmul SLIC pentru segmentarea inițială în superpixeli.

Sistemul integrează și informații 3D din LIDAR/stereo pentru localizare mai precisă.

Un clasificator Adaboost decide fuziunea superpixelilor în funcție de clasă.

CRF-ul dens propagă etichetele în mod automat în întreaga imagine.

Utilizatorul poate ajusta parametri în timp real pentru control mai bun.

Rezultatele arată o reducere semnificativă a timpului de adnotare.

În concluzie, contribuția majoră este un sistem semi-automat eficient pentru segmentare semantică.



**Clara: Semi-Automatic Annotation Algorithm for Medical Image Recognition**



Lucrarea propune o metodă semi-automată pentru adnotarea imaginilor medicale destinate recunoașterii automate.

Problema abordată este faptul că adnotarea manuală este lentă, costisitoare și necesită personal specializat.

Contribuția principală este integrarea algoritmului Live-Wire pentru creșterea vitezei și preciziei adnotării.

Metoda introduce „loss mask” și „complete mask” pentru eliminarea caracteristicilor irelevante.

Sistemul permite interacțiune om-mașină pentru corectarea rapidă a erorilor de etichetare.

Comparativ cu LabelMe, metoda obține adnotări mai stabile și mai precise.

Rezultatele arată îmbunătățiri ale eficienței de peste 60% și creșteri ale acurateții cu aproximativ 10%.

Datele generate sunt utilizate pentru antrenarea modelelor precum Mask R-CNN și BlendMask.

Metoda este portabilă și poate fi aplicată și în computer vision sau robotică.

În concluzie, contribuția majoră este un sistem semi-automat care îmbunătățește atât viteza, cât și calitatea adnotării medicale.



**PiPo-Net: A Semi-automatic and Polygon-based Annotation Method for Pathological Images**



Lucrarea propune PiPo-Net, o metodă semi-automată bazată pe poligoane pentru adnotarea imaginilor patologice.

Abordează problema procesului laborios și consumator de timp al segmentării manuale a metastazelor ganglionare.

Contribuția tehnică principală constă în arhitectura duală ce îmbină sub-rețelele Pi-Net și Po-Net.

Pi-Net execută segmentarea la nivel de pixel folosind o structură optimizată de tip encoder-decoder.

Po-Net utilizează o rețea recurentă pentru a genera secvențial vârfurile poligoanelor de adnotare.

Este introdusă o nouă funcție de pierdere (loss function) pentru a optimiza precizia ambelor sarcini.

Sistemul permite interacțiunea umană pentru rafinarea rezultatelor, asigurând un control calitativ superior.

Rezultatele experimentale demonstrează obținerea unui scor Dice de 91% încă de la prima iterație.

Metoda transformă predicțiile de tip raster în contururi vectoriale strânse, ușor de manipulat de experți.

Contribuția majoră este eficientizarea fluxului de lucru prin reducerea drastică a sarcinii de etichetare manuală.



**SegBuilder: A Semi-Automatic Annotation Tool for Segmentation**



Lucrarea propune SegBuilder, un cadru semi-automat bazat pe modelul de fundație Segment Anything (SAM).

Problema vizată este efortul uman masiv și timpul necesar pentru adnotarea pixel-cu-pixel a imaginilor.

Contribuția tehnică majoră constă în integrarea SAM pentru generarea automată a măștilor de segmentare.

Sistemul permite utilizatorilor să eticheteze segmentele generate printr-o listă de selecție rapidă și intuitivă.

Funcționalitatea include procesarea eficientă a scenelor complexe prin interacțiunea minimă a operatorului uman.

Metoda a fost validată prin crearea unui set de date inedit pentru medii subacvatice dificile.

Rezultatele demonstrează o accelerare semnificativă a procesului de etichetare față de metodele tradiționale.

Instrumentul suportă diverse categorii de obiecte, de la animale marine la structuri în medii dificile.

Arhitectura facilitează rafinarea segmentelor, asigurând o precizie ridicată necesară antrenării modelelor profunde.

Concluzia evidențiază succesul utilizării modelelor pre-antrenate în eficientizarea fluxurilor pentru viziune artificială.



**Semi-automatic image annotation using sparse coding**



Lucrarea propune o tehnică de adnotare semi-automată bazată pe un mecanism de transfer de etichete (label transfer).

Problema vizată este dificultatea atribuirii automate de cuvinte cheie și necesitatea unei reprezentări eficiente a imaginilor.

Contribuția tehnică majoră constă în utilizarea codificării rare (sparse coding) integrate cu potrivirea piramidală spațială (ScSPM).

Metoda extrage descriptori SIFT denși, care sunt codificați printr-un dicționar învățat pentru a reduce eroarea de reconstrucție.

Funcționalitatea de „spatial pyramid matching” utilizează „max pooling” pentru a păstra informațiile geometrice și contextul spațial.

Sistemul clasifică inițial imaginile în categorii generale folosind un clasificator Linear Support Vector Machine (SVM).

Recomandarea cuvintelor cheie (tag-uri) se realizează prin transferul etichetelor de la imaginile cele mai apropiate din categoria prezisă.

Modelarea prin codificare rară permite obținerea unor reprezentări mai discriminative comparativ cu metodele vectoriale tradiționale.

Rezultatele experimentale pe seturile de date Corel5K și IAPR TC-12 demonstrează o precizie și o reamintire superioare.

Concluzia subliniază eficiența codificării rare în reducerea decalajului semantic pentru organizarea marilor colecții de date vizuale.



**Semi-Automatic Semantic Annotation of Images**



Lucrarea propune o metodă semi-automată pentru adnotarea semantică a imaginilor științifice și medicale.

Problema abordată este dificultatea realizării manuale a unor adnotări consistente și precise pentru volume mari de imagini.

Contribuția principală este introducerea unui lanț generic de procesare pentru maparea caracteristicilor low-level către termeni semantici.

Sistemul utilizează rețele neuronale artificiale pentru clasificarea regiunilor segmentate din imagini.

Metoda extrage caracteristici precum formă, arie, culoare și excentricitate ale obiectelor.

Autorii subliniază importanța termenilor intermediari („circular”, „long”, „adjacent”) înainte de clasificarea semantică finală.

Lucrarea introduce și conceptul de mapare multi-etapă între low-level features și semantică de domeniu.

Evaluarea pe imagini micrografice celulare demonstrează fezabilitatea clasificării semi-automate.

Rezultatele arată că relațiile spațiale și descriptorii semantici intermediari cresc acuratețea clasificării.



**Video Annotation System Using a Voice User Interface**



Lucrarea propune un sistem de adnotare video semi-automată bazat pe o interfață vocală (VUI).

Vizează reducerea efortului manual în analiza sportivă prin captarea datelor „când, cine, ce”.

Timpul evenimentului este extras automat din cadrul corespunzător începutului rostirii utilizatorului.

Tehnologia include WebRTC VAD pentru detecție și faster-whisper pentru recunoașterea vorbirii.

Sistemul utilizează word embedding chiVe și modele SVM pentru clasificarea informațiilor în etichete.

Metoda oferă flexibilitate și precizie ridicată comparativ cu sistemele tradiționale bazate pe butoane.

Testele pe secvențe de baschet au raportat o rată de eroare a etichetelor (TER) de 9,20%.

Precizia sincronizării temporale a înregistrat un RMSE de 1,36 secunde în cadrul experimentelor.

Aproximativ 98,8% dintre adnotări au avut o deviație temporală sub 3 secunde față de ideal.

Soluția este considerată eficientă pentru diverse sporturi care necesită indexare temporală precisă.

