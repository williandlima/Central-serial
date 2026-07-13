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
