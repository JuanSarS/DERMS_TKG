/** Controles de origen y tiempo sin datos secretos del backend. */
export function scenarioForm() {
  return `<div class="form-grid">
    <label>Modelo eléctrico<select id="topology"><option value="ieee13">IEEE13</option></select></label>
    <label>Perfil<select id="profile"><option value="ausgrid_c12_2011-07-01.csv">Ausgrid C12 · 2011-07-01</option></select></label>
    <label>Multiplicador QSTS<input id="scale" type="number" min="0.1" max="1.3" step="0.05" value="1" /></label>
    <label>Periodo<div class="readonly">48 × 30 minutos</div></label>
  </div><p class="muted small">El QSTS remoto sólo modifica carga global. FV/BESS del optimizador no se aplican a la API original.</p>`;
}
