/** Punto de entrada del laboratorio. Navegación SPA pequeña sin framework pesado. */
import "./styles/tokens.css";
import "./styles/app.css";
import { api } from "./api.js";
import { statusBar } from "./components/status_bar.js";
import { closeLive } from "./live.js";
import { dermsPage } from "./pages/derms.js";
import { experimentsPage } from "./pages/experiments.js";
import { graphPage } from "./pages/graph.js";
import { update } from "./state.js";

const app = document.getElementById("app");
app.innerHTML = `<header class="shell-header"><div class="brand"><div class="brand-icon">⬡</div>
   <div><b>DERMS <span>TKG</span> POWER LAB</b><small>Tesis II · Plataforma experimental</small></div></div>
   <nav aria-label="Navegación principal"><button data-page="derms">DERMS y QSTS</button>
     <button data-page="graph">Explorador TKG</button>
     <button data-page="experiments">Experimentos</button></nav><div class="header-note">IEEE13 · RDF/CIM</div></header>
   <div id="statusBar" class="status-shell"></div><div class="page" id="page"></div>
   <footer>OpenDSS remoto mediante REST/WSS · datos reales, simulados y derivados identificados · sin control físico</footer>`;

async function navigate(page) {
  closeLive();
  update({ page, error: "" });
  for (const tab of app.querySelectorAll("nav button"))
    tab.classList.toggle("active", tab.dataset.page === page);
  const root = app.querySelector("#page");
  root.innerHTML = `<p class="muted">Preparando laboratorio...</p>`;
  try {
    if (page === "derms") await dermsPage(root);
    else if (page === "graph") await graphPage(root);
    else await experimentsPage(root);
  } catch (error) {
    root.innerHTML = `<section class="card warning"></section>`;
    root.firstChild.textContent = error.message;
  }
}

app.querySelectorAll("nav button").forEach((tab) => {
  tab.addEventListener("click", () => navigate(tab.dataset.page));
});
async function refreshStatus() {
  try {
    const data = await api.status();
    update({ status: data });
    app.querySelector("#statusBar").innerHTML = statusBar(data);
  } catch (error) {
    app.querySelector("#statusBar").textContent =
      `El servidor local no responde: ${error.message}. No se borran datos confirmados.`;
  }
}
await refreshStatus();
await navigate("derms");
setInterval(refreshStatus, 15000);
