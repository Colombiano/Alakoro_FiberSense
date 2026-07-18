@echo off
chcp 65001 >nul
:: ═══════════════════════════════════════════════════════════════════
:: Alakoro FiberSense — Instalador Automático Windows
:: Automatic Windows Installer
:: ═══════════════════════════════════════════════════════════════════

title 🎸 Alakoro FiberSense — Instalador

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║   🎸  ALAKORO FIBERSENSE v2.2.1                             ║
echo  ║      Plataforma DFOS para Poços de Petróleo                  ║
echo  ║      DFOS Platform for Oil ^& Gas Wells                     ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python não encontrado! / Python not found!
    echo.
    echo  🌐 Baixe Python em: https://python.org/downloads
    echo     Download Python at: https://python.org/downloads
    echo.
    echo  ⚠️  IMPORTANTE / IMPORTANT:
    echo     Durante a instalação, marque "Add Python to PATH"
    echo     During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo  ✅ Python detectado: / Python detected:
python --version
echo.

:: Criar ambiente virtual
echo  📦 Criando ambiente virtual... / Creating virtual environment...
python -m venv alakoro_env
if errorlevel 1 (
    echo  ❌ Falha ao criar ambiente virtual / Failed to create venv
    pause
    exit /b 1
)

:: Ativar ambiente
echo  ⚡ Ativando ambiente... / Activating environment...
call alakoro_env\Scripts\activate.bat

:: Atualizar pip
echo  ⬆️  Atualizando pip... / Upgrading pip...
python -m pip install --upgrade pip

:: Instalar dependências
echo  📥 Instalando dependências... / Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo  ❌ Falha na instalação de dependências / Dependency installation failed
    pause
    exit /b 1
)

:: Criar atalho desktop
echo  🖥️  Criando atalho... / Creating shortcut...
(
echo @echo off
echo call "%%~dp0alakoro_env\Scripts\activate.bat"
echo python -c "from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig; from src.validation import SignatureValidator; from src.processing import LFDASProcessor; print('🎸 Alakoro FiberSense v2.2.1 pronto! / ready!')"
echo python
) > Alakoro_FiberSense.bat

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  ✅ INSTALAÇÃO CONCLUÍDA! / INSTALLATION COMPLETE!          ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo  🎸 Para usar o Alakoro FiberSense:
echo     To use Alakoro FiberSense:
echo.
echo     1. Clique duplo em: Alakoro_FiberSense.bat
echo        Double-click: Alakoro_FiberSense.bat
echo.
echo     2. Ou execute no terminal / Or run in terminal:
echo        call alakoro_env\Scripts\activate.bat
echo        python -c "from src.simulation import SignatureGenerator; ..."
echo.
echo  📚 Documentação: README.md
echo  🧪 Testes: pytest tests/ -v
echo.
pause
