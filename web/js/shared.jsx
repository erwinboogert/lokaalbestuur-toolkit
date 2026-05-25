// shared.jsx — Sidebar, AppFrame en herbruikbare primitieven

const sharedStyles = {
  frame: {
    width: '100%',
    height: '100%',
    display: 'grid',
    gridTemplateColumns: '220px 1fr',
    background: 'var(--bg)',
    color: 'var(--text)',
    fontFamily: 'var(--font-ui)',
    fontSize: 13,
    overflow: 'hidden',
  },
  sidebar: {
    background: 'oklch(0.135 0.004 70)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    padding: '18px 0 14px',
    userSelect: 'none',
  },
  brand: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 8,
    padding: '4px 18px 22px',
    borderBottom: '1px solid var(--rule)',
    marginBottom: 14,
  },
  brandMark: {
    fontFamily: 'var(--font-serif)',
    fontWeight: 600,
    fontSize: 18,
    letterSpacing: '-0.01em',
    color: 'var(--text)',
  },
  brandDot: {
    width: 6, height: 6, borderRadius: 1, background: 'var(--accent)',
    transform: 'translateY(-2px)',
  },
  brandSub: {
    marginLeft: 'auto',
    fontFamily: 'var(--font-mono)',
    fontSize: 9.5,
    letterSpacing: '0.08em',
    color: 'var(--dim)',
    textTransform: 'uppercase',
  },
  navLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: 9.5,
    color: 'var(--dim)',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    padding: '6px 18px 8px',
  },
  navItem: (active) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '7px 18px',
    cursor: 'pointer',
    color: active ? 'var(--text)' : 'var(--text-2)',
    background: active ? 'oklch(0.215 0.005 70)' : 'transparent',
    borderLeft: `2px solid ${active ? 'var(--accent)' : 'transparent'}`,
    paddingLeft: 16,
    fontWeight: active ? 500 : 400,
    fontSize: 13,
    letterSpacing: '-0.005em',
    transition: 'background 80ms',
  }),
  navCount: (active) => ({
    marginLeft: 'auto',
    fontFamily: 'var(--font-mono)',
    fontSize: 10.5,
    color: active ? 'var(--text-2)' : 'var(--muted)',
    fontVariantNumeric: 'tabular-nums',
  }),
  navDivider: { height: 1, background: 'var(--rule)', margin: '14px 18px' },
  footer: {
    marginTop: 'auto',
    padding: '10px 18px',
    fontFamily: 'var(--font-mono)',
    fontSize: 10.5,
    color: 'var(--dim)',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    minWidth: 0,
  },
  topbar: {
    height: 48,
    display: 'flex',
    alignItems: 'center',
    padding: '0 28px',
    borderBottom: '1px solid var(--rule)',
    background: 'var(--bg)',
    gap: 14,
    flexShrink: 0,
  },
  crumb: {
    display: 'flex', alignItems: 'baseline', gap: 8,
    fontSize: 12.5, color: 'var(--text-2)',
  },
  crumbSep: { color: 'var(--dim)', fontFamily: 'var(--font-mono)' },
  topbarRight: {
    marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14,
    fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--muted)',
  },
  scroll: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 28px 40px',
  },
};

// ── PadModal ──────────────────────────────────────────────────────────────────

