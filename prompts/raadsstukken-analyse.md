# Prompt: Analyse van raadsstukken over een specifiek dossier

Gebruik deze prompt als template voor het analyseren van gemeentelijke raadsstukken over een willekeurig beleidsonderwerp. Vervang de tekst tussen `[rechte haken]` door de specifieke invulling voor het dossier dat je wilt onderzoeken.

---

## Prompt 1 — Huidige stand van zaken

```
Lees alle bestanden in deze map. Zoek alles wat te vinden is over [onderwerp],
specifiek:

- [Perspectief A: bijv. bewoners die willen blijven / groep die aanspraak maakt op voorziening]
- [Perspectief B: bijv. nieuwe instroom / lopende procedures / opvang]

Geef mij op basis van de raadsstukken het volgende:

1. **Grote lijnen en tijdlijn**: Wat zijn de belangrijkste ontwikkelingen geweest,
   in chronologische volgorde?

2. **Hoofddiscussies**: Waar heeft men het over? Wat zijn de grootste
   discussiepunten? Waar botsen visies?

3. **Genomen beslissingen**: Welke besluiten zijn er de afgelopen periode genomen?
   Wat is vastgesteld, wat is afgewezen?

4. **Openstaande punten**: Welke zaken liggen nog open ter discussie?
   Waar komt men niet uit? Wat is nog niet besloten?

5. **Overlast of klachten**: Zijn er meldingen van overlast, incidenten of klachten
   gerelateerd aan [onderwerp of doelgroep]? Wie heeft daar last van,
   en wat is de aard van de overlast?

6. **Politieke posities**: Wat zijn de standpunten van de verschillende
   politieke partijen over [onderwerp]? Geef per partij de hoofdlijn,
   de argumenten, en hoe zij hebben gestemd of zich hebben uitgesproken.

Presenteer de uitkomst gestructureerd met kopjes. Gebruik citaten uit de stukken
waar dat de analyse ondersteunt. Vermeld bij besluiten altijd de datum en
stemverhouding als die beschikbaar zijn.
```

---

## Prompt 2 — Vooruitblik

```
Op basis van de raadsstukken die je hebt gelezen over [onderwerp]:
werp een blik in de toekomst.

Wat kan ik de komende 3 maanden, en de komende 6 tot 9 maanden verwachten?

Geef mij:

1. **Lopende discussies**: Welke debatten lopen nog door en verwacht je
   de komende maanden?

2. **Aankomende beslismomenten**: Waarover moet de raad of het college
   nog een besluit nemen? Wat ligt er op de agenda of staat er aan te komen?

3. **Kritieke onzekerheden**: Welke factoren kunnen de ontwikkeling
   versnellen, vertragen of kantelen? Wat zijn de splijtzwammen?

4. **Externe invloeden**: Zijn er landelijke wetgeving, rechterlijke uitspraken,
   Europese regelgeving of andere externe factoren die de komende maanden
   van invloed zijn op dit dossier?

5. **Politieke posities per verwacht discussiepunt**: Hoe zullen de
   verschillende partijen naar verwachting staan tegenover de aankomende
   beslissingen? Geef per partij een verwachte positie en de redenering
   daarachter, gebaseerd op eerder ingenomen standpunten.

Werk per tijdshorizon (3 maanden / 6-9 maanden) en gebruik een tabel
voor de partijposities waar dat de leesbaarheid vergroot.
```

---

## Instructies voor hergebruik

1. **Vul `[onderwerp]` in** — bijv. *woningbouw*, *verkeer en mobiliteit*, *jeugdzorg*, *duurzaamheid*
2. **Vul `[Perspectief A en B]` in** — de twee kanten van het dossier die je wilt onderzoeken
3. **Vul `[doelgroep]` in bij overlast** — de groep of het project waarover klachten kunnen bestaan
4. **Beide prompts werken zelfstandig**, maar zijn sterker in combinatie: eerst Prompt 1 voor de analyse, dan Prompt 2 voor de vooruitblik
5. **Zorg dat de raadsstukken beschikbaar zijn** in de werkmap voordat je de prompt uitvoert

---

## Instructies voor Claude: rapport opslaan en alert aanbieden

*Dit gedeelte is een instructie aan Claude, niet aan de gebruiker. Het beschrijft wat Claude moet doen op het moment dat de gebruiker aangeeft het rapport te willen opslaan.*

Wanneer de gebruiker vraagt om de analyse op te slaan als Markdown-bestand — met woorden als "leg dit vast", "sla dit op als rapport" of "schrijf dit weg" — doe dan het volgende:

**Stap 1 — Sla het rapport op**

Schrijf de volledige analyse naar een Markdown-bestand. Gebruik als bestandsnaam:

```
~/Documents/notulen/<gemeente>/YYYY-MM-DD - onderzoek-<onderwerp>.md
```

**Stap 2 — Bied eenmalig de alert aan**

Doe dit aanbod pas nádat het rapport is opgeslagen. Niet eerder, niet na elke tussentijdse prompt.

Destilleer uit de analyse 8 tot 12 trefwoorden die de gemeente zelf gebruikt in de stukken — niet de woorden die de journalist veronderstelde, maar de taal die terugkomt in de documenten. Presenteer ze als concreet voorstel.

Stel daarna deze twee vragen:

> "Het rapport is opgeslagen. Wil je dat ik een wekelijkse alert instel die je waarschuwt als er nieuwe raadsstukken verschijnen over dit onderwerp?
>
> Op basis van de analyse stel ik deze trefwoorden voor:
> `[trefwoord1]`, `[trefwoord2]`, `[trefwoord3]` ...
>
> Pas de lijst aan als je wilt, en geef aan hoe vaak je een update wilt: **wekelijks** of **maandelijks**."

**Stap 3 — Maak het dossier aan**

Zodra de gebruiker akkoord gaat, voer dan dit commando uit vanuit de toolkit-map:

```bash
python3 /Users/erwin/Documents/lokaalbestuur-toolkit/toolkit.py nieuw-alert \
  --dossier <onderwerp> \
  --orgaan <orgaan> \
  --trefwoorden "<woord1>,<woord2>,<woord3>" \
  --frequentie wekelijks
```

Vervang `<onderwerp>`, `<orgaan>`, `<woord1>` etc. door de werkelijke waarden uit de analyse en het gesprek. Het commando maakt de dossier JSON aan en voegt automatisch de crontabregel toe.
