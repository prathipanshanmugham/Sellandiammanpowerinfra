// Settings -> AI agents & MCP: agents that let Claude (or any MCP client) work in the ERP as one staff login.
import { useMemo, useState } from "react";
import { Bot, Plus, Copy, Check, KeyRound, Pause, Play, Pencil, Ban, ListChecks, ShieldCheck, ShieldOff, ChevronLeft, ChevronRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { fmtDateTime, fmtDate, ago } from "@/lib/format";
import { Button, Badge, Skeleton, Input, Textarea, Select, Field, Tabs, TabPanel, Alert, Dialog, Confirm, Empty, Checkbox } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi } from "../lib";
import { PageHead, Panel, Table, usePageTitle } from "../ui";

const STATUS = { active: ["green", "Active"], paused: ["amber", "Paused"], revoked: ["red", "Revoked"], expired: ["gray", "Expired"] };
const NEVER = ["delete anything", "approve or reject requests", "change logins, keys or company settings", "open the password vault", "check in, apply for leave or run payroll"];

function CopyField({ label, value, mono = true, hint }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(value); setDone(true); setTimeout(() => setDone(false), 1500); } catch { toast.error("Couldn't copy. Select the text and copy it."); }
  }
  return (
    <div className="min-w-0">
      {label && <p className="mb-1 text-xs font-medium text-muted">{label}</p>}
      <div className="flex items-stretch gap-2">
        <code className={cn("block min-w-0 flex-1 select-all break-all rounded-md border border-edge bg-canvas px-3 py-2 text-[13px] leading-snug", !mono && "font-sans")}>{value}</code>
        <Button type="button" size="sm" variant="outline" onClick={copy} className="shrink-0" aria-label={`Copy ${label || "text"}`}>{done ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}</Button>
      </div>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

// How to add the server to Claude and to Claude Code, filled in with the real address (and the key when we have it)
function ConnectSteps({ url, keyText }) {
  const k = keyText || "spi_…your key…";
  return (
    <div className="space-y-5 text-sm">
      <section className="space-y-2">
        <h3 className="font-sans text-[15px] font-semibold">Claude (web, desktop and phone apps)</h3>
        <ol className="list-decimal space-y-1.5 ps-5">
          <li>In Claude, open <b>Customize → Connectors</b>, choose <b>+ Add</b>, then <b>Add custom connector</b>. On a Team or Enterprise plan an owner adds it under <b>Organization settings → Connectors</b>.</li>
          <li>Name it <b>Sellandiamman Power Infra</b> and paste the server address below.</li>
          <li>For authentication choose <b>No sign in</b>, and under <b>Request headers</b> add <code className="rounded bg-canvas px-1">Authorization</code> with the value <code className="rounded bg-canvas px-1 break-all">Bearer {k}</code>.</li>
          <li>Add it, then switch it on in a chat from <b>+ → Connectors</b>.</li>
        </ol>
        <CopyField label="Server address" value={url} />
        <CopyField label="Request header value (Authorization)" value={`Bearer ${k}`} />
      </section>
      <section className="space-y-2">
        <h3 className="font-sans text-[15px] font-semibold">Claude Code</h3>
        <CopyField value={`claude mcp add --transport http --scope user spi-power-infra ${url} --header "Authorization: Bearer ${k}"`} />
      </section>
      <section className="space-y-2">
        <h3 className="font-sans text-[15px] font-semibold">Apps that only take an address</h3>
        <p className="text-muted">Use the address with the key in it. The key then also appears in the web server's access log, so prefer the header where you can.</p>
        <CopyField value={`${url}?key=${k}`} />
      </section>
    </div>
  );
}

function AgentCard({ a, writable, onEdit, onToggle, onRotate, onRevoke, onLog }) {
  const [tone, label] = STATUS[a.status] || STATUS.paused;
  const live = a.status !== "revoked";
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-xl border border-edge bg-surface p-4 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className={cn("mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md", a.status === "active" ? "bg-ink text-signal-bright" : "bg-fg/[.06] text-muted")}><Bot className="h-5 w-5" /></span>
          <div className="min-w-0">
            <h3 className="break-words font-sans text-[16px] font-semibold leading-snug">{a.name}</h3>
            <p className="text-sm text-muted">Works as {a.user_name || "a removed login"}{a.user_role_label ? ` · ${a.user_role_label}` : ""}{a.user_active === false ? " (login switched off)" : ""}</p>
          </div>
        </div>
        <Badge tone={tone} dot>{label}</Badge>
      </div>
      {a.purpose && <p className="line-clamp-3 text-sm text-fg/85">{a.purpose}</p>}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div><dt className="text-xs text-muted">Access</dt><dd className="flex items-center gap-1.5">{a.access === "write" ? <ShieldCheck className="h-3.5 w-3.5 text-warn" /> : <ShieldOff className="h-3.5 w-3.5 text-muted" />}{a.access === "write" ? "Read & write" : "Read only"}</dd></div>
        <div><dt className="text-xs text-muted">Key</dt><dd className="font-mono text-[13px]">{a.key_prefix}…</dd></div>
        <div><dt className="text-xs text-muted">Last used</dt><dd>{a.last_used_at ? ago(a.last_used_at) : "Not yet"}{a.last_client ? <span className="block truncate text-xs text-muted">{a.last_client}</span> : null}</dd></div>
        <div><dt className="text-xs text-muted">Calls</dt><dd className="tabular">{a.calls_total || 0}</dd></div>
        <div><dt className="text-xs text-muted">Expires</dt><dd>{a.expires_on ? fmtDate(a.expires_on) : "No end date"}</dd></div>
        <div><dt className="text-xs text-muted">Made by</dt><dd className="truncate">{a.created_by_name}, {fmtDate(a.created_at)}</dd></div>
      </dl>
      <div className="mt-auto flex flex-wrap gap-2 border-t border-edge pt-3">
        <Button size="sm" variant="outline" onClick={onLog}><ListChecks className="h-4 w-4" />Activity</Button>
        {writable && live && <>
          <Button size="sm" variant="outline" onClick={onToggle}>{a.active ? <><Pause className="h-4 w-4" />Pause</> : <><Play className="h-4 w-4" />Switch on</>}</Button>
          <Button size="sm" variant="outline" onClick={onRotate}><KeyRound className="h-4 w-4" />New key</Button>
          <Button size="sm" variant="outline" onClick={onEdit}><Pencil className="h-4 w-4" />Edit</Button>
          <Button size="sm" variant="ghost" className="text-bad hover:bg-bad/10" onClick={onRevoke}><Ban className="h-4 w-4" />Revoke</Button>
        </>}
      </div>
    </article>
  );
}

