// scrape.jsx — Scrapen-scherm met echte SSE-voortgang

const scrapeStyles = {
  tabs: {
    display: 'flex', gap: 0,
    borderBottom: '1px solid var(--border)', marginBottom: 24,
  },
  tab: (active) => ({
    padding: '10px 18px 12px',
    fontSize: 13,
    color: active ? 'var(--text)' : 'var(--muted)',
    fontWeight: active ? 600 : 500,
    borderBottom: `2px solid ${active ? 'var(--accent)' : 'transparent'}`,
    marginBottom: -1, cursor: 'pointer', letterSpacing: '-0.005em',
    display: 'flex', alignItems: 'center', gap: 8,
    transition: 'color 80ms',
  }),
  field: { display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 },
  fieldLabel: {
    fontFamily: 'var(--font-mono)', fontSize: 10,
    color: 'var(--dim)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 500,
  },
  fieldHint: { fontSize: 11.5, color: 'var(--muted)', marginTop: -2 },
  select: {
    width: '100%', padding: '9px 12px',
    background: 'oklch(0.215 0.005 70)',
    border: '1px solid var(--border)', borderRadius: 'var(--r-2)',
    color: 'var(--text)', fontFamily: 'var(--font-ui)', fontSize: 13, appearance: 'none',
    backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%238a8278' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E\")",
    backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center', paddingRight: 30,
  },
  radioGroup: {
    display: 'flex', gap: 6,
    background: 'oklch(0.21 0.005 70)', border: '1px solid var(--border)',
    padding: 3, borderRadius: 'var(--r-2)', width: 'fit-content',
  },
  radio: (active) => ({
    padding: '7px 14px',
    background: active ? 'oklch(0.28 0.005 70)' : 'transparent',
    color: active ? 'var(--text)' : 'var(--text-2)',
    fontSize: 12.5, fontWeight: active ? 600 : 500,
    fontFamily: 'var(--font-mono)', borderRadius: 3, cursor: 'pointer',
    border: active ? '1px solid var(--border-2)' : '1px solid transparent',
  }),
  toggleWrap: {
    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
    background: 'oklch(0.21 0.005 70)', border: '1px solid var(--border)',
    borderRadius: 'var(--r-2)', cursor: 'pointer',
  },
  toggle: (on) => ({
    width: 32, height: 18, borderRadius: 10,
    background: on ? 'var(--accent)' : 'oklch(0.30 0.005 70)',
    position: 'relative', flexShrink: 0, transition: 'background 120ms',
  }),
  toggleDot: (on) => ({
    position: 'absolute', top: 2, left: on ? 16 : 2,
    width: 14, height: 14, borderRadius: '50%',
    background: on ? 'var(--accent-ink)' : 'oklch(0.85 0.003 80)',
    transition: 'left 140ms',
  }),
};

const TABS = [
  { id: 'pakket',           label: 'Via gemeente',         type: null },
  { id: 'gemeente',         label: 'Gemeente',             type: 'gemeente' },
  { id: 'gr',               label: "GR's",                 type: 'gr' },
  { id: 'waterschap',       label: 'Waterschap',           type: 'waterschap' },
  { id: 'veiligheidsregio', label: "Veiligheidsregio",    type: 'veiligheidsregio' },
  { id: 'provincie',        label: 'Provincie',            type: 'provincie' },
];

