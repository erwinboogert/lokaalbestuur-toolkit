# Prompt: Budgetanalyse

Gebruik deze prompt om financiële keuzes in raadsstukken te analyseren: begrotingen, subsidies, kostenoverschrijdingen en verschuivingen in budgetten. Geld vertelt een verhaal dat beleidswoorden soms verhullen.

Deze prompt werkt op raadsstukken en begrotingsdocumenten. Voor vergelijking met andere gemeenten, zie ook `vergelijking.md`.

Vervang de tekst tussen `[rechte haken]` door de invulling voor jouw dossier.

---

## Prompt 1 — Wat wordt er uitgegeven?

```
Lees de raadsstukken en begrotingsdocumenten in deze map.
Analyseer alles wat te vinden is over de financiën rondom [onderwerp].

Geef mij:

1. **Overzicht van bedragen**: Welke bedragen worden genoemd in verband
   met [onderwerp]? Maak onderscheid tussen:
   - Begrote bedragen (wat was de planning)
   - Werkelijke uitgaven (wat is er daadwerkelijk uitgegeven)
   - Reserveringen of potjes (wat staat er klaar maar is nog niet uitgegeven)

2. **Herkomst van het geld**: Waar komt het geld vandaan?
   Gemeentelijke middelen, rijkssubsidie, provinciale bijdrage,
   Europese fondsen, of een combinatie?

3. **Kostenoverschrijdingen of -onderschrijdingen**: Zijn er gevallen
   waarbij het uiteindelijke bedrag afweek van de begroting?
   Hoe groot was die afwijking, en wat was de verklaring?

4. **Vergelijking in de tijd**: Is het budget voor [onderwerp] de afgelopen
   jaren gegroeid, gekrompen of gelijkgebleven? Zijn er opvallende
   verschuivingen in een specifiek jaar?

5. **Wat ontbreekt**: Zijn er kostenposten die je zou verwachten maar
   die niet terug te vinden zijn in de stukken?

Vermeld bij elk bedrag de bron (document, datum, pagina indien bekend).
Gebruik waar mogelijk een tabel.
```

---

## Prompt 2 — Wat vertellen de cijfers?

```
Je hebt zojuist de financiën rondom [onderwerp] in [gemeente/orgaan] in kaart gebracht.

Analyseer nu wat de cijfers journalistiek betekenen:

1. **Prioriteit**: Hoeveel procent van het totale gemeentebudget gaat naar
   [onderwerp]? Is dat veel of weinig vergeleken met wat politiek
   werd beloofd of wat er maatschappelijk speelt?

2. **Rode vlaggen**: Zijn er financiële signalen die vragen oproepen?
   Denk aan: onverklaarde stijgingen, weggevallen posten, vage omschrijvingen
   van wat geld wordt besteed, of grote reserves die niet worden ingezet.

3. **Politieke keuzes zichtbaar in geld**: Welke politieke prioriteiten
   zijn terug te zien in de budgettaire keuzes? Welke partijen hebben
   gevochten voor of tegen bepaalde posten?

4. **Wat ik verder moet uitzoeken**: Welke financiële vragen kan ik
   niet beantwoorden op basis van de raadsstukken alleen?
   Wat zou ik op moeten vragen via een WOO-verzoek of een gesprek
   met de financieel woordvoerder?
```

---

## Instructies voor hergebruik

1. **Zorg voor begrotingsstukken** — de gewone raadsstukken bevatten soms financiële informatie, maar de begroting en jaarrekening zijn de hoofdbronnen; download die expliciet
2. **Begin met Prompt 1** voor het feitenoverzicht, gebruik Prompt 2 voor de interpretatie
3. **Combineer met vergelijking** — `vergelijking.md` helpt bij het contextualiseren van bedragen ten opzichte van andere gemeenten
4. **WOO-verzoek als vervolgstap** — gebruik `/wob-verzoek` als de stukken onvoldoende financiële detail bevatten
