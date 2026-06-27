"""Main application window: wires the connection panel, protocol readers and the
real-time monitor view together."""
from __future__ import annotations

import csv
import logging
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from communication.can_reader import CanReader, CanSettings
from communication.modbus_reader import ModbusReader
from communication.rs232_reader import Rs232Reader
from communication.rs485_reader import Rs485Reader
from communication.scpi_reader import ScpiReader
from communication.serial_manager import SerialSettings
from communication.uart_reader import UartReader
from database.settings import SettingsStore
from gui.protocol_config import CAN_PROTOCOLS
from gui.serial_panel import ConnectionPanel
from protocols.can_parser import CanFrame
from protocols.parser import Packet

logger = logging.getLogger(__name__)

DISPLAY_FORMATS = ("ASCII", "HEX", "DEC", "BIN")

READER_BY_PROTOCOL = {
    "UART": UartReader,
    "RS232": Rs232Reader,
    "RS485": Rs485Reader,
    "Modbus RTU": ModbusReader,
    "SCPI": ScpiReader,
    "ASCII Custom": UartReader,
    "Binary Custom": UartReader,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Central Serial")
        self.resize(1100, 720)

        self.settings_store = SettingsStore()
        self._reader = None
        self._records: list[object] = []
        self._rx_bytes = 0
        self._error_count = 0
        self._connected_since: float | None = None

        self._build_ui()
        self._build_menu()

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

    # ---------------------------------------------------------------- UI ---
    def _build_ui(self):
        central = QWidget()
        layout = QHBoxLayout(central)

        splitter = QSplitter()
        self.panel = ConnectionPanel()
        splitter.addWidget(self.panel)

        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout(monitor_widget)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(DISPLAY_FORMATS)
        self.format_combo.currentTextChanged.connect(self._refresh_table)
        format_row.addWidget(self.format_combo)
        format_row.addStretch(1)
        monitor_layout.addLayout(format_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Tamanho/DLC", "Protocolo", "Dados"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        monitor_layout.addWidget(self.table)

        splitter.addWidget(monitor_widget)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.panel.connectRequested.connect(self.on_connect)
        self.panel.disconnectRequested.connect(self.on_disconnect)
        self.panel.pauseRequested.connect(self.on_pause)
        self.panel.resumeRequested.connect(self.on_resume)
        self.panel.clearRequested.connect(self.on_clear)
        self.panel.exportRequested.connect(self.on_export)

    def _build_menu(self):
        menu = self.menuBar().addMenu("Perfis")
        save_action = menu.addAction("Salvar perfil...")
        load_action = menu.addAction("Carregar perfil...")
        save_action.triggered.connect(self.on_save_profile)
        load_action.triggered.connect(self.on_load_profile)

    # ----------------------------------------------------------- actions ---
    def on_connect(self):
        protocol = self.panel.current_protocol()
        config = self.panel.current_config()
        auto_reconnect = self.panel.auto_reconnect_enabled()

        try:
            if protocol in CAN_PROTOCOLS:
                can_settings = CanSettings(
                    interface=config["interface"],
                    channel=config["channel"],
                    bitrate=config["bitrate"],
                    is_extended=config["is_extended"],
                )
                self._reader = CanReader(can_settings, auto_reconnect=auto_reconnect)
                self._reader.frameReceived.connect(self._on_can_frame)
            else:
                port = self.panel.current_port()
                if not port:
                    QMessageBox.warning(self, "Central Serial", "Selecione uma porta de comunicação.")
                    return
                serial_settings = SerialSettings(
                    port=port,
                    baudrate=config["baudrate"],
                    bytesize=config["bytesize"],
                    parity=config["parity"],
                    stopbits=config["stopbits"],
                    xonxoff=config["xonxoff"],
                    rtscts=config["rtscts"],
                )
                reader_cls = READER_BY_PROTOCOL.get(protocol, UartReader)
                self._reader = reader_cls(serial_settings, auto_reconnect=auto_reconnect)
                self._reader.packetReceived.connect(self._on_packet)
        except Exception as exc:
            logger.exception("Failed to create reader")
            QMessageBox.critical(self, "Central Serial", f"Erro ao configurar conexão:\n{exc}")
            self._reader = None
            return

        self._reader.connected.connect(self._on_connected)
        self._reader.disconnected.connect(self._on_disconnected)
        self._reader.errorOccurred.connect(self._on_error)
        self._reader.reconnecting.connect(self._on_reconnecting)
        self._reader.start()

    def on_disconnect(self):
        if self._reader is not None:
            self._reader.stop()
            self._reader = None
        self._elapsed_timer.stop()
        self._connected_since = None
        self.panel.set_connected_state(False)

    def on_pause(self):
        if self._reader is not None:
            self._reader.pause()
            self.panel.set_paused_state(True)

    def on_resume(self):
        if self._reader is not None:
            self._reader.resume()
            self.panel.set_paused_state(False)

    def on_clear(self):
        self._records.clear()
        self.table.setRowCount(0)
        self._rx_bytes = 0
        self._error_count = 0
        self.panel.set_bytes_count(0)
        self.panel.set_error_count(0)

    def on_export(self):
        if not self._records:
            QMessageBox.information(self, "Central Serial", "Não há dados para exportar.")
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Exportar log", "", "CSV (*.csv);;Texto (*.txt)"
        )
        if not path:
            return
        try:
            if path.endswith(".csv") or "CSV" in selected_filter:
                self._export_csv(path)
            else:
                self._export_txt(path)
        except OSError as exc:
            QMessageBox.critical(self, "Central Serial", f"Erro ao exportar log:\n{exc}")

    def on_save_profile(self):
        name, ok = QInputDialog.getText(self, "Salvar perfil", "Nome do perfil:")
        if not ok or not name:
            return
        protocol = self.panel.current_protocol()
        config = dict(self.panel.current_config())
        if protocol not in CAN_PROTOCOLS:
            config["port"] = self.panel.current_port()
        self.settings_store.save_profile(name, protocol, config)

    def on_load_profile(self):
        profiles = self.settings_store.list_profiles()
        if not profiles:
            QMessageBox.information(self, "Central Serial", "Nenhum perfil salvo.")
            return
        name, ok = QInputDialog.getItem(self, "Carregar perfil", "Perfil:", profiles, editable=False)
        if not ok:
            return
        profile = self.settings_store.load_profile(name)
        if profile:
            self.panel.protocol_combo.setCurrentText(profile["protocol"])

    # ------------------------------------------------------------ signals ---
    def _on_connected(self):
        self.panel.set_connected_state(True)
        self._connected_since = time.time()
        self._elapsed_timer.start()
        logger.info("Connected (%s)", self.panel.current_protocol())

    def _on_disconnected(self):
        self.panel.set_connected_state(False)
        self._elapsed_timer.stop()
        logger.info("Disconnected")

    def _on_error(self, message: str):
        self._error_count += 1
        self.panel.set_error_count(self._error_count)
        logger.error(message)

    def _on_reconnecting(self, seconds_left: int):
        self.panel.set_status_text(f"Reconectando em {seconds_left}s...")

    def _on_packet(self, packet: Packet):
        self._records.append(packet)
        self._rx_bytes += packet.size
        self.panel.set_bytes_count(self._rx_bytes)
        self._append_packet_row(packet)
        logger.info("%s | %s bytes | %s", packet.protocol, packet.size, packet.to_hex())

    def _on_can_frame(self, frame: CanFrame):
        self._records.append(frame)
        self._rx_bytes += len(frame.data)
        self.panel.set_bytes_count(self._rx_bytes)
        self._append_can_row(frame)
        logger.info(frame.format_line())

    def _update_elapsed(self):
        if self._connected_since is None:
            return
        elapsed = int(time.time() - self._connected_since)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.panel.set_elapsed_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    # ------------------------------------------------------------- table ---
    def _append_packet_row(self, packet: Packet):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(packet.timestamp_str()))
        self.table.setItem(row, 1, QTableWidgetItem(str(packet.size)))
        self.table.setItem(row, 2, QTableWidgetItem(packet.protocol))
        self.table.setItem(row, 3, QTableWidgetItem(packet.formatted(self.format_combo.currentText())))
        self.table.scrollToBottom()

    def _append_can_row(self, frame: CanFrame):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(frame.timestamp_str()))
        self.table.setItem(row, 1, QTableWidgetItem(str(frame.dlc)))
        self.table.setItem(row, 2, QTableWidgetItem(f"CAN {frame.id_str}"))
        self.table.setItem(row, 3, QTableWidgetItem(f"{frame.frame_type} | {frame.data_hex}"))
        self.table.scrollToBottom()

    def _refresh_table(self):
        self.table.setRowCount(0)
        for record in self._records:
            if isinstance(record, CanFrame):
                self._append_can_row(record)
            else:
                self._append_packet_row(record)

    def _export_csv(self, path: str):
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Timestamp", "Protocolo", "Tamanho/DLC", "Dados"])
            for record in self._records:
                if isinstance(record, CanFrame):
                    writer.writerow([record.timestamp_str(), f"CAN {record.id_str}", record.dlc, record.data_hex])
                else:
                    writer.writerow(
                        [
                            record.timestamp_str(),
                            record.protocol,
                            record.size,
                            record.formatted(self.format_combo.currentText()),
                        ]
                    )

    def _export_txt(self, path: str):
        with open(path, "w", encoding="utf-8") as handle:
            for record in self._records:
                if isinstance(record, CanFrame):
                    handle.write(record.format_line() + "\n")
                else:
                    handle.write(
                        f"TIME: {record.timestamp_str()}  PROTO: {record.protocol}  "
                        f"SIZE: {record.size}  DATA: {record.formatted(self.format_combo.currentText())}\n"
                    )

    def closeEvent(self, event):
        self.on_disconnect()
        self.settings_store.close()
        super().closeEvent(event)
