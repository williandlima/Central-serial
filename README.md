# Central Serial

Central universal de monitoramento de comunicação serial e barramentos
industriais, desenvolvida em **Python + PySide6**. Permite conectar e
acompanhar em tempo real a comunicação de diversos protocolos em modo
**somente leitura (RX / Monitor)**:

- UART
- RS232
- RS485
- Modbus RTU (sniffing passivo, validado por CRC16)
- SCPI
- ASCII personalizado
- Comunicação binária personalizada
- CAN Bus (CAN 2.0A / 2.0B)

## Estrutura do projeto

```
Central-serial/
├── main.py                    # ponto de entrada
├── gui/
│   ├── main_window.py         # janela principal, liga painel + leitores + tabela
│   ├── serial_panel.py        # painel de conexão, botões e indicadores
│   └── protocol_config.py     # configurações específicas por protocolo (Serial/CAN)
├── communication/
│   ├── serial_manager.py      # QThread genérica de leitura serial (pyserial)
│   ├── uart_reader.py         # framing por silêncio entre bytes
│   ├── rs232_reader.py
│   ├── rs485_reader.py
│   ├── modbus_reader.py       # sniffer Modbus RTU com validação CRC16
│   ├── scpi_reader.py         # framing por terminador de linha
│   └── can_reader.py          # QThread CAN Bus (python-can)
├── protocols/
│   ├── parser.py              # modelo de pacote (ASCII/HEX/DEC/BIN) e framing
│   ├── can_parser.py          # modelo e formatação de frames CAN
│   └── crc.py                 # CRC16 (Modbus) e CRC8
├── database/
│   └── settings.py            # perfis de equipamento e configurações (SQLite)
├── logs/                      # logs diários (gerados em tempo de execução)
└── tests/
    └── test_protocols.py      # testes unitários da camada de protocolos
```

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Instalação no Windows (passo a passo)

1. **Instale o Python 3.11+** em https://www.python.org/downloads/windows/
   (baixe o instalador oficial, não use a versão da Microsoft Store).
   Na primeira tela do instalador, marque a opção **"Add python.exe to PATH"**
   antes de clicar em Install.

2. **Baixe/clone o projeto** e abra o PowerShell (ou Prompt de Comando) na
   pasta `Central-serial`:
   ```powershell
   git clone <url-do-repositorio>
   cd Central-serial
   ```
   Se preferir sem git, baixe o ZIP do repositório (botão "Code" → "Download
   ZIP") e extraia a pasta.

3. **Crie e ative o ambiente virtual:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
   Se o PowerShell bloquear a ativação com erro de "execution policy", rode
   uma vez (como usuário normal, não precisa ser admin):
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

4. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Execute:**
   ```powershell
   python main.py
   ```

### Observações específicas do Windows

- **Porta serial (UART/RS232/RS485/Modbus/SCPI):** o Windows já reconhece
  conversores USB-serial comuns (FTDI, CP210x, CH340) automaticamente via
  Windows Update. Se a porta não aparecer no botão "Atualizar" do painel,
  verifique no **Gerenciador de Dispositivos** se o driver do chip
  USB-serial está instalado (baixe do fabricante do conversor, ex.:
  FTDI VCP driver, CP210x driver, CH340 driver). A porta aparecerá como
  `COM3`, `COM4`, etc.
- **CAN Bus:** o Windows não tem suporte nativo a `socketcan` (exclusivo
  Linux). Use uma interface suportada pelo `python-can` no Windows, como
  **PCAN (Peak-System)**, **Vector**, **Kvaser** ou **IXXAT**, instalando o
  driver/DLL do fabricante e selecionando a interface correspondente na UI.
  Para testar sem hardware CAN físico, use a interface `virtual`.
- **Antivírus/SmartScreen:** como o projeto roda via `python main.py` (não é
  um `.exe`), não deve haver bloqueio, mas se o Windows Defender alertar na
  primeira execução, escolha "Executar assim mesmo" — o código é aberto e
  pode ser conferido neste repositório.

## Execução

```bash
python main.py
```

## Testes

A camada `protocols/` não depende de Qt/pyserial/python-can e pode ser
testada isoladamente:

```bash
python -m unittest discover -s tests -v
```

## Notas de arquitetura

- Cada protocolo possui sua própria classe leitora (`communication/*_reader.py`),
  rodando a aquisição em uma `QThread` separada da interface — a UI nunca
  trava durante a leitura.
- `UartReader`, `Rs232Reader` e `Rs485Reader` compartilham a mesma estratégia
  de enquadramento por silêncio entre bytes (camada física distinta, mesmo
  comportamento de framing); `Rs232Reader`/`Rs485Reader` são especializações
  de `UartReader` preparadas para divergir no futuro.
- `ModbusReader` opera em modo sniffer passivo (sem polling de master),
  validando cada quadro pelo CRC16. A biblioteca MinimalModbus está prevista
  em `requirements.txt` para a futura expansão com transmissão (TX/master).
- Reconexão automática, detecção de portas, exportação CSV/TXT e perfis de
  equipamento (SQLite) já estão implementados como recursos profissionais.
- CAN Bus usa `python-can`; o tipo de frame (2.0A/2.0B) e a interface
  (socketcan, pcan, vector, virtual, ...) são configuráveis na própria UI.

## Expansões futuras (previstas na arquitetura)

- Transmissão (TX) de comandos
- Scripts automatizados / testes FCT-ATE
- Controle de instrumentos
- Banco de dados de ensaios
- Gráficos em tempo real (matplotlib, já presente em requirements.txt)
