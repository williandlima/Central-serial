"""Connection panel: protocol/port selection, action buttons and status indicators."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from communication.serial_manager import SerialManager
from gui.protocol_config import CAN_PROTOCOLS, SERIAL_PROTOCOLS, ProtocolConfigStack


class ConnectionPanel(QWidget):
    connectRequested = Signal()
    disconnectRequested = Signal()
    pauseRequested = Signal()
    resumeRequested = Signal()
    clearRequested = Signal()
    exportRequested = Signal()
    protocolChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        self.refresh_ports()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        conn_group = QGroupBox("Conexão")
        form = QFormLayout()

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(list(SERIAL_PROTOCOLS) + list(CAN_PROTOCOLS))

        self.port_widget = QWidget()
        port_row = QHBoxLayout(self.port_widget)
        port_row.setContentsMargins(0, 0, 0, 0)
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Atualizar")
        port_row.addWidget(self.port_combo)
        port_row.addWidget(self.refresh_button)

        form.addRow("Protocolo:", self.protocol_combo)
        form.addRow("Porta:", self.port_widget)
        self.port_row_label = form.labelForField(self.port_widget)
        conn_group.setLayout(form)

        self.protocol_config = ProtocolConfigStack()

        self.auto_reconnect_checkbox = QCheckBox("Reconexão automática")
        self.auto_reconnect_checkbox.setChecked(True)

        button_row = QHBoxLayout()
        self.connect_button = QPushButton("Conectar")
        self.disconnect_button = QPushButton("Desconectar")
        self.pause_button = QPushButton("Pausar")
        self.resume_button = QPushButton("Continuar")
        self.clear_button = QPushButton("Limpar tela")
        self.export_button = QPushButton("Exportar log")
        for btn in (
            self.connect_button,
            self.disconnect_button,
            self.pause_button,
            self.resume_button,
            self.clear_button,
            self.export_button,
        ):
            button_row.addWidget(btn)

        self.disconnect_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)

        indicators_group = QGroupBox("Indicadores")
        indicators_layout = QFormLayout()
        self.status_label = QLabel("Desconectado")
        self.bytes_label = QLabel("0")
        self.tx_label = QLabel("0 (preparado para expansão)")
        self.errors_label = QLabel("0")
        self.elapsed_label = QLabel("00:00:00")
        indicators_layout.addRow("Status:", self.status_label)
        indicators_layout.addRow("Bytes recebidos (RX):", self.bytes_label)
        indicators_layout.addRow("Bytes transmitidos (TX):", self.tx_label)
        indicators_layout.addRow("Erros detectados:", self.errors_label)
        indicators_layout.addRow("Tempo conectado:", self.elapsed_label)
        indicators_group.setLayout(indicators_layout)

        layout.addWidget(conn_group)
        layout.addWidget(self.protocol_config)
        layout.addWidget(self.auto_reconnect_checkbox)
        layout.addLayout(button_row)
        layout.addWidget(indicators_group)
        layout.addStretch(1)

    def _connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.protocol_combo.currentTextChanged.connect(self._on_protocol_changed)
        self.connect_button.clicked.connect(self.connectRequested)
        self.disconnect_button.clicked.connect(self.disconnectRequested)
        self.pause_button.clicked.connect(self.pauseRequested)
        self.resume_button.clicked.connect(self.resumeRequested)
        self.clear_button.clicked.connect(self.clearRequested)
        self.export_button.clicked.connect(self.exportRequested)
        self._on_protocol_changed(self.protocol_combo.currentText())

    def _on_protocol_changed(self, protocol: str):
        self.protocol_config.show_for_protocol(protocol)
        is_can = protocol in CAN_PROTOCOLS
        self.port_widget.setVisible(not is_can)
        if self.port_row_label:
            self.port_row_label.setVisible(not is_can)
        self.protocolChanged.emit(protocol)

    def refresh_ports(self):
        self.port_combo.clear()
        if self.current_protocol() in CAN_PROTOCOLS:
            return
        self.port_combo.addItems(SerialManager.list_ports())

    def current_protocol(self) -> str:
        return self.protocol_combo.currentText()

    def current_port(self) -> str:
        return self.port_combo.currentText()

    def current_config(self) -> dict:
        return self.protocol_config.current_config()

    def auto_reconnect_enabled(self) -> bool:
        return self.auto_reconnect_checkbox.isChecked()

    def set_connected_state(self, connected: bool):
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.pause_button.setEnabled(connected)
        self.resume_button.setEnabled(False)
        self.protocol_combo.setEnabled(not connected)
        self.port_combo.setEnabled(not connected)
        self.refresh_button.setEnabled(not connected)
        self.status_label.setText("Conectado" if connected else "Desconectado")

    def set_paused_state(self, paused: bool):
        self.pause_button.setEnabled(not paused)
        self.resume_button.setEnabled(paused)

    def set_status_text(self, text: str):
        self.status_label.setText(text)

    def set_bytes_count(self, count: int):
        self.bytes_label.setText(str(count))

    def set_error_count(self, count: int):
        self.errors_label.setText(str(count))

    def set_elapsed_text(self, text: str):
        self.elapsed_label.setText(text)
