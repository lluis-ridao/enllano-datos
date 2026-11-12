#!/usr/bin/env bash
# Sube los datos nuevos sin pisar los de la otra acción. El catálogo y el manifiesto se regeneran al final.
set -euo pipefail
MSG="${1:-Datos actualizados}"
git config user.name "enllano-datos[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for intento in 1 2 3; do
  git checkout -- datos/catalogo.json mapas/manifest.json 2>/dev/null || true
  git stash push -u -q -- datos mapas || true
  git pull -q --rebase origin main
  git stash pop -q 2>/dev/null || true
  python scripts/catalogo.py
  git add -A datos mapas
  if git diff --cached --quiet; then echo "Sin cambios"; exit 0; fi
  git commit -q -m "$MSG $(date -u +%F)"
  if git push -q origin HEAD:main; then echo "Subido"; exit 0; fi
  echo "Otro proceso subió antes; reintento $intento"
  git reset -q --soft HEAD~1
  sleep $((intento * 5))
done
exit 1
