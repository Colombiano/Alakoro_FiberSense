#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alakoro FiberSense — Instalador Universal v1.0
Universal Installer

Modo Leigo / Easy Mode: clique duplo → instala tudo automaticamente
Double-click → installs everything automatically

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

import os
import sys
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading


class AlakoroInstaller:
    """Instalador gráfico do Alakoro FiberSense / Graphical installer"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎸 Alakoro FiberSense — Instalador / Installer")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        # Estilo / Style
        self.style = ttk.Style()
        self.style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        self.style.configure('Subtitle.TLabel', font=('Helvetica', 10))
        self.style.configure('Status.TLabel', font=('Helvetica', 11))

        self._build_ui()

    def _build_ui(self):
        """Construir interface gráfica / Build GUI"""
        # Título / Title
        title = ttk.Label(self.root, text="🎸 Alakoro FiberSense v2.2.1",
                         style='Title.TLabel')
        title.pack(pady=(20, 5))

        subtitle = ttk.Label(self.root,
            text="Plataforma DFOS para Poços de Petróleo / DFOS Platform for Oil & Gas Wells",
            style='Subtitle.TLabel')
        subtitle.pack(pady=(0, 20))

        # Frame de status / Status frame
        self.status_frame = ttk.LabelFrame(self.root, text="Status da Instalação / Installation Status",
                                          padding=10)
        self.status_frame.pack(fill=tk.X, padx=20, pady=10)

        self.status_var = tk.StringVar(value="⏳ Pronto para instalar / Ready to install")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var,
                                     style='Status.TLabel')
        self.status_label.pack(anchor=tk.W)

        self.progress = ttk.Progressbar(self.status_frame, mode='determinate', length=600)
        self.progress.pack(fill=tk.X, pady=(10, 0))

        # Log / Log
        self.log_frame = ttk.LabelFrame(self.root, text="Log / Log", padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=12, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Botões / Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.install_btn = ttk.Button(btn_frame, text="📦 Instalar / Install",
                                     command=self._start_install)
        self.install_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.test_btn = ttk.Button(btn_frame, text="🧪 Testar / Test",
                                  command=self._run_tests, state=tk.DISABLED)
        self.test_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="❌ Sair / Exit",
                  command=self.root.destroy).pack(side=tk.RIGHT)

    def _log(self, message):
        """Adicionar mensagem ao log / Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _set_status(self, message, progress_value=None):
        """Atualizar status / Update status"""
        self.status_var.set(message)
        if progress_value is not None:
            self.progress['value'] = progress_value
        self.root.update_idletasks()

    def _run_command(self, cmd, description):
        """Executar comando e logar / Run command and log"""
        self._log(f"$ {description}")
        self._log(f"  → {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            if result.stdout:
                for line in result.stdout.strip().split('\n')[:5]:
                    self._log(f"  {line}")
            return True
        except subprocess.CalledProcessError as e:
            self._log(f"  ❌ Erro: {e}")
            if e.stderr:
                self._log(f"  {e.stderr[:200]}")
            return False

    def _start_install(self):
        """Iniciar instalação em thread / Start installation in thread"""
        self.install_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._install)
        thread.daemon = True
        thread.start()

    def _install(self):
        """Processo de instalação / Installation process"""
        try:
            self._set_status("🔍 Verificando Python... / Checking Python...", 10)
            self._log("=" * 60)
            self._log("🎸 Iniciando instalação do Alakoro FiberSense")
            self._log("   Starting Alakoro FiberSense installation")
            self._log("=" * 60)

            # Verificar Python
            py_cmd = "python3" if platform.system() != "Windows" else "python"
            if not self._run_command(f"{py_cmd} --version", "Verificando Python / Checking Python"):
                raise Exception("Python não encontrado / Python not found")

            self._set_status("📦 Criando ambiente virtual... / Creating virtual environment...", 25)
            if not self._run_command(f"{py_cmd} -m venv alakoro_env",
                                     "Criando venv / Creating venv"):
                raise Exception("Falha ao criar venv / Failed to create venv")

            self._set_status("⚡ Ativando ambiente... / Activating environment...", 40)
            # Ativação é feita nos comandos subsequentes com path completo

            self._set_status("📥 Instalando dependências... / Installing dependencies...", 60)
            pip_cmd = os.path.join("alakoro_env", "Scripts" if platform.system() == "Windows" else "bin", "pip")
            if not self._run_command(f"{pip_cmd} install --upgrade pip",
                                     "Atualizando pip / Upgrading pip"):
                raise Exception("Falha ao atualizar pip / Failed to upgrade pip")

            if not self._run_command(f"{pip_cmd} install -r requirements.txt",
                                     "Instalando dependências / Installing dependencies"):
                raise Exception("Falha nas dependências / Dependency installation failed")

            self._set_status("✅ Instalação concluída! / Installation complete!", 100)
            self._log("")
            self._log("╔══════════════════════════════════════════════════════╗")
            self._log("║  ✅ INSTALAÇÃO CONCLUÍDA! / INSTALLATION COMPLETE!  ║")
            self._log("╚══════════════════════════════════════════════════════╝")
            self._log("")
            self._log("🎸 Para usar / To use:")
            self._log(f"   {pip_cmd} install -e .  # (opcional / optional)")
            self._log("")
            self._log("📚 Leia README.md para exemplos / Read README.md for examples")

            self.test_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Sucesso / Success",
                              "✅ Alakoro FiberSense instalado com sucesso!\n"
                              "✅ Alakoro FiberSense installed successfully!")

        except Exception as e:
            self._set_status(f"❌ Erro: {str(e)[:50]}", 0)
            self._log(f"\n❌ ERRO FATAL / FATAL ERROR: {e}")
            messagebox.showerror("Erro / Error", str(e))
        finally:
            self.install_btn.config(state=tk.NORMAL)

    def _run_tests(self):
        """Executar testes / Run tests"""
        self._log("")
        self._log("🧪 Executando testes... / Running tests...")
        py_cmd = os.path.join("alakoro_env", "Scripts" if platform.system() == "Windows" else "bin", "python")
        self._run_command(f"{py_cmd} -m pytest tests/ -v --tb=short",
                         "pytest tests/ -v")


def main():
    """Ponto de entrada / Entry point"""
    root = tk.Tk()
    app = AlakoroInstaller(root)
    root.mainloop()


if __name__ == '__main__':
    main()