function Scrape({ onNavigate }) {
  const [tabIdx, setTabIdx]   = React.useState(0);
  const [stap, setStap]       = React.useState('idle');
  const [jobId, setJobId]     = React.useState(null);
  const [orgaan, setOrgaan]   = React.useState('');
  const [orgType, setOrgType] = React.useState('gemeente');
  const [periode, setPeriode] = React.useState(24);
  const [simuleer, setSimuleer] = React.useState(false);
  const [geindexeerd, setGeindexeerd] = React.useState(false);
  const [samenvatting, setSamenvatting] = React.useState(null);

  // Pakket-tab staat: bewaard hier zodat verkennen-resultaat intact blijft tijdens/na een scrape
  const [pakketGemeente, setPakketGemeente] = React.useState('');
  const [pakketResultaat, setPakketResultaat] = React.useState(null);

  const activeTab = TABS[tabIdx];

  // typeOverride: gebruikt vanuit ScrapeGemeentePakket waar het type niet uit de tab komt
  // indexNaScrape: of er na de download ook automatisch geïndexeerd moet worden
  const handleStart = async (org, per, sim, typeOverride, indexNaScrape = true) => {
    const type = typeOverride !== undefined ? typeOverride : activeTab.type;
    try {
      const resp = await fetch('/api/scrapen/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type, orgaan: org, periode: per, simuleer: sim,
          index_na_scrape: indexNaScrape,
        }),
      });
      const data = await resp.json();
      if (data.fout) { alert(data.fout); return; }
      setJobId(data.job_id);
      setOrgaan(org);
      setOrgType(type);
      setPeriode(per);
      setSimuleer(sim);
      setGeindexeerd(!!data.geindexeerd);
      setStap('progress');
    } catch (e) {
      alert(`Kon scraper niet starten: ${e.message}`);
    }
  };

  const handleDone = (sam) => {
    setSamenvatting(sam);
    setStap('done');
  };

  const handleIndexeer = async () => {
    try {
      const resp = await fetch('/api/index/bijwerken', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orgaan }),
      });
      const data = await resp.json();
      if (data.job_id) {
        setJobId(data.job_id);
        setSamenvatting(null);
        setStap('indexing');
      }
    } catch (e) {
      alert(`Kan indexering niet starten: ${e.message}`);
    }
  };

  const handleIndexDone = () => {
    setStap('idle');
    if (onNavigate) onNavigate('zoeken');
  };

  const handleDownloadEcht = () => {
    // Zelfde orgaan, type en periode als de simulatie, maar nu echt downloaden
    handleStart(orgaan, periode, false, orgType);
  };

  return (
    <>
      {/* Tabs */}
      <div style={scrapeStyles.tabs}>
        {TABS.map((t, i) => (
          <div key={t.id} style={scrapeStyles.tab(i === tabIdx)}
               onClick={() => { setTabIdx(i); setStap('idle'); }}>
            {t.label}
          </div>
        ))}
        <div style={{ flex: 1, borderBottom: '1px solid var(--border)' }}></div>
      </div>

      {stap === 'idle' && activeTab.id === 'pakket' && (
        <ScrapeGemeentePakket
          onStart={handleStart}
          gemeente={pakketGemeente}
          onGemeenteChange={setPakketGemeente}
          resultaat={pakketResultaat}
          onResultaat={setPakketResultaat}
        />
      )}
      {stap === 'idle' && activeTab.id !== 'pakket' && (
        <ScrapeIdle orgaanType={activeTab.type} onStart={handleStart} />
      )}
      {stap === 'progress' && <ScrapeProgress jobId={jobId} orgaan={orgaan} periode={periode}
                                               simuleer={simuleer}
                                               geindexeerd={geindexeerd}
                                               onDone={handleDone}
                                               onCancel={() => setStap('idle')} />}
      {stap === 'indexing' && <ScrapeProgress jobId={jobId} orgaan={orgaan} periode={0}
                                               simuleer={false}
                                               titel="Indexeren"
                                               onDone={handleIndexDone}
                                               onCancel={handleIndexDone} />}
      {stap === 'done'     && <ScrapeDone orgaan={orgaan} samenvatting={samenvatting}
                                           geindexeerd={geindexeerd}
                                           onIndexeer={handleIndexeer}
                                           onDownloadEcht={handleDownloadEcht}
                                           onNaarZoeken={() => onNavigate && onNavigate('zoeken')}
                                           onLater={() => setStap('idle')} />}
    </>
  );
}

