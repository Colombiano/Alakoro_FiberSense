# Politica de Seguranca

## Reportando Vulnerabilidades

Se voce descobrir uma vulnerabilidade de seguranca no Alakoro FiberSense, por favor reporte de forma responsavel.

### Como Reportar

1. **Nao abra uma issue publica** para vulnerabilidades de seguranca
2. Envie um e-mail para: luizpaulo.colombiano@gmail.com
3. Inclua:
   - Descricao detalhada da vulnerabilidade
   - Passos para reproducao
   - Impacto potencial
   - Sugestoes de mitigacao (se houver)

### Processo de Resposta

1. **Confirmacao**: Ate 48 horas apos o recebimento
2. **Investigacao**: Ate 7 dias para avaliacao inicial
3. **Correcao**: Ate 30 dias para lancamento de patch
4. **Divulgacao**: Apos a correcao, divulgacao coordenada

## Boas Praticas

### Credenciais

- Nunca commite credenciais no repositorio
- Use variaveis de ambiente para senhas e tokens
- O arquivo `.env` esta no `.gitignore`

### Redis

- Em producao, configure senha forte para Redis
- Limite acesso ao Redis apenas entre containers/pods
- Habilite TLS para conexoes Redis

### API

- A API utiliza validacao de dados via Pydantic
- Limite de upload configuravel (max 500MB)
- Rate limiting recomendado para producao

### C++ Engine

- O engine C++ opera em sandbox dentro do container
- Memoria limitada via cgroups no Kubernetes
- Sem acesso direto ao sistema de arquivos host

## Dependencias

### Atualizacao

- Dependencias sao verificadas mensalmente
- CVEs sao monitorados automaticamente via GitHub Security Advisories

### Versoes Minimas Recomendadas

- Python: 3.11+
- Node.js: 20+
- Redis: 7+
- Kubernetes: 1.28+

## Contato

- Responsavel: Luiz Paulo Colombiano
- GitHub: [@Colombiano](https://github.com/Colombiano)
