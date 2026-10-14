import os
import sys
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient

root = Path.cwd()
out = root / 'diagnostico'
out.mkdir(exist_ok=True)
os.environ['MPLCONFIGDIR'] = '/tmp/sonar-validation/matplotlib'
os.environ['IPYTHONDIR'] = '/tmp/sonar-validation/ipython'
os.environ['JUPYTER_RUNTIME_DIR'] = '/tmp/sonar-validation/runtime'
# Select the interpreter containing the installed notebook libraries.
from jupyter_client import KernelManager
km = KernelManager(kernel_name='python3')
km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
nb = nbformat.read(root / 'SONAR_Colab.ipynb', as_version=4)
mode = sys.argv[1]
if mode == 'local':
    nb.cells[5].source = 'print("Validación local: se usa archive/dataset.csv; no se monta Google Drive.")'
    nb.cells[7].source = nb.cells[7].source.replace('"/content/drive/MyDrive/SONAR/dataset.csv"', repr(str(root / 'archive/dataset.csv')))
    nb.cells.append(nbformat.v4.new_code_cell('''
# Ejercitar los callbacks reales de la interfaz y propagar errores capturados.
assert estado_ui["resultado"] is not None, mensaje.value
assert selector_comparacion.value == 0
assert len(estado_ui["resultado"]["recommendations"]) == 6
selector_comparacion.value = 1
sliders["energy"].value = 3
assert estado_ui["resultado"] is None
recomendar_ui()
assert estado_ui["resultado"]["weights"]["energy"] == 3, mensaje.value
for slider in sliders.values():
    slider.value = 0
recomendar_ui()
assert estado_ui["resultado"] is None
assert "activa al menos" in mensaje.value, mensaje.value
assert not boton_recomendar.disabled
restablecer_pesos()
busqueda.value = "zzzz_no_existe_zzzz"
buscar_canciones()
assert selector.disabled
recomendar_ui()
assert "selecciona" in mensaje.value, mensaje.value
busqueda.value = "Blinding Lights"
buscar_canciones()
assert not selector.disabled
assert selector.value is not None
cantidad.value = 20
recomendar_ui()
assert len(estado_ui["resultado"]["recommendations"]) == 20, mensaje.value
print("Callbacks verificados: búsqueda, comparación, pesos, cero pesos, sin coincidencias y 20 resultados.")
'''))
client = NotebookClient(nb, km=km, timeout=180, allow_errors=True, resources={'metadata': {'path': str(root)}})
client.execute()
nbformat.write(nb, out / f'SONAR_{mode}_ejecutado.ipynb')
errors = []
for i,c in enumerate(nb.cells):
    if c.cell_type != 'code': continue
    cell_errors = [o for o in c.outputs if o.output_type == 'error']
    for e in cell_errors:
        errors.append({'cell_index':i, 'title':c.source.splitlines()[0], 'type':e.ename, 'message':e.evalue})
    print(f'CELL {i}: {"ERROR" if cell_errors else "OK"}', flush=True)
    for e in cell_errors: print(e.ename, e.evalue, flush=True)
(out / f'errores_{mode}.json').write_text(json.dumps(errors, ensure_ascii=False, indent=2))
print('TOTAL ERRORS',len(errors),flush=True)
