/** Esquema referencial, no diagrama físico IEEE13 georreferenciado. */
export function feederDiagram() {
  return `<section class="card"><h3>Alimentador IEEE13 · vista conceptual</h3>
   <svg viewBox="0 0 460 145" class="feeder-svg" role="img" aria-label="Esquema abstracto de alimentador">
   <path d="M35 38H430 M155 38V99H345 M265 38V99" stroke="#6085a9" fill="none" stroke-width="3" />
   <g fill="#53add9" stroke="#153651" stroke-width="3"><circle cx="35" cy="38" r="8"/><circle cx="155" cy="38" r="8"/>
   <circle cx="265" cy="38" r="8"/><circle cx="430" cy="38" r="8"/><circle cx="155" cy="99" r="8"/>
   <circle cx="265" cy="99" r="8"/><circle cx="345" cy="99" r="8"/></g>
   <text x="12" y="20">Origen</text><text x="375" y="20">PV modelado</text><text x="93" y="129">BESS modelada</text>
   <path d="M155 106v12" stroke="#4bd49d" stroke-width="2"/></svg>
   <p class="muted small">Esquema ilustrativo. CIM cargado desde el XML del usuario: 11 líneas, 52 terminales, 16 nodos de conectividad.</p>
  </section>`;
}
