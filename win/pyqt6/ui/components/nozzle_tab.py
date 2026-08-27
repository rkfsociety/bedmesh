import json
import os
import re
import tempfile

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.ssh_client import (
    read_remote_text_via_ssh,
    reboot_printer_via_ssh,
    upload_cfg_with_backup_and_verify,
)
from utils.logger import get_logger


NOZZLE_DIAMETERS = ("0.25", "0.40", "0.60", "0.80", "1.00")
NOZZLE_MATERIALS = (("Brass", "brass"), ("Hardened Steel", "hardened_steel"))


def _format_nozzle_label(material: str, diameter: str) -> str:
    """Returns the same unambiguous label used by the printer UI."""
    return f"{material}-{diameter}"


def _read_nozzle_metadata(text: str) -> tuple[str | None, str | None]:
    try:
        metadata = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None, None
    material = metadata.get("material")
    diameter = metadata.get("diameter")
    return (
        str(material).strip().lower() if material and str(material).strip() != "-" else None,
        str(diameter).strip() if diameter and str(diameter).strip() != "-" else None,
    )


def _read_nozzle_diameter(text: str) -> str | None:
    in_extruder = False
    for line in text.splitlines():
        section = re.match(r"^\s*\[([^]]+)\]\s*$", line)
        if section:
            in_extruder = section.group(1).strip().lower() == "extruder"
            continue
        if in_extruder:
            match = re.match(r"^\s*nozzle_diameter\s*:\s*([^#\s]+)", line, re.IGNORECASE)
            if match:
                try:
                    return f"{float(match.group(1)):.2f}"
                except ValueError:
                    return match.group(1).strip()
    return None


def _read_nozzle_material(text: str) -> str | None:
    in_extruder = False
    for line in text.splitlines():
        section = re.match(r"^\s*\[([^]]+)\]\s*$", line)
        if section:
            in_extruder = section.group(1).strip().lower() == "extruder"
            continue
        if in_extruder:
            match = re.match(r"^\s*nozzle_material\s*:\s*([^#\s]+)", line, re.IGNORECASE)
            if match:
                return match.group(1).strip().lower()
    return None


def _read_mutable_nozzle_values(text: str) -> tuple[str | None, str | None]:
    """Reads the persistent nozzle state from printer_mutable.cfg JSON."""
    try:
        config = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None, None
    extruder = config.get("extruder")
    if not isinstance(extruder, dict):
        return None, None
    diameter = extruder.get("nozzle_diameter")
    material = extruder.get("nozzle_material")
    try:
        normalized_diameter = f"{float(diameter):.2f}" if diameter not in (None, "") else None
    except (TypeError, ValueError):
        normalized_diameter = None
    return (
        normalized_diameter,
        str(material).strip().lower() if material not in (None, "") else None,
    )


def _replace_mutable_nozzle(text: str, diameter: str, material: str) -> str:
    """Updates only the persistent extruder nozzle fields in mutable JSON."""
    try:
        config = json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("printer_mutable.cfg имеет неверный JSON") from error
    extruder = config.get("extruder")
    if not isinstance(extruder, dict):
        raise ValueError("В printer_mutable.cfg отсутствует объект extruder")
    extruder["nozzle_diameter"] = diameter
    extruder["nozzle_material"] = material
    return json.dumps(config, ensure_ascii=False, indent="\t") + "\n"


def _replace_nozzle_diameter(text: str, diameter: str) -> str:
    """Changes only Klipper's numeric diameter; material is stored in mutable JSON."""
    lines = text.splitlines(keepends=True)
    in_extruder = False
    diameter_index = None
    for index, line in enumerate(lines):
        section = re.match(r"^\s*\[([^]]+)\]\s*$", line.rstrip("\r\n"))
        if section:
            in_extruder = section.group(1).strip().lower() == "extruder"
            continue
        if not in_extruder:
            continue
        if re.match(r"^\s*nozzle_diameter\s*:", line, re.IGNORECASE):
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            prefix = line[: len(line) - len(line.lstrip())]
            lines[index] = f"{prefix}nozzle_diameter : {diameter}{newline}"
            diameter_index = index
    if diameter_index is None:
        raise ValueError("В секции [extruder] не найден параметр nozzle_diameter")
    return "".join(lines)


