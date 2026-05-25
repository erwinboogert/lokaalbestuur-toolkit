// dashboard.jsx — Dashboard met echte data van /api/status

const dashStyles = {
  alertRow: (nieuw) => ({
    display: 'grid',
    gridTemplateColumns: '4px 1fr 160px 100px 80px 48px',
    alignItems: 'center',
    gap: 16,
    padding: '11px 16px 11px 0',
    borderBottom: '1px solid var(--rule)',
    background: nieuw ? 'oklch(0.205 0.012 60)' : 'transparent',
    cursor: 'pointer',
    transition: 'background 80ms',
  }),
  unreadBar: (nieuw) => ({
    width: 4, alignSelf: 'stretch',
    background: nieuw ? 'var(--orange)' : 'transparent',
  }),
  th: {
    textAlign: 'left', padding: '8px 12px',
    fontFamily: 'var(--font-mono)', fontSize: 10,
    letterSpacing: '0.12em', textTransform: 'uppercase',
    color: 'var(--dim)', fontWeight: 500,
    borderBottom: '1px solid var(--border)',
    background: 'oklch(0.175 0.005 70)',
  },
  td: {
    padding: '11px 12px',
    borderBottom: '1px solid var(--rule)',
    color: 'var(--text-2)', verticalAlign: 'middle',
  },
  sourceTile: {
    background: 'oklch(0.205 0.005 70)',
    border: '1px solid var(--rule)',
    borderRadius: 'var(--r-2)',
    padding: '14px 16px',
    display: 'flex', flexDirection: 'column', gap: 6,
    cursor: 'pointer', transition: 'background 80ms',
  },
};

