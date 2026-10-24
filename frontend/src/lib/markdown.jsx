import { Fragment } from "react";

// Small, safe markdown: ## headings, paragraphs, - lists, **bold**, [links](url). No raw HTML.
function inline(text, key) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(<strong key={`${key}-${i++}`}>{tok.slice(2, -2)}</strong>);
    else {
      const [, label, href] = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok);
      const safe = /^(https?:|mailto:|tel:|\/)/.test(href) ? href : "#";
      out.push(<a key={`${key}-${i++}`} href={safe} target={safe.startsWith("http") ? "_blank" : undefined} rel="noreferrer">{label}</a>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text, className }) {
  if (!text) return null;
  const blocks = String(text).replace(/\r/g, "").split(/\n{2,}/);
  return (
    <div className={className}>
      {blocks.map((b, n) => {
        const lines = b.split("\n").filter((l) => l.trim());
        if (!lines.length) return null;
        if (lines[0].startsWith("### ")) return <h3 key={n}>{inline(lines[0].slice(4), n)}</h3>;
        if (lines[0].startsWith("## ")) {
          return <Fragment key={n}><h2>{inline(lines[0].slice(3), n)}</h2>{lines.length > 1 && <p>{inline(lines.slice(1).join(" "), `${n}p`)}</p>}</Fragment>;
        }
        if (lines.every((l) => /^\s*[-*] /.test(l))) return <ul key={n}>{lines.map((l, k) => <li key={k}>{inline(l.replace(/^\s*[-*] /, ""), `${n}-${k}`)}</li>)}</ul>;
        return <p key={n}>{inline(lines.join(" "), n)}</p>;
      })}
    </div>
  );
}
