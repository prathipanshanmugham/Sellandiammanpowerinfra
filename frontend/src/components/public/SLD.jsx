// The hero's single-line diagram: 11 kV grid -> VCB -> transformer -> LT busbar -> your loads.
// It energises once on load (the only ambient motion on the site) and respects reduced-motion settings.
function Wire({ d, len, delay = 0, live = true, w = 2.5 }) {
  return <path d={d} className={live ? "sld-wire" : undefined} style={live ? { "--len": len, "--d": `${delay}s` } : undefined} stroke={live ? "#FFC400" : "#3A4D66"} strokeWidth={w} fill="none" strokeLinecap="round" />;
}
function Node({ children, delay = 0 }) {
  return <g className="sld-node" style={{ "--d": `${delay}s` }}>{children}</g>;
}
const T = ({ x, y, children, anchor = "start", dim }) => <text x={x} y={y} textAnchor={anchor} fill={dim ? "#7D8CA0" : "#E8ECF1"} fontSize="13" fontFamily="Inter, sans-serif">{children}</text>;

export default function SLD({ className }) {
  const loads = [
    { x: 92, label: "Production", sub: "PCC, motors" },
    { x: 212, label: "Utilities", sub: "APFC, lighting" },
    { x: 332, label: "Solar", sub: "net metered" },
    { x: 452, label: "EV & backup", sub: "chargers, DG" },
  ];
  return (
    <svg viewBox="0 0 520 560" className={className} role="img" aria-label="Single-line diagram: 11 kV supply through a breaker and transformer to an LT busbar feeding production, utilities, solar and EV loads">
      <defs>
        <pattern id="sldgrid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#13253B" strokeWidth="1" /></pattern>
      </defs>
      <rect width="520" height="560" fill="url(#sldgrid)" rx="12" />
      {/* static schematic underlay */}
      <g stroke="#3A4D66" strokeWidth="2.5" fill="none">
        <path d="M272 30V92M272 136V178M272 268V318M40 318H500" />
        {loads.map((l) => <path key={l.x} d={`M${l.x} 318V404M${l.x} 440V480`} />)}
      </g>
      {/* grid */}
      <Node delay={0}>
        <path d="M232 30H312M244 20H300M256 10H288" stroke="#A9ADB3" strokeWidth="2.5" />
        <T x={330} y={26}>11 kV grid</T><T x={330} y={44} dim>TNPDCL supply</T>
      </Node>
      <Wire d="M272 30V92" len={62} delay={0.1} />
      {/* VCB */}
      <Node delay={0.45}>
        <rect x="256" y="92" width="32" height="44" rx="3" stroke="#A9ADB3" strokeWidth="2.5" fill="#0A1626" />
        <path d="M262 126L282 102" stroke="#FFC400" strokeWidth="2.5" />
        <T x={300} y={112}>VCB</T><T x={300} y={130} dim>630 A, 20 kA</T>
      </Node>
      <Wire d="M272 136V178" len={42} delay={0.55} />
      {/* transformer */}
      <Node delay={0.8}>
        <circle cx="272" cy="203" r="25" stroke="#A9ADB3" strokeWidth="2.5" fill="#0A1626" />
        <circle cx="272" cy="243" r="25" stroke="#A9ADB3" strokeWidth="2.5" fill="none" />
        <T x={310} y={210}>1000 kVA</T><T x={310} y={228} dim>11/0.433 kV, Dyn11</T>
      </Node>
      <Wire d="M272 268V318" len={50} delay={0.95} />
      {/* LT busbar */}
      <Node delay={1.15}>
        <rect x="36" y="312" width="468" height="12" rx="2" fill="#16283F" stroke="#A9ADB3" strokeWidth="2" />
        <T x={40} y={300} dim>415 V LT busbar</T>
      </Node>
      <Wire d="M272 318H40" len={232} delay={1.2} w={3.5} />
      <Wire d="M272 318H500" len={228} delay={1.2} w={3.5} />
      {loads.map((l, n) => (
        <g key={l.x}>
          <Node delay={1.5 + n * 0.12}>
            <rect x={l.x - 12} y="404" width="24" height="36" rx="3" stroke="#A9ADB3" strokeWidth="2.2" fill="#0A1626" />
            <path d={`M${l.x - 6} 432L${l.x + 6} 412`} stroke="#FFC400" strokeWidth="2.2" />
          </Node>
          <Wire d={`M${l.x} 318V404`} len={86} delay={1.45 + n * 0.12} />
          <Wire d={`M${l.x} 440V480`} len={40} delay={1.8 + n * 0.12} />
          <Node delay={1.95 + n * 0.12}>
            <path d={`M${l.x - 16} 480L${l.x} 500L${l.x + 16} 480Z`} fill="#FFC400" />
            <T x={l.x} y={524} anchor="middle">{l.label}</T>
            <T x={l.x} y={542} anchor="middle" dim>{l.sub}</T>
          </Node>
        </g>
      ))}
    </svg>
  );
}