function Dashboard({ onNavigate }) {
  const [data, setData] = React.useState(null);
  const [fout, setFout] = React.useState(null);

  React.useEffect(() => {
    fetch('/api/status')
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then(setData)
      .catch(e => setFout(e.message));
  }, []);

  if (fout)  return <Foutmelding tekst={`Kan status niet laden: ${fout}`} />;
  if (!data) return <Laadspinner />;

  const { alerts, dossiers, bronnen, stats } = data;
  const heeftData = stats.totaal_docs > 0;

  if (!heeftData) return <DashboardLeeg onNavigate={onNavigate} />;

  const n_nieuw = alerts.filter(a => a.nieuw).length;

  return (
    <>
      {/* Hero-stats */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        marginBottom: 28,
        border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
        background: 'oklch(0.185 0.005 70)', overflow: 'hidden',
      }}>
        {[
          { k: 'Documenten in index',  v: stats.totaal_docs.toLocaleString('nl-NL'), sub: '' },
          { k: 'Actieve dossiers',     v: String(stats.actieve_dossiers), sub: `${n_nieuw} alert${n_nieuw !== 1 ? 's' : ''} vandaag` },
          { k: 'Bronnen gemonitord',   v: String(
              (bronnen.gemeenten.geconfigureerd || 0) +
              (bronnen.grs.geconfigureerd || 0) +
              (bronnen.waterschappen.geconfigureerd || 0) +
              (bronnen.veiligheidsregios.geconfigureerd || 0) +
              (bronnen.provincies.geconfigureerd || 0)
            ), sub: 'organen' },
          { k: 'Dossiers actief',      v: String(dossiers.filter(d => d.status === 'actief').length), sub: `${dossiers.filter(d => d.status === 'wacht').length} wachten` },
        ].map((s, i) => (
          <div key={i} style={{
            padding: '16px 20px',
            borderRight: i < 3 ? '1px solid var(--rule)' : 'none',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--dim)', letterSpacing: '0.10em', textTransform: 'uppercase',
            }}>{s.k}</div>
            <div style={{
              fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 28,
              letterSpacing: '-0.02em', color: 'var(--text)', lineHeight: 1.05,
              fontVariantNumeric: 'tabular-nums',
            }}>{s.v}</div>
            {s.sub && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--muted)' }}>{s.sub}</div>}
          </div>
        ))}
      </div>

      {/* Alerts */}
      <div style={{ marginBottom: 32 }}>
        <SectionHead
          kicker="01"
          title="Nieuwe meldingen"
          count={n_nieuw > 0 ? `${n_nieuw} ongelezen` : alerts.length === 0 ? 'geen' : 'alles gelezen'}
          right={<Btn small onClick={() => onNavigate('alerts')}>Naar Alerts →</Btn>}
        />
        {alerts.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 12, padding: '12px 0' }}>
            Geen alertrapporten gevonden — stel een dossier in om te beginnen.
          </div>
        ) : (
          <div style={{
            border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
            background: 'oklch(0.185 0.005 70)', overflow: 'hidden',
          }}>
            {alerts.slice(0, 8).map((a, i) => (
              <div key={i} style={dashStyles.alertRow(a.nieuw)}
                   onClick={() => onNavigate('alerts')}>
                <div style={dashStyles.unreadBar(a.nieuw)}></div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {a.nieuw && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
                                     color: 'var(--orange)', fontWeight: 600, letterSpacing: '0.08em' }}>
                        NIEUW
                      </span>
                    )}
                    <span style={{ color: 'var(--text)', fontWeight: 500, fontSize: 13.5,
                                   letterSpacing: '-0.005em', overflow: 'hidden',
                                   textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.dossier}
                    </span>
                  </div>
                  <Mono color="var(--muted)" size={11}>{a.orgaan}</Mono>
                </div>
                <Mono color="var(--muted)">{a.datum_display}</Mono>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, justifyContent: 'flex-end' }}>
                  <span style={{ fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 18, color: 'var(--text)' }}>{a.docs}</span>
                  <Mono color="var(--dim)" size={10.5}>docs</Mono>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--accent)' }}>→</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actieve dossiers */}
      <div style={{ marginBottom: 32 }}>
        <SectionHead
          kicker="02"
          title="Actieve dossiers"
          count={`${dossiers.length} dossiers`}
          right={<Btn small onClick={() => onNavigate('dossiers')}>+ Nieuw dossier</Btn>}
        />
        {dossiers.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 12, padding: '12px 0' }}>
            Geen dossiers — maak er een aan via Dossiers.
          </div>
        ) : (
          <div style={{ border: '1px solid var(--rule)', borderRadius: 'var(--r-2)', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: 12.5 }}>
              <thead>
                <tr>
                  <th style={dashStyles.th}>Dossier</th>
                  <th style={dashStyles.th}>Orgaan</th>
                  <th style={dashStyles.th}>Trefwoorden</th>
                  <th style={dashStyles.th}>Laatste run</th>
                  <th style={{ ...dashStyles.th, width: 100 }}>Status</th>
                  <th style={{ ...dashStyles.th, width: 120, textAlign: 'right' }}></th>
                </tr>
              </thead>
              <tbody>
                {dossiers.map((d, i) => (
                  <tr key={i} style={{ background: i % 2 === 1 ? 'oklch(0.175 0.005 70)' : 'transparent' }}>
                    <td style={{ ...dashStyles.td, color: 'var(--text)', fontWeight: 500 }}>
                      {d.label || d.naam}
                    </td>
                    <td style={dashStyles.td}><Mono color="var(--text-2)">{d.orgaan}</Mono></td>
                    <td style={dashStyles.td}>
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
                    <td style={dashStyles.td}><Mono color="var(--muted)">{d.laatste_run}</Mono></td>
                    <td style={dashStyles.td}><Badge kind={d.status} /></td>
                    <td style={{ ...dashStyles.td, textAlign: 'right' }}>
                      <NuDraaienKnop dossier={d.naam} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bronnen-status */}
      <div>
        <SectionHead
          kicker="03"
          title="Bronnen-status"
          right={<Btn small ghost onClick={() => onNavigate('scrapen')}>Naar Scrapen →</Btn>}
        />
        <BronnenDetail bronnen={bronnen} onNavigate={onNavigate} />
      </div>
    </>
  );
}

function NuDraaienKnop({ dossier }) {
  const [bezig, setBezig] = React.useState(false);
  const [klaar, setKlaar] = React.useState(false);

  const handleClick = async () => {
    setBezig(true);
    try {
      const resp = await fetch('/api/analyse/draaien', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dossier }),
      });
      const data = await resp.json();
      if (data.job_id) setKlaar(true);
    } finally {
      setBezig(false);
    }
  };

  if (klaar) return <Mono color="var(--green)" size={11}>Gestart ✓</Mono>;
  return (
    <Btn small onClick={handleClick} disabled={bezig}>
      {bezig ? 'Bezig…' : 'Nu draaien ↻'}
    </Btn>
  );
}

function DashboardLeeg({ onNavigate }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
      maxWidth: 760, margin: '40px auto 0', gap: 28,
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5,
                    color: 'var(--accent)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
        Eerste sessie
      </div>
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontWeight: 600,
        fontSize: 44, lineHeight: 1.1, letterSpacing: '-0.025em',
        color: 'var(--text)', margin: 0,
      }}>
        Welkom in Bronnenboek.<br />
        <span style={{ color: 'var(--muted)' }}>Nog geen documenten in de index.</span>
      </h1>
      <p style={{ fontSize: 14.5, lineHeight: 1.55, color: 'var(--text-2)', maxWidth: 580, margin: 0 }}>
        Bronnenboek downloadt vergaderstukken van Nederlandse gemeenten, waterschappen en
        andere bestuursorganen naar je eigen schijf. Begin met één gemeente.
      </p>
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0,
        width: '100%', border: '1px solid var(--rule)', borderRadius: 'var(--r-2)',
        overflow: 'hidden', background: 'oklch(0.185 0.005 70)',
      }}>
        {[
          { n: '01', t: 'Verkennen',       d: 'Zoek een gemeente op. Je ziet direct welke GRs, waterschappen en veiligheidsregio erbij horen.' },
          { n: '02', t: 'Scrapen',          d: '24 maanden terugkijken is de aanbevolen instelling. Droog uitvoeren is ook mogelijk.' },
          { n: '03', t: 'Doorzoekbaar maken', d: 'Bronnenboek bouwt een lokale full-text index. Duurt ~15 min per 300 documenten.' },
        ].map((s, i) => (
          <div key={i} style={{
            padding: '20px 22px',
            borderRight: i < 2 ? '1px solid var(--rule)' : 'none',
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            <Mono color="var(--accent)" size={11}>{s.n}</Mono>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 17, fontWeight: 600,
                          color: 'var(--text)', letterSpacing: '-0.01em' }}>{s.t}</div>
            <div style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.5 }}>{s.d}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        <Btn primary onClick={() => onNavigate('verkennen')}>Begin hier  →  Verkennen</Btn>
        <Btn ghost onClick={() => onNavigate('scrapen')}>Of meteen scrapen</Btn>
      </div>
    </div>
  );
}