function ScrapeIdle({ orgaanType, onStart }) {
  const [orgaan, setOrgaan]   = React.useState('');
  const [periode, setPeriode] = React.useState(24);
  const [simuleer, setSimuleer] = React.useState(false);
  const [indexNaScrape, setIndexNaScrape] = React.useState(true);
  const [opties, setOpties]   = React.useState([]);

  React.useEffect(() => {
    // Geconfigureerde organen laden als snel suggestie
    fetch('/api/organen')
      .then(r => r.json())
      .then(organen => {
        const gefilterd = organen
          .filter(o => {
            const t = o.type || 'gemeente';
            if (orgaanType === 'gemeente') return t === 'gemeente';
            return t === orgaanType;
          })
          .map(o => o._slug);
        setOpties(gefilterd);
        if (gefilterd.length > 0 && !orgaan) setOrgaan(gefilterd[0]);
      })
      .catch(() => {});
    // Gemeenten ook ophalen voor autocomplete
    if (orgaanType === 'gemeente') {
      fetch('/api/gemeenten').then(r => r.json()).then(g => {
        setOpties(g);
        if (g.length > 0 && !orgaan) setOrgaan(g[0]);
      }).catch(() => {});
    }
  }, [orgaanType]);

  const typeLabel = {
    gemeente: 'Gemeente', gr: 'Gemeenschappelijke regeling',
    waterschap: 'Waterschap', veiligheidsregio: 'Veiligheidsregio', provincie: 'Provincie',
  }[orgaanType] || orgaanType;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
      <div>
        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: 26, fontWeight: 600,
          letterSpacing: '-0.02em', margin: '0 0 6px', color: 'var(--text)',
        }}>Documenten ophalen — {typeLabel}</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13, margin: '0 0 28px', lineHeight: 1.55, maxWidth: 460 }}>
          Bronnenboek leest het raadsinformatiesysteem en downloadt alle openbare
          vergaderstukken naar je lokale schijf.
        </p>

        <div style={scrapeStyles.field}>
          <label style={scrapeStyles.fieldLabel}>{typeLabel}</label>
          <input
            list="orgaan-opties"
            value={orgaan}
            onChange={e => setOrgaan(e.target.value)}
            placeholder={`Typ een ${typeLabel.toLowerCase()}-naam…`}
            style={{
              ...scrapeStyles.select,
              backgroundImage: 'none',
            }}
          />
          <datalist id="orgaan-opties">
            {opties.map(o => <option key={o} value={o} />)}
          </datalist>
          <div style={scrapeStyles.fieldHint}>
            {opties.length > 0 ? `${opties.length} beschikbaar` : 'Laden…'}
          </div>
        </div>

        <div style={scrapeStyles.field}>
          <label style={scrapeStyles.fieldLabel}>Terugkijkperiode</label>
          <div style={scrapeStyles.radioGroup}>
            {[6, 12, 18, 24].map(p => (
              <div key={p} onClick={() => setPeriode(p)} style={scrapeStyles.radio(periode === p)}>
                {p} mnd
                {p === 24 && <sup style={{ color: 'var(--accent)', fontFamily: 'var(--font-mono)', fontSize: 8, marginLeft: 3 }}>★</sup>}
              </div>
            ))}
          </div>
          <div style={scrapeStyles.fieldHint}>
            24 maanden = aanbevolen. Dekt {'>'} 90% van relevante stukken.
          </div>
        </div>

        <div style={scrapeStyles.field}>
          <label style={scrapeStyles.fieldLabel}>Modus</label>
          <div style={scrapeStyles.toggleWrap} onClick={() => setSimuleer(!simuleer)}>
            <div style={scrapeStyles.toggle(simuleer)}>
              <div style={scrapeStyles.toggleDot(simuleer)}></div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, color: 'var(--text)' }}>Eerst simuleren</div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                Lijst tonen zonder te downloaden. Aanrader voor een onbekend orgaan.
              </div>
            </div>
            <Mono color={simuleer ? 'var(--accent)' : 'var(--dim)'} size={10.5}>
              {simuleer ? 'AAN' : 'UIT'}
            </Mono>
          </div>
        </div>

        <div style={scrapeStyles.field}>
          <label style={scrapeStyles.fieldLabel}>Na download</label>
          <div
            style={{ ...scrapeStyles.toggleWrap, opacity: simuleer ? 0.5 : 1 }}
            onClick={() => !simuleer && setIndexNaScrape(!indexNaScrape)}
          >
            <div style={scrapeStyles.toggle(indexNaScrape && !simuleer)}>
              <div style={scrapeStyles.toggleDot(indexNaScrape && !simuleer)}></div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, color: 'var(--text)' }}>Automatisch doorzoekbaar maken</div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                {simuleer
                  ? 'Niet van toepassing bij simulatie.'
                  : 'Direct na de download de zoekindex bijwerken.'}
              </div>
            </div>
            <Mono color={indexNaScrape && !simuleer ? 'var(--accent)' : 'var(--dim)'} size={10.5}>
              {indexNaScrape && !simuleer ? 'AAN' : 'UIT'}
            </Mono>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
          <Btn primary
               onClick={() => orgaan && onStart(orgaan, periode, simuleer, undefined, indexNaScrape)}
               disabled={!orgaan}>
            {simuleer ? 'Start simulatie' : 'Start download'} →
          </Btn>
        </div>
      </div>

      {/* Rechter paneel: info */}
      <div>
        <SectionHead kicker="Info" title={orgaan || typeLabel} />
        <div style={{
          background: 'oklch(0.185 0.005 70)', border: '1px solid var(--rule)',
          borderRadius: 'var(--r-2)', padding: '16px 18px',
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {[
            ['Terugkijkperiode', `${periode} maanden`],
            ['Modus', simuleer ? 'Simuleren (droog)' : 'Echt downloaden'],
            ['Opgeslagen in', `~/Documents/notulen/${orgaan || '…'}`],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
              <span style={{ color: 'var(--muted)' }}>{k}</span>
              <Mono color="var(--text)">{v}</Mono>
            </div>
          ))}
        </div>

        <div style={{
          marginTop: 18, padding: '12px 14px',
          borderLeft: '2px solid var(--accent)',
          background: 'var(--accent-soft)',
          fontSize: 12, color: 'var(--text-2)', lineHeight: 1.55,
        }}>
          <strong style={{ color: 'var(--text)' }}>Let op.</strong>{' '}
          Bronnenboek wacht 1,5s tussen verzoeken en respecteert de API-limieten.
          Onderbreken kan altijd — voortgang wordt bewaard.
        </div>
      </div>
    </div>
  );
}

