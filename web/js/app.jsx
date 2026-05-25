// app.jsx — Hoofdapp: routing, sidebar, schermwisseling

// Schermen die nog geen eigen component hebben
function Verkennen() {
  return (
    <>
      <Topbar crumbs={['Verkennen']} />
      <div style={sharedStyles.scroll}>
        <VerkennenScherm />
      </div>
    </>
  );
}

function Dossiers({ onNavigate }) {
  return (
    <>
      <Topbar crumbs={['Dossiers']} />
      <div style={sharedStyles.scroll}>
        <DossiersBeheer onNavigate={onNavigate} />
      </div>
    </>
  );
}

function Alerts() {
  return (
    <>
      <Topbar crumbs={['Alerts']} />
      {/* Geen scroll-wrapper: AlertsScherm heeft een split-layout die de hoogte vult */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <AlertsScherm />
      </div>
    </>
  );
}

// ── Verkennen-scherm ──────────────────────────────────────────────────────────

function VerkennenScherm() {
  const [gemeente,   setGemeente]   = React.useState('');
  const [gemeenten,  setGemeenten]  = React.useState([]);
  const [resultaat,  setResultaat]  = React.useState(null);
  const [bezig,      setBezig]      = React.useState(false);
  const [fout,       setFout]       = React.useState(null);

  React.useEffect(() => {
    fetch('/api/gemeenten').then(r => r.json()).then(setGemeenten).catch(() => {});
  }, []);

  const verken = async (e) => {
    if (e) e.preventDefault();
    if (!gemeente.trim()) return;
    setBezig(true); setFout(null); setResultaat(null);
    try {
      const resp = await fetch(`/api/verkennen?gemeente=${encodeURIComponent(gemeente.trim())}`);
      if (!resp.ok) throw new Error(await resp.text());
      setResultaat(await resp.json());
    } catch (err) {
      setFout(err.message);
    } finally {
      setBezig(false);
    }
  };

  return (
    <>
      {/* Zoekbalk */}
      <form onSubmit={verken} style={{
        display: 'flex', gap: 8, alignItems: 'center', marginBottom: 24,
        background: 'oklch(0.185 0.005 70)',
        border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
        padding: '14px 16px',
      }}>
        <input
          type="text"
          list="gemeenten-lijst"
          value={gemeente}
          onChange={e => setGemeente(e.target.value)}
          placeholder="Naam van gemeente…"
          style={{
            flex: 1,
            background: 'oklch(0.225 0.005 70)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-1)',
            color: 'var(--text)', padding: '7px 12px',
            fontFamily: 'var(--font-ui)', fontSize: 13.5, outline: 'none',
          }}
          autoFocus
        />
        <datalist id="gemeenten-lijst">
          {gemeenten.map(g => <option key={g} value={g} />)}
        </datalist>
        <Btn primary disabled={!gemeente.trim() || bezig} onClick={verken}>
          {bezig ? 'Zoeken…' : 'Verkennen'}
        </Btn>
      </form>

      {bezig && <Laadspinner />}
      {fout   && <Foutmelding tekst={fout} />}

      {resultaat && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 16,
          background: 'oklch(0.185 0.005 70)',
          border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          padding: '20px 22px',
        }}>
          <div style={{
            fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 20,
            letterSpacing: '-0.01em', color: 'var(--text)', marginBottom: 4,
          }}>
            {resultaat.gemeente} — vooronderzoek
          </div>

          {[
            { k: 'Provincie',           v: resultaat.provincie },
            { k: 'Veiligheidsregio',    v: resultaat.veiligheidsregio },
            { k: 'Waterschap(pen)',      v: (resultaat.waterschappen || []).join(', ') || '—' },
          ].map(({ k, v }) => (
            <div key={k} style={{ display: 'flex', gap: 16, alignItems: 'baseline' }}>
              <Mono color="var(--dim)" size={11} style={{ minWidth: 180 }}>{k}</Mono>
              <span style={{ fontSize: 13, color: 'var(--text-2)' }}>{v || '—'}</span>
            </div>
          ))}

          {resultaat.regelingen && resultaat.regelingen.length > 0 && (
            <div>
              <div style={{ display: 'flex', gap: 16, alignItems: 'baseline', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--dim)', minWidth: 180 }}>
                  Gemeenschappelijke regelingen ({resultaat.regelingen.length})
                </span>
                {resultaat.regelingen_bron && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'oklch(0.40 0.005 70)' }}>
                    bron: {resultaat.regelingen_bron}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, paddingLeft: 196 }}>
                {resultaat.regelingen.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
                      — {r.naam !== undefined ? r.naam : r}
                    </span>
                    {r.in_catalogus && (
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 9.5,
                        color: 'var(--green)', letterSpacing: '0.06em',
                        border: '1px solid oklch(0.760 0.150 148 / 0.35)',
                        borderRadius: 2, padding: '1px 5px',
                      }}>downloadbaar</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!resultaat && !bezig && !fout && (
        <div style={{
          fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, maxWidth: 480,
        }}>
          Zoek een gemeente op om de bijbehorende provincie, veiligheidsregio, waterschap
          en gemeenschappelijke regelingen te tonen. Ideaal als startpunt voor onderzoek.
        </div>
      )}
    </>
  );
}

