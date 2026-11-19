/** Selección de intervalos, sin confundir hora UTC de Ausgrid con reloj OpenDSS. */
export function timeSlider(rows, callback) {
  const holder = document.createElement("div");
  holder.className = "time-slider";
  const label = document.createElement("label");
  label.textContent = "Intervalo seleccionado";
  const span = document.createElement("span");
  span.className = "mono";
  const input = document.createElement("input");
  input.type = "range";
  input.min = 0;
  input.max = Math.max(0, rows.length - 1);
  input.value = 0;
  function render() {
    const index = Number(input.value);
    span.textContent = rows[index]?.timestamp ?? `Paso ${index + 1}`;
    callback?.(rows[index], index);
  }
  input.addEventListener("input", render);
  holder.append(label, input, span);
  render();
  return holder;
}