function PadModal({ huidigPad, onOpslaan, onSluiten }) {
  const [pad, setPad]       = React.useState(huidigPad || '');
  const [bezig, setBezig]   = React.useState(false);
  const [fout, setFout]     = React.useState(null);
  const [succes, setSucces] = React.useState(false);

  const opslaan = async () => {
    if (!pad.trim()) return;
    setBezig(true); setFout(null);
    try {
      const resp = await fetch('/api/instellingen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ output_pad: pad.trim() }),
      });
      const data = await resp.json();
      if (data.fout) setFout(data.fout);
      else { setSucces(true); onOpslaan(data.nieuw_pad || pad.trim()); }
    } catch (e) {
      setFout(e.message);
    } finally {
      setBezig(false);
    }
  };

  const invoerStyle = {
    background: 'oklch(0.175 0.005 70)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-2)',
    color: 'var(--text)',
    fontFamily: 'var(--font-mono)', fontSize: 12.5,
    padding: '9px 12px',
    outline: 'none',
    width: '100%',
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'oklch(0 0 0 / 0.55)', zIndex: 200,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={onSluiten}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'oklch(0.21 0.005 70)',
          border: '1px solid var(--border-2)',
          borderRadius: 'var(--r-3)',
          padding: '24px 28px', width: 500,
          display: 'flex', flexDirection: 'column', gap: 16,
          boxShadow: '0 20px 60px oklch(0 0 0 / 0.6)',
        }}
      >
        <div style={{
          fontFamily: 'var(--font-serif)', fontSize: 17,
          fontWeight: 600, color: 'var(--text)',
        }}>
          Documentenmap instellen
        </div>
        <div style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.55 }}>
          Absoluut pad waar Bronnenboek documenten opslaat. Je kunt{' '}
          <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5 }}>~</code>{' '}
          gebruiken voor de thuismap. Na het opslaan is een{' '}
          <strong style={{ color: 'var(--text-2)' }}>herstart van de server</strong>{' '}
          nodig.
        </div>
        <input
          type="text"
          value={pad}
          onChange={e => { setPad(e.target.value); setSucces(false); setFout(null); }}
          placeholder="/Users/naam/Documents/notulen"
          autoFocus
          style={invoerStyle}
          onKeyDown={e => { if (e.key === 'Enter' && !succes) opslaan(); if (e.key === 'Escape') onSluiten(); }}
        />
        {fout && (
          <div style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            {fout}
          </div>
        )}
        {succes && (
          <div style={{ color: 'var(--green)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            ✓ Opgeslagen — herstart de server om de wijziging door te voeren.
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn ghost onClick={onSluiten}>Annuleren</Btn>
          <Btn primary onClick={opslaan} disabled={bezig || !pad.trim() || succes}>
            {bezig ? 'Opslaan…' : 'Opslaan'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ active, onNavigate, counts = {} }) {
  const [outputPad, setOutputPad] = React.useState(null);
  const [editOpen, setEditOpen]   = React.useState(false);

  React.useEffect(() => {
    fetch('/api/instellingen')
      .then(r => r.json())
      .then(d => setOutputPad(d.output_pad))
      .catch(() => {});
  }, []);

  // ~/Documents/notulen in plaats van /Users/erwin/Documents/notulen
  const padKort = outputPad
    ? outputPad.replace(/^\/Users\/[^/]+/, '~')
    : null;

  const werkItems = [
    { id: 'dashboard',  label: 'Dashboard',  count: null },
    { id: 'verkennen',  label: 'Verkennen',  count: null },
    { id: 'scrapen',    label: 'Scrapen',    count: null },
    { id: 'zoeken',     label: 'Zoeken',     count: null },
  ];
  const onderzoekItems = [
    { id: 'dossiers',   label: 'Dossiers',   count: counts.dossiers || null },
    { id: 'alerts',     label: 'Alerts',     count: counts.alerts || null },
  ];

  const renderItems = (items) => items.map(it => (
    <div
      key={it.id}
      style={sharedStyles.navItem(active === it.id)}
      onClick={() => onNavigate && onNavigate(it.id)}
    >
      <span>{it.label}</span>
      {it.count > 0 && (
        <span style={{
          ...sharedStyles.navCount(active === it.id),
          ...(it.id === 'alerts' && it.count > 0
            ? { color: 'var(--orange)', fontWeight: 600 }
            : {}),
        }}>{it.count}</span>
      )}
    </div>
  ));

  return (
    <aside style={sharedStyles.sidebar}>
      <div style={sharedStyles.brand}>
        <span style={sharedStyles.brandDot}></span>
        <span style={sharedStyles.brandMark}>Bronnenboek</span>
        <span style={sharedStyles.brandSub}>v1.0</span>
      </div>

      <div style={sharedStyles.navLabel}>Werk</div>
      {renderItems(werkItems)}

      <div style={sharedStyles.navDivider}></div>
      <div style={sharedStyles.navLabel}>Onderzoek</div>
      {renderItems(onderzoekItems)}

      <div style={sharedStyles.footer}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }}></span>
          <span>{window.location.host}</span>
        </div>
        {padKort && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
            <span style={{
              flex: 1, fontSize: 10, color: 'var(--dim)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }} title={outputPad}>
              {padKort}
            </span>
            <button
              onClick={() => setEditOpen(true)}
              title="Documentenmap wijzigen"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--dim)', fontSize: 12, padding: '1px 3px',
                flexShrink: 0, lineHeight: 1,
                transition: 'color 80ms',
              }}
              onMouseEnter={e => e.target.style.color = 'var(--text-2)'}
              onMouseLeave={e => e.target.style.color = 'var(--dim)'}
            >✎</button>
          </div>
        )}
      </div>

      {editOpen && (
        <PadModal
          huidigPad={outputPad}
          onOpslaan={(nieuwPad) => { setOutputPad(nieuwPad); setEditOpen(false); }}
          onSluiten={() => setEditOpen(false)}
        />
      )}
    </aside>
  );
}