// ── Dossiers-beheer ───────────────────────────────────────────────────────────

function DossiersBeheer({ onNavigate }) {
  const [dossiers, setDossiers] = React.useState(null);
  const [fout,     setFout]     = React.useState(null);

  React.useEffect(() => {
    fetch('/api/status')
      .then(r => r.json())
      .then(d => setDossiers(d.dossiers))
      .catch(e => setFout(e.message));
  }, []);

  if (fout)     return <Foutmelding tekst={fout} />;
  if (!dossiers) return <Laadspinner />;

  if (dossiers.length === 0) {
    return (
      <div style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, maxWidth: 480 }}>
        <p style={{ marginTop: 0 }}>
          Je hebt nog geen monitoringsdossiers. Maak er een aan via de terminal:
        </p>
        <pre style={{
          fontFamily: 'var(--font-mono)', fontSize: 12,
          background: 'oklch(0.185 0.005 70)',
          border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          padding: '12px 14px', color: 'var(--text-2)',
        }}>
          python3 toolkit.py nieuw-dossier
        </pre>
        <p>
          Een dossier bestaat uit een orgaan, trefwoorden en een label. Zodra
          er een dossier aanwezig is, kun je het hier beheren en handmatig draaien.
        </p>
      </div>
    );
  }

  return (
    <div style={{ border: '1px solid var(--rule)', borderRadius: 'var(--r-2)', overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: 12.5 }}>
        <thead>
          <tr>
            {['Dossier', 'Orgaan', 'Trefwoorden', 'Laatste run', 'Status', ''].map((h, i) => (
              <th key={i} style={{
                textAlign: i === 5 ? 'right' : 'left',
                padding: '8px 12px',
                fontFamily: 'var(--font-mono)', fontSize: 10,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: 'var(--dim)', fontWeight: 500,
                borderBottom: '1px solid var(--border)',
                background: 'oklch(0.175 0.005 70)',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dossiers.map((d, i) => (
            <tr key={i} style={{ background: i % 2 === 1 ? 'oklch(0.175 0.005 70)' : 'oklch(0.185 0.005 70)' }}>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)', color: 'var(--text)', fontWeight: 500 }}>
                {d.label || d.naam}
              </td>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)' }}>
                <Mono color="var(--text-2)">{d.orgaan}</Mono>
              </td>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)' }}>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {d.trefwoorden.map((t, j) => (
                    <span key={j} style={{
                      fontFamily: 'var(--font-mono)', fontSize: 10.5,
                      padding: '2px 6px',
                      background: 'oklch(0.265 0.005 70)',
                      color: 'var(--text-2)', borderRadius: 2,
                    }}>{t}</span>
                  ))}
                </div>
              </td>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)' }}>
                <Mono color="var(--muted)">{d.laatste_run}</Mono>
              </td>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)' }}>
                <Badge kind={d.status} />
              </td>
              <td style={{ padding: '11px 12px', borderBottom: '1px solid var(--rule)', textAlign: 'right' }}>
                <NuDraaienKnop dossier={d.naam} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// NuDraaienKnop staat ook in dashboard.jsx — maar we zetten hem hier ook neer