def _verify_remote_nozzle_values(
    printer_cfg: str,
    mutable_cfg: str,
    nozzle_cfg: str,
    diameter: str,
    material: str,
) -> tuple[bool, str]:
    """Checks all persistent sources before allowing a reboot."""
    actual_diameter = _read_nozzle_diameter(printer_cfg)
    mutable_diameter, actual_material = _read_mutable_nozzle_values(mutable_cfg)
    try:
        metadata = json.loads(nozzle_cfg)
    except (TypeError, json.JSONDecodeError):
        return False, "nozzle.cfg имеет неверный JSON"

    if actual_diameter != diameter:
        return False, f"printer.cfg: диаметр {actual_diameter!r}, ожидался {diameter!r}"
    if mutable_diameter != diameter:
        return False, f"printer_mutable.cfg: диаметр {mutable_diameter!r}, ожидался {diameter!r}"
    if actual_material != material:
        return False, f"printer_mutable.cfg: материал {actual_material!r}, ожидался {material!r}"
    if str(metadata.get("diameter", "")) != diameter:
        return False, f"nozzle.cfg: диаметр {metadata.get('diameter')!r}, ожидался {diameter!r}"
    if str(metadata.get("material", "")).lower() != material:
        return False, f"nozzle.cfg: материал {metadata.get('material')!r}, ожидался {material!r}"
    if metadata.get("modify") is not False:
        return False, "nozzle.cfg: флаг modify не равен false"
    return True, ""


def _atomic_write(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temporary = tempfile.mkstemp(prefix=".bedmesh-nozzle-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


class _NozzleUploadWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, local_path: str, ssh_config: dict, diameter: str, material: str):
        super().__init__()
        self.local_path = local_path
        self.ssh_config = ssh_config
        self.diameter = diameter
        self.material = material

    def run(self):
        temporary_paths: list[str] = []
        try:
            mutable_text = read_remote_text_via_ssh(
                self.ssh_config["ip"], self.ssh_config["port"],
                self.ssh_config["user"], self.ssh_config["password"],
                "/userdata/app/gk/printer_mutable.cfg",
            )
            if mutable_text is None:
                self.finished.emit(False, "не удалось прочитать printer_mutable.cfg")
                return
            mutable_path = None
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".json", delete=False) as stream:
                mutable_path = stream.name
                temporary_paths.append(mutable_path)
                stream.write(_replace_mutable_nozzle(mutable_text, self.diameter, self.material))

            ok, error = upload_cfg_with_backup_and_verify(
                self.local_path,
                self.ssh_config["ip"],
                self.ssh_config["port"],
                self.ssh_config["user"],
                self.ssh_config["password"],
                self.ssh_config["path"],
            )
            if not ok:
                self.finished.emit(False, error)
                return
            ok, error = upload_cfg_with_backup_and_verify(
                mutable_path,
                self.ssh_config["ip"], self.ssh_config["port"],
                self.ssh_config["user"], self.ssh_config["password"],
                "/userdata/app/gk/printer_mutable.cfg",
            )
            if not ok:
                self.finished.emit(False, error)
                return
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".json", delete=False) as stream:
                metadata_path = stream.name
                temporary_paths.append(metadata_path)
                json.dump(
                    # The printer's stock startup flow treats modify=true as a
                    # request to run the full nozzle calibration after reboot.
                    # Keep this disabled: the requested full reboot must not
                    # trigger the stock full nozzle calibration chain.
                    {"material": self.material, "diameter": self.diameter, "modify": False},
                    stream,
                    ensure_ascii=False,
                )
            ok, error = upload_cfg_with_backup_and_verify(
                metadata_path,
                self.ssh_config["ip"], self.ssh_config["port"],
                self.ssh_config["user"], self.ssh_config["password"],
                "/userdata/app/gk/config/nozzle.cfg",
            )
            if ok:
                remote_printer_cfg = read_remote_text_via_ssh(
                    self.ssh_config["ip"], self.ssh_config["port"],
                    self.ssh_config["user"], self.ssh_config["password"],
                    self.ssh_config["path"],
                )
                remote_nozzle_cfg = read_remote_text_via_ssh(
                    self.ssh_config["ip"], self.ssh_config["port"],
                    self.ssh_config["user"], self.ssh_config["password"],
                    "/userdata/app/gk/config/nozzle.cfg",
                )
                remote_mutable_cfg = read_remote_text_via_ssh(
                    self.ssh_config["ip"], self.ssh_config["port"],
                    self.ssh_config["user"], self.ssh_config["password"],
                    "/userdata/app/gk/printer_mutable.cfg",
                )
                if remote_printer_cfg is None or remote_mutable_cfg is None or remote_nozzle_cfg is None:
                    ok, error = False, "не удалось прочитать конфигурации после загрузки"
                else:
                    ok, error = _verify_remote_nozzle_values(
                        remote_printer_cfg, remote_mutable_cfg, remote_nozzle_cfg,
                        self.diameter, self.material,
                    )
            self.finished.emit(ok, error)
        except Exception as error:
            self.finished.emit(False, str(error))
        finally:
            for path in temporary_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass


