#!/bin/bash
# ============================================================
# Script de Commit para GitHub — Alakoro FiberSense v2.2.1
# ============================================================

# Configurar (substitua pelo seu token se necessário)
# export GITHUB_TOKEN="seu_token_aqui"

echo "🚀 Alakoro FiberSense — Commit para GitHub"
echo "============================================"

# Verificar se está no diretório correto
if [ ! -f "README.md" ]; then
    echo "❌ Erro: README.md não encontrado. Execute do diretório raiz do projeto."
    exit 1
fi

# Configurar git (ajuste se necessário)
git config user.name "Luiz Paulo Colombiano" 2>/dev/null || true
git config user.email "seu_email@exemplo.com" 2>/dev/null || true

echo ""
echo "📋 Arquivos a serem commitados:"
git add -A
git status --short

echo ""
echo "📝 Criando commit..."
git commit -m "Alakoro FiberSense v2.2.1 — Correções e Melhorias

- signature_generator.py v4.1: refatoração, eliminação de duplicação
- lfdas_processor.py v1.1.0: refresh rate ~2s alinhado com README
- signature_validator.py v1.2.1: detecção de múltiplos picos (crossflow)
- fibersense_event_schema_v1.1.0.json: 18 event types (4 novos)
- __init__.py: exports em todos os módulos
- tests/: 40+ testes unitários pytest
- README.md: atualizado para v2.2.1

Taxa de validação: 91.3% (15/15 assinaturas ≥90%)"

echo ""
echo "⬆️  Enviando para GitHub..."
git push origin main

echo ""
echo "✅ Commit concluído!"
