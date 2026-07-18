Contribuindo / Contributing
=========================

Obrigado pelo interesse em contribuir! / Thank you for your interest!

Como Contribuir / How to Contribute
------------------------------------

1. **Fork e Clone**

   .. code-block:: bash

      git clone https://github.com/SEU_USUARIO/Alakoro_FiberSense.git
      cd Alakoro_FiberSense

2. **Crie um Branch**

   .. code-block:: bash

      git checkout -b feature/minha-feature

3. **Instale em Modo Desenvolvimento**

   .. code-block:: bash

      pip install -r requirements.txt
      pip install -e ".[dev]"

4. **Execute os Testes**

   .. code-block:: bash

      pytest tests/ -v

5. **Commit e Push**

   .. code-block:: bash

      git add .
      git commit -m "feat: descrição clara da mudança"
      git push origin feature/minha-feature

6. **Abra um Pull Request**

Padrões de Código / Code Standards
-----------------------------------

* **PEP 8** — Estilo Python
* **Docstrings bilíngues** — PT + EN
* **Type hints** — Em todas as funções
* **Testes** — Todo novo recurso precisa de testes

Tipos de Commit / Commit Types
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Tipo / Type
     - Uso / Use
   * - ``feat:``
     - Novo recurso / New feature
   * - ``fix:``
     - Correção de bug / Bug fix
   * - ``docs:``
     - Documentação / Documentation
   * - ``test:``
     - Testes / Tests
   * - ``refactor:``
     - Refatoração / Refactoring
   * - ``perf:``
     - Performance / Performance
   * - ``chore:``
     - Manutenção / Maintenance

Checklist do PR / PR Checklist
-------------------------------

- [ ] Testes passam / Tests pass
- [ ] Documentação atualizada / Documentation updated
- [ ] CHANGELOG.md atualizado / CHANGELOG.md updated
- [ ] Código segue PEP 8 / Code follows PEP 8
- [ ] Docstrings bilíngues / Bilingual docstrings