function Topbar({ crumbs = [], right }) {
  return (
    <div style={sharedStyles.topbar}>
      <div style={sharedStyles.crumb}>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            <span style={{
              color: i === crumbs.length - 1 ? 'var(--text)' : 'var(--muted)',
              fontWeight: i === crumbs.length - 1 ? 500 : 400,
            }}>{c}</span>
            {i < crumbs.length - 1 && <span style={sharedStyles.crumbSep}>/</span>}
          </React.Fragment>
        ))}
      </div>
      {right && <div style={sharedStyles.topbarRight}>{right}</div>}
    </div>
  );
}

// ── Primitieven ───────────────────────────────────────────────────────────────

function Badge({ kind = 'gray', children, dot = true }) {
  const map = {
    nieuw:  { bg: 'var(--orange-soft)', fg: 'var(--orange)' },
    actief: { bg: 'var(--green-soft)',  fg: 'var(--green)'  },
    fout:   { bg: 'var(--red-soft)',    fg: 'var(--red)'    },
    wacht:  { bg: 'var(--grayb-soft)', fg: 'var(--grayb)'  },
    accent: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
    gray:   { bg: 'oklch(0.27 0.005 70)', fg: 'var(--text-2)' },
    klaar:  { bg: 'var(--green-soft)',  fg: 'var(--green)'  },
  };
  const s = map[kind] || map.gray;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '2px 8px 2px 6px',
      background: s.bg, color: s.fg,
      borderRadius: 'var(--r-1)',
      fontSize: 10.5, fontWeight: 500,
      fontFamily: 'var(--font-ui)',
      letterSpacing: '0.02em',
      lineHeight: 1.4,
      whiteSpace: 'nowrap',
    }}>
      {dot && <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.fg }}></span>}
      {children || kind}
    </span>
  );
}

function ProgressBar({ pct, label, kind = 'accent', height = 6, indeterminate = false }) {
  const color = kind === 'green' ? 'var(--green)' : 'var(--accent)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
      <div style={{
        flex: 1, height,
        background: 'oklch(0.225 0.005 70)',
        borderRadius: 2, overflow: 'hidden', position: 'relative',
      }}>
        {indeterminate ? (
          <div style={{
            position: 'absolute', top: 0, left: 0, height: '100%', width: '40%',
            background: color,
            animation: 'indeterminate 1.4s ease-in-out infinite',
          }}></div>
        ) : (
          <div style={{
            width: `${Math.max(0, Math.min(100, pct))}%`,
            height: '100%', background: color,
            transition: 'width 300ms ease',
          }}></div>
        )}
      </div>
      {label !== false && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text)', fontVariantNumeric: 'tabular-nums',
          minWidth: 40, textAlign: 'right',
        }}>{label ?? `${Math.round(pct)}%`}</span>
      )}
      <style>{`
        @keyframes indeterminate {
          0%   { left: -40%; }
          100% { left: 100%; }
        }
      `}</style>
    </div>
  );
}

