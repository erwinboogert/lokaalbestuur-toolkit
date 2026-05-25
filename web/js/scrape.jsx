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
  { id: 'gemeente',         label: 'Gemeenten',           type: 'gemeente' },
  { id: 'gr',               label: "GR's",                type: 'gr' },
  { id: 'waterschap',       label: 'Waterschappen',        type: 'waterschap' },
  { id: 'veiligheidsregio', label: "Veiligheidsregio's",  type: 'veiligheidsregio' },
  { id: 'provincie',        label: 'Provincies',           type: 'provincie' },
];

function Scrape({ onNavigate }) {
  const [tabIdx, setTabIdx]   = React.useState(0);
  const [stap, setStap]       = React.useState('idle');
  const [jobId, setJobId]     = React.useState(null);
  const [orgaan, setOrgaan]   = React.useState('');
  const [periode, setPeriode] = React.useState(24);
  const [simuleer, setSimuleer] = React.useState(false);
  const [samenvatting, setSamenvatting] = React.useState(null);

  const activeTab = TABS[tabIdx];

  const handleStart = async (org, per, sim) => {
    try {
      const resp = await fetch('/api/scrapen/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: activeTab.type, orgaan: org, periode: per, simuleer: sim }),
      });
      const data = await resp.json();
      if (data.fout) { alert(data.fout); return; }
      setJobId(data.job_id);
      setOrgaan(org);
      setPeriode(per);
      setSimuleer(sim);
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

      {stap === 'idle'     && <ScrapeIdle orgaanType={activeTab.type} onStart={handleStart} />}
      {stap === 'progress' && <ScrapeProgress jobId={jobId} orgaan={orgaan} periode={periode}
                                               simuleer={simuleer}
                                               onDone={handleDone}
                                               onCancel={() => setStap('idle')} />}
      {stap === 'indexing' && <ScrapeProgress jobId={jobId} orgaan={orgaan} periode={0}
                                               simuleer={false}
                                               titel="Indexeren"
                                               onDone={handleIndexDone}
                                               onCancel={handleIndexDone} />}
      {stap === 'done'     && <ScrapeDone orgaan={orgaan} samenvatting={samenvatting}
                                           onIndexeer={handleIndexeer}
                                           onLater={() => setStap('idle')} />}
    </>
  );
}

function ScrapeIdle({ orgaanType, onStart }) {
  const [orgaan, setOrgaan]   = React.useState('');
  const [periode, setPeriode] = React.useState(24);
  const [simuleer, setSimuleer] = React.useState(false);
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

        <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
          <Btn primary onClick={() => orgaan && onStart(orgaan, periode, simuleer)}
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

function ScrapeProgress({ jobId, orgaan, periode, simuleer, titel, onDone, onCancel }) {
  const [regels, setRegels] = React.useState([]);
  const [nieuw, setNieuw]   = React.useState(0);
  const [fouten, setFouten] = React.useState(0);
  const [klaar, setKlaar]   = React.useState(false);
  const esRef = React.useRef(null);

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
        // Geef samenvatting mee
        onDone({ nieuw, fouten });
        return;
      }

      if (data.type === 'log' && data.text) {
        const tekst = data.text;
        setRegels(prev => [tekst, ...prev].slice(0, 80));

        // Parse statistieken uit log-output
        const mNieuw = tekst.match(/Nieuw gedownload\s*:\s*(\d+)/);
        if (mNieuw) setNieuw(parseInt(mNieuw[1]));

        const mFout = tekst.match(/Fouten\s*:\s*(\d+)/);
        if (mFout) setFouten(parseInt(mFout[1]));

        if (tekst.includes('! FOUT') || tekst.includes('! fout')) {
          setFouten(f => f + 1);
        }

        // Tel gedownloade docs (+) en overgeslagen
        if (tekst.trim().startsWith('+ ')) {
          setNieuw(n => n + 1);
        }
      }
    };

    es.onerror = () => es.close();
    return () => es.close();
  }, [jobId]);

  const titelTekst = titel || `${orgaan} — ${simuleer ? 'simuleren' : 'downloaden'}`;

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
            <Mono color="var(--text-2)" size={13}>nieuw gedownload</Mono>
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

function ScrapeDone({ orgaan, samenvatting = {}, onIndexeer, onLater }) {
  const nieuw   = samenvatting.nieuw   || 0;
  const fouten  = samenvatting.fouten  || 0;

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

      {/* Indexeer-dialoog */}
      {nieuw > 0 && (
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

      {nieuw === 0 && (
        <div style={{ marginTop: 16 }}>
          <Btn ghost onClick={onLater}>← Terug</Btn>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Scrape });
