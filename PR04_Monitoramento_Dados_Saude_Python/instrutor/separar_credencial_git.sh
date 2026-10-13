#!/usr/bin/env bash
set -euo pipefail
# Executar a partir da raiz do repositório. Não copia nem imprime a chave.
REPO="$(git rev-parse --show-toplevel)"
SOURCE="$REPO/PR04_Monitoramento_Dados_Saude_Python/instrutor/oficina-python-saude-teste-firebase-adminsdk-chave-privada.json"
DEST="$REPO/../credenciais-ocean/conta-servico-firebase-ANTIGA-DESATIVADA.json"
if [[ -f "$SOURCE" ]]; then
  mkdir -p "$(dirname "$DEST")"
  chmod 700 "$(dirname "$DEST")"
  if [[ -e "$DEST" ]]; then echo "Destino já existe: $DEST; nada movido" >&2; exit 1; fi
  mv -- "$SOURCE" "$DEST"
  chmod 600 "$DEST"
  echo "Credencial movida para fora do repositório (chave antiga/desativada)."
else
  echo "Arquivo original não encontrado; verifique se já foi movido."
fi
# Se ainda houver registro no índice Git, retirá-lo sem mexer no histórico.
if git -C "$REPO" ls-files --error-unmatch "${SOURCE#"$REPO/"}" >/dev/null 2>&1; then
  git -C "$REPO" rm --cached --ignore-unmatch -- "${SOURCE#"$REPO/"}"
fi
printf '\nRevise e faça commit: git add .gitignore PR04_Monitoramento_Dados_Saude_Python/instrutor/CONFIGURACAO_FIREBASE.md && git commit -m "Separar credencial Firebase do repositorio"\n'
printf 'ATENÇÃO: a chave continua em commits históricos; gere nova chave e saneie o histórico separadamente.\n'