// zodat Dossiers onafhankelijk werkt als dashboard.jsx niet geladen is.
// In de echte app worden beide geladen, dus één definitie volstaat. Bewust
// geen duplicaat: de window-export in dashboard.jsx dekt dit ook.

// ── Alerts-scherm ─────────────────────────────────────────────────────────────

function AlertsScherm() {
  const [alerts,  setAlerts]  = React.useState(null);
  const [actief,  setActief]  = React.useState(null);   // geselecteerde alert
  const [inhoud,  setInhoud]  = React.useState(null);
  const [fout,    setFout]    = React.useState(null);

  React.useEffect(() => {
    fetch('/api/alerts')
      .then(r => r.json())
      .then(setAlerts)
      .catch(e => setFout(e.message));
  }, []);

  const openAlert = async (a) => {
    setActief(a);
    setInhoud(null);
    try {
      const resp = await fetch(`/api/alerts/${a.id}`);
      const data = await resp.json();
      setInhoud(data.inhoud || data.fout);
    } catch (e) {
      setInhoud(`Fout: ${e.message}`);
    }
  };

  if (fout)    return <Foutmelding tekst={fout} />;
  if (!alerts) return <Laadspinner />;

  if (alerts.length === 0) {
    return (
      <div style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, maxWidth: 480 }}>
        Geen alertrapporten gevonden. Stel eerst een dossier in en draai de analyse.
      </div>
    );
  }

  const n_nieuw = alerts.filter(a => a.nieuw).length;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 0, flex: 1, minHeight: 0 }}>
      {/* Lijst */}
      <div style={{
        borderRight: '1px solid var(--rule)',
        overflowY: 'auto', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '10px 14px 8px',
          borderBottom: '1px solid var(--rule)',
          background: 'oklch(0.175 0.005 70)',
        }}>
          <Mono color="var(--dim)" size={10} style={{ letterSpacing: '0.10em', textTransform: 'uppercase' }}>
            Alerts — {n_nieuw > 0 ? `${n_nieuw} ongelezen` : 'alles gelezen'}
          </Mono>
        </div>
        {alerts.map((a, i) => (
          <div
            key={i}
            onClick={() => openAlert(a)}
            style={{
              padding: '11px 14px',
              borderBottom: '1px solid var(--rule)',
              cursor: 'pointer',
              background: actief?.id === a.id
                ? 'oklch(0.215 0.008 70)'
                : a.nieuw ? 'oklch(0.200 0.010 60)' : 'transparent',
              display: 'flex', flexDirection: 'column', gap: 4,
              transition: 'background 80ms',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {a.nieuw && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9.5,
                  color: 'var(--orange)', fontWeight: 600, letterSpacing: '0.08em',
                }}>NIEUW</span>
              )}
              <span style={{
                fontSize: 13, fontWeight: 500, color: 'var(--text)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{a.dossier}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <Mono color="var(--muted)" size={11}>{a.orgaan}</Mono>
              <Mono color="var(--dim)" size={10.5}>{a.datum_display}</Mono>
            </div>
          </div>
        ))}
      </div>

      {/* Detail */}
      <div style={{ overflowY: 'auto', padding: '20px 24px' }}>
        {!actief && (
          <div style={{ color: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            ← Klik op een alert om de inhoud te lezen.
          </div>
        )}
        {actief && !inhoud && <Laadspinner />}
        {actief && inhoud && (
          <div>
            <div style={{
              fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 18,
              letterSpacing: '-0.01em', color: 'var(--text)', marginBottom: 16,
            }}>
              {actief.dossier}
            </div>
            <MarkdownLezer tekst={inhoud} />
          </div>
        )}
      </div>
    </div>
  );
}

// Eenvoudige Markdown-lezer (geen externe bibliotheek)
function MarkdownLezer({ tekst }) {
  if (!tekst) return null;
  const regels = tekst.split('\n');
  const elementen = [];
  let inCode = false;
  let codeBuffer = [];

  for (let i = 0; i < regels.length; i++) {
    const r = regels[i];

    if (r.startsWith('```')) {
      if (inCode) {
        elementen.push(
          <pre key={i} style={{
            fontFamily: 'var(--font-mono)', fontSize: 11.5,
            background: 'oklch(0.175 0.005 70)',
            border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
            padding: '12px 14px', color: 'var(--text-2)',
            overflowX: 'auto', lineHeight: 1.6,
          }}>{codeBuffer.join('\n')}</pre>
        );
        codeBuffer = []; inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) { codeBuffer.push(r); continue; }

    if (r.startsWith('### ')) {
      elementen.push(<h3 key={i} style={{ fontFamily: 'var(--font-serif)', fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: '20px 0 8px', letterSpacing: '-0.01em' }}>{r.slice(4)}</h3>);
    } else if (r.startsWith('## ')) {
      elementen.push(<h2 key={i} style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600, color: 'var(--text)', margin: '24px 0 10px', letterSpacing: '-0.01em' }}>{r.slice(3)}</h2>);
    } else if (r.startsWith('# ')) {
      elementen.push(<h1 key={i} style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: '0 0 16px', letterSpacing: '-0.01em' }}>{r.slice(2)}</h1>);
    } else if (r.startsWith('- ') || r.startsWith('* ')) {
      elementen.push(<li key={i} style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, marginBottom: 4 }}>{formatInline(r.slice(2))}</li>);
    } else if (r.startsWith('**') && r.endsWith('**')) {
      elementen.push(<p key={i} style={{ fontWeight: 600, color: 'var(--text)', margin: '8px 0', fontSize: 13 }}>{r.slice(2, -2)}</p>);
    } else if (r.trim() === '') {
      elementen.push(<div key={i} style={{ height: 8 }} />);
    } else {
      elementen.push(<p key={i} style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, margin: '4px 0' }}>{formatInline(r)}</p>);
    }
  }

  function formatInline(tekst) {
    const parts = tekst.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((p, i) =>
      p.startsWith('**') && p.endsWith('**')
        ? <strong key={i} style={{ color: 'var(--text)', fontWeight: 600 }}>{p.slice(2, -2)}</strong>
        : p
    );
  }

  return <div style={{ maxWidth: 680 }}>{elementen}</div>;
}

