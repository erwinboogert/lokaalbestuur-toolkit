// search.jsx — Zoekscherm: full-text FTS5 zoeken in lokale index

function Search() {
  const [organen, setOrganen]   = React.useState([]);
  const [orgaan,  setOrgaan]    = React.useState('');
  const [query,   setQuery]     = React.useState('');
  const [hits,    setHits]      = React.useState(null);   // null = niet gezocht
  const [bezig,   setBezig]     = React.useState(false);
  const [fout,    setFout]      = React.useState(null);
  const [tijdMs,  setTijdMs]    = React.useState(null);
  const [geopend, setGeopend]   = React.useState(null);   // pad van geopend doc

  // Laad organenlijst voor de selector
  React.useEffect(() => {
    fetch('/api/organen')
      .then(r => r.json())
      .then(lijst => {
        setOrganen(lijst);
        if (lijst.length === 1) setOrgaan(lijst[0]._slug);
      })
      .catch(() => {});
  }, []);

  const zoek = async (e) => {
    if (e) e.preventDefault();
    if (!orgaan || !query.trim()) return;
    setBezig(true);
    setFout(null);
    setHits(null);
    try {
      const params = new URLSearchParams({ orgaan, q: query.trim() });
      const resp   = await fetch(`/api/zoeken?${params}`);
      const data   = await resp.json();
      if (data.fout) { setFout(data.fout); }
      else           { setHits(data.hits); setTijdMs(Math.round((data.tijd || 0) * 1000)); }
    } catch (err) {
      setFout(err.message);
    } finally {
      setBezig(false);
    }
  };

  const openDoc = async (pad) => {
    setGeopend(pad);
    try {
      await fetch('/api/document/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pad }),
      });
    } catch (_) {}
    setTimeout(() => setGeopend(null), 2000);
  };

  // Groepeer hits per vergadertype voor een overzichtelijker resultaat
  const groepenPerType = React.useMemo(() => {
    if (!hits) return [];
    const map = {};
    for (const h of hits) {
      const type = h.vergadertype || 'Overig';
      if (!map[type]) map[type] = [];
      map[type].push(h);
    }
    return Object.entries(map).sort((a, b) => b[1].length - a[1].length);
  }, [hits]);

  const heeftIndex = orgaan && organen.find(o => o._slug === orgaan);

  return (
    <>
      <Topbar crumbs={['Zoeken']} />

      <div style={sharedStyles.scroll}>
        {/* Zoekbalk */}
        <form onSubmit={zoek} style={{
          display: 'flex', gap: 8, alignItems: 'center', marginBottom: 24,
          background: 'oklch(0.185 0.005 70)',
          border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
          padding: '14px 16px',
        }}>
          {/* Orgaan-selector */}
          {organen.length > 1 && (
            <select
              value={orgaan}
              onChange={e => { setOrgaan(e.target.value); setHits(null); }}
              style={{
                background: 'oklch(0.225 0.005 70)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-1)',
                color: 'var(--text)', padding: '6px 10px',
                fontFamily: 'var(--font-ui)', fontSize: 12.5,
                cursor: 'pointer', minWidth: 160,
              }}
            >
              <option value="">— Kies orgaan —</option>
              {organen.map(o => (
                <option key={o._slug} value={o._slug}>
                  {o.naam || o._slug}
                </option>
              ))}
            </select>
          )}

          {/* Zoekveld */}
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={orgaan ? `Zoek in ${orgaan}…` : 'Kies eerst een orgaan'}
            disabled={!orgaan}
            style={{
              flex: 1,
              background: 'oklch(0.225 0.005 70)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-1)',
              color: 'var(--text)', padding: '7px 12px',
              fontFamily: 'var(--font-ui)', fontSize: 13.5,
              outline: 'none',
            }}
            autoFocus
          />

          <Btn primary disabled={!orgaan || !query.trim() || bezig}
               onClick={zoek}>
            {bezig ? 'Zoeken…' : 'Zoeken'}
          </Btn>
        </form>

        {/* Tips als er nog geen orgaan geconfigureerd is */}
        {organen.length === 0 && (
          <Foutmelding tekst="Geen organen geconfigureerd — download eerst documenten via Scrapen." />
        )}

        {/* Foutmelding */}
        {fout && <Foutmelding tekst={fout} />}

        {/* Laadspinner */}
        {bezig && <Laadspinner />}

        {/* Leeg resultaat */}
        {hits !== null && hits.length === 0 && !bezig && (
          <div style={{
            padding: '28px 0', color: 'var(--muted)',
            fontFamily: 'var(--font-mono)', fontSize: 12,
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            <div>Geen resultaten voor <strong style={{ color: 'var(--text-2)' }}>{query}</strong>.</div>
            <div style={{ fontSize: 11 }}>
              Probeer een kortere zoekterm, of gebruik FTS5-syntax: <code>woord1 AND woord2</code>, <code>"exacte zin"</code>, <code>woord*</code>.
            </div>
          </div>
        )}

        {/* Resultaten */}
        {hits !== null && hits.length > 0 && (
          <>
            {/* Samenvattingsbalk */}
            <div style={{
              display: 'flex', alignItems: 'baseline', gap: 12,
              marginBottom: 20, paddingBottom: 10,
              borderBottom: '1px solid var(--rule)',
            }}>
              <span style={{
                fontFamily: 'var(--font-serif)', fontWeight: 600,
                fontSize: 18, letterSpacing: '-0.01em', color: 'var(--text)',
              }}>{hits.length.toLocaleString('nl-NL')}</span>
              <Mono color="var(--text-2)">
                resultaten voor &ldquo;{query}&rdquo; in {orgaan}
              </Mono>
              {tijdMs !== null && (
                <Mono color="var(--muted)" size={10.5}>{tijdMs} ms</Mono>
              )}
            </div>

            {/* Resultaten gegroepeerd per vergadertype */}
            {groepenPerType.map(([type, groepHits]) => (
              <div key={type} style={{ marginBottom: 28 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  marginBottom: 10,
                }}>
                  <Mono color="var(--accent)" size={10}>{type.toUpperCase()}</Mono>
                  <div style={{ flex: 1, height: 1, background: 'var(--rule)' }}></div>
                  <Mono color="var(--dim)" size={10}>{groepHits.length}</Mono>
                </div>

                <div style={{
                  border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
                  overflow: 'hidden',
                  background: 'oklch(0.185 0.005 70)',
                }}>
                  {groepHits.map((hit, i) => (
                    <HitRegel
                      key={i}
                      hit={hit}
                      query={query}
                      geopend={geopend === hit.pad}
                      onOpen={() => openDoc(hit.pad)}
                      isLast={i === groepHits.length - 1}
                    />
                  ))}
                </div>
              </div>
            ))}

            {hits.length === 200 && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 11,
                color: 'var(--muted)', paddingTop: 8,
              }}>
                Maximaal 200 resultaten weergegeven — verfijn je zoekopdracht voor meer precisie.
              </div>
            )}
          </>
        )}

        {/* Leeg scherm (nog niet gezocht) */}
        {hits === null && !bezig && !fout && organen.length > 0 && (
          <ZoekLeeg orgaan={orgaan} />
        )}
      </div>
    </>
  );
}

