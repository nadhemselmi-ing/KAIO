/* KAIO dashboard — English / French switch.
   The page is written in English. When French is selected, every text node, a few attributes and every
   canvas label (fillText) is passed through tr(): first an exact-match dictionary, then patterns for
   sentences that contain numbers. New text written by the dashboard code is translated as it appears
   (MutationObserver), so the code that builds the page does not need to change. */
(function(){
  const FR = {
  // header
  'Mission control':'Centre de contrôle','Orbit designer':"Concepteur d'orbite",'Mission replay':'Rejeu de mission',
  'Benchmark':'Évaluation','Real data':'Données réelles','How it decides':'Comment il décide','Light':'Clair','Dark':'Sombre',
  'Loading orbit data…':"Chargement des données d'orbite…",
  'This browser cannot unpack the mission data (needs a 2023+ browser).':'Ce navigateur ne peut pas décompresser les données de mission (navigateur 2023 ou plus récent requis).',
  '3D view unavailable (WebGL or the three.js library could not load). All readouts still work.':'Vue 3D indisponible (WebGL ou three.js n’a pas pu se charger). Toutes les autres données restent disponibles.',
  // headline
  'Onboard intelligence for Earth-observation satellites':"Intelligence embarquée pour satellites d'observation de la Terre",
  'Not every image':'Toutes les images','deserves the':'ne méritent pas le','downlink.':'downlink.',
  'KAIO decides onboard, every 10 seconds:':'KAIO décide à bord, toutes les 10 secondes :',
  'process':'traiter','keep':'garder','transmit':'transmettre','or':'ou','offload':'déléguer',
  'Explore the satellite':'Explorer le satellite','Watch the mission replay':'Voir le rejeu de mission',
  'of the reachable value':'de la valeur atteignable','over a tuned rule engine':'de plus qu’un moteur à règles optimisé',
  'real days won':'jours réels gagnés',
  // explore panels
  'Which images deserve the downlink?':'Quelles images méritent le downlink ?',
  'Φsat-2 takes far more pictures than it can send to the ground. Every 10 seconds the E-LOTUS engine decides, for each image, whether to process it onboard, keep it, transmit it or hand it to a neighbour, without draining the battery or overheating. Drag the satellite or pick another orbit to see what changes.':
    'Φsat-2 prend bien plus d’images qu’il ne peut en envoyer au sol. Toutes les 10 secondes, le moteur E-LOTUS décide pour chaque image s’il faut la traiter à bord, la garder, la transmettre ou la confier à un voisin, sans vider la batterie ni surchauffer. Déplacez le satellite ou choisissez une autre orbite pour voir ce qui change.',
  'Details ▾':'Détails ▾','Hide ▴':'Masquer ▴','Open the mission replay':'Ouvrir le rejeu de mission','Pause':'Pause','Play':'Lecture',
  'Fly the orbit':"Parcourir l'orbite",'← Back to overview':'← Retour à l’accueil',
  'Tracked orbit':'Orbite suivie','What-if orbit':'Orbite hypothétique','Inclination':'Inclinaison',
  'Ascending node, local solar time':'Nœud ascendant, heure solaire locale',
  'Real tracked orbit':'Orbite réelle suivie','Best orbit (battery ≥ 50 %)':'Meilleure orbite (batterie ≥ 50 %)',
  '80 what-if orbits, 24 h each':'80 orbites hypothétiques, 24 h chacune',
  'Lowest battery':'Batterie minimale','Solar energy':'Énergie solaire','Value / day':'Valeur / jour',
  'Click a cell to fly that orbit. × = real orbit.':'Cliquez sur une case pour parcourir cette orbite. × = orbite réelle.',
  'Each cell is a full 24-hour engine run on the real NASA scenes under that orbit (RK4 two-body + J2, real altitude). Value also depends on which fires and clear land an orbit happens to overfly that day.':
    'Chaque case est une simulation complète de 24 h du moteur sur les vraies scènes NASA sous cette orbite (RK4 deux corps + J2, altitude réelle). La valeur dépend aussi des feux et des terres dégagées survolés ce jour-là.',
  'Spacecraft now':'Satellite en direct','Sunlit':'Au soleil','Eclipse':'Éclipse','No contact':'Pas de contact',
  'Laser link ready':'Liaison laser prête','Laser link idle':'Liaison laser inactive','Offloading by laser':'Délégation par laser',
  '% battery':'% batterie','Temperature':'Température','Backlog':'File d’attente','Solar input':'Apport solaire','Power load':'Consommation',
  'E-LOTUS decision':'Décision E-LOTUS','Store':'Garder','Process':'Traiter','Transmit':'Transmettre','Offload':'Déléguer',
  'Holding data on board. Nothing in the queue is worth the energy or the link right now.':'Données gardées à bord. Rien dans la file ne vaut l’énergie ou la liaison pour l’instant.',
  'Sunlit with battery margin: the GPU turns raw images into small, high-value products.':'Au soleil avec de la marge batterie : le GPU transforme les images brutes en petits produits à forte valeur.',
  'A ground station is in view: downlinking the most valuable finished products first.':'Une station sol est en vue : envoi des produits finis les plus précieux en premier.',
  "In Earth's shadow: sending raw images to a sunlit neighbour over the laser link instead of draining the battery.":'Dans l’ombre de la Terre : envoi des images brutes à un voisin ensoleillé par liaison laser au lieu de vider la batterie.',
  'Battery over 24 h':'Batterie sur 24 h','value / day':'valeur / jour','lowest battery':'batterie minimale','healthy':'saine','tight':'juste','critical':'critique',
  'time in shadow':"temps à l'ombre",'Wh solar / day':'Wh solaires / jour','min contact / day':'min de contact / jour','peak temperature':'température max',
  'The battery touches the 20 % safety floor: the engine has to hold back the payload.':'La batterie touche le seuil de sécurité de 20 % : le moteur doit retenir la charge utile.',
  'Drag the satellite to move it along its orbit. Drag the Earth to turn it.':'Faites glisser le satellite le long de son orbite. Faites glisser la Terre pour la tourner.',
  // replay
  'Real orbit, real NASA scenes,':'Orbite réelle, vraies scènes NASA,',
  'One real day flown three times on the same hardware: by the E-LOTUS engine, by a greedy processor and by a hand-tuned rule engine.':
    'Une journée réelle rejouée trois fois sur le même matériel : par le moteur E-LOTUS, par un traitement glouton et par un moteur à règles réglé à la main.',
  'Change the mission':'Modifier la mission',
  'Each combination is a full 24-hour run of all three controllers, computed in advance (270 runs).':'Chaque combinaison est une simulation complète de 24 h des trois contrôleurs, calculée à l’avance (270 simulations).',
  'Engine priority (Lyapunov V)':'Priorité du moteur (V de Lyapunov)','Battery at start':'Batterie au départ','Radiator capacity':'Capacité du radiateur',
  'Onboard storage':'Stockage à bord','Inter-satellite laser link':'Liaison laser inter-satellites','On':'Activée','Off':'Désactivée',
  'E-LOTUS value delivered':'Valeur livrée par E-LOTUS','as nominal':'comme en nominal','vs Rule-Based, same scenario':'vs moteur à règles, même scénario',
  'payload energy used':'énergie de la charge utile','tasks completed':'tâches accomplies','Restart':'Recommencer','No pass':'Pas de passage','Ground pass':'Passage station sol',
  'sunlit arc':'arc au soleil','eclipse arc':'arc en éclipse','ground pass':'passage station sol','scene entropy low → high':'entropie de scène faible → élevée',
  'VIIRS fire alert':'alerte feu VIIRS','satellite now':'satellite maintenant','E-LOTUS engine':'Moteur E-LOTUS','Battery':'Batterie','Value so far':'Valeur cumulée',
  'Battery low: payload switched off':'Batterie faible : charge utile coupée','Too hot: GPU throttled':'Trop chaud : GPU bridé','Temperature close to the hardware limit':'Température proche de la limite matérielle',
  'Battery charge (%). The payload is switched off below 20 %.':'Charge batterie (%). La charge utile est coupée sous 20 %.',
  'Computer temperature (°C). Limit 45 °C, hardware throttle 60 °C.':'Température du calculateur (°C). Limite 45 °C, bridage matériel 60 °C.',
  'Value delivered to the ground, cumulative':'Valeur livrée au sol, cumulée','E-LOTUS decision log, newest first':'Journal des décisions E-LOTUS, plus récentes en premier',
  'Waiting for the first decision…':'En attente de la première décision…','Rule-Based (dashed)':'Moteur à règles (pointillés)','eclipse':'éclipse',
  // benchmark
  'real days, mean with 95 % confidence interval':'jours réels, moyenne avec intervalle de confiance à 95 %',
  'Same orbit, same NASA scenes, same hardware for every strategy; only the decision rule changes. Each day is an independent 24-hour run, so the whiskers show how much the result varies from day to day.':
    'Même orbite, mêmes scènes NASA, même matériel pour chaque stratégie ; seule la règle de décision change. Chaque jour est une simulation indépendante de 24 h, les barres d’erreur montrent la variation d’un jour à l’autre.',
  'more images delivered or triaged than the rule engine':'images livrées ou triées de plus que le moteur à règles',
  '% of the reachable value, mean ± 95 % CI':'% de la valeur atteignable, moyenne ± IC 95 %',
  'Strategy':'Stratégie','Value/day':'Valeur/jour','% reachable':'% atteignable','Completion %':'Accomplies %','Alerts on time %':'Alertes à temps %',
  'Energy Wh/day':'Énergie Wh/jour','Latency min':'Latence min','Min battery %':'Batterie min %','Max °C':'Max °C','Time >45 °C %':'Temps >45 °C %',
  'Load-shed %':'Délestage %','E-LOTUS better on':'E-LOTUS meilleur sur',
  'Rule-Based':'Moteur à règles','Bandwidth-Rules':'Règles + débit','Store-and-Forward':'Stocker-transmettre','Greedy-Process':'Traitement glouton','Always-Transmit':'Toujours transmettre',
  'Stress tests':'Tests de robustesse','One resource degraded at a time,':'Une ressource dégradée à la fois,','real days each, nothing retuned':'jours réels chacun, aucun réglage modifié',
  'Bars show the share of the reachable value. Where a rule engine scores higher than E-LOTUS, the panel says what it pays for it.':
    'Les barres montrent la part de la valeur atteignable. Quand un moteur à règles fait mieux qu’E-LOTUS, le panneau indique ce que cela lui coûte.',
  'Nominal':'Nominal','we win':'gagné','we lose':'perdu','Solar array -30 %':'Panneaux solaires −30 %','Small battery (40 Wh) + solar -30 %':'Petite batterie (40 Wh) + solaire −30 %',
  'Storage / 3 (2.7 GB)':'Stockage / 3 (2,7 Go)','GPU 2.5x slower':'GPU 2,5× plus lent','Downlink / 2, 20 deg mask':'Downlink / 2, masque 20°',
  'Fire season (3x alerts)':'Saison des feux (3× alertes)','Radiator -25 %':'Radiateur −25 %',
  // real data
  'Clouds fool raw entropy':'Les nuages trompent l’entropie brute','What 20 days of real NASA quick-looks showed us':'Ce que 20 jours d’aperçus NASA réels nous ont appris',
  'On real VIIRS quick-looks, clouds are the most textured scenes. Fusing entropy with the onboard land mask fixes the ranking.':
    'Sur les vrais aperçus VIIRS, les nuages sont les scènes les plus texturées. Combiner l’entropie avec le masque terre/mer embarqué corrige le classement.',
  'Median quick-look entropy by real scene type [bit/px]':'Entropie médiane des aperçus par type de scène réelle [bit/px]',
  'Share of all scenes in brackets. Cloud is both the most common and the most "information-rich" looking.':'Part de toutes les scènes entre parenthèses. Le nuage est à la fois le plus fréquent et le plus « riche en information » en apparence.',
  'Value captured by the top 30 % of scenes (held-out days)':'Valeur captée par les 30 % meilleures scènes (jours de test)',
  'random':'aléatoire','raw entropy':'entropie brute','land prior':'masque terre seul','oracle':'oracle',
  'Raw entropy triages worse than random. The E-LOTUS estimator comes within a few points of a label-aware oracle.':'L’entropie brute trie moins bien que le hasard. L’estimateur E-LOTUS arrive à quelques points d’un oracle qui connaît la vérité.',
  // how
  'How KAIO decides':'Comment KAIO décide','Runs onboard every 10 seconds':'Tourne à bord toutes les 10 secondes',
  'Four steps, a few hundred lines of code, no training. Every input is something a real satellite already has onboard.':'Quatre étapes, quelques centaines de lignes de code, aucun entraînement. Chaque entrée est une donnée qu’un vrai satellite possède déjà à bord.',
  'Step 1':'Étape 1','Step 2':'Étape 2','Step 3':'Étape 3','Step 4':'Étape 4',
  'Estimate what each image is worth':'Estimer la valeur de chaque image','Score every action':'Noter chaque action','Safety guard can veto':'Le garde de sécurité peut bloquer','Log a one-line reason':'Expliquer en une ligne',
  'Quick-look entropy (texture) × land fraction from an onboard land/water mask, × 4 for fire alerts.':'Entropie de l’aperçu (texture) × fraction de terre issue d’un masque terre/mer embarqué, × 4 pour les alertes feu.',
  'Process, transmit, offload or keep. Score = growth of three debts (storage backlog, battery below its eclipse floor, heat above 45 °C) minus V × value delivered, per second of resource used.':
    'Traiter, transmettre, déléguer ou garder. Score = hausse de trois dettes (file de stockage, batterie sous son seuil d’éclipse, chaleur au-dessus de 45 °C) moins V × valeur livrée, par seconde de ressource utilisée.',
  'An independent check, like flight-software FDIR: no job starts if the battery would fall below the energy needed to survive the next eclipse, or the computer would end above 45 °C. Only fire alerts may use the margin up to the 60 °C hardware limit.':
    'Un contrôle indépendant, comme le FDIR des logiciels de vol : aucune tâche ne démarre si la batterie tombait sous l’énergie nécessaire pour survivre à la prochaine éclipse, ou si le calculateur finissait au-dessus de 45 °C. Seules les alertes feu peuvent utiliser la marge jusqu’à la limite matérielle de 60 °C.',
  'Every started job carries a reason built only from onboard data, so operators on the ground can audit each decision.':'Chaque tâche lancée porte une raison construite uniquement à partir des données de bord, pour que les opérateurs au sol puissent vérifier chaque décision.',
  // pi
  'Runs on a credit-card computer':'Tourne sur un ordinateur de la taille d’une carte bancaire','Engine cost on a development laptop':'Coût du moteur sur un ordinateur de développement',
  'Measured on':'Mesuré sur',
  'The decision engine was timed over a full real day on the board below: value estimate, scoring, safety checks and explanations included.':'Le moteur de décision a été chronométré sur une journée réelle complète sur la carte ci-dessous : estimation de valeur, notation, contrôles de sécurité et explications compris.',
  'Timed over a full real day. The same script runs unchanged on a Raspberry Pi (onboard/pi_benchmark.py).':'Chronométré sur une journée réelle complète. Le même script tourne sans modification sur un Raspberry Pi (onboard/pi_benchmark.py).',
  'of one CPU core used by the engine over a real day':'d’un cœur CPU utilisé par le moteur sur une journée réelle',
  'to compute the quick-look entropy of one image':'pour calculer l’entropie de l’aperçu d’une image',
  'peak memory of the whole program, simulator included':'mémoire max du programme entier, simulateur compris',
  'plus sgp4: the only libraries needed onboard. No GPU, no training.':'plus sgp4 : les seules bibliothèques nécessaires à bord. Pas de GPU, pas d’entraînement.',
  'energy per day for the engine (USB power meter)':'énergie par jour du moteur (wattmètre USB)',
  // footer
  'Data sources and model assumptions ▾':'Sources de données et hypothèses du modèle ▾','Data sources and model assumptions ▴':'Sources de données et hypothèses du modèle ▴',
  'Real inputs: satellite orbit from a public CelesTrak TLE (SGP4); NASA GIBS':'Entrées réelles : orbite du satellite à partir d’un TLE public CelesTrak (SGP4) ; NASA GIBS',
  '; ground stations at Svalbard and Matera. Globe imagery: NASA Blue Marble and Black Marble (public domain). Milky Way sky: three.js example skybox (MIT).':
    ' ; stations sol à Svalbard et Matera. Images du globe : NASA Blue Marble et Black Marble (domaine public). Ciel de la Voie lactée : skybox d’exemple three.js (MIT).',
  'Simulated: battery (RK4), radiator (Stefan–Boltzmann), 15 W edge-AI GPU, 10 Mbps downlink, 100 Mbps optical inter-satellite link, neighbour donor model. Thermal limit 45 °C (operating), 60 °C (hardware throttle). KAIO · powered by the E-LOTUS decision engine.':
    'Simulé : batterie (RK4), radiateur (Stefan–Boltzmann), GPU edge-AI de 15 W, downlink 10 Mbps, liaison optique inter-satellites 100 Mbps, modèle de voisin donneur. Limite thermique 45 °C (fonctionnement), 60 °C (bridage matériel). KAIO · propulsé par le moteur de décision E-LOTUS.',
  // attributes
  'Colour theme':'Thème de couleur','Language':'Langue','3D Earth with the satellite orbit. Drag the satellite to move it along its orbit.':'Terre 3D avec l’orbite du satellite. Faites glisser le satellite le long de son orbite.',
  'Battery level over 24 hours':'Niveau de batterie sur 24 heures','Ground track map':'Carte de la trace au sol','Map of orbit results by inclination and node time':'Carte des résultats par inclinaison et heure du nœud',
  'Mission time':'Temps de mission','Replay speed':'Vitesse du rejeu','1× plays the 24-hour day in 3 minutes':'1× rejoue la journée de 24 h en 3 minutes',
  // scene classes
  'cloud':'nuage','ocean':'océan','land':'terre','dark':'nuit','coast':'côte','clear land':'terre dégagée','polar night':'nuit polaire','fire':'feu','scene':'scène',
  };
  const N = '(-?[\\d.,]+)';
  const cls = s => FR[s] || s;
  // sentences with numbers: [regex, replacement]
  const RULES = [
    [/^Process now: est\. value (.+?) \((.+?), land (.+?)%\)\. (.+?) MB raw -> (.+?) MB product, next pass in (.+?) min; battery (.+?) Wh after \(floor (.+?)\), (.+?) °C\.$/,
      (m,v,src,l,a,b,p,e,f,t)=>`Traiter maintenant : valeur est. ${v} (${src2(src)}, terre ${l} %). ${a} Mo bruts → ${b} Mo de produit, prochain passage dans ${p} min ; batterie ${e} Wh après (seuil ${f}), ${t} °C.`],
    [/^Downlink product: est\. value (.+?) \(processed product of (.+?), land (.+?)%\), (.+?) MB, (.+?) s of pass time; battery (.+?) Wh after \(floor (.+?)\), (.+?) °C\.$/,
      (m,v,src,l,mb,s,e,f,t)=>`Envoyer le produit : valeur est. ${v} (produit traité de ${src2(src)}, terre ${l} %), ${mb} Mo, ${s} s de passage ; batterie ${e} Wh après (seuil ${f}), ${t} °C.`],
    [/^Downlink raw image: est\. value (.+?) \((.+?), land (.+?)%\), (.+?) MB, (.+?) s of pass time; battery (.+?) Wh after \(floor (.+?)\), (.+?) °C\.$/,
      (m,v,src,l,mb,s,e,f,t)=>`Envoyer l’image brute : valeur est. ${v} (${src2(src)}, terre ${l} %), ${mb} Mo, ${s} s de passage ; batterie ${e} Wh après (seuil ${f}), ${t} °C.`],
    [/^Eclipse: offload (.+?) MB over the laser link to the (leading|trailing) neighbour in sunlight \(est\. value (.+?), (.+?), land (.+?)%\); saves (.+?) Wh of battery vs processing here\.$/,
      (m,mb,which,v,src,l,wh)=>`Éclipse : délégation de ${mb} Mo par liaison laser au voisin ${which==='leading'?'de tête':'arrière'} au soleil (valeur est. ${v}, ${src2(src)}, terre ${l} %) ; économise ${wh} Wh de batterie par rapport à un traitement ici.`],
    [/^Over (.+?) · local solar time (.+)$/, (m,a,b)=>`Au-dessus de ${a} · heure solaire locale ${b}`],
    [/^Pass over (.+)$/, (m,a)=>`Passage au-dessus de ${a}`],
    [/^(.+) \(real\)$/, (m,a)=>`${a} (réelle)`],
    [/^(.+) % vs rules$/, (m,a)=>`${a} % vs règles`],
    [/^(.+) % vs real orbit$/, (m,a)=>`${a} % vs orbite réelle`],
    [/^(.+) vs nominal$/, (m,a)=>`${a} vs nominal`],
    [/^Greedy (.+) · Rules (.+)$/, (m,a,b)=>`Glouton ${a} · Règles ${b}`],
    [/^Safety (.+)$/, (m,a)=>`Sécurité ${a}`], [/^Balanced (.+)$/, (m,a)=>`Équilibré ${a}`], [/^Value (\d.*)$/, (m,a)=>`Valeur ${a}`],
    [/^(.+)° · node (.+?) → (.+?)( · payload loses power)?$/, (m,i,n,v,p)=>`${i}° · nœud ${n} → ${tr(v)}${p?' · charge utile coupée':''}`],
    [/^(.+) % lowest battery$/, (m,a)=>`${a} % batterie minimale`], [/^(.+) Wh solar per day$/, (m,a)=>`${a} Wh solaires par jour`], [/^(.+) value per day$/, (m,a)=>`${a} de valeur par jour`],
    [/^The payload loses power (.+) % of the day\.(.*)$/, (m,a,b)=>`La charge utile perd l’alimentation ${a} % de la journée.` +
      (b.includes('edge-on') ? ' Sur ce plan, le Soleil est rasant sur les panneaux fixés au corps : ils collectent trop peu d’énergie.' : b ? ' Les éclipses sont trop longues pour cette batterie.' : '')],
    [/^of the reachable value delivered \(± (.+) pts over (.+) days\)$/, (m,a,b)=>`de la valeur atteignable livrée (± ${a} pts sur ${b} jours)`],
    [/^over a tuned rule engine with the same information, better on (.+) of (.+) days$/, (m,a,b)=>`de plus qu’un moteur à règles optimisé avec les mêmes informations, meilleur sur ${a} jours sur ${b}`],
    [/^load-sheds or hardware throttles in (.+) days; above 45 °C (.+) % of the time \(Greedy: (.+) %\)$/, (m,a,b,c)=>`délestages ou bridages matériels en ${a} jours ; au-dessus de 45 °C ${b} % du temps (glouton : ${c} %)`],
    [/^scene triage on held-out days \(raw entropy (.+) %, oracle (.+) %\)$/, (m,a,b)=>`tri des scènes sur jours de test (entropie brute ${a} %, oracle ${b} %)`],
    [/^(.+) \/ (.+) days$/, (m,a,b)=>`${a} / ${b} jours`],
    [/^E-LOTUS better than Rule-Based on (.+) of (.+) days\.$/, (m,a,b)=>`E-LOTUS meilleur que le moteur à règles sur ${a} jours sur ${b}.`],
    [/^Greedy load-sheds (.+) % of the time\.$/, (m,a)=>`Le traitement glouton déleste ${a} % du temps.`],
    [/^Greedy is throttled (.+) % of the time\.$/, (m,a)=>`Le traitement glouton est bridé ${a} % du temps.`],
    [/^(.+?) scores higher here(?: but (.+))?\.$/, (m,who,why)=>`${tr(who)} fait mieux ici${why ? ' mais ' + why.split(' and ').map(w=>trWhy(w)).join(' et ') : ''}.`],
    [/^If operators allow the 60 °C hardware limit for all jobs, E-LOTUS reaches (.+) % \(and runs hot (.+) % of the day\)\.$/, (m,a,b)=>`Si les opérateurs autorisent la limite matérielle de 60 °C pour toutes les tâches, E-LOTUS atteint ${a} % (et chauffe ${b} % de la journée).`],
    [/^Without the eclipse-aware battery floor, E-LOTUS would load-shed (.+) % of the time\.$/, (m,a)=>`Sans le seuil de batterie adapté aux éclipses, E-LOTUS délesterait ${a} % du temps.`],
    [/^median time for one decision \(worst (.+) ms\); the satellite needs one every (.+) s$/, (m,a,b)=>`temps médian d’une décision (pire cas ${a} ms) ; le satellite en a besoin d’une toutes les ${b} s`],
    [/^(.+) \((\d+) %\)$/, (m,a,b)=> FR[a] ? `${FR[a]} (${b} %)` : m],
    [/^(.+) · fire alert · (.+)$/, (m,a,b)=>`${cls(a)} · alerte feu · ${trTick(b)}`],
    [/^(cloud|ocean|coast|land|dark|clear land|polar night|fire|scene) · (.+)$/, (m,a,b)=>`${cls(a)} · ${trTick(b)}`],
  ];
  function src2(s){ return s.replace('optical','optique').replace('thermal-IR','IR thermique').replace('fire alert','alerte feu'); }
  function trWhy(w){ let r;
    if((r = w.match(/^runs above 45 °C for (.+) % of the day \(E-LOTUS (.+) %\)$/))) return `fonctionne au-dessus de 45 °C pendant ${r[1]} % de la journée (E-LOTUS ${r[2]} %)`;
    if((r = w.match(/^drains the battery to (.+) % \(E-LOTUS (.+) %\)$/))) return `vide la batterie jusqu’à ${r[1]} % (E-LOTUS ${r[2]} %)`;
    return w; }
  function trTick(s){ return s.replace(' · to leading neighbour',' · vers le voisin de tête').replace(' · to trailing neighbour',' · vers le voisin arrière'); }

  let lang = 'en';
  try { lang = localStorage.getItem('kaio-lang') === 'fr' ? 'fr' : 'en'; } catch(e){}
  const HAS_LETTER = /[A-Za-z]/;
  function tr(s){
    if(lang !== 'fr' || !s || !HAS_LETTER.test(s)) return s;
    const lead = s.match(/^\s*/)[0], trail = s.match(/\s*$/)[0], core = s.trim();
    let out = FR[core];
    if(out === undefined){ for(const [re, fn] of RULES){ const m = core.match(re); if(m){ out = core.replace(re, fn); break; } } }
    return out === undefined ? s : lead + out + trail;
  }
  window.kaioTr = tr;

  // text nodes: remember the English original of each node
  const orig = new WeakMap(), shown = new WeakMap();
  const SKIP = {SCRIPT:1, STYLE:1, CODE:1, TEXTAREA:1};
  function doNode(n){
    const p = n.parentNode; if(!p || SKIP[p.nodeName]) return;
    let en = orig.get(n);
    if(en === undefined || n.nodeValue !== shown.get(n)){ en = n.nodeValue; orig.set(n, en); }
    const v = lang === 'fr' ? tr(en) : en;
    shown.set(n, v); if(n.nodeValue !== v) n.nodeValue = v;
  }
  function walk(root){
    if(root.nodeType === 3){ doNode(root); return; }
    if(root.nodeType !== 1 || SKIP[root.nodeName]) return;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n; const list = [];
    while((n = w.nextNode())) list.push(n);
    list.forEach(doNode);
    if(root.querySelectorAll) [root, ...root.querySelectorAll('[aria-label],[title]')].forEach(doAttrs);
  }
  const ATTR = ['aria-label','title'];
  function doAttrs(el){ if(!el.getAttribute) return; ATTR.forEach(a=>{ const v = el.getAttribute(a); if(v == null) return;
    const key = 'i18n' + a.replace('-',''); if(el.dataset[key] === undefined || (v !== tr(el.dataset[key]) && v !== el.dataset[key])) el.dataset[key] = v;
    const want = lang === 'fr' ? tr(el.dataset[key]) : el.dataset[key]; if(v !== want) el.setAttribute(a, want); }); }

  const mo = new MutationObserver(muts=>{ for(const m of muts){
    if(m.type === 'characterData') doNode(m.target);
    else m.addedNodes.forEach(walk); } });
  mo.observe(document.documentElement, {childList:true, subtree:true, characterData:true});

  // canvas labels
  const ft = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function(t, ...a){ return ft.call(this, typeof t === 'string' ? tr(t) : t, ...a); };

  function setLang(l){
    lang = l === 'fr' ? 'fr' : 'en';
    try { localStorage.setItem('kaio-lang', lang); } catch(e){}
    document.documentElement.lang = lang;
    walk(document.body);
    document.querySelectorAll('[data-lang-set]').forEach(b=>b.setAttribute('aria-pressed', String(b.dataset.langSet === lang)));
    window.dispatchEvent(new Event('resize'));   // canvases redraw with translated labels
  }
  window.kaioSetLang = setLang;
  window.kaioAddFR = d => { Object.assign(FR, d); if(lang === 'fr') walk(document.body); };
  window.kaioLang = () => lang;
  document.documentElement.lang = lang;
  document.addEventListener('DOMContentLoaded', ()=>{
    document.querySelectorAll('[data-lang-set]').forEach(b=>b.addEventListener('click', ()=>setLang(b.dataset.langSet)));
    setLang(lang);
  });
})();