// ── Hoofd-App ─────────────────────────────────────────────────────────────────

function App() {
  const [scherm, setScherm] = React.useState('dashboard');
  const [counts, setCounts] = React.useState({ dossiers: 0, alerts: 0 });

  // Haal alerttellingen op voor de sidebar-badges
  React.useEffect(() => {
    const laadCounts = () => {
      fetch('/api/status')
        .then(r => r.json())
        .then(d => setCounts({
          dossiers: d.dossiers?.length || 0,
          alerts:   d.alerts?.filter(a => a.nieuw).length || 0,
        }))
        .catch(() => {});
    };
    laadCounts();
    const interval = setInterval(laadCounts, 60_000);
    return () => clearInterval(interval);
  }, []);

  const navigate = (id) => setScherm(id);

  // Elk scherm levert zijn eigen volledige layout (Topbar + scroll of split).
  // Dashboard en Scrape hebben geen eigen Topbar/scroll — die wikkelen we hier.
  const renderScherm = () => {
    switch (scherm) {
      case 'dashboard':
        return (
          <>
            <Topbar crumbs={['Dashboard']} />
            <div style={sharedStyles.scroll}>
              <Dashboard onNavigate={navigate} />
            </div>
          </>
        );
      case 'scrapen':
        return (
          <>
            <Topbar crumbs={['Scrapen']} />
            <div style={sharedStyles.scroll}>
              <Scrape onNavigate={navigate} />
            </div>
          </>
        );
      case 'verkennen': return <Verkennen />;
      case 'zoeken':    return <Search />;
      case 'dossiers':  return <Dossiers onNavigate={navigate} />;
      case 'alerts':    return <Alerts />;
      default:
        return (
          <>
            <Topbar crumbs={['Dashboard']} />
            <div style={sharedStyles.scroll}>
              <Dashboard onNavigate={navigate} />
            </div>
          </>
        );
    }
  };

  return (
    <div style={sharedStyles.frame}>
      <Sidebar active={scherm} onNavigate={navigate} counts={counts} />
      <div style={sharedStyles.content}>
        {renderScherm()}
      </div>
    </div>
  );
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

const rootEl = document.getElementById('root');
ReactDOM.createRoot(rootEl).render(<App />);