function HitRegel({ hit, query, geopend, onOpen, isLast }) {
  const [uitgeklapt, setUitgeklapt] = React.useState(false);

  // Markeer zoektermen in snippet (eenvoudig: **term** → <mark>
  const renderSnippet = (tekst) => {
    if (!tekst) return null;
    const parts = tekst.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((p, i) =>
      p.startsWith('**') && p.endsWith('**')
        ? <mark key={i} style={{
            background: 'var(--mark-soft)', color: 'var(--mark)',
            borderRadius: 1, padding: '0 1px',
          }}>{p.slice(2, -2)}</mark>
        : p
    );
  };

  return (
    <div style={{
      borderBottom: isLast ? 'none' : '1px solid var(--rule)',
    }}>
      {/* Hoofdregel */}
      <div
        onClick={() => setUitgeklapt(v => !v)}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 90px 28px',
          alignItems: 'start',
          gap: 12,
          padding: '11px 14px',
          cursor: 'pointer',
          transition: 'background 80ms',
        }}
      >
        {/* Bestandsnaam + snippet */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
          <div style={{
            fontSize: 13, fontWeight: 500, color: 'var(--text)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {hit.bestandsnaam || hit.pad.split('/').pop()}
          </div>
          <div style={{
            fontSize: 11.5, color: 'var(--text-2)', lineHeight: 1.5,
            overflow: 'hidden', display: '-webkit-box',
            WebkitLineClamp: uitgeklapt ? 'unset' : 2,
            WebkitBoxOrient: 'vertical',
          }}>
            {renderSnippet(hit.snippet)}
          </div>
        </div>

        {/* Datum */}
        <Mono color="var(--muted)" size={11}>{hit.datum || '—'}</Mono>

        {/* Uitklapindicator */}
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--dim)', transition: 'transform 150ms',
          transform: uitgeklapt ? 'rotate(90deg)' : 'none',
        }}>›</span>
      </div>

      {/* Uitklap: volledig snippet + open-knop */}
      {uitgeklapt && (
        <div style={{
          padding: '0 14px 14px',
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          {hit.pad && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10.5,
              color: 'var(--dim)', wordBreak: 'break-all',
            }}>
              {hit.pad}
            </div>
          )}
          <div>
            <Btn small onClick={(e) => { e.stopPropagation(); onOpen(); }} disabled={geopend}>
              {geopend ? 'Geopend ✓' : 'Openen in Finder ↗'}
            </Btn>
          </div>
        </div>
      )}
    </div>
  );
}

function ZoekLeeg({ orgaan }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 20,
      maxWidth: 560, marginTop: 8,
    }}>
      <div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--accent)', letterSpacing: '0.16em',
          textTransform: 'uppercase', marginBottom: 10,
        }}>Full-text zoeken</div>
        <p style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.6, margin: 0 }}>
          Zoek door alle gedownloade vergaderstukken met SQLite FTS5.
          Resultaten verschijnen direct, gegroepeerd per vergadertype.
        </p>
      </div>

      <div style={{
        background: 'oklch(0.185 0.005 70)',
        border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
        padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        <Mono color="var(--dim)" size={10} style={{ letterSpacing: '0.10em', textTransform: 'uppercase' }}>
          Zoeksyntax
        </Mono>
        {[
          ['woord*',             'Begint met "woord" (truncation)'],
          ['"exacte zin"',       'Exacte woordvolgorde zoeken'],
          ['woord1 AND woord2',  'Beide termen moeten voorkomen'],
          ['woord1 OR woord2',   'Een van beide termen'],
          ['woord1 NOT woord2',  'Woord1 maar niet woord2'],
        ].map(([syntax, uitleg]) => (
          <div key={syntax} style={{ display: 'flex', gap: 14, alignItems: 'baseline' }}>
            <code style={{
              fontFamily: 'var(--font-mono)', fontSize: 11.5,
              color: 'var(--accent)', minWidth: 150,
            }}>{syntax}</code>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{uitleg}</span>
          </div>
        ))}
      </div>

      {!orgaan && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11.5,
          color: 'var(--muted)',
        }}>
          ← Kies eerst een orgaan in de zoekbalk.
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Search });