function AgentDialog({ open, onOpenChange, agent, templates, staff, onSaved }) {
  const editing = !!agent?.id;
  const [tpl, setTpl] = useState(agent?.template || "");
  const [v, setV] = useState(() => agent?.id ? { name: agent.name, purpose: agent.purpose || "", access: agent.access, user_id: agent.user_id, expires_on: agent.expires_on || "" }
    : { name: "", purpose: "", access: "read", user_id: "", expires_on: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (x) => setV((s) => ({ ...s, [k]: x?.target ? x.target.value : x }));
  function pickTemplate(t) {
    setTpl(t?.key || "");
    if (!t) return;
    const suggested = t.roles.map((r) => staff.find((u) => u.role === r)).find(Boolean);
    setV((s) => ({ ...s, name: t.name, purpose: t.purpose, access: t.access, user_id: s.user_id || suggested?.id || "" }));
  }
  async function save() {
    setBusy(true);
    try {
      const body = { ...v, template: tpl || null, expires_on: v.expires_on || null };
      if (!body.user_id) delete body.user_id;
      const r = editing ? await api.patch(`/ai/agents/${agent.id}`, body) : await api.post("/ai/agents", body);
      onSaved(r.data, editing);
    } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange} wide title={editing ? `Edit ${agent.name}` : "New AI agent"}
      description={editing ? "Changes apply from the agent's next call. The key stays the same." : "Pick a job to start from, choose whose login it works as, then copy its key."}
      footer={<><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button loading={busy} onClick={save} disabled={!v.name.trim()}>{editing ? "Save" : "Create agent"}</Button></>}>
      <div className="space-y-4">
        {!editing && (
          <div>
            <p className="field-label">Job</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {templates.map((t) => (
                <button key={t.key} type="button" onClick={() => pickTemplate(t)} aria-pressed={tpl === t.key}
                  className={cn("rounded-lg border px-3 py-2.5 text-start transition-colors", tpl === t.key ? "border-ink bg-signal-soft/40" : "border-edge hover:border-fg/30")}>
                  <span className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{t.name}</span><Badge tone={t.access === "write" ? "amber" : "gray"}>{t.access === "write" ? "Read & write" : "Read only"}</Badge></span>
                  <span className="mt-0.5 line-clamp-2 text-xs text-muted">{t.purpose}</span>
                </button>
              ))}
              <button type="button" onClick={() => { setTpl(""); setV((s) => ({ ...s, name: s.name && tpl ? "" : s.name, purpose: tpl ? "" : s.purpose })); }} aria-pressed={!tpl}
                className={cn("rounded-lg border border-dashed px-3 py-2.5 text-start", !tpl ? "border-ink bg-signal-soft/40" : "border-edge hover:border-fg/30")}>
                <span className="text-sm font-semibold">Your own job</span><span className="block text-xs text-muted">Write the job description yourself</span>
              </button>
            </div>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" required htmlFor="ai-name"><Input id="ai-name" value={v.name} onChange={set("name")} placeholder="Sales assistant" maxLength={60} /></Field>
          <Field label="Works as" htmlFor="ai-user" hint="It gets this person's permissions, branches and hidden fields">
            <Select id="ai-user" value={v.user_id} onChange={set("user_id")} placeholder="Me" options={staff.map((u) => ({ value: u.id, label: `${u.name}, ${u.role_label}` }))} />
          </Field>
        </div>
        <fieldset>
          <legend className="field-label">Access</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {[["read", "Read only", "Looks things up, runs reports and screens. Changes nothing."], ["write", "Read & write", "Can also add and change records and move them on, as the person could. Never deletes."]].map(([k, l, d]) => (
              <label key={k} className={cn("flex cursor-pointer gap-2.5 rounded-lg border px-3 py-2.5", v.access === k ? "border-ink bg-signal-soft/40" : "border-edge")}>
                <input type="radio" name="ai-access" value={k} checked={v.access === k} onChange={() => set("access")(k)} className="mt-1 accent-ink" />
                <span><span className="block text-sm font-semibold">{l}</span><span className="block text-xs text-muted">{d}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
        <Field label="Job description" htmlFor="ai-purpose" hint="The AI reads this when it connects. Say what to look after and what to leave alone.">
          <Textarea id="ai-purpose" rows={4} value={v.purpose} onChange={set("purpose")} maxLength={2000} />
        </Field>
        <Field label="Stops working after" htmlFor="ai-exp" hint="Optional. Useful for a trial or a contractor's tool." className="sm:max-w-xs">
          <Input id="ai-exp" type="date" value={v.expires_on || ""} onChange={set("expires_on")} />
        </Field>
      </div>
    </Dialog>
  );
}

function Activity({ agents, agentId, setAgentId, tools }) {
  const titles = useMemo(() => Object.fromEntries((tools || []).map((t) => [t.name, t.title])), [tools]);
  const [errors, setErrors] = useState(false);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useApi("/ai/calls", { agent_id: agentId || undefined, errors: errors || undefined, page });
  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap sm:items-center">
        <Select value={agentId} onChange={(e) => { setAgentId(e.target.value); setPage(1); }} placeholder="All agents" options={(agents || []).map((a) => ({ value: a.id, label: a.name }))} className="h-9 sm:w-64" aria-label="Agent" />
        <Checkbox checked={errors} onChange={(x) => { setErrors(x); setPage(1); }} label="Only calls that failed" id="ai-errors" />
        {data && <span className="text-sm text-muted sm:ms-auto">{data.total} calls, kept 90 days</span>}
      </div>
      <Panel bodyClass="p-0">
        {isLoading ? <Skeleton className="m-4 h-40" /> : (
          <Table empty="No calls yet. They appear here as soon as an agent connects." columns={[
            { label: "Call", render: (c) => <span><span className="font-medium">{titles[c.tool] || c.tool || (c.method === "initialize" ? "Connected" : c.method)}</span><span className="block text-xs font-normal text-muted">{c.agent_name}</span></span> },
            { label: "When", render: (c) => fmtDateTime(c.at), className: "whitespace-nowrap" },
            { label: "Result", render: (c) => <Badge tone={c.ok ? "green" : "red"}>{c.ok ? "Done" : "Refused"}</Badge> },
            { label: "Time", right: true, render: (c) => `${c.ms ?? 0} ms` },
            { label: "Details", render: (c) => <span className={cn("line-clamp-2 break-all text-xs", c.ok ? "text-muted" : "text-bad")}>{c.error || c.args || "—"}</span>, className: "max-w-[420px]" },
          ]} rows={data?.items || []} />
        )}
      </Panel>
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft className="h-4 w-4" />Newer</Button>
          <span className="text-muted tabular">{page} / {pages}</span>
          <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>Older<ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
    </div>
  );
}

export default function AiAgentsPage() {
  const { can } = useAuth();
  const writable = can("ai", "w");
  usePageTitle("AI agents & MCP");
  const { data: info } = useApi("/ai/info");
  const { data: agents, isLoading, refetch } = useApi("/ai/agents");
  const { data: staff } = useApi("/users/lookup", null, { staleTime: 5 * 60e3 });
  const [tab, setTab] = useState("agents");
  const [dialog, setDialog] = useState(null); // {} new, agent = edit
  const [issued, setIssued] = useState(null);
  const [revoke, setRevoke] = useState(null);
  const [rotate, setRotate] = useState(null);
  const [logAgent, setLogAgent] = useState("");
  const sorted = useMemo(() => [...(agents || [])].sort((a, b) => (a.status === "revoked") - (b.status === "revoked")), [agents]);
  const url = info?.mcp_url || `${window.location.origin}/api/mcp`;

  async function patch(a, body, msg) {
    try { await api.patch(`/ai/agents/${a.id}`, body); toast.success(msg); refetch(); } catch (ex) { toast.error(errMsg(ex)); }
  }
  async function doRotate(a) {
    try { const r = await api.post(`/ai/agents/${a.id}/rotate`); setIssued(r.data); refetch(); } catch (ex) { toast.error(errMsg(ex)); }
  }
  async function doRevoke(a) {
    try { await api.post(`/ai/agents/${a.id}/revoke`); toast.success(`${a.name} can't connect any more`); refetch(); } catch (ex) { toast.error(errMsg(ex)); }
  }

  return (
    <div className="pb-10">
      <PageHead icon="bot" title="AI agents & MCP"
        sub="Let Claude, or any app that speaks MCP, work in the ERP. Each agent works as one staff login, with that person's permissions, and everything it does is in the activity log."
        actions={writable && <Button size="sm" onClick={() => setDialog({})}><Plus className="h-4 w-4" />New agent</Button>} />
      <Tabs value={tab} onValueChange={setTab} tabs={[{ value: "agents", label: "Agents", count: agents?.filter((a) => a.status === "active").length }, { value: "activity", label: "Activity" }, { value: "connect", label: "How to connect" }]}>
        <TabPanel value="agents">
          {isLoading ? <div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-64" /><Skeleton className="h-64" /></div> : !sorted.length ? (
            <div className="rounded-xl border border-edge bg-surface">
              <Empty icon={Bot} title="No AI agents yet" text="Make one for each job, such as a sales assistant that logs follow-ups or a read-only analyst for the CEO view and reports."
                action={writable ? <Button size="sm" onClick={() => setDialog({})}><Plus className="h-4 w-4" />New agent</Button> : null} />
            </div>
          ) : (
            <div className="grid items-stretch gap-4 lg:grid-cols-2">
              {sorted.map((a) => <AgentCard key={a.id} a={a} writable={writable} onEdit={() => setDialog(a)} onLog={() => { setLogAgent(a.id); setTab("activity"); }}
                onToggle={() => patch(a, { active: !a.active }, a.active ? `${a.name} is paused` : `${a.name} is switched on`)} onRotate={() => setRotate(a)} onRevoke={() => setRevoke(a)} />)}
            </div>
          )}
          <Alert tone="gray" className="mt-4" icon={ShieldCheck} title="What agents can never do">
            Whatever the login's role allows, an agent can't {NEVER.slice(0, -1).join(", ")} or {NEVER[NEVER.length - 1]}. Records it adds or changes go through the same checks, numbering and approvals as in the app.
          </Alert>
        </TabPanel>
        <TabPanel value="activity"><Activity agents={agents} agentId={logAgent} setAgentId={setLogAgent} tools={info?.tools} /></TabPanel>
        <TabPanel value="connect">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <Panel title="Connect an agent" sub="Use the key you copied when you made the agent. Lost it? Make a new key on the agent's card.">
              <ConnectSteps url={url} />
            </Panel>
            <div className="space-y-4">
              <Panel title="What the AI can use" bodyClass="p-0">
                <ul className="divide-y divide-edge">
                  {(info?.tools || []).map((t) => (
                    <li key={t.name} className="px-4 py-2.5"><p className="flex items-center gap-2 text-sm font-medium">{t.title}{t.write && <Badge tone="amber">Read & write agents</Badge>}</p><p className="text-xs text-muted">{t.description}</p></li>
                  ))}
                </ul>
              </Panel>
              {info?.prompts?.length > 0 && (
                <Panel title="Ready-made requests" sub="Shown in Claude's prompt list once connected" bodyClass="p-0">
                  <ul className="divide-y divide-edge">{info.prompts.map((p) => <li key={p.name} className="px-4 py-2.5"><p className="text-sm font-medium">{p.title}</p><p className="text-xs text-muted">{p.description}</p></li>)}</ul>
                </Panel>
              )}
            </div>
          </div>
        </TabPanel>
      </Tabs>

      {dialog && <AgentDialog open onOpenChange={(x) => !x && setDialog(null)} agent={dialog} templates={info?.templates || []} staff={staff || []}
        onSaved={(d, editing) => { setDialog(null); refetch(); if (editing) toast.success("Agent saved"); else setIssued(d); }} />}
      <Dialog open={!!issued} onOpenChange={(x) => !x && setIssued(null)} wide title={`Key for ${issued?.agent?.name || "the agent"}`}
        description="Copy it now: it's shown only this once. If it's lost, make a new key."
        footer={<Button onClick={() => setIssued(null)}>I've copied it</Button>}>
        {issued && (
          <div className="space-y-5">
            <CopyField label="Key" value={issued.key} />
            <Alert tone="amber" title="Treat it like a password">Anyone with this key can do what {issued.agent?.user_name} can, within the agent's access. Revoke the agent if the key is shared by mistake.</Alert>
            <ConnectSteps url={issued.mcp_url} keyText={issued.key} />
          </div>
        )}
      </Dialog>
      <Confirm open={!!rotate} onOpenChange={(x) => !x && setRotate(null)} title={`New key for ${rotate?.name || ""}`} text="The current key stops working straight away. Put the new one into Claude's connector settings."
        confirmLabel="Make a new key" onConfirm={() => doRotate(rotate)} />
      <Confirm open={!!revoke} onOpenChange={(x) => !x && setRevoke(null)} title={`Revoke ${revoke?.name || ""}`} tone="danger"
        text="It stops working at once and can't be switched back on. Its activity stays in the log." confirmLabel="Revoke" onConfirm={() => doRevoke(revoke)} />
    </div>
  );
}