class _NozzlePrinterRebootWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, ssh_config: dict):
        super().__init__()
        self.ssh_config = ssh_config

    def run(self):
        try:
            ok, details = reboot_printer_via_ssh(
                self.ssh_config["ip"],
                self.ssh_config["port"],
                self.ssh_config["user"],
                self.ssh_config["password"],
            )
            self.finished.emit(ok, details)
        except Exception as error:
            self.finished.emit(False, str(error))


class NozzleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self._ssh_config: dict | None = None
        self._file_path: str | None = None
        self._upload_thread = None
        self._upload_worker = None
        self._restart_thread = None
        self._restart_worker = None
        self._loaded_diameter: str | None = None
        self._loaded_material = "brass"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        group = QGroupBox("🧩 Диаметр сопла")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(QLabel(
            "Выберите фактически установленный диаметр. Будет изменён только "
            "параметр nozzle_diameter в секции [extruder]."
        ))
        self.diameter = QComboBox()
        self.diameter.addItems(NOZZLE_DIAMETERS)
        self.diameter.setEnabled(False)
        group_layout.addWidget(self.diameter)
        group_layout.addWidget(QLabel("Тип сопла"))
        self.material = QComboBox()
        for label, value in NOZZLE_MATERIALS:
            self.material.addItem(label, value)
        self.material.setEnabled(False)
        group_layout.addWidget(self.material)
        self.selection = QLabel("Выбрано: —")
        self.selection.setStyleSheet("font-weight: 600; color: #fbbf24;")
        group_layout.addWidget(self.selection)
        self.diameter.currentTextChanged.connect(self._update_selection_label)
        self.material.currentTextChanged.connect(self._update_selection_label)

        self.btn_apply = QPushButton("✅ Сохранить и перезапустить принтер")
        self.btn_apply.setObjectName("primaryButton")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setToolTip(
            "Создаст бекап printer.cfg и выполнит полный перезапуск принтера. "
            "Полная калибровка из приложения не запускается."
        )
        self.btn_apply.clicked.connect(self.apply)
        group_layout.addWidget(self.btn_apply)
        layout.addWidget(group)

        self.status = QLabel("Сначала загрузите printer.cfg по SSH.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #9fb3cc;")
        layout.addWidget(self.status)

        note = QLabel(
            "После применения выполняется полный перезапуск Linux-принтера. "
            "Флаг modify остаётся выключенным, поэтому автоматическая цепочка "
            "PID → шейперы → стол не вызывается."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; background: #101a2b; padding: 8px;")
        layout.addWidget(note)
        layout.addStretch()

    def set_ssh_config(self, ssh_data: dict) -> None:
        try:
            port = int(ssh_data.get("port", 2222))
        except (TypeError, ValueError):
            port = 2222
        self._ssh_config = {
            "ip": ssh_data.get("ip", ""),
            "port": port,
            "user": ssh_data.get("user", "root"),
            "password": ssh_data.get("password", ""),
            "path": ssh_data.get("path", "/userdata/app/gk/printer.cfg"),
        }
        self.btn_apply.setEnabled(False)

    def _update_selection_label(self) -> None:
        diameter = self.diameter.currentText().strip()
        material = self.material.currentText().strip()
        if diameter and material:
            self.selection.setText(f"Выбрано: {_format_nozzle_label(material, diameter)}")

    def load_file(self, path: str) -> None:
        try:
            text = open(path, "r", encoding="utf-8").read()
            diameter = _read_nozzle_diameter(text)
            material = _read_nozzle_material(text) or "brass"
            if diameter is None:
                raise ValueError("В загруженном printer.cfg не найден nozzle_diameter")
            self._file_path = path
            self._loaded_diameter = diameter
            self._loaded_material = material
            index = self.diameter.findText(diameter)
            if index < 0:
                self.diameter.addItem(diameter)
                index = self.diameter.findText(diameter)
            self.diameter.setCurrentIndex(index)
            material_index = self.material.findData(material)
            if material_index < 0:
                self.material.addItem(material, material)
                material_index = self.material.findData(material)
            self.material.setCurrentIndex(material_index)
            self.diameter.setEnabled(True)
            self.material.setEnabled(True)
            self.btn_apply.setEnabled(bool(self._ssh_config))
            self.status.setText(f"Текущие значения: {diameter} мм, {self.material.currentText()}")
        except Exception as error:
            self._file_path = None
            self.diameter.setEnabled(False)
            self.material.setEnabled(False)
            self.btn_apply.setEnabled(False)
            self.status.setText(f"❌ Не удалось прочитать диаметр: {error}")

    def load_metadata(self, text: str) -> None:
        """Applies the printer's nozzle.cfg material to the visible selection."""
        material, metadata_diameter = _read_nozzle_metadata(text)
        if not material:
            return
        material_index = self.material.findData(material)
        if material_index < 0:
            self.material.addItem(material, material)
            material_index = self.material.findData(material)
        self.material.setCurrentIndex(material_index)
        self._loaded_material = material
        diameter_note = ""
        if metadata_diameter and metadata_diameter != self._loaded_diameter:
            diameter_note = f"; предупреждение: nozzle.cfg содержит {metadata_diameter} мм"
        self.status.setText(
            f"Текущие значения: {self._loaded_diameter} мм, {self.material.currentText()}"
            f"{diameter_note}"
        )

    def load_mutable(self, text: str) -> None:
        """Uses printer_mutable.cfg as the source of the saved material/diameter."""
        diameter, material = _read_mutable_nozzle_values(text)
        if material:
            material_index = self.material.findData(material)
            if material_index < 0:
                self.material.addItem(material, material)
                material_index = self.material.findData(material)
            self.material.setCurrentIndex(material_index)
            self._loaded_material = material
        if diameter:
            index = self.diameter.findText(diameter)
            if index < 0:
                self.diameter.addItem(diameter)
                index = self.diameter.findText(diameter)
            self.diameter.setCurrentIndex(index)
            self._loaded_diameter = diameter
        if diameter or material:
            self.status.setText(
                f"Текущие сохранённые значения: {diameter or self._loaded_diameter or '—'} мм, "
                f"{self.material.currentText()}"
            )

    def apply(self) -> None:
        if not self._ssh_config or not self._file_path:
            QMessageBox.warning(self, "Сопло", "Сначала загрузите printer.cfg по SSH.")
            return
        diameter = self.diameter.currentText().strip()
        material = self.material.currentData()
        if diameter not in NOZZLE_DIAMETERS:
            QMessageBox.warning(self, "Сопло", "Выберите диаметр из списка.")
            return
        if diameter == self._loaded_diameter and material == self._loaded_material:
            QMessageBox.information(self, "Сопло", "Эти параметры уже установлены.")
            return
        if self._upload_thread and self._upload_thread.isRunning():
            return
        if self._restart_thread and self._restart_thread.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "Применить диаметр сопла?",
            f"Будет установлено сопло: {diameter} мм, {self.material.currentText()}.\n\n"
            "Будет создан бекап и выполнен полный перезапуск принтера. "
            "Полная калибровка стола не запускается. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            text = open(self._file_path, "r", encoding="utf-8").read()
            _atomic_write(self._file_path, _replace_nozzle_diameter(text, diameter))
        except Exception as error:
            QMessageBox.critical(self, "Сопло", f"Не удалось изменить локальный конфиг:\n{error}")
            return

        self.btn_apply.setEnabled(False)
        self.diameter.setEnabled(False)
        self.material.setEnabled(False)
        self.status.setText("⏳ Сохраняю printer.cfg и создаю бекап...")
        self._upload_thread = QThread(self)
        self._upload_worker = _NozzleUploadWorker(
            self._file_path, self._ssh_config, diameter, material
        )
        self._upload_worker.moveToThread(self._upload_thread)
        self._upload_thread.started.connect(self._upload_worker.run)
        self._upload_worker.finished.connect(self._on_upload_finished)
        self._upload_worker.finished.connect(self._upload_worker.deleteLater)
        self._upload_worker.finished.connect(self._upload_thread.quit)
        self._upload_thread.finished.connect(self._upload_thread.deleteLater)
        self._upload_thread.start()

    def _on_upload_finished(self, ok: bool, details: str) -> None:
        self._upload_worker = None
        self._upload_thread = None
        if not ok:
            self.diameter.setEnabled(True)
            self.material.setEnabled(True)
            self.btn_apply.setEnabled(True)
            self.status.setText("❌ Ошибка сохранения printer.cfg")
            self.logger.error("Nozzle config upload failed: %s", details)
            QMessageBox.critical(self, "Сопло", "Не удалось сохранить printer.cfg. Проверьте бекап и SSH.")
            return

        self.status.setText("⏳ Выполняю полный перезапуск принтера...")
        self._restart_thread = QThread(self)
        self._restart_worker = _NozzlePrinterRebootWorker(self._ssh_config)
        self._restart_worker.moveToThread(self._restart_thread)
        self._restart_thread.started.connect(self._restart_worker.run)
        self._restart_worker.finished.connect(self._on_restart_finished)
        self._restart_worker.finished.connect(self._restart_worker.deleteLater)
        self._restart_worker.finished.connect(self._restart_thread.quit)
        self._restart_thread.finished.connect(self._restart_thread.deleteLater)
        self._restart_thread.start()

    def _on_restart_finished(self, ok: bool, details: str) -> None:
        self._restart_worker = None
        self._restart_thread = None
        self.diameter.setEnabled(True)
        self.material.setEnabled(True)
        self.btn_apply.setEnabled(True)
        if ok:
            self._loaded_diameter = self.diameter.currentText().strip()
            self._loaded_material = self.material.currentData()
            self.status.setText(
                f"✅ Сопло {self._loaded_diameter} мм, {self.material.currentText()} применено. "
                "Выполнен полный перезапуск принтера."
            )
            QMessageBox.information(
                self,
                "Сопло",
                "Диаметр сохранён. Выполнен полный перезапуск принтера без полной калибровки.",
            )
        else:
            self.status.setText("❌ Конфиг сохранён, но принтер не перезапущен")
            self.logger.error("Nozzle printer reboot failed: %s", details)
            QMessageBox.critical(self, "Сопло", "Конфиг сохранён, но принтер не удалось перезапустить.")