function ScrapeProgress({ jobId, orgaan, periode, simuleer, geindexeerd, titel, onDone, onCancel }) {
  const [regels, setRegels]           = React.useState([]);
  const [nieuw, setNieuw]             = React.useState(0);
  const [fouten, setFouten]           = React.useState(0);
  const [vergaderingen, setVergaderingen] = React.useState([]);
  const [klaar, setKlaar]             = React.useState(false);
  const [huidigeStap, setHuidigeStap] = React.useState(null);   // {index, totaal, label}
  const esRef = React.useRef(null);

  // Refs om stale-closure te vermijden in de onmessage-callback
  const nieuwRef       = React.useRef(0);
  const foutenRef      = React.useRef(0);
  const overgeslagenRef = React.useRef(0);
  const vergRef        = React.useRef([]);

  React.useEffect(() => {
    nieuwRef.current       = 0;
    foutenRef.current      = 0;
    overgeslagenRef.current = 0;
    vergRef.current        = [];
    setHuidigeStap(null);
  }, [jobId]);

  React.useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`/api/scrapen/stream/${jobId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      let data;
      try { data = JSON.parse(e.data); } catch { return; }

      if (data.type === 'done') {
        es.close();
        setKlaar(true);
        onDone({
          nieuw:         nieuwRef.current,
          fouten:        foutenRef.current,
          overgeslagen:  overgeslagenRef.current,
          vergaderingen: vergRef.current,
          simuleer,
        });
        return;
      }

      if (data.type === 'stap') {
        setHuidigeStap({ index: data.index, totaal: data.totaal, label: data.label });
        return;
      }

      if (data.type === 'log' && data.text) {
        const tekst = data.text;
        setRegels(prev => [tekst, ...prev].slice(0, 80));

        // Eindstatistieken uit samenvattingsblok
        const mNieuw = tekst.match(/Nieuw gedownload\s*:\s*(\d+)/);
        if (mNieuw) {
          const n = parseInt(mNieuw[1]);
          nieuwRef.current = n;
          setNieuw(n);
        }

        const mOverg = tekst.match(/Al aanwezig\s*:\s*(\d+)/);
        if (mOverg) {
          overgeslagenRef.current = parseInt(mOverg[1]);
        }

        const mFout = tekst.match(/Fouten\s*:\s*(\d+)/);
        if (mFout) {
          const f = parseInt(mFout[1]);
          foutenRef.current = f;
          setFouten(f);
        }

        if (tekst.includes('! FOUT') || tekst.includes('! fout')) {
          foutenRef.current += 1;
          setFouten(f => f + 1);
        }

        // Live tellen tijdens de run
        if (simuleer && tekst.includes('[DROOG]')) {
          nieuwRef.current += 1;
          setNieuw(n => n + 1);
        } else if (!simuleer && tekst.trim().startsWith('+ ')) {
          nieuwRef.current += 1;
          setNieuw(n => n + 1);
        }

        // Vergadering-headers: "  Naam (datum) — N nieuw van M"
        const mVerg = tekst.match(/^\s{2}(.+?)\s*\((\d{4}-\d{2}-\d{2})\)\s*[—-]\s*(\d+)\s*nieuw\s*van\s*(\d+)/);
        if (mVerg) {
          const verg = {
            naam:   mVerg[1].trim(),
            datum:  mVerg[2],
            nieuw:  parseInt(mVerg[3]),
            totaal: parseInt(mVerg[4]),
          };
          vergRef.current = [...vergRef.current, verg];
          setVergaderingen(v => [...v, verg]);
        }
      }
    };

    es.onerror = () => es.close();
    return () => es.close();
  }, [jobId]);

  const titelTekst  = titel || `${orgaan} — ${simuleer ? 'simuleren' : 'downloaden'}`;
  const statLabel   = simuleer ? 'gevonden' : 'nieuw gedownload';
  const toonStapBar = huidigeStap && huidigeStap.totaal > 1;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 4 }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                     fontSize: 22, letterSpacing: '-0.02em', margin: 0 }}>
          {titelTekst}
        </h1>
        {!klaar && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--green)',
                           animation: 'pulse 1.4s ease-in-out infinite' }}></span>
            <Mono color="var(--green)">live</Mono>
          </div>
        )}
      </div>

      {toonStapBar && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
          <Mono color="var(--accent)" size={10.5}>
            STAP {huidigeStap.index + 1} / {huidigeStap.totaal}
          </Mono>
          <span style={{ fontSize: 13, color: 'var(--text-2)' }}>{huidigeStap.label}</span>
        </div>
      )}

      {/* Voortgang */}
      <div style={{
        marginTop: 22, padding: '20px 22px',
        background: 'oklch(0.19 0.005 70)',
        border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <span style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                           fontSize: 32, letterSpacing: '-0.02em', color: 'var(--text)',
                           fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
              {nieuw.toLocaleString('nl-NL')}
            </span>
            <Mono color="var(--text-2)" size={13}>{statLabel}</Mono>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 18 }}>
            <div>
              <Mono color="var(--dim)" size={10}>FOUTEN</Mono>{' '}
              <Mono color={fouten > 0 ? 'var(--red)' : 'var(--text)'} size={12}>{fouten}</Mono>
            </div>
          </div>
        </div>
        <ProgressBar pct={0} kind="green" label={false} height={8} indeterminate={!klaar} />
      </div>

      {/* Live log */}
      <div style={{ marginTop: 24 }}>
        <Mono color="var(--dim)" size={10}>LIVE LOG · meest recent bovenaan</Mono>
        <div style={{
          marginTop: 8, border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          background: 'oklch(0.135 0.005 70)', fontFamily: 'var(--font-mono)',
          fontSize: 11.5, maxHeight: 360, overflowY: 'auto',
        }}>
          {regels.length === 0 ? (
            <div style={{ padding: '14px 16px', color: 'var(--dim)' }}>Verbinden met scraper…</div>
          ) : (
            regels.map((r, i) => {
              const isFout = r.includes('FOUT') || r.includes('fout') || r.startsWith('    !');
              const isOk   = r.trim().startsWith('+');
              const fg = isFout ? 'var(--red)' : isOk ? 'var(--green)' : 'var(--text-2)';
              return (
                <div key={i} style={{
                  padding: '5px 14px',
                  borderBottom: i < regels.length - 1 ? '1px solid oklch(0.18 0.005 70)' : 'none',
                  color: fg,
                  background: isFout ? 'oklch(0.21 0.04 25 / 0.25)' : 'transparent',
                }}>{r || ' '}</div>
              );
            })
          )}
        </div>
      </div>

      <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
        {!klaar && <Btn danger onClick={() => { esRef.current?.close(); onCancel(); }}>Annuleren</Btn>}
        {klaar  && <Mono color="var(--green)">Klaar ✓</Mono>}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 oklch(0.76 0.15 148 / 0.6); }
          50%       { box-shadow: 0 0 0 6px oklch(0.76 0.15 148 / 0); }
        }
      `}</style>
    </div>
  );
}

