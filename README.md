# J.A.R.V.I.S.
**Just A Rather Very Intelligent System**

Assistente de voz local inspirado no JARVIS do Homem de Ferro. Detecta a palavra-chave "JARVIS", transcreve comandos de voz, raciocina com a API Claude e responde com voz britânica sintética — tudo sem depender de serviços de nuvem para áudio.

---

## Funcionalidades

- **Detecção de hotword** — "JARVIS" detectado por Picovoice Porcupine (ou fallback por energia + Whisper)
- **Speech-to-Text** — Transcrição local via `faster-whisper` (modelo `base`, PT/EN)
- **Inteligência** — Respostas geradas pela API Claude (`claude-opus-4-5`) com personalidade do JARVIS e histórico de 10 turnos
- **Text-to-Speech** — Voz masculina britânica `en-GB-RyanNeural` via `edge-tts`
- **Skills integradas**
  | Comando de exemplo | Ação |
  |--------------------|------|
  | "Abrir Spotify" | `open_app` |
  | "Fechar Chrome" | `close_app` |
  | "Volume 60" | `set_volume` |
  | "Clima em São Paulo" | `get_weather` (wttr.in) |
  | "Buscar Python tutorial" | `search_web` (DuckDuckGo) |
  | "Bateria" | `get_battery_status` |

---

## Requisitos

| Componente | Versão mínima |
|------------|---------------|
| Windows | 10 / 11 (64-bit) |
| Python | **3.10+** |
| Microfone | Qualquer dispositivo de entrada padrão |

> **Dependências de sistema no Windows:** o `faster-whisper` usa modelos GGML — não é necessário CUDA, mas uma GPU NVIDIA acelera a transcrição. O `pyaudio` requer o runtime PortAudio incluído no pacote PyPI para Windows.

---

## Instalação rápida (recomendado)

Execute o script de instalação automática como **Administrador**:

```bat
install.bat
```

O script cria um virtualenv, instala todas as dependências e adiciona um atalho `JARVIS` à Área de Trabalho.

---

## Instalação manual

```bash
# 1. Criar e ativar virtualenv
python -m venv .venv
.venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env
```

---

## Configuração do `.env`

Abra `.env` e preencha as chaves:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...   # Obrigatório — console.anthropic.com
PICOVOICE_KEY=                 # Opcional — console.picovoice.ai (plano gratuito disponível)
```

> Se `PICOVOICE_KEY` estiver vazio, o JARVIS usa um fallback de detecção por energia de áudio + transcrição Whisper. Funciona, mas consome mais CPU.

---

## Como rodar

```bash
# Com o virtualenv ativo:
python -m jarvis.main

# Ou via atalho criado pelo install.bat
```

### Sequência de inicialização

1. Calibração do microfone (~2 s de silêncio)
2. Mensagem de boas-vindas em voz
3. Loop de escuta — diga **"JARVIS"** para ativar
4. Beep de confirmação → fale seu comando
5. `Ctrl+C` para encerrar

---

## Estrutura do projeto

```
J.A.R.V.S/
├── .env.example          # Template de variáveis de ambiente
├── config.py             # Carrega ANTHROPIC_API_KEY e PICOVOICE_KEY
├── requirements.txt      # Dependências Python
├── install.bat           # Instalador Windows
└── jarvis/
    ├── main.py           # Orquestrador principal (asyncio)
    ├── brain.py          # JarvisBrain — API Claude + histórico
    ├── tts.py            # Text-to-Speech (edge-tts + sounddevice)
    ├── stt.py            # Speech-to-Text (faster-whisper + sounddevice)
    ├── hotword.py        # HotwordDetector (Porcupine / fallback Whisper)
    └── skills/
        ├── system.py     # Bateria, volume, apps (psutil + ctypes)
        └── web.py        # Clima (wttr.in) e busca (DuckDuckGo)
```

---

## Fluxo de uma interação

```
Microfone ──► HotwordDetector ──► beep 440 Hz
                                       │
                                  stt.listen()
                                       │
                               detecção de skill?
                              ┌────────┴────────┐
                             Sim               Não
                              │                 │
                         skill()          brain.think()
                              └────────┬────────┘
                                  brain.think()
                                       │
                                  tts.speak()
                                       │
                                  Alto-falante
```

---

## Logs

Todas as interações são gravadas em `jarvis.log` (UTF-8) no diretório raiz do projeto:

```
2025-01-15 14:32:01 [INFO] jarvis.main: User  : abrir spotify
2025-01-15 14:32:01 [INFO] jarvis.main: Skill : open_app('spotify')
2025-01-15 14:32:02 [INFO] jarvis.main: Result: Opening Spotify, Sir.
2025-01-15 14:32:04 [INFO] jarvis.main: JARVIS: Initiating Spotify, Sir. Shall I queue your usual playlist?
```