function Mono({ children, color, size }) {
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: size || 11.5,
      color: color || 'var(--text-2)', fontVariantNumeric: 'tabular-nums',
    }}>{children}</span>
  );
}

function Btn({ children, primary, danger, ghost, small, onClick, disabled }) {
  let bg = 'oklch(0.255 0.005 70)';
  let fg = 'var(--text)';
  let border = '1px solid var(--border)';
  if (primary) { bg = 'var(--accent)';    fg = 'var(--accent-ink)'; border = '1px solid var(--accent)'; }
  if (ghost)   { bg = 'transparent';       fg = 'var(--text-2)'; }
  if (danger)  { bg = 'transparent';       fg = 'var(--red)'; border = '1px solid oklch(0.45 0.12 25 / 0.5)'; }
  return (
    <button onClick={onClick} disabled={disabled} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: small ? '4px 10px' : '7px 14px',
      background: bg, color: fg, border,
      borderRadius: 'var(--r-2)',
      fontFamily: 'var(--font-ui)', fontSize: small ? 11.5 : 12.5,
      fontWeight: primary ? 600 : 500,
      letterSpacing: '-0.005em',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: 'background 120ms, border-color 120ms',
    }}>
      {children}
    </button>
  );
}

function SectionHead({ kicker, title, count, right }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 12,
      marginBottom: 12, paddingBottom: 8,
      borderBottom: '1px solid var(--rule)',
    }}>
      {kicker && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--accent)', letterSpacing: '0.16em', textTransform: 'uppercase',
          fontWeight: 600,
        }}>{kicker}</span>
      )}
      <h2 style={{
        margin: 0, fontFamily: 'var(--font-serif)', fontWeight: 600,
        fontSize: 18, letterSpacing: '-0.01em', color: 'var(--text)',
      }}>{title}</h2>
      {count != null && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--muted)', fontVariantNumeric: 'tabular-nums',
        }}>{count}</span>
      )}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>{right}</div>
    </div>
  );
}

function Toast({ kind = 'info', title, body, onClose }) {
  const colors = { info: 'var(--accent)', success: 'var(--green)', error: 'var(--red)' };
  React.useEffect(() => {
    if (onClose) {
      const t = setTimeout(onClose, 4000);
      return () => clearTimeout(t);
    }
  }, []);
  return (
    <div style={{
      position: 'fixed', right: 24, bottom: 24, width: 320, zIndex: 100,
      background: 'oklch(0.21 0.005 70)',
      border: '1px solid var(--border-2)',
      borderLeft: `3px solid ${colors[kind] || colors.info}`,
      borderRadius: 'var(--r-2)',
      padding: '12px 14px',
      boxShadow: '0 12px 32px oklch(0 0 0 / 0.5)',
      fontSize: 12.5,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 3, color: 'var(--text)' }}>{title}</div>
      {body && <div style={{ color: 'var(--muted)', fontSize: 11.5 }}>{body}</div>}
    </div>
  );
}

function Laadspinner() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '40px 0', color: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 12,
    }}>
      <div style={{
        width: 14, height: 14, borderRadius: '50%',
        border: '2px solid var(--border)', borderTopColor: 'var(--accent)',
        animation: 'spin 0.8s linear infinite',
      }}></div>
      Laden…
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function Foutmelding({ tekst }) {
  return (
    <div style={{
      padding: '16px 18px',
      background: 'var(--red-soft)', border: '1px solid var(--red)',
      borderRadius: 'var(--r-2)', color: 'var(--red)',
      fontFamily: 'var(--font-mono)', fontSize: 12,
    }}>
      {tekst}
    </div>
  );
}

Object.assign(window, {
  sharedStyles, Sidebar, Topbar, PadModal,
  Badge, ProgressBar, Mono, Btn, SectionHead, Toast, Laadspinner, Foutmelding,
});
