import { Link } from "react-router-dom";
import { MapPin } from "lucide-react";
import { asset, fileUrl } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSite, optLabel } from "./site";

const ILL = { ht_substation: "substation", lt_electrification: "panel", ht_lt_panels: "panel", transformers: "transformer", cabling: "cable",
  earthing_lps: "earthing", dg_ups: "panel", street_lighting: "lighting", solar_epc: "solar", ev_charging: "ev", liaison: "substation",
  testing: "testing", amc: "testing", energy_audit: "testing" };
export const illustrationFor = (service) => asset(`/illustrations/${ILL[service] || "substation"}.svg`);

export function Cover({ file, service, alt, className, label = true }) {
  const url = fileUrl(file);
  return (
    <div className={cn("relative overflow-hidden bg-ink", className)}>
      <img src={url || illustrationFor(service)} alt={alt || ""} loading="lazy" decoding="async" className="h-full w-full object-cover" />
      {!url && label && <span className="absolute bottom-2 start-2 rounded bg-ink/80 px-1.5 py-0.5 text-[11px] text-white/80">Illustration</span>}
    </div>
  );
}

export function Chip({ children, dark }) {
  return <span className={cn("inline-flex items-center rounded px-2 py-0.5 text-xs font-medium", dark ? "bg-white/10 text-white/85" : "bg-paper text-fg/80 ring-1 ring-inset ring-line")}>{children}</span>;
}

export function ProjectCard({ p, big }) {
  const site = useSite();
  return (
    <Link to={`/projects/${p.slug}`} className="group block">
      <Cover file={p.cover} service={p.service} alt={p.title} className={cn("rounded-lg", big ? "aspect-[16/10]" : "aspect-[4/3]")} />
      <div className="mt-3">
        <div className="flex flex-wrap gap-1.5">
          {p.capacity_kva && <Chip>{p.capacity_kva} kVA</Chip>}
          {p.voltage && <Chip>{p.voltage.replace("kV", " kV").replace("415V", "415 V")}</Chip>}
          {p.sample && <Chip>Sample</Chip>}
          {p.ongoing && <Chip>Ongoing</Chip>}
        </div>
        <h3 className="mt-2 font-display text-[17px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:decoration-2 group-hover:underline-offset-4">{p.title}</h3>
        <p className="mt-1 flex items-center gap-1 text-sm text-muted"><MapPin className="h-3.5 w-3.5" />{p.town}{p.year ? `, ${p.year}` : ""}</p>
        <p className="text-sm text-muted">{optLabel(site, "services", p.service)}</p>
      </div>
    </Link>
  );
}

export function Stat({ value, label, dark }) {
  return (
    <div>
      <p className={cn("font-display text-[28px] font-extrabold leading-none md:text-[34px]", dark ? "text-white" : "text-fg")} style={{ letterSpacing: "-0.03em" }}>{value}</p>
      <p className={cn("mt-2 text-sm leading-snug", dark ? "text-white/75" : "text-muted")}>{label}</p>
    </div>
  );
}