// ── BronnenDetail ─────────────────────────────────────────────────────────────

const BRONNEN_TYPES = [
  { label: 'Gemeenten',          sleutel: 'gemeenten' },
  { label: "GR's",               sleutel: 'grs' },
  { label: 'Waterschappen',      sleutel: 'waterschappen' },
  { label: "Veiligheidsregio's", sleutel: 'veiligheidsregios' },
  { label: 'Provincies',         sleutel: 'provincies' },
];

function BronnenDetail({ bronnen, onNavigate }) {
  // Start open voor types die docs hebben, dicht voor lege
  const [open, setOpen] = React.useState(() => {
    const init = {};
    BRONNEN_TYPES.forEach(t => {
      init[t.sleutel] = (bronnen[t.sleutel]?.docs || 0) > 0;
    });
    return init;
  });

  const toggle = (sleutel) => setOpen(p => ({ ...p, [sleutel]: !p[sleutel] }));

  return (
    <div style={{ border: '1px solid var(--rule)', borderRadius: 'var(--r-2)', overflow: 'hidden' }}>
      {BRONNEN_TYPES.map((t, ti) => {
        const b      = bronnen[t.sleutel] || { geconfigureerd: 0, docs: 0, organen: [] };
        const organen = b.organen || [];
        const isOpen  = open[t.sleutel];
        const heeftOrganen = organen.length > 0;

        return (
          <div key={t.sleutel}>
            {/* Type-rij */}
            <div
              onClick={heeftOrganen ? () => toggle(t.sleutel) : undefined}
              style={{
                display: 'grid',
                gridTemplateColumns: '18px 1fr auto 100px',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                background: ti % 2 === 0
                  ? 'oklch(0.185 0.005 70)'
                  : 'oklch(0.178 0.005 70)',
                borderBottom: (isOpen && heeftOrganen) ? '1px solid var(--rule)' : 'none',
                cursor: heeftOrganen ? 'pointer' : 'default',
                userSelect: 'none',
              }}
            >
              {/* Uitklap-indicator */}
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                color: 'var(--dim)',
                opacity: heeftOrganen ? 1 : 0,
                transition: 'transform 150ms',
                display: 'inline-block',
                transform: isOpen ? 'rotate(90deg)' : 'none',
              }}>›</span>

              {/* Type-naam */}
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                color: 'var(--dim)', letterSpacing: '0.10em', textTransform: 'uppercase',
              }}>{t.label}</span>

              {/* Geconfigureerd */}
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--muted)' }}>
                {b.geconfigureerd} {b.geconfigureerd === 1 ? 'orgaan' : 'organen'}
              </span>

              {/* Docs-teller */}
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, justifyContent: 'flex-end' }}>
                <span style={{
                  fontFamily: 'var(--font-serif)', fontWeight: 600,
                  fontSize: b.docs > 0 ? 18 : 14,
                  color: b.docs > 0 ? 'var(--text)' : 'var(--dim)',
                  letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums',
                }}>{(b.docs || 0).toLocaleString('nl-NL')}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dim)' }}>docs</span>
              </div>
            </div>

            {/* Organen-rijen (uitgekalpt) */}
            {isOpen && heeftOrganen && organen.map((org, oi) => (
              <div
                key={org.slug}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '18px 1fr auto 100px',
                  alignItems: 'center',
                  gap: 10,
                  padding: '7px 14px 7px 32px',
                  background: 'oklch(0.162 0.004 70)',
                  borderBottom: oi < organen.length - 1
                    ? '1px solid oklch(0.205 0.005 70)'
                    : '1px solid var(--rule)',
                }}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'oklch(0.35 0.005 70)' }}>—</span>
                <span style={{ fontSize: 12.5, color: 'var(--text-2)', letterSpacing: '-0.005em' }}>
                  {org.naam}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'oklch(0.40 0.005 70)' }}>
                  {org.slug}
                </span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, justifyContent: 'flex-end' }}>
                  <span style={{
                    fontFamily: 'var(--font-serif)', fontWeight: 600,
                    fontSize: 14,
                    color: org.docs > 0 ? 'var(--text-2)' : 'oklch(0.38 0.005 70)',
                    fontVariantNumeric: 'tabular-nums',
                  }}>{org.docs.toLocaleString('nl-NL')}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dim)' }}>docs</span>
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { Dashboard, BronnenDetail });
