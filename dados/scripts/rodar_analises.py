"""
rodar_analises.py
=================
Orchestration script that executes analysis scripts for thresholds
of 0.95 and 0.75, saving outputs in saida/95/ and saida/75/ respectively.

Scripts that do NOT depend on threshold filters (gerar_graficos_tipologia.py)
are run once with output in the root saida/ folder.

Usage:
    python rodar_analises.py
"""

import subprocess
import sys
from pathlib import Path

DIR_SCRIPTS = Path(__file__).resolve().parent
DIR_BASE = DIR_SCRIPTS.parent
DIR_SAIDA = DIR_BASE / "saida"

PYTHON = sys.executable

# Thresholds to process
LIMIARES = [0.95, 0.75]

# Scripts that DEPEND on threshold (run once for each threshold)
SCRIPTS_COM_LIMIAR = [
    "filtro_dados_matriz.py",
    "analise_matriz_similaridade.py",
    "contar_pontos_sobraram.py",
    "histogramas_tipologia_prod_escalar.py",
]

# Scripts that do NOT depend on threshold (run once, save in root)
SCRIPTS_SEM_LIMIAR = [
    "gerar_graficos_tipologia.py",
]


def rodar(script: str, args: list[str] = None):
    """Runs a Python script as a subprocess."""
    script_path = DIR_SCRIPTS / script
    if not script_path.exists():
        print(f"  [Skip] Script {script} not found, skipping...")
        return True

    cmd = [PYTHON, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'=' * 70}")
    print(f"  EXECUTING: {script} {' '.join(args or [])}")
    print(f"{'=' * 70}\n")

    result = subprocess.run(cmd, cwd=str(DIR_BASE))
    if result.returncode != 0:
        print(f"\n  [ERROR] {script} returned code {result.returncode}")
        return False
    return True


def main():
    print("=" * 70)
    print("  ANALYSIS ORCHESTRATOR")
    print(f"  Thresholds: {LIMIARES}")
    print(f"  Output folder: {DIR_SAIDA}")
    print("=" * 70)

    for limiar in LIMIARES:
        pasta = DIR_SAIDA / str(int(limiar * 100))
        pasta.mkdir(parents=True, exist_ok=True)
        print(f"  [ok] Output folder ready: {pasta}")

    erros = []

    # 1. Scripts WITH threshold
    for limiar in LIMIARES:
        limiar_str = str(limiar)
        limiar_int = int(limiar * 100)
        print(f"\n\n{'#' * 70}")
        print(f"  PROCESSING THRESHOLD >= {limiar} (folder: saida/{limiar_int}/)")
        print(f"{'#' * 70}")

        for script in SCRIPTS_COM_LIMIAR:
            ok = rodar(script, ["--limiar", limiar_str])
            if not ok:
                erros.append(f"{script} --limiar {limiar_str}")

    # 2. Scripts WITHOUT threshold
    print(f"\n\n{'#' * 70}")
    print(f"  PROCESSING SCRIPTS WITHOUT THRESHOLD (folder: saida/)")
    print(f"{'#' * 70}")

    for script in SCRIPTS_SEM_LIMIAR:
        ok = rodar(script)
        if not ok:
            erros.append(script)

    print("\n\n" + "=" * 70)
    if erros:
        print(f"  COMPLETED WITH {len(erros)} ERROR(S):")
        for e in erros:
            print(f"    - {e}")
    else:
        print("  ALL ANALYSES COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