function ScrapeDone({ orgaan, samenvatting = {}, geindexeerd, onIndexeer, onNaarZoeken, onLater, onDownloadEcht }) {
  const nieuw         = samenvatting.nieuw         || 0;
  const fouten        = samenvatting.fouten        || 0;
  const overgeslagen  = samenvatting.overgeslagen  || 0;
  const simuleer      = samenvatting.simuleer      || false;
  const vergaderingen = samenvatting.vergaderingen || [];

  // ── Simulate-resultaat ────────────────────────────────────────────────────
  if (simuleer) {
    return (
      <div style={{ position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 14 }}>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                       fontSize: 24, letterSpacing: '-0.02em', margin: 0 }}>
            {orgaan} — simulatie klaar
          </h1>
          <Badge kind="accent">droog</Badge>
        </div>

        {/* Stats */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
          border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          background: 'oklch(0.185 0.005 70)', overflow: 'hidden', marginBottom: 24,
        }}>
          {[
            { k: 'Te downloaden', v: String(nieuw),        s: 'nieuwe documenten',  c: 'var(--accent)' },
            { k: 'Al aanwezig',   v: String(overgeslagen), s: 'overgeslagen',        c: 'var(--text-2)' },
            { k: 'Orgaan',        v: orgaan,                s: '',                   c: 'var(--text)' },
          ].map((s, i) => (
            <div key={i} style={{
              padding: '18px 22px',
              borderRight: i < 2 ? '1px solid var(--rule)' : 'none',
              display: 'flex', flexDirection: 'column', gap: 4,
            }}>
              <Mono color="var(--dim)" size={10}>{s.k.toUpperCase()}</Mono>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 600,
                            color: s.c, letterSpacing: '-0.02em', lineHeight: 1,
                            fontVariantNumeric: 'tabular-nums' }}>{s.v}</div>
              {s.s && <Mono color="var(--muted)" size={11}>{s.s}</Mono>}
            </div>
          ))}
        </div>

        {/* Vergadering-breakdown */}
        {vergaderingen.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Mono color="var(--dim)" size={10}>VERGADERINGEN MET NIEUWE STUKKEN</Mono>
            <div style={{
              marginTop: 8, border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
              background: 'oklch(0.135 0.005 70)', fontFamily: 'var(--font-mono)',
              fontSize: 11.5, maxHeight: 240, overflowY: 'auto',
            }}>
              {vergaderingen.map((v, i) => (
                <div key={i} style={{
                  padding: '8px 14px',
                  borderBottom: i < vergaderingen.length - 1 ? '1px solid oklch(0.18 0.005 70)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <span style={{ color: 'var(--text-2)' }}>{v.naam}</span>
                    <span style={{ color: 'var(--dim)', marginLeft: 12, fontSize: 11 }}>{v.datum}</span>
                  </div>
                  <Mono color="var(--accent)" size={11}>{v.nieuw} nieuw van {v.totaal}</Mono>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA: nu echt downloaden */}
        <div style={{
          border: '1px solid var(--border-2)',
          background: 'oklch(0.215 0.008 70)',
          borderRadius: 'var(--r-2)', padding: '22px 24px',
          display: 'grid', gridTemplateColumns: '1fr auto',
          gap: 24, alignItems: 'center',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: -1, left: 24, width: 60, height: 2,
            background: 'var(--accent)',
          }}></div>
          <div>
            <Mono color="var(--accent)" size={10}>VERVOLGSTAP</Mono>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                         fontSize: 22, letterSpacing: '-0.02em',
                         margin: '4px 0 8px', color: 'var(--text)' }}>
              {nieuw > 0
                ? `${nieuw} documenten staan klaar — nu echt downloaden?`
                : 'Alles al aanwezig — niets te downloaden.'}
            </h2>
            <p style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55, margin: 0 }}>
              {nieuw > 0
                ? 'De simulatie is klaar. Klik hiernaast om alle gevonden stukken daadwerkelijk op te slaan.'
                : 'Er zijn geen nieuwe documenten gevonden. Alles is al aanwezig op schijf.'}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
            {nieuw > 0 && onDownloadEcht && (
              <Btn primary onClick={onDownloadEcht}>Ja, download echt →</Btn>
            )}
            <Btn ghost onClick={onLater}>← Terug</Btn>
          </div>
        </div>
      </div>
    );
  }

  // ── Echte download voltooid ───────────────────────────────────────────────
  return (
    <div style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 14 }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                     fontSize: 24, letterSpacing: '-0.02em', margin: 0 }}>
          {orgaan} — voltooid
        </h1>
        <Badge kind="klaar">klaar</Badge>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
        background: 'oklch(0.185 0.005 70)', overflow: 'hidden', marginBottom: 24,
      }}>
        {[
          { k: 'Nieuwe documenten', v: String(nieuw),  s: 'gedownload', c: 'var(--accent)' },
          { k: 'Fouten',            v: String(fouten), s: 'zie log',    c: fouten > 0 ? 'var(--red)' : 'var(--text-2)' },
          { k: 'Orgaan',            v: orgaan,         s: '',           c: 'var(--text)' },
        ].map((s, i) => (
          <div key={i} style={{
            padding: '18px 22px',
            borderRight: i < 2 ? '1px solid var(--rule)' : 'none',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            <Mono color="var(--dim)" size={10}>{s.k.toUpperCase()}</Mono>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 600,
                          color: s.c, letterSpacing: '-0.02em', lineHeight: 1,
                          fontVariantNumeric: 'tabular-nums' }}>{s.v}</div>
            {s.s && <Mono color="var(--muted)" size={11}>{s.s}</Mono>}
          </div>
        ))}
      </div>

      {/* Indexeer-dialoog: alleen tonen als er nieuwe docs zijn en nog niet geïndexeerd */}
      {nieuw > 0 && !geindexeerd && (
        <div style={{
          border: '1px solid var(--border-2)',
          background: 'oklch(0.215 0.008 70)',
          borderRadius: 'var(--r-2)', padding: '22px 24px',
          display: 'grid', gridTemplateColumns: '1fr auto',
          gap: 24, alignItems: 'center',
          boxShadow: '0 16px 40px oklch(0 0 0 / 0.35)',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: -1, left: 24, width: 60, height: 2,
            background: 'var(--accent)',
          }}></div>
          <div>
            <Mono color="var(--accent)" size={10}>VERVOLGSTAP</Mono>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                         fontSize: 22, letterSpacing: '-0.02em',
                         margin: '4px 0 8px', color: 'var(--text)' }}>
              Wil je de {nieuw} nieuwe documenten doorzoekbaar maken?
            </h2>
            <p style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55, margin: 0, maxWidth: 560 }}>
              Bronnenboek bouwt een full-text index zodat je via{' '}
              <span style={{ fontFamily: 'var(--font-mono)' }}>Zoeken</span> direct door alle
              bestanden kunt gaan. Duurt naar schatting{' '}
              <strong style={{ color: 'var(--text)' }}>~{Math.max(1, Math.round(nieuw / 20))} minuten</strong>.
              Loopt op de achtergrond.
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
            <Btn primary onClick={onIndexeer}>Ja, indexeren ↻</Btn>
            <Btn ghost onClick={onLater}>Later</Btn>
          </div>
        </div>
      )}

      {/* Al automatisch geïndexeerd: succesbericht met directe doorklik */}
      {nieuw > 0 && geindexeerd && (
        <div style={{
          border: '1px solid var(--border-2)',
          background: 'oklch(0.215 0.008 70)',
          borderRadius: 'var(--r-2)', padding: '22px 24px',
          display: 'grid', gridTemplateColumns: '1fr auto',
          gap: 24, alignItems: 'center',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: -1, left: 24, width: 60, height: 2,
            background: 'var(--green)',
          }}></div>
          <div>
            <Mono color="var(--green)" size={10}>DOORZOEKBAAR</Mono>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontWeight: 600,
                         fontSize: 22, letterSpacing: '-0.02em',
                         margin: '4px 0 8px', color: 'var(--text)' }}>
              Klaar — {nieuw} nieuwe documenten zijn doorzoekbaar.
            </h2>
            <p style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55, margin: 0, maxWidth: 560 }}>
              De zoekindex is direct na de download bijgewerkt. Je kunt nu via{' '}
              <span style={{ fontFamily: 'var(--font-mono)' }}>Zoeken</span> door alle stukken.
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
            {onNaarZoeken && <Btn primary onClick={onNaarZoeken}>Naar zoeken →</Btn>}
            <Btn ghost onClick={onLater}>Terug</Btn>
          </div>
        </div>
      )}

      {nieuw === 0 && (
        <div style={{ marginTop: 16 }}>
          <Btn ghost onClick={onLater}>← Terug</Btn>
        </div>
      )}
    </div>
  );
}

