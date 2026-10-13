from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["owner-console"])

_OWNER_CONSOLE = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AI Holding — Control Plane</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    body { margin:0; background:#0b0d10; color:#f3f4f6; }
    main { max-width:1500px; margin:auto; padding:24px; }
    header { display:flex; justify-content:space-between; gap:16px; align-items:end; margin-bottom:20px; }
    h1 { margin:0; font-size:28px; }
    .muted { color:#9ca3af; font-size:13px; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:18px; }
    .card,.panel { background:#15191f; border:1px solid #252b34; border-radius:10px; }
    .card { padding:14px; }
    .card strong { display:block; font-size:24px; margin-top:4px; }
    .panel { padding:14px; margin-bottom:18px; overflow:auto; }
    table { width:100%; border-collapse:collapse; min-width:1100px; }
    th,td { text-align:left; padding:10px 8px; border-bottom:1px solid #252b34; vertical-align:top; }
    th { color:#9ca3af; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
    td { font-size:13px; }
    .badge { display:inline-block; border:1px solid #3a424d; border-radius:999px; padding:2px 7px; font-size:11px; }
    .ok { border-color:#287a4b; }
    .warn { border-color:#9a6a18; }
    .bad { border-color:#9b3333; }
    .actions { display:grid; gap:8px; }
    .action { border:1px solid #333b46; border-radius:8px; padding:10px; }
    .error { color:#fca5a5; white-space:pre-wrap; }
    .project-panels { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }
    .project-panel { padding:12px; border:1px solid #333b46; border-radius:8px; }
    .project-panel h3 { margin:0 0 9px; font-size:15px; }
    .project-panel .line { margin:8px 0; }
    .columns { display:grid; grid-template-columns:minmax(0,2fr) minmax(280px,1fr); gap:18px; align-items:start; }
    .event-list { display:grid; gap:9px; max-height:440px; overflow:auto; }
    .event { padding:10px 0; border-bottom:1px solid #252b34; }
    .event .muted { display:block; margin-top:5px; }
    @media (max-width:900px) { .columns { grid-template-columns:1fr; } }

  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>AI Holding — Control Plane</h1>
      <div class="muted">Estado verificado do ecossistema · atualização automática a cada 30 s</div>
    </div>
    <div id="freshness" class="muted">Carregando…</div>
  </header>

  <section id="cards" class="cards"></section>
  <section class="panel" aria-label="Quadros operacionais">
    <h2>Quadros simultâneos por projeto</h2>
    <div id="project-panels" class="project-panels"></div>
  </section>

  <div class="columns">
  <section class="panel">
    <h2>Projetos</h2>
    <table>
      <thead><tr>
        <th>Projeto</th><th>Status</th><th>Verificado</th><th>Saúde</th>
        <th>Release</th><th>WIP</th><th>Bloqueios</th><th>Próxima ação</th>
      </tr></thead>
      <tbody id="projects"></tbody>
    </table>
  </section>

  <section class="panel">
    <h2>Atividade recebida do Hermes</h2>
    <p class="muted">Eventos persistidos, não comprovam disponibilidade nem conclusão do projeto.</p>
    <div id="events" class="event-list" aria-live="polite"></div>
  </section>
  </div>
  <section class="panel">
    <h2>Precisa de você</h2>
    <div id="actions" class="actions"></div>
  </section>
  <div id="error" class="error"></div>
</main>
<script>
const ownerUrl = "/api/v1/holding/control-plane/owner-view";
const actionsUrl = "/api/v1/holding/control-plane/human-actions";
const eventsUrl = "/api/v1/holding/control-plane/event-feed?limit=30";
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
const cls = value => {
  const v = String(value ?? "").toUpperCase();
  if (["READY","RELEASED","HEALTHY","ACTIVE","DONE"].includes(v)) return "ok";
  if (["BLOCKED","FAILED","UNHEALTHY","DISCONTINUED"].includes(v)) return "bad";
  return "warn";
};
function badge(value) { return '<span class="badge '+cls(value)+'">'+esc(value || "—")+'</span>'; }
async function refresh() {
  try {
    const [ownerResponse, actionsResponse, eventsResponse] = await Promise.all([fetch(ownerUrl, {cache:"no-store"}), fetch(actionsUrl, {cache:"no-store"}), fetch(eventsUrl, {cache:"no-store"})]);
    if (!ownerResponse.ok || !actionsResponse.ok || !eventsResponse.ok) throw new Error("Control Plane indisponível ou acesso não autorizado");
    const owner = await ownerResponse.json();
    const actions = await actionsResponse.json();
    const eventFeed = await eventsResponse.json();
    const metrics = [
      ["Ativos", owner.active_projects], ["Pausados", owner.paused_projects],
      ["Bloqueados", owner.blocked_projects], ["Vendáveis", owner.sellable_products],
      ["Releases em risco", owner.releases_at_risk], ["Ações humanas", owner.human_actions],
      ["Serviços não saudáveis", owner.unhealthy_services]
    ];
    document.getElementById("cards").innerHTML = metrics.map(([label,value]) =>
      '<div class="card"><span class="muted">'+esc(label)+'</span><strong>'+esc(value)+'</strong></div>'
    ).join("");
    document.getElementById("project-panels").innerHTML = owner.projects.length ? owner.projects.map(p => {
      const activity = eventFeed.items.find(e => e.project_key === p.key);
      return '<article class="project-panel"><h3>'+esc(p.name)+'</h3>'+
        '<div class="line">Governança: '+badge(p.verified_status)+'</div>'+
        '<div class="line">Saúde registrada: '+badge(p.health_status)+'</div>'+
        '<div class="muted">Release: '+esc(p.current_release || "Não informada")+'</div>'+
        '<div class="muted">Último evento consultado: '+esc(activity ? new Date(activity.received_at).toLocaleString("pt-BR") : "Sem evento recente")+'</div>'+
        '<div class="line muted">Próxima ação: '+esc(p.next_best_action || "Não informada")+'</div></article>';
    }).join("") : '<span class="muted">Nenhum projeto registrado na Holding.</span>';
    document.getElementById("projects").innerHTML = owner.projects.map(p =>
      '<tr><td><strong>'+esc(p.name)+'</strong><br><span class="muted">'+esc(p.key)+'</span></td>'+
      '<td>'+badge(p.project_status)+'</td><td>'+badge(p.verified_status)+'</td><td>'+badge(p.health_status)+'</td>'+
      '<td>'+esc(p.current_release || "—")+'</td><td>'+esc(p.wip)+'</td><td>'+esc(p.open_blockers)+'</td>'+
      '<td>'+esc(p.next_best_action || "—")+'</td></tr>'
    ).join("");
    document.getElementById("actions").innerHTML = actions.length ? actions.map(a =>
      '<div class="action"><strong>'+esc(a.priority)+' · '+esc(a.title)+'</strong><br>'+
      '<span>'+esc(a.action_required)+'</span><br><span class="muted">Responsável: '+esc(a.owner)+'</span></div>'
    ).join("") : '<span class="muted">Nenhuma ação humana pendente.</span>';
    document.getElementById("events").innerHTML = eventFeed.items.length ? eventFeed.items.map(e =>
      '<div class="event"><strong>'+esc(e.project_key)+'</strong> · '+badge(e.event_type)+
      '<span class="muted">Recebido: '+esc(new Date(e.received_at).toLocaleString("pt-BR"))+
      ' · Origem: '+esc(e.producer)+'</span></div>'
    ).join("") : '<span class="muted">Nenhum evento Hermes persistido até o momento.</span>';
    document.getElementById("freshness").textContent = "Dados consultados: "+esc(new Date(eventFeed.generated_at).toLocaleString("pt-BR"));
    document.getElementById("error").textContent = "";
  } catch (error) {
    document.getElementById("error").textContent = String(error);
    document.getElementById("freshness").textContent = "Falha de atualização";
  }
}
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def owner_console() -> HTMLResponse:
    return HTMLResponse(_OWNER_CONSOLE)