// ── ScrapeGemeentePakket ──────────────────────────────────────────────────────
// Gemeente-eerst workflow: vul gemeente in → zie alle gerelateerde organen →
// scrape elk orgaan met één klik.

function ScrapeGemeentePakket({ onStart, gemeente, onGemeenteChange, resultaat, onResultaat }) {
  // gemeente en resultaat komen van de Scrape-parent (lifted state),
  // zodat het verkennen-resultaat bewaard blijft tijdens en na een scrape.
  const [gemeenten, setGemeenten] = React.useState([]);
  const [bezig, setBezig]         = React.useState(false);
  const [fout, setFout]           = React.useState(null);
  const [periode, setPeriode]     = React.useState(24);
  const [simuleer, setSimuleer]   = React.useState(false);

  React.useEffect(() => {
    fetch('/api/gemeenten').then(r => r.json()).then(setGemeenten).catch(() => {});
  }, []);

  const verken = async (e) => {
    if (e) e.preventDefault();
    if (!gemeente.trim()) return;
    setBezig(true); setFout(null); onResultaat(null);
    try {
      const resp = await fetch(`/api/verkennen?gemeente=${encodeURIComponent(gemeente.trim())}`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.fout || resp.statusText);
      onResultaat(data);
    } catch (err) {
      setFout(err.message);
    } finally {
      setBezig(false);
    }
  };

  // Bouw gegroepeerde orgaanlijst uit het verkennen-resultaat
  const groepen = resultaat ? [
    {
      kicker: 'Gemeente',
      orgs: [{ type: 'gemeente', naam: resultaat.gemeente, slug: resultaat.gemeente, beschikbaar: true }],
    },
    ...(resultaat.waterschappen?.length ? [{
      kicker: 'Waterschap',
      orgs: resultaat.waterschappen.map(ws => ({
        type: 'waterschap', naam: ws.naam, slug: ws.slug, beschikbaar: true,
      })),
    }] : []),
    ...(resultaat.veiligheidsregio ? [{
      kicker: 'Veiligheidsregio',
      orgs: [{ type: 'veiligheidsregio', naam: resultaat.veiligheidsregio.naam, slug: resultaat.veiligheidsregio.slug, beschikbaar: true }],
    }] : []),
    ...(resultaat.provincie ? [{
      kicker: 'Provincie',
      orgs: [{ type: 'provincie', naam: resultaat.provincie.naam, slug: resultaat.provincie.slug, beschikbaar: true }],
    }] : []),
    ...(resultaat.regelingen?.length ? [{
      kicker: `Gemeenschappelijke regelingen (${resultaat.regelingen.length})`,
      orgs: resultaat.regelingen.map(gr => ({
        type: 'gr', naam: gr.naam, slug: gr.slug, beschikbaar: gr.in_catalogus,
      })),
    }] : []),
  ] : [];

  const nBeschikbaar = groepen.reduce((s, g) => s + g.orgs.filter(o => o.beschikbaar).length, 0);

  return (
    <div>
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: 26, fontWeight: 600,
        letterSpacing: '-0.02em', margin: '0 0 6px', color: 'var(--text)',
      }}>Documenten ophalen — Via gemeente</h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, margin: '0 0 24px', lineHeight: 1.55, maxWidth: 540 }}>
        Vul een gemeente in. Je ziet direct alle gerelateerde organen — waterschap,
        veiligheidsregio, provincie en GR's — en kunt elk orgaan met één klik scrapen.
      </p>

      {/* Zoekbalk */}
      <form onSubmit={verken} style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
        <input
          list="pakket-gemeenten"
          value={gemeente}
          onChange={e => onGemeenteChange(e.target.value)}
          placeholder="Naam van gemeente…"
          style={{
            flex: 1, padding: '9px 12px',
            background: 'oklch(0.215 0.005 70)',
            border: '1px solid var(--border)', borderRadius: 'var(--r-2)',
            color: 'var(--text)', fontFamily: 'var(--font-ui)', fontSize: 13.5,
          }}
          autoFocus
        />
        <datalist id="pakket-gemeenten">
          {gemeenten.map(g => <option key={g} value={g} />)}
        </datalist>
        <Btn primary disabled={!gemeente.trim() || bezig} onClick={verken}>
          {bezig ? 'Laden…' : 'Verkennen →'}
        </Btn>
      </form>

      {bezig && <Laadspinner />}
      {fout  && <Foutmelding tekst={fout} />}

      {/* Geen resultaat nog */}
      {!resultaat && !bezig && !fout && (
        <div style={{
          padding: '16px 20px',
          border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          background: 'oklch(0.175 0.005 70)',
          fontSize: 13, color: 'var(--muted)', lineHeight: 1.6,
        }}>
          Zoek een gemeente om direct te zien welke organen beschikbaar zijn.
          Handig als je niet zeker weet welke GR's, waterschappen of regio's bij
          een gemeente horen.
        </div>
      )}

      {resultaat && (
        <>
          {/* Instellingen-balk */}
          <div style={{
            display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap',
            padding: '10px 14px', marginBottom: 22,
            background: 'oklch(0.19 0.005 70)',
            border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          }}>
            <Mono color="var(--dim)" size={10}>PERIODE</Mono>
            <div style={scrapeStyles.radioGroup}>
              {[6, 12, 18, 24].map(p => (
                <div key={p} onClick={() => setPeriode(p)} style={scrapeStyles.radio(periode === p)}>
                  {p} mnd
                  {p === 24 && (
                    <sup style={{ color: 'var(--accent)', fontFamily: 'var(--font-mono)', fontSize: 8, marginLeft: 3 }}>★</sup>
                  )}
                </div>
              ))}
            </div>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginLeft: 'auto' }}
              onClick={() => setSimuleer(!simuleer)}
            >
              <div style={scrapeStyles.toggle(simuleer)}>
                <div style={scrapeStyles.toggleDot(simuleer)}></div>
              </div>
              <Mono color={simuleer ? 'var(--accent)' : 'var(--text-2)'} size={11}>
                {simuleer ? 'Simuleren AAN' : 'Simuleren UIT'}
              </Mono>
            </div>
          </div>

          {/* Orgaan-groepen */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {groepen.map((groep, gi) => (
              <div key={gi}>
                <Mono color="var(--dim)" size={10}>{groep.kicker.toUpperCase()}</Mono>
                <div style={{
                  marginTop: 7,
                  border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
                  background: 'oklch(0.185 0.005 70)', overflow: 'hidden',
                }}>
                  {groep.orgs.map((org, oi) => (
                    <div key={oi} style={{
                      display: 'flex', alignItems: 'center', gap: 14,
                      padding: '11px 16px',
                      borderBottom: oi < groep.orgs.length - 1 ? '1px solid var(--rule)' : 'none',
                      opacity: org.beschikbaar ? 1 : 0.4,
                    }}>
                      <span style={{
                        flex: 1, fontSize: 13.5, color: 'var(--text)',
                        letterSpacing: '-0.005em', textTransform: 'capitalize',
                      }}>
                        {org.naam}
                      </span>
                      {org.beschikbaar ? (
                        <Btn small primary onClick={() => onStart(org.slug, periode, simuleer, org.type)}>
                          {simuleer ? 'Simuleer →' : 'Scrape →'}
                        </Btn>
                      ) : (
                        <Mono color="var(--dim)" size={10}>niet downloadbaar</Mono>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {nBeschikbaar === 0 && (
            <div style={{ marginTop: 16, color: 'var(--muted)', fontSize: 13 }}>
              Geen downloadbare organen gevonden voor deze gemeente.
            </div>
          )}
        </>
      )}
    </div>
  );
}

Object.assign(window, { Scrape });
