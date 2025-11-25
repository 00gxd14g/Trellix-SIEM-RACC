#!/usr/bin/env python3
"""
McAfee SIEM Alarm Editor - Dark Gray Theme & Complete Format Support

Bu sürümde:
- Koyu gri bir tema kullanıldı.
- Alarm dosyasındaki tüm alanlar (alarmData, conditionData, actions) UI'da destekleniyor.
- Eksik ve çalışmayan fonksiyonlar düzeltildi.
- Bulk Edit ve Generate Report özellikleri tamamlandı.
Version: 1.5.1
"""

import os
import sys
import copy
import logging
import datetime
# Secure XML parsing - DO NOT use xml.etree.ElementTree directly
# import xml.etree.ElementTree as ET  # SECURITY: Replaced with SecureXMLParser
from typing import Any, Dict, List, Optional, Tuple, Set
import weakref
from functools import lru_cache
import xml.etree.ElementTree as StdET

from lxml import etree
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QToolBar,
    QStatusBar,
    QMenu,
    QMenuBar,
    QPushButton,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QFormLayout,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QSplitter,
    QGroupBox,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QListWidget,
    QHeaderView,
    QGridLayout,
    QAbstractItemView,
    QInputDialog,
)
from PyQt6.QtGui import (
    QAction,
    QStandardItemModel,
    QStandardItem,
    QUndoStack,
    QUndoCommand,
    QKeySequence,
    QBrush,
    QColor,
    QShortcut,
    QIcon,
)
from PyQt6.QtCore import Qt, QModelIndex, QTimer

# Import application modules
try:
    from validator import Validator
    from customer_manager import CustomerManager, Customer
    from utils.rule_parser import RuleParser, RuleData, RuleAlarmMapper
    from utils.xml_validator import XMLValidator
    from config import (
        SeverityLevel, DEFAULT_ASSIGNEE_ID, DEFAULT_ESC_ASSIGNEE_ID,
        DEFAULT_MIN_VERSION, DEFAULT_DEVICE_FILTER_PREFIX,
        ActionType, ActionProcess, ConditionType,
        app_settings, update_globals_from_settings
    )
    from utils.secure_xml_parser import SecureXMLParser, XMLParsingError, XMLSecurityError
    from utils.input_validator import InputValidator
    from exceptions import (
        ValidationError, FileOperationError, CustomerNotFoundError
    )
    # Use SecureXMLParser as ET replacement for security
    ET = SecureXMLParser
except ImportError as e:
    raise ImportError(f"Could not import required modules: {e}")

from alarm_state_manager import AlarmStateManager

# Global set to track newly created alarms
# SİL: NEW_ALARMS_SET: Set[str] = set()

# Enhanced logging configuration
from utils.logging_config import configure_logging, log_audit_event, PerformanceTimer

# Configure comprehensive logging system
configure_logging(log_level="INFO", enable_console=True)
logger = logging.getLogger("AlarmEditor")

# Koyu gri tema
DARK_GRAY_STYLESHEET = """
QWidget {
    background-color: #2d2d2d;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 9pt;
}
QPushButton {
    background-color: #4d4d4d;
    color: #e0e0e0;
    border: 1px solid #5a5a5a;
    padding: 6px 12px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #5d5d5d;
}
QPushButton:pressed {
    background-color: #6d6d6d;
}
QPushButton:disabled {
    background-color: #3a3a3a;
    color: #7a7a7a;
}
QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #3d3d3d;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 4px;
    color: #e0e0e0;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #6a9fb5;
    background-color: #4d4d4d;
}
QTableView {
    background-color: #2d2d2d;
    gridline-color: #444444;
    alternate-background-color: #323232;
    color: #e0e0e0;
}
QHeaderView::section {
    background-color: #3d3d3d;
    padding: 4px;
    border: 1px solid #5a5a5a;
    font-weight: bold;
    color: #e0e0e0;
}
QGroupBox {
    background-color: #3a3a3a;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 6px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    background-color: #3a3a3a;
    color: #e0e0e0;
    font-weight: bold;
}
QTabWidget::pane {
    background-color: #2d2d2d;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #3d3d3d;
    color: #e0e0e0;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #2d2d2d;
    border: 1px solid #5a5a5a;
    border-bottom: none;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #4d4d4d;
}
QMenuBar {
    background-color: #3d3d3d;
    color: #e0e0e0;
    border-bottom: 1px solid #5a5a5a;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
}
QMenuBar::item:selected {
    background-color: #5d5d5d;
}
QMenu {
    background-color: #3d3d3d;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 4px;
    color: #e0e0e0;
}
QMenu::item {
    padding: 6px 12px;
    margin: 1px;
}
QMenu::item:selected {
    background-color: #5d5d5d;
}
QToolBar {
    background-color: #3d3d3d;
    border: none;
    border-bottom: 1px solid #5a5a5a;
    spacing: 4px;
    padding: 4px;
}
QStatusBar {
    background-color: #3d3d3d;
    color: #bfbfbf;
    border-top: 1px solid #5a5a5a;
    padding: 4px 8px;
}
QScrollBar:vertical {
    background-color: #2d2d2d;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #5a5a5a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6a6a6a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #2d2d2d;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #5a5a5a;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6a6a6a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QSplitter::handle {
    background-color: #5a5a5a;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover {
    background-color: #6a6a6a;
}
"""

class FieldChangeCommand(QUndoCommand):
    def __init__(
        self,
        alarm_model: "AlarmModel",
        section: str,
        field: str,
        old_value: Any,
        new_value: Any,
        parent=None,
    ):
        super().__init__(parent)
        self.alarm_model = alarm_model
        self.section = section
        self.field = field
        self.old_value = old_value
        self.new_value = new_value
        self.first_time = True

        if isinstance(old_value, str) and isinstance(new_value, str):
            old_preview = (old_value[:10] + "...") if len(old_value) > 10 else old_value
            new_preview = (new_value[:10] + "...") if len(new_value) > 10 else new_value
            self.setText(f"Change {field} from '{old_preview}' to '{new_preview}'")
        else:
            self.setText(f"Change {field}")

    def redo(self):
        if not self.first_time:
            self.alarm_model.set_field(
                self.section, self.field, self.new_value, record_undo=False
            )
            if self.alarm_model.main_window:
                self.alarm_model.main_window.update_alarm_table()
                self.alarm_model.main_window.property_editor.update_form()
        self.first_time = False

    def undo(self):
        self.alarm_model.set_field(
            self.section, self.field, self.old_value, record_undo=False
        )
        if self.alarm_model.main_window:
            self.alarm_model.main_window.update_alarm_table()
            self.alarm_model.main_window.property_editor.update_form()


class AddAlarmCommand(QUndoCommand):
    def __init__(self, main_window, alarm_model, parent=None):
        super().__init__(parent)
        self.main_window = weakref.ref(main_window)
        self.alarm_model = alarm_model
        self.setText(f"Add alarm '{alarm_model.name}'")
        self.first_time = True
        
    def redo(self):
        if not self.first_time:
            mw = self.main_window()
            if mw:
                mw.alarms.append(self.alarm_model)
                mw.alarm_state_manager.mark_as_new(self.alarm_model)
                mw.update_alarm_table()
                mw.status_bar.showMessage(f"Added alarm: {self.alarm_model.name}")
        self.first_time = False
        
    def undo(self):
        mw = self.main_window()
        if mw and self.alarm_model in mw.alarms:
            mw.alarms.remove(self.alarm_model)
            mw.alarm_state_manager.unmark_as_new(self.alarm_model)
            mw.update_alarm_table()
            mw.status_bar.showMessage(f"Removed alarm: {self.alarm_model.name}")


class DeleteAlarmCommand(QUndoCommand):
    def __init__(self, main_window, rows_to_delete, parent=None):
        super().__init__(parent)
        self.main_window = weakref.ref(main_window)
        self.deleted_alarms = []
        
        mw = main_window
        for row in sorted(rows_to_delete, reverse=True):
            if row < len(mw.alarms):
                alarm = mw.alarms[row]
                was_new = mw.alarm_state_manager.is_new(alarm)
                self.deleted_alarms.append((row, alarm, was_new))
        
        count = len(self.deleted_alarms)
        self.setText(f"Delete {count} alarm{'s' if count > 1 else ''}")
        self.first_time = True
        
    def redo(self):
        if not self.first_time:
            mw = self.main_window()
            if mw:
                for row, alarm, was_new in sorted(self.deleted_alarms, reverse=True):
                    if alarm in mw.alarms:
                        mw.alarms.remove(alarm)
                        mw.alarm_state_manager.unmark_as_new(alarm)
                mw.update_alarm_table()
                mw.status_bar.showMessage(f"Deleted {len(self.deleted_alarms)} alarms")
        self.first_time = False
        
    def undo(self):
        mw = self.main_window()
        if mw:
            for row, alarm, was_new in sorted(self.deleted_alarms):
                mw.alarms.insert(row, alarm)
                if was_new:
                    mw.alarm_state_manager.mark_as_new(alarm)
            mw.update_alarm_table()
            mw.status_bar.showMessage(f"Restored {len(self.deleted_alarms)} alarms")


class ActionListCommand(QUndoCommand):
    """Alarm aksiyonları üzerindeki değişiklikleri geri alınabilir hale getiren komut sınıfı"""
    
    ADD_ACTION = 0
    EDIT_ACTION = 1
    REMOVE_ACTION = 2
    
    def __init__(self, property_editor, action_type, action_data, old_data=None, index=None, parent=None):
        super().__init__(parent)
        self.property_editor = weakref.ref(property_editor)
        self.action_type = action_type
        self.action_data = copy.deepcopy(action_data)
        self.old_data = copy.deepcopy(old_data) if old_data else None
        self.index = index
        
        # Komut açıklamasını belirle
        if action_type == self.ADD_ACTION:
            self.setText("Add action")
        elif action_type == self.EDIT_ACTION:
            self.setText("Edit action")
        elif action_type == self.REMOVE_ACTION:
            self.setText("Remove action")
    
    def redo(self):
        editor = self.property_editor()
        if not editor or not editor.current_alarm:
            return
            
        alarm = editor.current_alarm
        action_list = alarm.data["actions"]["actionData"]
        
        if self.action_type == self.ADD_ACTION:
            action_list.append(self.action_data)
            alarm.modified = True
        
        elif self.action_type == self.EDIT_ACTION and self.index is not None:
            if 0 <= self.index < len(action_list):
                action_list[self.index] = self.action_data
                alarm.modified = True
        
        elif self.action_type == self.REMOVE_ACTION and self.index is not None:
            if 0 <= self.index < len(action_list):
                action_list.pop(self.index)
                alarm.modified = True
        
        # UI güncelle
        editor.update_actions_list()
        if alarm.main_window:
            alarm.main_window.update_alarm_table()
    
    def undo(self):
        editor = self.property_editor()
        if not editor or not editor.current_alarm:
            return
            
        alarm = editor.current_alarm
        action_list = alarm.data["actions"]["actionData"]
        
        if self.action_type == self.ADD_ACTION:
            # Son eklenen aksiyonu bul ve kaldır
            for i, action in enumerate(action_list):
                if action == self.action_data:
                    action_list.pop(i)
                    break
            alarm.modified = True
        
        elif self.action_type == self.EDIT_ACTION and self.index is not None:
            if 0 <= self.index < len(action_list) and self.old_data:
                action_list[self.index] = self.old_data
                alarm.modified = True
        
        elif self.action_type == self.REMOVE_ACTION and self.index is not None:
            if self.old_data:
                action_list.insert(self.index, self.old_data)
                alarm.modified = True
        
        # UI güncelle
        editor.update_actions_list()
        if alarm.main_window:
            alarm.main_window.update_alarm_table()


class AlarmModel:
    """
    Basit veri modeli; QStandardItemModel kullanıldığı için bu model
    yalnızca veri tutmak ve serialize etmek için kullanılır.
    """

    def __init__(self, parent=None):
        # Use weakref to avoid circular reference
        self._main_window = weakref.ref(parent) if parent else None
        self.name: str = ""
        self.min_version: str = ""
        self.data: Dict[str, Any] = {
            "alarmData": {},
            "conditionData": {},
            "actions": {"actionData": []},
        }
        self.change_log: List[Dict[str, Any]] = []
        self.modified: bool = False
    
    @property
    def main_window(self):
        """Get main window reference safely"""
        return self._main_window() if self._main_window else None

    def from_element(self, element: ET.Element) -> None:
        """
        Load alarm data from XML element with proper encoding handling
        and data validation.
        """
        self.name = self._fix_encoding(element.get("name", ""))
        self.min_version = self._fix_encoding(element.get("minVersion", ""))

        self.data = {"alarmData": {}, "conditionData": {}, "actions": {"actionData": []}}

        # Parse alarmData section
        alarm_data = element.find("alarmData")
        if alarm_data is not None:
            for child in alarm_data:
                if child.tag == "deviceIDs":
                    try:
                        self.data["alarmData"]["deviceIDs"] = self._parse_device_ids(child)
                    except Exception as e:
                        logger.warning(f"Error parsing deviceIDs in alarm '{self.name}': {e}")
                        # Store raw XML as fallback
                        self.data["alarmData"]["deviceIDs"] = ET.tostring(child, encoding='unicode')
                else:
                    self.data["alarmData"][child.tag] = self._fix_encoding(child.text)

        # Set default value for enabled field if missing
        if "enabled" not in self.data["alarmData"]:
            self.data["alarmData"]["enabled"] = "T"

        # Parse conditionData section
        condition_data = element.find("conditionData")
        if condition_data is not None:
            for child in condition_data:
                self.data["conditionData"][child.tag] = self._fix_encoding(child.text)

        # Set default values for required fields if missing
        if "matchField" not in self.data["conditionData"]:
            self.data["conditionData"]["matchField"] = "DSIDSigID"
        if "matchValue" not in self.data["conditionData"]:
            self.data["conditionData"]["matchValue"] = ""
        if "xMin" not in self.data["conditionData"]:
            self.data["conditionData"]["xMin"] = "10"  # Default minimum events

        # Parse actions section
        actions = element.find("actions")
        if actions is not None:
            action_data_list = []
            for action_elem in actions.findall("actionData"):
                action_data = {
                    "actionType": self._fix_encoding(action_elem.findtext("actionType", "0")),
                    "actionProcess": self._fix_encoding(action_elem.findtext("actionProcess", "1")),
                    "actionAttributes": {},
                }
                attr_elem = action_elem.find("actionAttributes")
                if attr_elem is not None:
                    for attr in attr_elem.findall("attribute"):
                        name = attr.get("name", "")
                        if name:
                            action_data["actionAttributes"][name] = self._fix_encoding(attr.text or "")
                action_data_list.append(action_data)

            # Add default action if no actions are defined
            if not action_data_list:
                action_data_list.append(
                    {"actionType": "0", "actionProcess": "1", "actionAttributes": {}}
                )
            self.data["actions"]["actionData"] = action_data_list

        self.change_log = []
        self.modified = False

    def to_element(self) -> ET.Element:
        alarm = ET.Element("alarm")
        alarm.set("name", self.name)
        alarm.set("minVersion", self.min_version)

        # alarmData
        alarm_data = ET.SubElement(alarm, "alarmData")
        for key, value in self.data["alarmData"].items():
            if key == "deviceIDs":
                device_ids_elem = ET.SubElement(alarm_data, "deviceIDs")
                self._build_device_ids(device_ids_elem, value)
            else:
                child = ET.SubElement(alarm_data, key)
                if value is not None:
                    child.text = str(value)

        # conditionData
        condition_data = ET.SubElement(alarm, "conditionData")
        for key, value in self.data["conditionData"].items():
            child = ET.SubElement(condition_data, key)
            if value is not None:
                child.text = str(value)

        # actions
        actions = ET.SubElement(alarm, "actions")
        for action in self.data["actions"].get("actionData", []):
            action_data = ET.SubElement(actions, "actionData")

            action_type = ET.SubElement(action_data, "actionType")
            action_type.text = str(action.get("actionType", ""))

            action_process = ET.SubElement(action_data, "actionProcess")
            action_process.text = str(action.get("actionProcess", ""))

            action_attrs = ET.SubElement(action_data, "actionAttributes")
            for attr_name, attr_value in action.get("actionAttributes", {}).items():
                attr = ET.SubElement(action_attrs, "attribute")
                attr.set("name", attr_name)
                if attr_value is not None:
                    attr.text = str(attr_value)

        return alarm

    def _parse_device_ids(self, device_ids_elem: ET.Element) -> Dict:
        result = {"deviceFilter": []}
        for device_filter in device_ids_elem.findall("deviceFilter"):
            filter_data = {"mask": device_filter.get("mask", ""), "constraintFilter": []}
            for constraint in device_filter.findall("constraintFilter"):
                constraint_data = {
                    "type": constraint.get("type", ""),
                    "value": constraint.get("value", ""),
                }
                filter_data["constraintFilter"].append(constraint_data)
            result["deviceFilter"].append(filter_data)
        return result

    def _build_device_ids(self, device_ids_elem: ET.Element, device_ids_data: Any) -> None:
        """
        Build device IDs XML structure based on input data.
        Uses DeviceIDValidator for validation when string input is provided.
        """
        if device_ids_data is None:
            device_ids_elem.text = ""
            return

        if isinstance(device_ids_data, str):
            device_text = str(device_ids_data).strip()
            
            # Validate the format
            is_valid, _ = DeviceIDValidator.validate(device_text)
            
            if not is_valid:
                logger.warning(f"Invalid device ID format: {device_text}")
                device_ids_elem.text = device_text
                return
                
            # XML format - preserve as raw text
            if device_text.startswith("<") and device_text.endswith(">"):
                device_ids_elem.text = device_text
            # Comma-separated IDs - convert to proper XML structure
            elif device_text and all(id.strip().isdigit() for id in device_text.split(",")):
                for device_id in device_text.split(","):
                    device_id = device_id.strip()
                    if device_id:
                        device_filter = ET.SubElement(device_ids_elem, "deviceFilter")
                        device_filter.set("mask", device_id)
            else:
                device_ids_elem.text = device_text
            return

        if not isinstance(device_ids_data, dict):
            device_ids_elem.text = str(device_ids_data)
            return

        try:
            for device_filter_data in device_ids_data.get("deviceFilter", []):
                device_filter = ET.SubElement(device_ids_elem, "deviceFilter")
                device_filter.set("mask", str(device_filter_data.get("mask", "")))
                for constraint_data in device_filter_data.get("constraintFilter", []):
                    constraint = ET.SubElement(device_filter, "constraintFilter")
                    constraint.set("type", str(constraint_data.get("type", "")))
                    constraint.set("value", str(constraint_data.get("value", "")))
        except Exception as e:
            logger.error(f"Error building device IDs: {str(e)}")
            device_ids_elem.text = str(device_ids_data)

    def get_field(self, section: str, field: str) -> Any:
        return self.data.get(section, {}).get(field)

    def set_field(
        self,
        section: str,
        field: str,
        value: Any,
        record_undo: bool = True,
        note: Optional[str] = None,
    ) -> bool:
        old_value = None

        if section == "alarm":
            if field == "name":
                old_value = self.name
                self.name = value
            elif field == "minVersion":
                old_value = self.min_version
                self.min_version = value
            else:
                return False
        else:
            if section not in self.data:
                self.data[section] = {}

            old_value = self.get_field(section, field)
            if old_value != value:
                self.data[section][field] = value

        if old_value != value:
            self.modified = True
            if record_undo and self.main_window and hasattr(self.main_window, "undo_stack"):
                self.main_window.undo_stack.push(
                    FieldChangeCommand(self, section, field, old_value, value)
                )
            self.add_change_log_entry(section, field, old_value, value, note)
            return True

        return False

    def add_change_log_entry(
        self,
        section: str,
        field: str,
        old_value: Any,
        new_value: Any,
        note: Optional[str] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "section": section,
            "field": field,
            "old": str(old_value) if old_value is not None else "",
            "new": str(new_value) if new_value is not None else "",
        }
        if note:
            entry["note"] = note
        self.change_log.append(entry)
        self.modified = True

    def get_field_display_value(self, section: str, field: str) -> str:
        value = self.get_field(section, field)
        if value is None:
            return "<not set>"
        if field in ("matchNot", "useWatchlist", "escEnabled", "enabled"):
            return "Yes (True)" if str(value).upper() == "T" else "No (False)"
        if isinstance(value, dict) or isinstance(value, list):
            if field == "deviceIDs":
                if isinstance(value, dict) and "deviceFilter" in value:
                    device_filters = []
                    for device_filter in value.get("deviceFilter", []):
                        mask = device_filter.get("mask", "")
                        constraints = []
                        for constraint in device_filter.get("constraintFilter", []):
                            constraints.append(
                                f"{constraint.get('type', '')}: {constraint.get('value', '')}"
                            )
                        if constraints:
                            device_filters.append(f"{mask} [{', '.join(constraints)}]")
                        else:
                            device_filters.append(mask)
                    return "; ".join(device_filters) if device_filters else "<empty device filters>"
                elif isinstance(value, str):
                    return value
                else:
                    return "<complex device data>"
            return "<complex data>"
        return str(value)

    @staticmethod
    def _fix_encoding(text: Optional[str]) -> str:
        """Fix potential encoding issues in text data"""
        if not text:
            return ""
            
        # First try if it's already valid UTF-8
        if isinstance(text, str):
            # If text has Turkish characters, it's likely already correctly encoded
            if any(ch in text for ch in "ğĞıİşŞöÖçÇüÜ"):
                return text
                
            # Try latin1 -> utf8 conversion to see if that helps
            try:
                fixed = text.encode("latin1").decode("utf-8")
                if any(ch in fixed for ch in "ğĞıİşŞöÖçÇüÜ"):
                    return fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        
        # Return original if all conversions fail
        return text

    def export_change_log(self) -> List[Dict[str, Any]]:
        return self.change_log

    def clear_change_log(self) -> None:
        self.change_log = []


class PropertyEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_alarm: Optional[AlarmModel] = None
        self._main_window = parent
        self.field_widgets: Dict[str, QWidget] = {}
        self.change_in_progress = False
        self._signals_connected = False
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("🔧 Alarm Properties")
        header.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.create_basic_info_tab()
        self.create_alarm_data_tab()
        self.create_condition_data_tab()
        self.create_actions_tab()
        self.create_device_settings_tab()

    def create_basic_info_tab(self):
        basic_tab = QWidget()
        vlayout = QVBoxLayout(basic_tab)
        form = QFormLayout()
        form.setSpacing(6)

        # Name
        self.field_widgets["name"] = QLineEdit()
        form.addRow("Name:", self.field_widgets["name"])

        # Min Version
        self.field_widgets["minVersion"] = QLineEdit()
        form.addRow("Min Version:", self.field_widgets["minVersion"])

        # Enabled
        self.field_widgets["enabled"] = QCheckBox()
        form.addRow("Enabled:", self.field_widgets["enabled"])

        # Note / Description
        self.field_widgets["note"] = QTextEdit()
        self.field_widgets["note"].setMaximumHeight(60)
        form.addRow("Description (note):", self.field_widgets["note"])

        vlayout.addLayout(form)
        vlayout.addStretch()
        self.tab_widget.addTab(basic_tab, "Basic Info")

    def create_alarm_data_tab(self):
        alarm_tab = QWidget()
        vlayout = QVBoxLayout(alarm_tab)
        form = QFormLayout()
        form.setSpacing(6)

        # filters (string)
        self.field_widgets["filters"] = QTextEdit()
        self.field_widgets["filters"].setMaximumHeight(40)
        form.addRow("Filters:", self.field_widgets["filters"])

        # notificationType
        self.field_widgets["notificationType"] = QComboBox()
        self.field_widgets["notificationType"].addItems(["0", "1", "2"])
        form.addRow("Notification Type:", self.field_widgets["notificationType"])

        # severity
        self.field_widgets["severity"] = QSpinBox()
        self.field_widgets["severity"].setRange(0, 100)
        self.field_widgets["severity"].setValue(50)
        form.addRow("Severity (0-100):", self.field_widgets["severity"])

        # escEnabled
        self.field_widgets["escEnabled"] = QCheckBox()
        form.addRow("Escalation Enabled:", self.field_widgets["escEnabled"])

        # escSeverity
        self.field_widgets["escSeverity"] = QSpinBox()
        self.field_widgets["escSeverity"].setRange(0, 100)
        self.field_widgets["escSeverity"].setValue(50)
        form.addRow("Escalation Severity:", self.field_widgets["escSeverity"])

        # escMin
        self.field_widgets["escMin"] = QSpinBox()
        self.field_widgets["escMin"].setRange(0, 1440)
        form.addRow("Escalation Minutes:", self.field_widgets["escMin"])

        # summaryTemplate
        self.field_widgets["summaryTemplate"] = QTextEdit()
        self.field_widgets["summaryTemplate"].setMaximumHeight(60)
        form.addRow("Summary Template:", self.field_widgets["summaryTemplate"])

        # assignee
        self.field_widgets["assignee"] = QLineEdit()
        form.addRow("Assignee ID:", self.field_widgets["assignee"])

        # assigneeType
        self.field_widgets["assigneeType"] = QComboBox()
        self.field_widgets["assigneeType"].addItems(["0", "1"])
        form.addRow("Assignee Type:", self.field_widgets["assigneeType"])

        # escAssignee
        self.field_widgets["escAssignee"] = QLineEdit()
        form.addRow("Escalation Assignee ID:", self.field_widgets["escAssignee"])

        # escAssigneeType
        self.field_widgets["escAssigneeType"] = QComboBox()
        self.field_widgets["escAssigneeType"].addItems(["0", "1"])
        form.addRow("Escalation Assignee Type:", self.field_widgets["escAssigneeType"])

        vlayout.addLayout(form)
        vlayout.addStretch()
        self.tab_widget.addTab(alarm_tab, "Alarm Data")

    def create_condition_data_tab(self):
        condition_tab = QWidget()
        vlayout = QVBoxLayout(condition_tab)
        form = QFormLayout()
        form.setSpacing(6)

        # conditionType
        self.field_widgets["conditionType"] = QSpinBox()
        self.field_widgets["conditionType"].setRange(0, 1000)
        form.addRow("Condition Type:", self.field_widgets["conditionType"])

        # queryID
        self.field_widgets["queryID"] = QSpinBox()
        self.field_widgets["queryID"].setRange(0, 1000)
        form.addRow("Query ID:", self.field_widgets["queryID"])

        # alertRateMin
        self.field_widgets["alertRateMin"] = QSpinBox()
        self.field_widgets["alertRateMin"].setRange(0, 1440)
        form.addRow("Alert Rate (Min):", self.field_widgets["alertRateMin"])

        # alertRateCount
        self.field_widgets["alertRateCount"] = QSpinBox()
        self.field_widgets["alertRateCount"].setRange(0, 1000)
        form.addRow("Alert Count:", self.field_widgets["alertRateCount"])

        # pctAbove
        self.field_widgets["pctAbove"] = QSpinBox()
        self.field_widgets["pctAbove"].setRange(0, 100)
        form.addRow("Percent Above:", self.field_widgets["pctAbove"])

        # pctBelow
        self.field_widgets["pctBelow"] = QSpinBox()
        self.field_widgets["pctBelow"].setRange(0, 100)
        form.addRow("Percent Below:", self.field_widgets["pctBelow"])

        # offsetMin
        self.field_widgets["offsetMin"] = QSpinBox()
        self.field_widgets["offsetMin"].setRange(0, 1440)
        form.addRow("Offset Minutes:", self.field_widgets["offsetMin"])

        # timeFilter
        self.field_widgets["timeFilter"] = QLineEdit()
        form.addRow("Time Filter:", self.field_widgets["timeFilter"])

        # xMin
        self.field_widgets["xMin"] = QSpinBox()
        self.field_widgets["xMin"].setRange(0, 1000)
        self.field_widgets["xMin"].setValue(1)
        form.addRow("Minimum Events (xMin):", self.field_widgets["xMin"])

        # useWatchlist
        self.field_widgets["useWatchlist"] = QCheckBox()
        form.addRow("Use Watchlist:", self.field_widgets["useWatchlist"])

        # matchField
        self.field_widgets["matchField"] = QComboBox()
        self.field_widgets["matchField"].addItems(["DSIDSigID", "NormID"])
        form.addRow("Match Field:", self.field_widgets["matchField"])

        # matchValue
        self.field_widgets["matchValue"] = QLineEdit()
        form.addRow("Match Value:", self.field_widgets["matchValue"])

        # matchNot
        self.field_widgets["matchNot"] = QCheckBox()
        form.addRow("Invert Match:", self.field_widgets["matchNot"])

        vlayout.addLayout(form)
        vlayout.addStretch()
        self.tab_widget.addTab(condition_tab, "Condition Data")

    def create_actions_tab(self):
        actions_tab = QWidget()
        vlayout = QVBoxLayout(actions_tab)

        self.actions_list = QListWidget()
        self.actions_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        vlayout.addWidget(self.actions_list)

        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Action")
        add_btn.clicked.connect(self.add_action)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Action")
        edit_btn.clicked.connect(self.edit_action)
        button_layout.addWidget(edit_btn)

        remove_btn = QPushButton("Remove Action")
        remove_btn.clicked.connect(self.remove_action)
        button_layout.addWidget(remove_btn)

        vlayout.addLayout(button_layout)
        vlayout.addStretch()
        self.tab_widget.addTab(actions_tab, "Actions")

    def create_device_settings_tab(self):
        device_tab = QWidget()
        vlayout = QVBoxLayout(device_tab)
        form = QFormLayout()
        form.setSpacing(6)

        # deviceIDs
        self.field_widgets["deviceIDs"] = QTextEdit()
        self.field_widgets["deviceIDs"].setMaximumHeight(60)
        form.addRow("Device IDs (as XML or CSV):", self.field_widgets["deviceIDs"])

        vlayout.addLayout(form)
        vlayout.addStretch()
        self.tab_widget.addTab(device_tab, "Device Settings")

    def connect_signals(self):
        if self._signals_connected:
            return
        for field_name, widget in self.field_widgets.items():
            self._connect_widget_signal(widget, field_name)
        self._signals_connected = True

    def _connect_widget_signal(self, widget: QWidget, field_name: str):
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(
                lambda text, fn=field_name: self._on_field_changed(fn, text)
            )
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(
                lambda value, fn=field_name: self._on_field_changed(fn, value)
            )
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(
                lambda state, fn=field_name: self._on_field_changed(
                    fn, state == Qt.CheckState.Checked.value
                )
            )
        elif isinstance(widget, QTextEdit):
            widget.textChanged.connect(
                lambda fn=field_name: self._on_field_changed(
                    fn, widget.toPlainText()
                )
            )
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(
                lambda text, fn=field_name: self._on_field_changed(fn, text)
            )

    def _on_field_changed(self, field_name: str, value: Any):
        if self.change_in_progress or not self.current_alarm:
            return

        self.change_in_progress = True
        try:
            mw = self._main_window
            if not mw:
                return

            if field_name in ("name", "minVersion"):
                section = "alarm"
            elif field_name in mw.ALARM_DATA_FIELDS:
                section = "alarmData"
            elif field_name in mw.CONDITION_DATA_FIELDS:
                section = "conditionData"
            else:
                return

            # Validation based on field type
            if field_name == "name":
                # Duplicate name kontrolü
                if section == "alarm":
                    other_names = [a.name for a in mw.alarms if a is not self.current_alarm]
                    if value in other_names:
                        QMessageBox.warning(
                            self, 
                            "Duplicate Name", 
                            f"An alarm with the name '{value}' already exists."
                        )
                        self.update_form()
                        return
                
                # Normal validation
                valid, error_msg = InputValidator.validate_alarm_name(str(value))
                if not valid:
                    QMessageBox.warning(self, "Invalid Input", error_msg)
                    self.update_form()
                    return
            
            elif field_name in ["severity", "escSeverity"]:
                valid, error_msg = InputValidator.validate_severity(value)
                if not valid:
                    QMessageBox.warning(self, "Invalid Input", error_msg)
                    self.update_form()
                    return
            
            elif field_name == "matchValue":
                match_field = self.current_alarm.get_field("conditionData", "matchField")
                valid, error_msg = InputValidator.validate_match_value(str(value), match_field)
                if not valid:
                    QMessageBox.warning(self, "Invalid Input", error_msg)
                    self.update_form()
                    return
            
            elif field_name == "deviceIDs":
                valid, error_msg = InputValidator.validate_device_ids(str(value))
                if not valid:
                    QMessageBox.warning(self, "Invalid Device ID", error_msg)
                    self.update_form()
                    return
            
            # Sanitize string values
            if isinstance(value, str) and field_name not in ["deviceIDs", "matchValue"]:
                value = InputValidator.sanitize_string(value)

            if isinstance(value, bool):
                value = "T" if value else "F"

            updated = self.current_alarm.set_field(section, field_name, value)
            if updated and mw:
                mw.update_alarm_table()
        finally:
            self.change_in_progress = False

    def set_current_alarm(self, alarm: Optional[AlarmModel]):
        self.current_alarm = alarm
        self.update_form()

    def update_form(self):
        if not self.current_alarm:
            self.clear_form()
            return

        self.change_in_progress = True
        try:
            alarm = self.current_alarm

            # Basic fields
            self.field_widgets["name"].setText(alarm.name or "")
            self.field_widgets["minVersion"].setText(alarm.min_version or "")
            self.field_widgets["enabled"].setChecked(
                str(alarm.get_field("alarmData", "enabled")).upper() == "T"
            )
            self.field_widgets["note"].setPlainText(
                str(alarm.get_field("alarmData", "note") or "")
            )

            # Alarm Data fields
            for field_name in [
                "filters",
                "notificationType",
                "severity",
                "escEnabled",
                "escSeverity",
                "escMin",
                "summaryTemplate",
                "assignee",
                "assigneeType",
                "escAssignee",
                "escAssigneeType",
            ]:
                value = alarm.get_field("alarmData", field_name)
                widget = self.field_widgets.get(field_name)
                if widget is None or value is None:
                    continue

                if isinstance(widget, QSpinBox):
                    try:
                        widget.setValue(int(value))
                    except (ValueError, TypeError):
                        widget.setValue(0)
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(str(value).upper() == "T")
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QTextEdit):
                    widget.setPlainText(str(value))

            # Device IDs
            self.field_widgets["deviceIDs"].setPlainText(
                str(alarm.get_field("alarmData", "deviceIDs") or "")
            )

            # Condition Data fields
            for field_name in [
                "conditionType",
                "queryID",
                "alertRateMin",
                "alertRateCount",
                "pctAbove",
                "pctBelow",
                "offsetMin",
                "timeFilter",
                "xMin",
                "useWatchlist",
                "matchField",
                "matchValue",
                "matchNot",
            ]:
                value = alarm.get_field("conditionData", field_name)
                widget = self.field_widgets.get(field_name)
                if widget is None or value is None:
                    continue

                if isinstance(widget, QSpinBox):
                    try:
                        widget.setValue(int(value))
                    except (ValueError, TypeError):
                        widget.setValue(0)
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(str(value).upper() == "T")
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value))

            # Actions list
            self.update_actions_list()
        finally:
            self.change_in_progress = False

    def clear_form(self):
        self.change_in_progress = True
        try:
            for widget in self.field_widgets.values():
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QSpinBox):
                    widget.setValue(0)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(False)
                elif isinstance(widget, QTextEdit):
                    widget.clear()
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(0)
            self.actions_list.clear()
        finally:
            self.change_in_progress = False

    def update_actions_list(self):
        self.actions_list.clear()
        if not self.current_alarm:
            return

        for action in self.current_alarm.data["actions"].get("actionData", []):
            action_type = action.get("actionType", "")
            action_process = action.get("actionProcess", "")

            process_names = {
                "1": "Event Logging",
                "6": "UI Display",
                "7": "Audio Alert",
                "9": "Email Notification",
            }
            process_name = process_names.get(action_process, f"Process {action_process}")
            item_text = f"Type: {action_type}, Process: {action_process} ({process_name})"
            self.actions_list.addItem(item_text)

    def add_action(self):
        if not self.current_alarm:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Action")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)

        action_type_combo = QComboBox()
        action_type_combo.addItems(["0", "1"])
        action_process_combo = QComboBox()
        action_process_combo.addItems(["1", "6", "7", "9"])

        layout.addRow("Action Type:", action_type_combo)
        layout.addRow("Action Process:", action_process_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            action_data = {
                "actionType": action_type_combo.currentText(),
                "actionProcess": action_process_combo.currentText(),
                "actionAttributes": {},
            }
            
            # Geri alma komutu oluştur
            command = ActionListCommand(
                self, 
                ActionListCommand.ADD_ACTION, 
                action_data
            )
            
            # Undo stack üzerinden işlemi yap
            main_window = self.current_alarm.main_window
            if main_window:
                main_window.undo_stack.push(command)
            else:
                # Main window referansı yoksa doğrudan işlemi yap
                self.current_alarm.data["actions"]["actionData"].append(action_data)
                self.update_actions_list()
                self.current_alarm.modified = True

    def edit_action(self):
        current_row = self.actions_list.currentRow()
        if current_row < 0 or not self.current_alarm:
            return

        actions = self.current_alarm.data["actions"]["actionData"]
        if current_row >= len(actions):
            return

        action_data = actions[current_row]
        old_data = copy.deepcopy(action_data)

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Action")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)

        action_type_combo = QComboBox()
        action_type_combo.addItems(["0", "1"])
        action_type_combo.setCurrentText(str(action_data.get("actionType", "0")))

        action_process_combo = QComboBox()
        action_process_combo.addItems(["1", "6", "7", "9"])
        action_process_combo.setCurrentText(str(action_data.get("actionProcess", "1")))

        layout.addRow("Action Type:", action_type_combo)
        layout.addRow("Action Process:", action_process_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Yeni değerleri içeren bir kopyasını oluştur
            new_data = copy.deepcopy(action_data)
            new_data["actionType"] = action_type_combo.currentText()
            new_data["actionProcess"] = action_process_combo.currentText()
            
            # Geri alma komutu oluştur
            command = ActionListCommand(
                self, 
                ActionListCommand.EDIT_ACTION, 
                new_data,
                old_data=old_data,
                index=current_row
            )
            
            # Undo stack üzerinden işlemi yap
            main_window = self.current_alarm.main_window
            if main_window:
                main_window.undo_stack.push(command)
            else:
                # Main window referansı yoksa doğrudan işlemi yap
                action_data["actionType"] = action_type_combo.currentText()
                action_data["actionProcess"] = action_process_combo.currentText()
                self.update_actions_list()
                self.current_alarm.modified = True

    def remove_action(self):
        current_row = self.actions_list.currentRow()
        if current_row < 0 or not self.current_alarm:
            return

        actions = self.current_alarm.data["actions"]["actionData"]
        if current_row < len(actions):
            # Silinecek aksiyonun yedeğini al
            old_action_data = copy.deepcopy(actions[current_row])
            
            # Geri alma komutu oluştur
            command = ActionListCommand(
                self, 
                ActionListCommand.REMOVE_ACTION, 
                action_data={},  # Silme işleminde yeni veri yok
                old_data=old_action_data,
                index=current_row
            )
            
            # Undo stack üzerinden işlemi yap
            main_window = self.current_alarm.main_window
            if main_window:
                main_window.undo_stack.push(command)
            else:
                # Main window referansı yoksa doğrudan işlemi yap
                actions.pop(current_row)
                self.update_actions_list()
                self.current_alarm.modified = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.alarms: List[AlarmModel] = []
        self.current_alarm: Optional[AlarmModel] = None
        self.current_file: Optional[str] = None
        self.original_tree: Optional[ET.ElementTree] = None
        self.undo_stack = QUndoStack(self)
        self.validator = Validator()
        
        # Yeni özellikler
        self.customer_manager = CustomerManager()
        self.rule_parser = RuleParser()
        self.xml_validator = XMLValidator()
        self.rule_alarm_mapper = RuleAlarmMapper()
        self.current_customer: Optional[Customer] = None
        self.current_rules: List[RuleData] = []
        self.alarm_state_manager = AlarmStateManager()
        
        # Initialization flag to prevent early triggers
        self._initializing = True

        # Field label haritası
        self.FIELD_LABELS: Dict[str, str] = {
            "name": "Alarm Name / Alarm Adı",
            "enabled": "Enabled / Aktif",
            "filters": "Filters",
            "note": "Description / Açıklama",
            "notificationType": "Notification Type / Bildirim Tipi",
            "severity": "Severity / Önem Seviyesi",
            "escEnabled": "Escalation Enabled / Eskalasyon Aktif",
            "escSeverity": "Escalation Severity / Eskalasyon Önem Seviyesi",
            "escMin": "Escalation Minutes / Eskalasyon Dakikası",
            "summaryTemplate": "Summary Template",
            "assignee": "Assignee / Atanan Kişi",
            "assigneeType": "Assignee Type / Atanan Kişi Tipi",
            "escAssignee": "Escalation Assignee / Eskalasyon Atanan Kişi",
            "escAssigneeType": "Escalation Assignee Type / Eskalasyon Atanan Kişi Tipi",
            "deviceIDs": "Device IDs / Cihaz IDleri",
            "conditionType": "Condition Type",
            "queryID": "Query ID",
            "alertRateMin": "Alert Rate Min",
            "alertRateCount": "Alert Rate Count",
            "pctAbove": "Percent Above",
            "pctBelow": "Percent Below",
            "offsetMin": "Offset Minutes",
            "timeFilter": "Time Filter",
            "xMin": "Minimum Events",
            "useWatchlist": "Use Watchlist",
            "matchField": "Match Field / Eşleşme Alanı",
            "matchValue": "Match Value / Eşleşme Değeri",
            "matchNot": "Invert Match / Eşleşmeyi Tersine Çevir",
        }

        # Alan kümeleri
        self.ALARM_DATA_FIELDS = {
            "filters",
            "notificationType",
            "severity",
            "escEnabled",
            "escSeverity",
            "escMin",
            "summaryTemplate",
            "assignee",
            "assigneeType",
            "escAssignee",
            "escAssigneeType",
            "deviceIDs",
            "note",
            "enabled",
        }
        self.CONDITION_DATA_FIELDS = {
            "conditionType",
            "queryID",
            "alertRateMin",
            "alertRateCount",
            "pctAbove",
            "pctBelow",
            "offsetMin",
            "timeFilter",
            "xMin",
            "useWatchlist",
            "matchField",
            "matchValue",
            "matchNot",
        }

        logger.info("Initializing main window")
        self.setup_ui()
        self.connect_signals()
        self.setup_shortcuts()
        self.update_ui_state()

        # Ayarlardan tema ve pencere boyutunu al
        if app_settings.get("dark_theme"):
            self.setStyleSheet(DARK_GRAY_STYLESHEET)
        else:
            self.setStyleSheet("")  # Use default style
            
        # Set window size from settings
        width = app_settings.get("window_width")
        height = app_settings.get("window_height")
        self.resize(width, height)
        
        # Mark initialization as complete and load first customer
        self._initializing = False
        logger.info("Main window initialization complete")
        
        # Müşteri yüklemeyi başlat
        if self.customer_combo.count() > 0:
            first_customer_text = self.customer_combo.itemText(0)
            if first_customer_text != "No customers available":
                # Timer kullanarak yükleme - UI tamamen hazır olduktan sonra
                QTimer.singleShot(100, lambda: self.load_first_customer())

    def setup_shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Open, self, self.open_file)
        QShortcut(QKeySequence.StandardKey.Save, self, self.save_file)
        QShortcut(QKeySequence.StandardKey.SaveAs, self, self.save_file_as)
        QShortcut(QKeySequence.StandardKey.Undo, self, lambda: self.undo_stack.undo())
        QShortcut(QKeySequence.StandardKey.Redo, self, lambda: self.undo_stack.redo())
        QShortcut(QKeySequence("Ctrl+D"), self, self.duplicate_selected_alarm)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search_input.setFocus())
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_new_alarm)
        QShortcut(QKeySequence("Ctrl+E"), self, self.edit_selected_alarm)
        QShortcut(QKeySequence("Ctrl+Alt+V"), self, self.validate_current_file)
        QShortcut(QKeySequence("Ctrl+B"), self, self.bulk_edit_selected)
        QShortcut(QKeySequence("Ctrl+R"), self, self.generate_change_report)

    def setup_ui(self):
        self.setWindowTitle("🔧 McAfee SIEM Alarm Editor v2.0.0 - Customer & Rule Management")
        
        # Minimum size from settings
        min_width = app_settings.get("dialog_min_width")
        min_height = app_settings.get("dialog_min_height")
        self.setMinimumSize(min_width, min_height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Ana tab widget
        self.main_tab_widget = QTabWidget()
        main_layout.addWidget(self.main_tab_widget)

        # Customer Management Tab
        customer_tab = self.create_customer_management_tab()
        self.main_tab_widget.addTab(customer_tab, "👥 Customer Management")

        # Alarm Management Tab (eski ana panel)
        alarm_tab = self.create_alarm_management_tab()
        self.main_tab_widget.addTab(alarm_tab, "⚠️ Alarm Management")

        # Rule Management Tab
        rule_tab = self.create_rule_management_tab()
        self.main_tab_widget.addTab(rule_tab, "📋 Rule Management")

        # Rule-Alarm Mapping Tab
        mapping_tab = self.create_mapping_tab()
        self.main_tab_widget.addTab(mapping_tab, "🔗 Rule-Alarm Mapping")

        self.create_menu_bar()
        self.create_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select a customer to begin")

    def create_customer_management_tab(self) -> QWidget:
        """Create customer management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("👥 Customer Management")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a90e2;")
        layout.addWidget(header)

        # Customer selection area
        customer_group = QGroupBox("Customer Selection")
        customer_layout = QVBoxLayout(customer_group)

        # Customer combo and buttons
        customer_selection_layout = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(300)
        self.customer_combo.currentTextChanged.connect(self.on_customer_selected)
        customer_selection_layout.addWidget(QLabel("Current Customer:"))
        customer_selection_layout.addWidget(self.customer_combo)

        new_customer_btn = QPushButton("New Customer")
        new_customer_btn.clicked.connect(self.create_new_customer)
        customer_selection_layout.addWidget(new_customer_btn)

        edit_customer_btn = QPushButton("Edit Customer")
        edit_customer_btn.clicked.connect(self.edit_current_customer)
        customer_selection_layout.addWidget(edit_customer_btn)

        delete_customer_btn = QPushButton("Delete Customer")
        delete_customer_btn.clicked.connect(self.delete_current_customer)
        customer_selection_layout.addWidget(delete_customer_btn)

        customer_layout.addLayout(customer_selection_layout)
        
        # Database management buttons
        db_buttons_layout = QHBoxLayout()
        
        refresh_db_btn = QPushButton("Refresh DB")
        refresh_db_btn.setToolTip("Refresh database by rescanning customer directories")
        refresh_db_btn.clicked.connect(self.refresh_database)
        db_buttons_layout.addWidget(refresh_db_btn)
        
        delete_all_btn = QPushButton("Delete All Customers")
        delete_all_btn.setStyleSheet("background-color: #d9534f; color: white;")
        delete_all_btn.setToolTip("WARNING: Delete all customers and their files")
        delete_all_btn.clicked.connect(self.delete_all_customers)
        db_buttons_layout.addWidget(delete_all_btn)
        
        customer_layout.addLayout(db_buttons_layout)

        # Customer info display
        self.customer_info_label = QLabel("No customer selected")
        self.customer_info_label.setStyleSheet("font-size: 10pt; color: #666;")
        customer_layout.addWidget(self.customer_info_label)

        layout.addWidget(customer_group)

        # File management area
        file_group = QGroupBox("File Management")
        file_layout = QGridLayout(file_group)

        # Rule file management
        file_layout.addWidget(QLabel("Rule File:"), 0, 0)
        self.rule_file_label = QLabel("No rule file loaded")
        self.rule_file_label.setStyleSheet("color: #888;")
        file_layout.addWidget(self.rule_file_label, 0, 1)

        import_rule_btn = QPushButton("Import Rule File")
        import_rule_btn.clicked.connect(self.import_rule_file)
        file_layout.addWidget(import_rule_btn, 0, 2)

        export_rule_btn = QPushButton("Export Rule File")
        export_rule_btn.clicked.connect(self.export_rule_file)
        file_layout.addWidget(export_rule_btn, 0, 3)

        # Alarm file management
        file_layout.addWidget(QLabel("Alarm File:"), 1, 0)
        self.alarm_file_label = QLabel("No alarm file loaded")
        self.alarm_file_label.setStyleSheet("color: #888;")
        file_layout.addWidget(self.alarm_file_label, 1, 1)

        import_alarm_btn = QPushButton("Import Alarm File")
        import_alarm_btn.clicked.connect(self.import_alarm_file)
        file_layout.addWidget(import_alarm_btn, 1, 2)

        export_alarm_btn = QPushButton("Export Alarm File")
        export_alarm_btn.clicked.connect(self.export_alarm_file)
        file_layout.addWidget(export_alarm_btn, 1, 3)

        layout.addWidget(file_group)

        # Validation area
        validation_group = QGroupBox("File Validation")
        validation_layout = QVBoxLayout(validation_group)

        validation_btn_layout = QHBoxLayout()
        validate_rule_btn = QPushButton("Validate Rule File")
        validate_rule_btn.clicked.connect(self.validate_current_rule_file)
        validation_btn_layout.addWidget(validate_rule_btn)

        validate_alarm_btn = QPushButton("Validate Alarm File")
        validate_alarm_btn.clicked.connect(self.validate_current_alarm_file)
        validation_btn_layout.addWidget(validate_alarm_btn)

        validate_relationship_btn = QPushButton("Validate Rule-Alarm Relationship")
        validate_relationship_btn.clicked.connect(self.validate_rule_alarm_relationship)
        validation_btn_layout.addWidget(validate_relationship_btn)

        validation_layout.addLayout(validation_btn_layout)

        self.validation_result_text = QTextEdit()
        self.validation_result_text.setMaximumHeight(120)
        self.validation_result_text.setReadOnly(True)
        validation_layout.addWidget(self.validation_result_text)

        layout.addWidget(validation_group)

        # Customer statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)

        self.total_customers_label = QLabel("Total Customers: 0")
        stats_layout.addWidget(self.total_customers_label, 0, 0)

        self.active_customers_label = QLabel("Active Customers: 0")
        stats_layout.addWidget(self.active_customers_label, 0, 1)

        layout.addWidget(stats_group)

        layout.addStretch()
        self.update_customer_list()
        return tab

    def create_alarm_management_tab(self) -> QWidget:
        """Create alarm management tab (eski ana panel)"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left_panel = self.create_left_panel()
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.property_editor = PropertyEditor(self)
        right_layout.addWidget(self.property_editor)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        return tab

    def create_rule_management_tab(self) -> QWidget:
        """Create rule management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("📋 Rule Management")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a90e2;")
        layout.addWidget(header)

        # Rule table
        rules_group = QGroupBox("Rules")
        rules_layout = QVBoxLayout(rules_group)

        # Controls
        controls_layout = QHBoxLayout()
        self.rule_search_input = QLineEdit()
        self.rule_search_input.setPlaceholderText("Search rules...")
        self.rule_search_input.textChanged.connect(self.filter_rules)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.rule_search_input)
        
        # Alarm status filter
        controls_layout.addWidget(QLabel("Filter:"))
        self.rule_alarm_filter = QComboBox()
        self.rule_alarm_filter.addItems(["All Rules", "With Alarms", "Without Alarms"])
        self.rule_alarm_filter.currentTextChanged.connect(self.filter_rules)
        controls_layout.addWidget(self.rule_alarm_filter)

        buttons_layout = QHBoxLayout()
        
        generate_alarms_btn = QPushButton("Generate Alarms from Selected Rules")
        generate_alarms_btn.clicked.connect(self.generate_alarms_from_selected_rules)
        buttons_layout.addWidget(generate_alarms_btn)
        
        export_rules_btn = QPushButton("Export Rules")
        export_rules_btn.clicked.connect(self.export_rule_file)
        buttons_layout.addWidget(export_rules_btn)
        
        controls_layout.addLayout(buttons_layout)

        rules_layout.addLayout(controls_layout)

        # Rule table
        self.create_rule_table()
        rules_layout.addWidget(self.rule_table_view)

        layout.addWidget(rules_group)

        # Rule details
        details_group = QGroupBox("Rule Details")
        details_layout = QVBoxLayout(details_group)

        # Buttons for rule operations
        buttons_layout = QHBoxLayout()
        
        export_all_rules_btn = QPushButton("Export All Rules")
        export_all_rules_btn.clicked.connect(self.export_rule_file)
        buttons_layout.addWidget(export_all_rules_btn)
        
        export_selected_rules_btn = QPushButton("Export Selected Rules")
        export_selected_rules_btn.clicked.connect(self.export_selected_rules)
        buttons_layout.addWidget(export_selected_rules_btn)
        
        details_layout.addLayout(buttons_layout)

        self.rule_details_text = QTextEdit()
        self.rule_details_text.setReadOnly(True)
        self.rule_details_text.setMaximumHeight(200)
        details_layout.addWidget(self.rule_details_text)

        layout.addWidget(details_group)

        return tab

    def create_mapping_tab(self) -> QWidget:
        """Create rule-alarm mapping tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("🔗 Rule-Alarm Mapping")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a90e2;")
        layout.addWidget(header)

        # Mapping analysis
        analysis_group = QGroupBox("Relationship Analysis")
        analysis_layout = QVBoxLayout(analysis_group)

        analyze_btn = QPushButton("Analyze Rule-Alarm Relationships")
        analyze_btn.clicked.connect(self.analyze_rule_alarm_relationships)
        analysis_layout.addWidget(analyze_btn)

        self.mapping_results_text = QTextEdit()
        self.mapping_results_text.setReadOnly(True)
        analysis_layout.addWidget(self.mapping_results_text)

        layout.addWidget(analysis_group)

        # Auto-generation
        generation_group = QGroupBox("Automatic Alarm Generation")
        generation_layout = QVBoxLayout(generation_group)

        gen_controls_layout = QHBoxLayout()
        self.auto_gen_severity_combo = QComboBox()
        self.auto_gen_severity_combo.addItems(["All", "Low (0-39)", "Medium (40-69)", "High (70-89)", "Critical (90-100)"])
        gen_controls_layout.addWidget(QLabel("Severity Filter:"))
        gen_controls_layout.addWidget(self.auto_gen_severity_combo)

        auto_gen_btn = QPushButton("Auto-Generate Alarms")
        auto_gen_btn.clicked.connect(self.auto_generate_alarms)
        gen_controls_layout.addWidget(auto_gen_btn)

        generation_layout.addLayout(gen_controls_layout)

        self.auto_gen_results_text = QTextEdit()
        self.auto_gen_results_text.setReadOnly(True)
        self.auto_gen_results_text.setMaximumHeight(150)
        generation_layout.addWidget(self.auto_gen_results_text)

        layout.addWidget(generation_group)

        return tab

    def create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Alarm Management")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)

        # Arama ve Yeni Alarm
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search alarms...")
        self.search_input.textChanged.connect(self.filter_alarms)
        search_layout.addWidget(self.search_input)

        add_button = QPushButton("New Alarm")
        add_button.clicked.connect(self.add_new_alarm)
        search_layout.addWidget(add_button)
        layout.addLayout(search_layout)

        # Filtreler
        filter_group = QGroupBox("Filters")
        flayout = QGridLayout(filter_group)
        flayout.setSpacing(6)

        flayout.addWidget(QLabel("Severity:"), 0, 0)
        self.severity_filter = QComboBox()
        self.severity_filter.addItems([
            "All", 
            SeverityLevel.LOW_LABEL, 
            SeverityLevel.MEDIUM_LABEL, 
            SeverityLevel.HIGH_LABEL, 
            SeverityLevel.CRITICAL_LABEL
        ])
        self.severity_filter.currentTextChanged.connect(self.filter_alarms)
        flayout.addWidget(self.severity_filter, 0, 1)

        flayout.addWidget(QLabel("Match Field:"), 1, 0)
        self.match_field_filter = QComboBox()
        self.match_field_filter.addItems(["All", "DSIDSigID", "NormID"])
        self.match_field_filter.currentTextChanged.connect(self.filter_alarms)
        flayout.addWidget(self.match_field_filter, 1, 1)

        flayout.addWidget(QLabel("Status:"), 2, 0)
        self.show_status_filter = QComboBox()
        self.show_status_filter.addItems(["All", "Enabled", "Disabled"])
        self.show_status_filter.currentTextChanged.connect(self.filter_alarms)
        flayout.addWidget(self.show_status_filter, 2, 1)
        
        flayout.addWidget(QLabel("Alarm Type:"), 3, 0)
        self.new_alarm_filter = QComboBox()
        self.new_alarm_filter.addItems(["All", "New Alarms Only", "Existing Alarms Only"])
        self.new_alarm_filter.currentTextChanged.connect(self.filter_alarms)
        flayout.addWidget(self.new_alarm_filter, 3, 1)

        layout.addWidget(filter_group)

        # Seçim bilgisi
        self.selection_label = QLabel("No alarms selected")
        layout.addWidget(self.selection_label)

        # Alarm tablosu
        self.create_alarm_table()
        layout.addWidget(self.alarm_table_view)

        # Hızlı işlemler
        quick_layout = QHBoxLayout()
        bulk_btn = QPushButton("Bulk Edit")
        bulk_btn.clicked.connect(self.bulk_edit_selected)
        quick_layout.addWidget(bulk_btn)

        enable_btn = QPushButton("Enable")
        enable_btn.clicked.connect(lambda: self.toggle_alarm_state(True))
        quick_layout.addWidget(enable_btn)

        disable_btn = QPushButton("Disable")
        disable_btn.clicked.connect(lambda: self.toggle_alarm_state(False))
        quick_layout.addWidget(disable_btn)

        # İkinci satır butonları
        export_layout = QHBoxLayout()
        
        export_all_btn = QPushButton("Export All Alarms")
        export_all_btn.clicked.connect(self.export_alarm_file)
        export_layout.addWidget(export_all_btn)
        
        export_selected_btn = QPushButton("Export Selected Alarms")
        export_selected_btn.clicked.connect(self.export_selected_alarms)
        export_layout.addWidget(export_selected_btn)

        layout.addLayout(quick_layout)
        layout.addLayout(export_layout)
        return panel

    def create_alarm_table(self):
        self.alarm_table_model = QStandardItemModel(0, 5)  # Column sayısını 5'e çıkardık (Description için)
        self.alarm_table_model.setHorizontalHeaderLabels(
            ["Name", "Severity", "Match Field", "Match Value", "Description"]
        )

        self.alarm_table_view = QTableView()
        self.alarm_table_view.setModel(self.alarm_table_model)
        self.alarm_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.alarm_table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.alarm_table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.alarm_table_view.setAlternatingRowColors(True)
        self.alarm_table_view.verticalHeader().setVisible(False)
        
        # Set row height from settings
        self.alarm_table_view.verticalHeader().setDefaultSectionSize(app_settings.get("table_row_height"))

        header = self.alarm_table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Severity
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Match Field
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Match Value
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Description

        self.alarm_table_view.setColumnWidth(1, 80)   # Severity
        self.alarm_table_view.setColumnWidth(2, 100)  # Match Field
        self.alarm_table_view.setColumnWidth(3, 180)  # Match Value

        self.alarm_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.alarm_table_view.customContextMenuRequested.connect(self.on_alarm_context_menu)
        self.alarm_table_view.doubleClicked.connect(self.edit_selected_alarm)

    def create_rule_table(self):
        """Create rule table for rule management tab"""
        self.rule_table_model = QStandardItemModel(0, 7)  # Added alarm status column
        self.rule_table_model.setHorizontalHeaderLabels([
            "Rule ID", "Message", "Severity", "SigID", "Alarm Status", "Description", "Triggers"
        ])

        self.rule_table_view = QTableView()
        self.rule_table_view.setModel(self.rule_table_model)
        self.rule_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.rule_table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.rule_table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.rule_table_view.setAlternatingRowColors(True)
        self.rule_table_view.verticalHeader().setVisible(False)
        
        # Set row height from settings
        self.rule_table_view.verticalHeader().setDefaultSectionSize(app_settings.get("table_row_height"))

        header = self.rule_table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Rule ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Message
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Severity
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # SigID
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Alarm Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Description
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Triggers

        self.rule_table_view.setColumnWidth(0, 120)  # Rule ID
        self.rule_table_view.setColumnWidth(2, 80)   # Severity
        self.rule_table_view.setColumnWidth(3, 100)  # SigID
        self.rule_table_view.setColumnWidth(4, 120)  # Alarm Status
        self.rule_table_view.setColumnWidth(6, 80)   # Triggers

        self.rule_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rule_table_view.customContextMenuRequested.connect(self.on_rule_context_menu)
        self.rule_table_view.selectionModel().currentRowChanged.connect(self.on_rule_selection_changed)
        self.rule_table_view.doubleClicked.connect(self.view_rule_details)

    def filter_alarms(self):
        """Alarm filtreleme - yeni alarm filtresi dahil"""
        search_text = self.search_input.text().lower()
        severity_filter = self.severity_filter.currentText()
        match_field_filter = self.match_field_filter.currentText()
        status_filter = self.show_status_filter.currentText()
        new_alarm_filter = getattr(self, 'new_alarm_filter', None)

        visible_count = 0
        total = self.alarm_table_model.rowCount()
        
        for row in range(total):
            name_item = self.alarm_table_model.item(row, 0)
            severity_item = self.alarm_table_model.item(row, 1)
            match_field_item = self.alarm_table_model.item(row, 2)
            match_value_item = self.alarm_table_model.item(row, 3)
            description_item = self.alarm_table_model.item(row, 4)  # Description item

            if not all([name_item, severity_item, match_field_item, match_value_item, description_item]):
                continue

            # Mevcut filtreler
            name_match = search_text in name_item.text().lower()
            value_match = search_text in match_value_item.text().lower()
            description_match = description_item and search_text in description_item.text().lower()
            text_match = name_match or value_match or description_match

            # Severity filtresi
            try:
                sev_val = int(severity_item.text())
                if severity_filter == SeverityLevel.LOW_LABEL:
                    sev_match = SeverityLevel.LOW_MIN <= sev_val <= SeverityLevel.LOW_MAX
                elif severity_filter == SeverityLevel.MEDIUM_LABEL:
                    sev_match = SeverityLevel.MEDIUM_MIN <= sev_val <= SeverityLevel.MEDIUM_MAX
                elif severity_filter == SeverityLevel.HIGH_LABEL:
                    sev_match = SeverityLevel.HIGH_MIN <= sev_val <= SeverityLevel.HIGH_MAX
                elif severity_filter == SeverityLevel.CRITICAL_LABEL:
                    sev_match = SeverityLevel.CRITICAL_MIN <= sev_val <= SeverityLevel.CRITICAL_MAX
                else:
                    sev_match = True
            except ValueError:
                sev_match = True

            # Diğer filtreler
            field_match = (match_field_filter == "All" or match_field_item.text() == match_field_filter)
            
            is_disabled = "(Disabled)" in name_item.text()
            if status_filter == "Enabled":
                status_match = not is_disabled
            elif status_filter == "Disabled":
                status_match = is_disabled
            else:
                status_match = True

            # Yeni alarm filtresi
            if new_alarm_filter and new_alarm_filter.currentText() != "All":
                alarm_name = name_item.text().replace(" (Disabled)", "")
                alarm_object = self.alarms[row]
                is_new = self.alarm_state_manager.is_new(alarm_object)
                if new_alarm_filter.currentText() == "New Alarms Only":
                    new_match = is_new
                else:  # Existing Alarms Only
                    new_match = not is_new
            else:
                new_match = True
            
            # Tüm filtreleri uygula
            is_visible = text_match and sev_match and field_match and status_match and new_match
            self.alarm_table_view.setRowHidden(row, not is_visible)
            
            if is_visible:
                visible_count += 1

        # Status bar güncelle
        if visible_count == total:
            self.status_bar.showMessage(f"Showing all {visible_count} alarms")
        else:
            self.status_bar.showMessage(f"Filtered: {visible_count} of {total} visible")

    def create_menu_bar(self):
        menu_bar = QMenuBar()
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("File")
        open_action = QAction("Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu("Edit")
        undo_action = self.undo_stack.createUndoAction(self, "Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        redo_action = self.undo_stack.createRedoAction(self, "Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        validate_action = QAction("Validate Alarms", self)
        validate_action.triggered.connect(self.validate_current_file)
        tools_menu.addAction(validate_action)
        
        report_action = QAction("Generate Change Report", self)
        report_action.triggered.connect(self.generate_change_report)
        tools_menu.addAction(report_action)
        
        health_report_action = QAction("Generate Health Report", self)
        health_report_action.triggered.connect(self.generate_health_report)
        tools_menu.addAction(health_report_action)
        
        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        app_settings_action = QAction("Application Settings", self)
        app_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(app_settings_action)

        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        toolbar.addSeparator()
        bulk_action = QAction("Bulk Edit", self)
        bulk_action.triggered.connect(self.bulk_edit_selected)
        toolbar.addAction(bulk_action)

        report_action = QAction("Generate Report", self)
        report_action.triggered.connect(self.generate_change_report)
        toolbar.addAction(report_action)
        
        toolbar.addSeparator()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

    def connect_signals(self):
        self.alarm_table_view.selectionModel().currentRowChanged.connect(
            self.on_alarm_selection_changed
        )
        self.alarm_table_view.selectionModel().selectionChanged.connect(
            self.update_selection_label
        )
        self.undo_stack.indexChanged.connect(self.on_undo_stack_changed)

    def update_ui_state(self):
        has_file = self.current_file is not None
        has_selection = self.current_alarm is not None

        if has_file:
            self.setWindowTitle(f"🔧 Alarm Editor - {os.path.basename(self.current_file)}")
        else:
            self.setWindowTitle("🔧 Alarm Editor")

        self.property_editor.setEnabled(has_selection)

    def update_selection_label(self):
        selected = self.alarm_table_view.selectionModel().selectedRows()
        count = len(selected)
        if count == 0:
            self.selection_label.setText("No alarms selected")
        elif count == 1:
            self.selection_label.setText("1 alarm selected")
        else:
            self.selection_label.setText(f"{count} alarms selected")

    def open_file(self):
        if self.has_unsaved_changes() and not self.confirm_discard_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Alarm File", "", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return

        try:
            logger.info(f"Opening file: {file_path}")
            # Use secure XML parser
            self.original_tree = SecureXMLParser.parse_file(file_path)
            root = self.original_tree.getroot()
            if root.tag != "alarms":
                raise XMLParsingError("Root element must be <alarms>")

            self.alarms.clear()
            self.alarm_table_model.setRowCount(0)
            self.current_alarm = None

            for alarm_elem in root.findall("alarm"):
                alarm_model = AlarmModel(self)
                alarm_model.from_element(alarm_elem)
                self.alarms.append(alarm_model)

            self.current_file = file_path
            self.update_alarm_table()
            if self.alarms:
                self.alarm_table_view.selectRow(0)
            self.status_bar.showMessage(f"Loaded {len(self.alarms)} alarms")
        except XMLSecurityError as e:
            logger.error(f"Security error in file: {e}")
            QMessageBox.critical(self, "Security Error", f"File contains security risks:\n{e}")
        except XMLParsingError as e:
            logger.error(f"XML parsing error: {e}")
            QMessageBox.critical(self, "Invalid XML", f"Failed to parse XML file:\n{e}")
        except FileOperationError as e:
            logger.error(f"File operation error: {e}")
            QMessageBox.critical(self, "File Error", f"Failed to open file:\n{e}")
        except Exception as e:
            logger.error(f"Unexpected error opening file: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{e}")

    def save_file(self) -> bool:
        # Duplicate name kontrolü
        duplicate_errors = self.validator.check_for_duplicate_names(self.alarms)
        if duplicate_errors:
            QMessageBox.critical(
                self,
                "Duplicate Alarm Names",
                "Cannot save file due to duplicate alarm names:\n\n" + 
                "\n".join(duplicate_errors[:5]) +
                ("\n..." if len(duplicate_errors) > 5 else "")
            )
            return False
        
        # Auto-validate kontrolü
        if app_settings.get("auto_validate_on_save"):
            all_errors = []
            for i, alarm in enumerate(self.alarms):
                errors = self.validator.validate_alarm(alarm)
                if errors:
                    all_errors.append(f"Alarm '{alarm.name}':\n  " + "\n  ".join(errors[:3]))
            
            if all_errors:
                msg = "Validation errors found:\n\n" + "\n\n".join(all_errors[:5])
                if len(all_errors) > 5:
                    msg += f"\n\n... and {len(all_errors) - 5} more alarms with errors"
                
                reply = QMessageBox.warning(
                    self,
                    "Validation Errors",
                    msg + "\n\nDo you want to save anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return False
        
        # Mevcut save kodu
        if not self.current_file:
            return self.save_file_as()
        return self._write_to_path(self.current_file)

    def save_file_as(self) -> bool:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Alarm File As", "", "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            return self._write_to_path(file_path)
        return False

    def _write_to_path(self, path: str) -> bool:
        try:
            # Build new XML structure without deep copy
            root = ET.Element("alarms")
            
            # Add alarms to the new root
            for alarm in self.alarms:
                try:
                    alarm_elem = alarm.to_element()
                    root.append(alarm_elem)
                except Exception as e:
                    logger.error(f"Error converting alarm {alarm.name} to XML: {e}")
                    raise ValueError(f"Failed to convert alarm '{alarm.name}' to XML: {e}")
            
            # Create tree and write to file
            tree = ET.ElementTree(root)

            # Write to temporary file first for safety
            temp_path = path + ".tmp"
            tree.write(temp_path, encoding="utf-8", xml_declaration=True)
            
            # Replace original file
            import shutil
            shutil.move(temp_path, path)
            
            # Update internal state
            self.current_file = path
            self.original_tree = tree
            
            # Mark all alarms as saved
            for alarm in self.alarms:
                alarm.modified = False
            
            # Clear new alarms tracking
            self.alarm_state_manager.clear_new_alarms()
                
            self.status_bar.showMessage(f"Saved {len(self.alarms)} alarms to {os.path.basename(path)}")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied saving file: {e}")
            QMessageBox.critical(self, "Permission Denied", f"Cannot write to file:\n{path}")
            return False
        except OSError as e:
            logger.error(f"OS error saving file: {e}")
            QMessageBox.critical(self, "File Error", f"Failed to save file:\n{e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving file: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
            return False

    def validate_current_file(self):
        if not self.alarms:
            QMessageBox.information(self, "Info", "No alarms to validate.")
            return

        errors: List[str] = []
        for idx, alarm in enumerate(self.alarms):
            alarm_errors = self.validator.validate_alarm(alarm)
            for err in alarm_errors:
                errors.append(f"Alarm #{idx+1} ({alarm.name}): {err}")

        if not errors:
            QMessageBox.information(self, "Valid", "All alarms are valid.")
        else:
            msg = "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n...and {len(errors)-10} more errors"
            QMessageBox.warning(self, "Validation Errors", msg)

    def has_unsaved_changes(self) -> bool:
        return any(alarm.modified for alarm in self.alarms)

    def confirm_discard_changes(self) -> bool:
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "There are unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self.save_file()
        if reply == QMessageBox.StandardButton.Discard:
            return True
        return False

    def update_alarm_table(self):
        """Alarm tablosunu güncelle - yeni alarmları renklendir"""
        self.alarm_table_model.setRowCount(0)
        
        for alarm in self.alarms:
            name_item = QStandardItem(alarm.name)
            sev = str(alarm.get_field("alarmData", "severity") or "0")
            severity_item = QStandardItem(sev)
            match_field_item = QStandardItem(
                str(alarm.get_field("conditionData", "matchField") or "")
            )
            match_value_item = QStandardItem(
                str(alarm.get_field("conditionData", "matchValue") or "")
            )
            # Description alanını ekle
            description_item = QStandardItem(
                str(alarm.get_field("alarmData", "note") or "")
            )

            # Yeni alarm kontrolü ve renklendirme
            if self.alarm_state_manager.is_new(alarm):
                # Yeni alarmları açık yeşil arka plan ile işaretle
                new_alarm_color = QColor(144, 238, 144, 80)  # Light green with transparency
                for item in [name_item, severity_item, match_field_item, match_value_item, description_item]:
                    item.setBackground(QBrush(new_alarm_color))
                    item.setToolTip("⚡ Newly created alarm")
            
            # Color code by severity using config
            try:
                severity = int(sev)
                color_tuple = SeverityLevel.get_color(severity)
                color = QColor(*color_tuple)
                severity_item.setForeground(QBrush(color))
            except (ValueError, TypeError):
                # Use gray for invalid severity values
                color = QColor(128, 128, 128)
                severity_item.setForeground(QBrush(color))
            
            # Disabled alarm kontrolü
            enabled = alarm.get_field("alarmData", "enabled")
            if enabled == "F":
                for itm in (name_item, severity_item, match_field_item, match_value_item, description_item):
                    itm.setForeground(QBrush(QColor(100, 100, 100)))
                name_item.setText(f"{alarm.name} (Disabled)")

            self.alarm_table_model.appendRow(
                [name_item, severity_item, match_field_item, match_value_item, description_item]
            )

        self.filter_alarms()

    def on_alarm_selection_changed(self, current: QModelIndex, previous: QModelIndex):
        if not current.isValid():
            self.current_alarm = None
            self.property_editor.set_current_alarm(None)
            return

        row = current.row()
        if 0 <= row < len(self.alarms):
            self.current_alarm = self.alarms[row]
            self.property_editor.set_current_alarm(self.current_alarm)
        else:
            self.current_alarm = None
            self.property_editor.set_current_alarm(None)
        self.update_ui_state()

    def on_undo_stack_changed(self):
        self.update_ui_state()

    def show_about(self):
        QMessageBox.about(
            self,
            "About Alarm Editor",
            "<h3>McAfee SIEM Alarm Editor</h3>"
            "<p>Version 1.5.1</p>"
            "<p>A tool for editing and managing McAfee SIEM alarm configurations.</p>"
            "<p>This application allows you to create, edit, and validate alarm configurations.</p>"
        )
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply settings that need immediate effect
            if app_settings.get("dark_theme"):
                self.setStyleSheet(DARK_GRAY_STYLESHEET)
            else:
                self.setStyleSheet("")  # Use default style
                
            # Resize window if needed
            width = app_settings.get("window_width")
            height = app_settings.get("window_height")
            self.resize(width, height)
            
            # Update UI components based on settings
            self.alarm_table_view.verticalHeader().setDefaultSectionSize(app_settings.get("table_row_height"))
            self.rule_table_view.verticalHeader().setDefaultSectionSize(app_settings.get("table_row_height"))
            
            # If any alarms are loaded, refresh their UI
            self.update_alarm_table()
            self.update_rule_table()
            
            # Notify user
            self.status_bar.showMessage("Settings updated successfully", 3000)

    def add_new_alarm(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Alarm")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        layout.addRow("Name:", name_edit)

        version_edit = QLineEdit()
        version_edit.setText(DEFAULT_MIN_VERSION)
        layout.addRow("Min Version:", version_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted and name_edit.text().strip():
            new_alarm = AlarmModel(self)
            new_alarm.name = name_edit.text().strip()
            new_alarm.min_version = version_edit.text().strip()
            # Varsayılan değerleri ayarla
            new_alarm.set_field("alarmData", "filters", "")
            new_alarm.set_field("alarmData", "note", "")
            new_alarm.set_field("alarmData", "notificationType", "0")
            new_alarm.set_field("alarmData", "severity", "50")
            new_alarm.set_field("alarmData", "escEnabled", "F")
            new_alarm.set_field("alarmData", "escSeverity", "50")
            new_alarm.set_field("alarmData", "escMin", "0")
            new_alarm.set_field("alarmData", "summaryTemplate", "")
            new_alarm.set_field("alarmData", "assignee", DEFAULT_ASSIGNEE_ID)
            new_alarm.set_field("alarmData", "assigneeType", "0")
            new_alarm.set_field("alarmData", "escAssignee", DEFAULT_ESC_ASSIGNEE_ID)
            new_alarm.set_field("alarmData", "escAssigneeType", "0")
            new_alarm.set_field("alarmData", "enabled", "T")
            new_alarm.set_field("alarmData", "deviceIDs", "")

            new_alarm.set_field("conditionData", "conditionType", "0")
            new_alarm.set_field("conditionData", "queryID", "0")
            new_alarm.set_field("conditionData", "alertRateMin", "0")
            new_alarm.set_field("conditionData", "alertRateCount", "0")
            new_alarm.set_field("conditionData", "pctAbove", "0")
            new_alarm.set_field("conditionData", "pctBelow", "0")
            new_alarm.set_field("conditionData", "offsetMin", "0")
            new_alarm.set_field("conditionData", "timeFilter", "")
            new_alarm.set_field("conditionData", "xMin", "1")
            new_alarm.set_field("conditionData", "useWatchlist", "F")
            new_alarm.set_field("conditionData", "matchField", "DSIDSigID")
            new_alarm.set_field("conditionData", "matchValue", "")
            new_alarm.set_field("conditionData", "matchNot", "F")

            # Default action
            new_alarm.data["actions"]["actionData"] = [
                {"actionType": "0", "actionProcess": "1", "actionAttributes": {}}
            ]

            # Undo command kullan
            command = AddAlarmCommand(self, new_alarm)
            self.undo_stack.push(command)

            # Alarmı ekle ve işaretle
            self.alarms.append(new_alarm)
            self.alarm_state_manager.mark_as_new(new_alarm)

            # UI güncelle
            self.update_alarm_table()
            self.alarm_table_view.selectRow(len(self.alarms) - 1)
            self.status_bar.showMessage(f"Created new alarm: {new_alarm.name}")

    def edit_selected_alarm(self):
        idx = self.alarm_table_view.currentIndex().row()
        if idx >= 0:
            self.alarm_table_view.selectRow(idx)

    def duplicate_selected_alarm(self):
        rows = {i.row() for i in self.alarm_table_view.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Info", "Select at least one alarm to duplicate.")
            return

        for row in sorted(rows):
            if row < len(self.alarms):
                orig = self.alarms[row]
                # Create new AlarmModel instead of deepcopy to avoid weakref issues
                duplicate = AlarmModel(self)
                duplicate.name = f"{orig.name}_copy"
                duplicate.min_version = orig.min_version
                duplicate.data = copy.deepcopy(orig.data)
                duplicate.modified = True
                self.alarms.append(duplicate)

        self.update_alarm_table()
        self.status_bar.showMessage(f"Duplicated {len(rows)} alarms")

    def delete_selected_alarm(self):
        rows = {i.row() for i in self.alarm_table_view.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Info", "Select at least one alarm to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Alarms",
            f"Delete {len(rows)} selected alarm(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            command = DeleteAlarmCommand(self, rows)
            self.undo_stack.push(command)

    def toggle_alarm_state(self, enable: bool):
        rows = {i.row() for i in self.alarm_table_view.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Info", "Select at least one alarm.")
            return

        for row in rows:
            if row < len(self.alarms):
                alarm = self.alarms[row]
                alarm.set_field("alarmData", "enabled", "T" if enable else "F")

        self.update_alarm_table()
        if self.current_alarm:
            self.property_editor.update_form()
        state = "enabled" if enable else "disabled"
        self.status_bar.showMessage(f"{len(rows)} alarms {state}")

    def bulk_edit_selected(self):
        rows = {i.row() for i in self.alarm_table_view.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Bulk Edit", "Select at least one alarm.")
            return

        # Create enhanced bulk edit dialog
        dialog = BulkEditDialog(self, rows, self.alarms)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            changes = dialog.get_changes()
            if changes:
                self.apply_bulk_changes(changes)
                self.update_alarm_table()
                self.status_bar.showMessage(f"Bulk edited {len(changes)} alarms")
    
    def apply_bulk_changes(self, changes: Dict[int, Dict]):
        """Apply bulk changes with validation"""
        success_count = 0
        error_count = 0
        validation_warnings = []
        changed_alarms = []
        
        for row, change in changes.items():
            try:
                alarm = change["alarm"]
                section = change["section"]
                field = change["field"]
                new_value = change["new_value"]
                old_value = change["old_value"]
                
                # Apply change
                alarm.set_field(section, field, new_value)
                
                # Validate after change
                validation_errors = self.validator.validate_alarm(alarm)
                if validation_errors:
                    logger.warning(f"Validation warnings for {alarm.name}: {validation_errors}")
                    for error in validation_errors:
                        validation_warnings.append(f"{alarm.name}: {error}")
                
                success_count += 1
                changed_alarms.append({
                    "name": alarm.name,
                    "field": field,
                    "old": old_value,
                    "new": new_value
                })
                
            except Exception as e:
                logger.error(f"Error applying bulk change: {str(e)}")
                error_count += 1
        
        # Update property editor if current alarm was changed
        if self.current_alarm and any(
            change["alarm"] == self.current_alarm for change in changes.values()
        ):
            self.property_editor.update_form()
        
        # Validate XML structure of the entire alarm set
        xml_valid = True
        try:
            # Create temporary XML to validate structure
            root = ET.Element("alarms")
            for alarm in self.alarms:
                root.append(alarm.to_element())
            # Basic XML validation passed
        except Exception as e:
            xml_valid = False
            logger.error(f"XML structure validation failed: {str(e)}")
        
        # Show detailed summary
        summary_msg = f"Bulk Edit Summary:\n\n"
        summary_msg += f"✓ Successfully updated: {success_count} alarms\n"
        if error_count > 0:
            summary_msg += f"✗ Failed to update: {error_count} alarms\n"
        summary_msg += f"\nXML Structure: {'✓ Valid' if xml_valid else '✗ Invalid'}\n"
        
        if changed_alarms:
            summary_msg += "\nChanges Applied:\n"
            for change in changed_alarms[:5]:
                summary_msg += f"• {change['name']}: {change['field']} changed from '{change['old']}' to '{change['new']}'\n"
            if len(changed_alarms) > 5:
                summary_msg += f"... and {len(changed_alarms) - 5} more changes\n"
        
        if validation_warnings:
            summary_msg += "\nValidation Warnings:\n"
            for warning in validation_warnings[:5]:
                summary_msg += f"⚠ {warning}\n"
            if len(validation_warnings) > 5:
                summary_msg += f"... and {len(validation_warnings) - 5} more warnings\n"
        
        if error_count > 0 or validation_warnings or not xml_valid:
            QMessageBox.warning(
                self,
                "Bulk Edit Completed with Issues",
                summary_msg
            )
        else:
            QMessageBox.information(
                self,
                "Bulk Edit Completed Successfully",
                summary_msg
            )

    def generate_change_report(self):
        if not self.alarms:
            QMessageBox.information(self, "Info", "No alarms to include in report.")
            return

        report_data = []
        for alarm in self.alarms:
            if alarm.change_log:
                report_data.append({
                    "name": alarm.name,
                    "changes": alarm.export_change_log()
                })

        if not report_data:
            QMessageBox.information(
                self, "Info", "No changes to report. Make and save changes first."
            )
            return

        report_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "", "Text Files (*.txt);;All Files (*)"
        )
        if not report_path:
            return

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("ALARM CHANGE REPORT\n")
                f.write("=================\n\n")
                f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Alarms with changes: {len(report_data)}\n\n")

                for alarm_data in report_data:
                    f.write(f"ALARM: {alarm_data['name']}\n")
                    f.write("-" * (len(alarm_data['name']) + 7) + "\n")
                    
                    for change in alarm_data["changes"]:
                        f.write(f"• {change['timestamp']}: ")
                        f.write(f"Changed {change['section']}.{change['field']} ")
                        f.write(f"from '{change['old_value']}' to '{change['new_value']}'\n")
                        if change.get("note"):
                            f.write(f"  Note: {change['note']}\n")
                    f.write("\n")

            QMessageBox.information(
                self, "Success", f"Report saved to {report_path}"
            )
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save report: {e}")

    def generate_health_report(self):
        """Generate a comprehensive health report about the current system state"""
        # Sağlık raporu jeneratörünü oluştur
        try:
            from health_report import HealthReportGenerator
            
            # Rapor jeneratörünü başlat ve bağımlılıkları ayarla
            generator = HealthReportGenerator()
            generator.set_dependencies(
                customer_manager=self.customer_manager,
                validator=self.validator,
                rule_parser=self.rule_parser
            )
            
            # Rapor oluştur
            current_customer = self.current_customer
            report_data = generator.generate_report(
                alarms=self.alarms,
                rules=self.current_rules,
                customer=current_customer
            )
            
            # Kaydedilecek dosya yolunu al
            report_path, _ = QFileDialog.getSaveFileName(
                self, "Save Health Report", "", "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
            )
            if not report_path:
                return
                
            # Dosya uzantısına göre JSON veya düz metin olarak kaydet
            if report_path.lower().endswith(".json"):
                success = generator.save_report_to_file(report_path)
                if success:
                    QMessageBox.information(
                        self, "Success", f"Health report saved to {report_path}"
                    )
                else:
                    QMessageBox.critical(
                        self, "Error", "Failed to save health report"
                    )
            else:
                # Düz metin raporu oluştur
                text_report = generator.generate_text_report()
                try:
                    with open(report_path, "w", encoding="utf-8") as f:
                        f.write(text_report)
                    QMessageBox.information(
                        self, "Success", f"Health report saved to {report_path}"
                    )
                except Exception as e:
                    logger.error(f"Error saving text report: {e}")
                    QMessageBox.critical(
                        self, "Error", f"Failed to save report: {e}"
                    )
            
        except ImportError as e:
            logger.error(f"Health report module not found: {e}")
            msg = (
                "Health report module not found. Make sure health_report.py is in the AlarmEditor directory.\n\n"
                "The health report feature requires:\n"
                "- health_report.py in the AlarmEditor directory\n"
                "- restart the application after adding the file\n\n"
                f"Error details: {e}"
            )
            QMessageBox.critical(self, "Error", msg)
        except Exception as e:
            logger.error(f"Error generating health report: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error", f"Failed to generate health report: {e}"
            )
            
    def update_customer_list(self):
        """Update customer combo box"""
        # Temporarily block signals to prevent triggering during population
        self.customer_combo.blockSignals(True)
        
        self.customer_combo.clear()
        customers = self.customer_manager.get_all_customers()
        
        if not customers:
            self.customer_combo.addItem("No customers available")
            self.update_customer_statistics()
            self.customer_combo.blockSignals(False)
            return
        
        for customer in customers:
            display_text = f"{customer.name} ({customer.id})"
            if not customer.active:
                display_text += " [INACTIVE]"
            self.customer_combo.addItem(display_text, customer.id)
        
        self.update_customer_statistics()
        
        # Re-enable signals
        self.customer_combo.blockSignals(False)

    def update_customer_statistics(self):
        """Update customer statistics display"""
        customers = self.customer_manager.get_all_customers()
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.active])
        
        self.total_customers_label.setText(f"Total Customers: {total_customers}")
        self.active_customers_label.setText(f"Active Customers: {active_customers}")

    def on_customer_selected(self, text: str):
        """Düzeltilmiş müşteri seçim handler'ı"""
        logger.info(f"Customer selected: {text}")
        
        # Önceki müşteri durumunu temizle
        self.undo_stack.clear()
        self.alarm_state_manager.clear_new_alarms()
        
        # Filtreleri sıfırla
        self.search_input.clear()
        self.severity_filter.setCurrentIndex(0)
        self.match_field_filter.setCurrentIndex(0)
        self.show_status_filter.setCurrentIndex(0)
        if hasattr(self, 'new_alarm_filter'):
            self.new_alarm_filter.setCurrentIndex(0)
        
        # Rule filtreleri sıfırla
        if hasattr(self, 'rule_search_input'):
            self.rule_search_input.clear()
        if hasattr(self, 'rule_alarm_filter'):
            self.rule_alarm_filter.setCurrentIndex(0)
        
        # Validation sonuçlarını temizle
        if hasattr(self, 'validation_result_text'):
            self.validation_result_text.clear()
        
        # Combo box boş ise veya 'No customers available' seçili ise
        if not text or text == "No customers available":
            self.current_customer = None
            self.customer_info_label.setText("No customer selected")
            self.rule_file_label.setText("No rule file loaded")
            self.alarm_file_label.setText("No alarm file loaded")
            self.current_rules = []
            self.alarms = []
            self.alarm_table_model.setRowCount(0)  # Tabloyu temizle
            if hasattr(self, 'rule_table_model'):
                self.rule_table_model.setRowCount(0)
            return
        
        try:
            # Extract customer ID
            if "(" in text and ")" in text:
                customer_id = text.split("(")[1].split(")")[0]
                logger.info(f"Extracted customer ID: {customer_id}")
                
                # Müşteri ID'sine göre müşteriyi al
                customer = self.customer_manager.get_customer(customer_id)
                
                if customer:
                    # Seçili müşteriyi ayarla
                    self.current_customer = customer
                    logger.info(f"Customer found and set: {self.current_customer.name}")
                    
                    # Müşteri bilgilerini güncelle
                    self.update_customer_info_display()
                    
                    # Müşteriye ait dosyaları yükle
                    self.load_customer_files()
                    
                    # Durum çubuğunu güncelle
                    self.status_bar.showMessage(f"Loaded customer: {self.current_customer.name}")
                else:
                    logger.error(f"Customer not found for ID: {customer_id}")
                    QMessageBox.warning(self, "Error", f"Customer not found: {customer_id}")
                    self.current_customer = None
            else:
                logger.error(f"Invalid customer format in combobox: {text}")
                QMessageBox.warning(self, "Error", f"Invalid customer format: {text}")
                self.current_customer = None
        except Exception as e:
            logger.error(f"Error selecting customer: {e}")
            QMessageBox.warning(self, "Error", f"Error selecting customer: {str(e)}")
            self.current_customer = None

    def update_customer_info_display(self):
        """Update customer info display"""
        if not self.current_customer:
            return
        
        info_text = f"Customer: {self.current_customer.name}\n"
        info_text += f"ID: {self.current_customer.id}\n"
        info_text += f"Description: {self.current_customer.description}\n"
        info_text += f"Created: {self.current_customer.created_date[:10]}"
        if self.current_customer.last_modified:
            info_text += f"\nLast Modified: {self.current_customer.last_modified[:10]}"
        
        self.customer_info_label.setText(info_text)

    def load_customer_files(self):
        """Load customer's rule and alarm files"""
        if not self.current_customer:
            self.status_bar.showMessage("No customer selected")
            return
        
        # Get current customer files
        logger.info(f"Loading files for customer: {self.current_customer.name}")
        files = self.customer_manager.get_customer_files(self.current_customer.id)
        
        rule_file = files.get("rule_file")
        alarm_file = files.get("alarm_file")
        
        # Display file paths in UI
        self.rule_file_label.setText(os.path.basename(rule_file) if rule_file else "No rule file")
        self.alarm_file_label.setText(os.path.basename(alarm_file) if alarm_file else "No alarm file")
        
        # Load rule file if available
        if rule_file and os.path.exists(rule_file):
            logger.info(f"Rule file path: {rule_file}")
            self.load_rule_file(rule_file)
        else:
            logger.warning(f"Rule file not found or path is empty: {rule_file}")
            self.rules = []
            self.current_rules = []
            self.rule_table_model.clear()
            # Kural tablosunu boş olarak güncelle
            self.update_rule_table()
            
        # Load alarm file if available
        if alarm_file and os.path.exists(alarm_file):
            logger.info(f"Alarm file path: {alarm_file}")
            self.load_alarm_file(alarm_file)
        else:
            logger.warning(f"Alarm file not found or path is empty: {alarm_file}")
            self.alarms = []
            self.alarm_table_model.clear()
        
        # Check if we need to create or update database entries
        try:
            customer_db_dir = os.path.join(self.customer_manager.customers_dir, self.current_customer.id, "db")
            rules_db_file = os.path.join(customer_db_dir, "rules.json")
            alarms_db_file = os.path.join(customer_db_dir, "alarms.json")
            
            # If database files don't exist but XML files do, create the database entries
            if ((not os.path.exists(rules_db_file) or not os.path.exists(alarms_db_file)) and 
                (rule_file or alarm_file)):
                try:
                    # Create database directory if it doesn't exist
                    if not os.path.exists(customer_db_dir):
                        os.makedirs(customer_db_dir)
                        logger.info(f"Created database directory for customer: {self.current_customer.name}")
                    
                    # Parse files to database silently
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    success = self.customer_manager.parse_rule_alarm_files_to_db(self.current_customer.id)
                    QApplication.restoreOverrideCursor()
                    
                    if success:
                        logger.info(f"Created/updated database entries for customer: {self.current_customer.name}")
                    else:
                        logger.error(f"Failed to create database entries for customer: {self.current_customer.name}")
                except Exception as e:
                    QApplication.restoreOverrideCursor()
                    logger.error(f"Error creating database entries: {e}")
        except Exception as e:
            logger.error(f"Error checking database entries: {e}")
        
        # Update UI after loading files
        logger.info("Updating tables after loading files")
        self.update_alarm_table()
        
        # Tablo güncellemelerini zorla
        self.rule_table_model.setRowCount(0)
        self.update_rule_table()
        
        self.update_customer_statistics()
        
        # Update customer UI to reflect modification state
        self.update_file_modification_status()
        
    def update_file_modification_status(self):
        """Update UI to reflect modification status of files"""
        if not self.current_customer:
            return
            
        customer = self.customer_manager.get_customer(self.current_customer.id)
        if not customer:
            return
            
        # Update rule file status
        if customer.rule_modified:
            self.rule_file_label.setText(f"{self.rule_file_label.text()} [Modified]")
            self.rule_file_label.setStyleSheet("color: #e67e22;")  # Orange color
            
            # Enable export button for rule file
            if hasattr(self, 'export_rule_btn'):
                self.export_rule_btn.setEnabled(True)
        else:
            self.rule_file_label.setStyleSheet("color: #888;")
            
        # Update alarm file status
        if customer.alarm_modified:
            self.alarm_file_label.setText(f"{self.alarm_file_label.text()} [Modified]")
            self.alarm_file_label.setStyleSheet("color: #e67e22;")  # Orange color
            
            # Enable export button for alarm file
            if hasattr(self, 'export_alarm_btn'):
                self.export_alarm_btn.setEnabled(True)
        else:
            self.alarm_file_label.setStyleSheet("color: #888;")
            
    def mark_current_rule_file_modified(self):
        """Mark current rule file as modified"""
        if not self.current_customer:
            return
            
        self.customer_manager.mark_rule_file_modified(self.current_customer.id)
        self.update_file_modification_status()
        
    def mark_current_alarm_file_modified(self):
        """Mark current alarm file as modified"""
        if not self.current_customer:
            return
            
        self.customer_manager.mark_alarm_file_modified(self.current_customer.id)
        self.update_file_modification_status()

    def create_new_customer(self):
        """Create a new customer"""
        dialog = QDialog(self)
        dialog.setWindowTitle("New Customer")
        dialog.setMinimumWidth(400)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(80)

        layout.addRow("Customer Name:", name_edit)
        layout.addRow("Description:", description_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Warning", "Customer name is required!")
                return
            
            description = description_edit.toPlainText().strip()
            customer = self.customer_manager.add_customer(name, description)
            
            # Müşteriyi doğrudan ayarla
            self.current_customer = customer
            
            # Müşteri listesini güncelle
            self.update_customer_list()
            
            # Listedeki yeni müşteriyi seç
            for i in range(self.customer_combo.count()):
                if customer.id in self.customer_combo.itemText(i):
                    self.customer_combo.setCurrentIndex(i)
                    break
                    
            # Müşteri bilgilerini göster
            self.update_customer_info_display()
            
            # Create customer directory structure
            customer_dir = os.path.join(self.customer_manager.customers_dir, customer.id)
            if not os.path.exists(customer_dir):
                os.makedirs(customer_dir)
            
            # Create database directory
            db_dir = os.path.join(customer_dir, "db")
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Müşteri oluşturulduğunda bilgilerini güncelle ve yükle
            self.update_customer_info_display()
            self.load_customer_files()
            
            QMessageBox.information(self, "Success", f"Customer '{name}' created successfully!")

    def edit_current_customer(self):
        """Edit current customer"""
        if not self.current_customer:
            QMessageBox.information(self, "Info", "No customer selected.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Customer")
        dialog.setMinimumWidth(400)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(self.current_customer.name)
        description_edit = QTextEdit()
        description_edit.setPlainText(self.current_customer.description)
        description_edit.setMaximumHeight(80)
        
        active_check = QCheckBox()
        active_check.setChecked(self.current_customer.active)

        layout.addRow("Customer Name:", name_edit)
        layout.addRow("Description:", description_edit)
        layout.addRow("Active:", active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Warning", "Customer name is required!")
                return
            
            self.customer_manager.update_customer(
                self.current_customer.id,
                name=name,
                description=description_edit.toPlainText().strip(),
                active=active_check.isChecked()
            )
            
            self.current_customer = self.customer_manager.get_customer(self.current_customer.id)
            self.update_customer_list()
            self.update_customer_info_display()
            
            QMessageBox.information(self, "Success", "Customer updated successfully!")

    def delete_current_customer(self):
        """Delete current customer"""
        if not self.current_customer:
            QMessageBox.information(self, "Info", "No customer selected.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Customer",
            f"Are you sure you want to delete customer '{self.current_customer.name}'?\n"
            "This will also delete all associated files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            customer_name = self.current_customer.name
            self.customer_manager.delete_customer(self.current_customer.id)
            self.current_customer = None
            self.update_customer_list()
            
            # Clear tables
            self.alarms = []
            self.current_rules = []
            self.update_alarm_table()
            self.update_rule_table()
            
            self.status_bar.showMessage(f"Customer '{customer_name}' deleted successfully")
    
    def refresh_database(self):
        """Refresh database by rescanning customer directories"""
        reply = QMessageBox.question(
            self,
            "Refresh Database",
            "This will rescan all customer directories and update the database.\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Show busy cursor
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            # Refresh database
            success = self.customer_manager.refresh_db()
            
            # Restore cursor
            QApplication.restoreOverrideCursor()
            
            if success:
                # Save current customer ID to reselect after refresh
                current_customer_id = self.current_customer.id if self.current_customer else None
                
                # Store current customer object temporarily
                temp_customer = self.current_customer
                self.current_customer = None
                
                # Update customer list
                self.update_customer_list()
                self.update_customer_statistics()
                
                # Reselect current customer if possible
                if current_customer_id:
                    found = False
                    for i in range(self.customer_combo.count()):
                        if current_customer_id in self.customer_combo.itemText(i):
                            self.customer_combo.setCurrentIndex(i)
                            found = True
                            break
                            
                    # If customer was not found in refreshed list, clear current customer
                    if not found:
                        self.current_customer = None
                        self.alarms = []
                        self.current_rules = []
                        self.update_alarm_table()
                        self.update_rule_table()
                else:
                    # Restore current customer if it was set before
                    self.current_customer = temp_customer
                
                QMessageBox.information(
                    self,
                    "Database Refreshed",
                    f"Database refreshed successfully.\nFound {len(self.customer_manager.get_all_customers())} customers."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to refresh database. Check logs for details."
                )
    
    def delete_all_customers(self):
        """Delete all customers and their files"""
        reply = QMessageBox.warning(
            self,
            "Delete All Customers",
            "WARNING: This will delete ALL customers and their associated files!\n"
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Double-check with a confirm dialog
            confirm_text = "DELETE ALL"
            text, ok = QInputDialog.getText(
                self,
                "Confirm Deletion",
                f"Type '{confirm_text}' to confirm deletion of all customers:",
                QLineEdit.EchoMode.Normal
            )
            
            if ok and text == confirm_text:
                # Show busy cursor
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                
                # Delete all customers
                success = self.customer_manager.delete_all_customers()
                
                # Restore cursor
                QApplication.restoreOverrideCursor()
                
                if success:
                    # Clear current customer and tables
                    self.current_customer = None
                    self.alarms = []
                    self.current_rules = []
                    
                    # Update UI
                    self.update_customer_list()
                    self.update_customer_statistics()
                    self.update_alarm_table()
                    self.update_rule_table()
                    
                    QMessageBox.information(
                        self,
                        "Customers Deleted",
                        "All customers have been deleted successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to delete all customers. Check logs for details."
                    )

    def import_rule_file(self):
        """Import rule file for current customer"""
        if not self.current_customer:
            logger.error("Current customer is None in import_rule_file")
            QMessageBox.information(self, "Info", "Please select a customer first.")
            return
            
        logger.info(f"Importing rule file for customer: {self.current_customer.name} (ID: {self.current_customer.id})")

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Rule File", "", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # Validate the rule file first
            if not self.xml_validator.validate_rule_file(file_path):
                validation_report = self.xml_validator.get_validation_report()
                error_msg = "Rule file validation failed:\n\n"
                error_msg += "\n".join(validation_report["errors"][:5])
                if len(validation_report["errors"]) > 5:
                    error_msg += f"\n... and {len(validation_report['errors']) - 5} more errors"
                
                reply = QMessageBox.question(
                    self,
                    "Validation Failed",
                    error_msg + "\n\nDo you want to import anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Import the file
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                if self.customer_manager.set_customer_rule_file(self.current_customer.id, file_path):
                    self.current_customer = self.customer_manager.get_customer(self.current_customer.id)
                    self.load_customer_files()
                    
                    # Parse rule file to database
                    db_success = self.customer_manager.parse_rule_alarm_files_to_db(self.current_customer.id)
                    
                    if db_success:
                        QMessageBox.information(
                            self, 
                            "Success", 
                            "Rule file imported and parsed to database successfully!"
                        )
                    else:
                        QMessageBox.warning(
                            self, 
                            "Warning", 
                            "Rule file imported successfully, but database parsing failed. Check logs for details."
                        )
                else:
                    QMessageBox.critical(self, "Error", "Failed to import rule file.")
            finally:
                QApplication.restoreOverrideCursor()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to import rule file:\n{str(e)}")

    def import_alarm_file(self):
        """Import alarm file for current customer"""
        if not self.current_customer:
            QMessageBox.information(self, "Info", "Please select a customer first.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Alarm File", "", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # Validate the alarm file first
            if not self.xml_validator.validate_alarm_file(file_path):
                validation_report = self.xml_validator.get_validation_report()
                error_msg = "Alarm file validation failed:\n\n"
                error_msg += "\n".join(validation_report["errors"][:5])
                if len(validation_report["errors"]) > 5:
                    error_msg += f"\n... and {len(validation_report['errors']) - 5} more errors"
                
                reply = QMessageBox.question(
                    self,
                    "Validation Failed",
                    error_msg + "\n\nDo you want to import anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

                                      # Import the file
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                if self.customer_manager.set_customer_alarm_file(self.current_customer.id, file_path):
                    self.current_customer = self.customer_manager.get_customer(self.current_customer.id)
                    self.load_customer_files()
                    
                    # Parse alarm file to database
                    db_success = self.customer_manager.parse_rule_alarm_files_to_db(self.current_customer.id)
                    
                    if db_success:
                        QMessageBox.information(
                            self, 
                            "Success", 
                            "Alarm file imported and parsed to database successfully!"
                        )
                    else:
                        QMessageBox.warning(
                            self, 
                            "Warning", 
                            "Alarm file imported successfully, but database parsing failed. Check logs for details."
                        )
                else:
                    QMessageBox.critical(self, "Error", "Failed to import alarm file.")
            finally:
                QApplication.restoreOverrideCursor()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to import alarm file:\n{str(e)}")

    def export_rule_file(self):
        """Export rule file for current customer"""
        if not self.current_customer or not self.current_customer.rule_file_path:
            QMessageBox.information(self, "Info", "No rule file to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Rule File", f"{self.current_customer.name}_rule.xml", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return

        try:
            import shutil
            shutil.copy2(self.current_customer.rule_file_path, file_path)
            QMessageBox.information(self, "Success", f"Rule file exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export rule file:\n{str(e)}")

    def export_alarm_file(self):
        """Export alarm file for current customer"""
        if not self.current_customer or not self.current_customer.alarm_file_path:
            QMessageBox.information(self, "Info", "No alarm file to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Alarm File", f"{self.current_customer.name}_alarm.xml", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return

        try:
            import shutil
            shutil.copy2(self.current_customer.alarm_file_path, file_path)
            QMessageBox.information(self, "Success", f"Alarm file exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export alarm file:\n{str(e)}")

    # === Validation Methods ===

    def validate_current_rule_file(self):
        """Validate current customer's rule file"""
        if not self.current_customer or not self.current_customer.rule_file_path:
            self.validation_result_text.setText("No rule file to validate.")
            return

        is_valid = self.xml_validator.validate_rule_file(self.current_customer.rule_file_path)
        report = self.xml_validator.get_validation_report()
        
        result_text = f"Rule File Validation Results:\n"
        result_text += f"Status: {'✓ VALID' if is_valid else '✗ INVALID'}\n"
        result_text += f"Errors: {report['error_count']}\n"
        result_text += f"Warnings: {report['warning_count']}\n\n"
        
        if report['errors']:
            result_text += "ERRORS:\n"
            result_text += "\n".join(report['errors'][:10])
            if len(report['errors']) > 10:
                result_text += f"\n... and {len(report['errors']) - 10} more errors"
        
        if report['warnings']:
            result_text += "\n\nWARNINGS:\n"
            result_text += "\n".join(report['warnings'][:5])
            if len(report['warnings']) > 5:
                result_text += f"\n... and {len(report['warnings']) - 5} more warnings"
        
        self.validation_result_text.setText(result_text)

    def validate_current_alarm_file(self):
        """Validate current customer's alarm file"""
        if not self.current_customer or not self.current_customer.alarm_file_path:
            self.validation_result_text.setText("No alarm file to validate.")
            return

        is_valid = self.xml_validator.validate_alarm_file(self.current_customer.alarm_file_path)
        report = self.xml_validator.get_validation_report()
        
        result_text = f"Alarm File Validation Results:\n"
        result_text += f"Status: {'✓ VALID' if is_valid else '✗ INVALID'}\n"
        result_text += f"Errors: {report['error_count']}\n"
        result_text += f"Warnings: {report['warning_count']}\n\n"
        
        if report['errors']:
            result_text += "ERRORS:\n"
            result_text += "\n".join(report['errors'][:10])
            if len(report['errors']) > 10:
                result_text += f"\n... and {len(report['errors']) - 10} more errors"
        
        if report['warnings']:
            result_text += "\n\nWARNINGS:\n"
            result_text += "\n".join(report['warnings'][:5])
            if len(report['warnings']) > 5:
                result_text += f"\n... and {len(report['warnings']) - 5} more warnings"
        
        self.validation_result_text.setText(result_text)

    def validate_rule_alarm_relationship(self):
        """Validate rule-alarm relationship"""
        if not self.current_customer:
            self.validation_result_text.setText("No customer selected.")
            return
        
        if not self.current_customer.rule_file_path or not self.current_customer.alarm_file_path:
            self.validation_result_text.setText("Both rule and alarm files are required for relationship validation.")
            return

        relationships = self.xml_validator.validate_rule_alarm_relationship(
            self.current_customer.rule_file_path,
            self.current_customer.alarm_file_path
        )
        
        result_text = "Rule-Alarm Relationship Analysis:\n\n"
        
        if relationships['errors']:
            result_text += "ERRORS:\n"
            result_text += "\n".join(relationships['errors'])
            result_text += "\n\n"
        
        result_text += f"Matched Pairs: {len(relationships['matched_pairs'])}\n"
        result_text += f"Unmatched Rules: {len(relationships['unmatched_rules'])}\n"
        result_text += f"Unmatched Alarms: {len(relationships['unmatched_alarms'])}\n\n"
        
        if relationships['matched_pairs']:
            result_text += "MATCHED PAIRS:\n"
            for pair in relationships['matched_pairs'][:5]:
                result_text += f"• SigID {pair['sigid']}: {pair['rule_name']} → {pair['alarm_name']}\n"
            if len(relationships['matched_pairs']) > 5:
                result_text += f"... and {len(relationships['matched_pairs']) - 5} more pairs\n"
        
        if relationships['unmatched_rules']:
            result_text += "\nUNMATCHED RULES:\n"
            for rule in relationships['unmatched_rules'][:5]:
                result_text += f"• SigID {rule['sigid']}: {rule['rule_name']}\n"
            if len(relationships['unmatched_rules']) > 5:
                result_text += f"... and {len(relationships['unmatched_rules']) - 5} more rules\n"
        
        self.validation_result_text.setText(result_text)

    # === Rule Management Methods ===

    def update_rule_table(self):
        """Update rule table"""
        # Check if rule table has been created
        if not hasattr(self, 'rule_table_model'):
            return
            
        self.rule_table_model.setRowCount(0)
        
        # Get all alarm sigids for status checking
        alarm_sigids = set()
        for alarm in self.alarms:
            match_value = alarm.get_field("conditionData", "matchValue")
            if match_value and "|" in match_value:
                sigid = match_value.split("|")[1]
                alarm_sigids.add(sigid)
        
        # current_rules değişkeninin var olduğundan emin ol
        if not hasattr(self, 'current_rules') or self.current_rules is None:
            self.current_rules = self.rules if hasattr(self, 'rules') else []
            
        for rule in self.current_rules:
            # Check if alarm exists
            has_alarm = rule.sigid in alarm_sigids
            alarm_status = "✓ Has Alarm" if has_alarm else "✗ No Alarm"
            
            row_items = [
                QStandardItem(rule.id),
                QStandardItem(rule.message),
                QStandardItem(str(rule.severity)),
                QStandardItem(rule.sigid),
                QStandardItem(alarm_status),
                QStandardItem(rule.description[:50] + "..." if len(rule.description) > 50 else rule.description),
                QStandardItem(str(len(rule.triggers)))
            ]
            
            # Color code by severity using config
            color_tuple = SeverityLevel.get_color(rule.severity)
            color = QColor(*color_tuple)
            
            # Set alarm status color
            alarm_status_item = row_items[4]
            if has_alarm:
                alarm_status_item.setForeground(QBrush(QColor(76, 175, 80)))  # Green
            else:
                alarm_status_item.setForeground(QBrush(QColor(220, 53, 69)))  # Red
            
            for i, item in enumerate(row_items):
                if i != 4:  # Don't override alarm status color
                    item.setForeground(QBrush(color))
            
            self.rule_table_model.appendRow(row_items)
            
        # Kuralların yüklendiğini logla
        if hasattr(self, 'current_rules'):
            logger.info(f"Rule table updated with {len(self.current_rules)} rules")

    def filter_rules(self):
        """Filter rules based on search text and alarm status"""
        if not hasattr(self, 'rule_table_model') or not hasattr(self, 'rule_search_input'):
            return
            
        search_text = self.rule_search_input.text().lower()
        alarm_filter = self.rule_alarm_filter.currentText() if hasattr(self, 'rule_alarm_filter') else "All Rules"
        
        visible_count = 0
        total = self.rule_table_model.rowCount()
        
        for row in range(total):
            rule_id_item = self.rule_table_model.item(row, 0)
            message_item = self.rule_table_model.item(row, 1)
            sigid_item = self.rule_table_model.item(row, 3)
            alarm_status_item = self.rule_table_model.item(row, 4)
            
            if not all([rule_id_item, message_item, sigid_item, alarm_status_item]):
                continue
            
            # Text search
            rule_id_match = search_text in rule_id_item.text().lower()
            message_match = search_text in message_item.text().lower()
            sigid_match = search_text in sigid_item.text().lower()
            text_match = rule_id_match or message_match or sigid_match
            
            # Alarm status filter
            alarm_status = alarm_status_item.text()
            if alarm_filter == "With Alarms":
                alarm_match = "✓" in alarm_status
            elif alarm_filter == "Without Alarms":
                alarm_match = "✗" in alarm_status
            else:
                alarm_match = True
            
            is_visible = text_match and alarm_match
            self.rule_table_view.setRowHidden(row, not is_visible)
            
            if is_visible:
                visible_count += 1
        
        # Update status bar
        if hasattr(self, 'status_bar'):
            if visible_count == total:
                self.status_bar.showMessage(f"Showing all {visible_count} rules")
            else:
                self.status_bar.showMessage(f"Filtered: {visible_count} of {total} rules visible")

    def on_rule_selection_changed(self, current: QModelIndex, previous: QModelIndex):
        """Handle rule selection change"""
        if not current.isValid():
            if hasattr(self, 'rule_details_text'):
                self.rule_details_text.clear()
            return
        
        row = current.row()
        if 0 <= row < len(self.current_rules):
            rule = self.current_rules[row]
            self.display_rule_details(rule)

    def display_rule_details(self, rule: RuleData):
        """Display rule details"""
        if not hasattr(self, 'rule_details_text'):
            return
            
        details = f"Rule ID: {rule.id}\n"
        details += f"Message: {rule.message}\n"
        details += f"Description: {rule.description}\n"
        details += f"Severity: {rule.severity}\n"
        details += f"SigID: {rule.sigid}\n"
        details += f"Rule Type: {rule.rule_type}\n"
        details += f"Normalization ID: {rule.normid}\n"
        details += f"Revision: {rule.revision}\n\n"
        
        details += f"Ruleset ID: {rule.ruleset_id}\n"
        details += f"Ruleset Name: {rule.ruleset_name}\n"
        details += f"Event Type: {rule.event_type}\n"
        details += f"Correlation Field: {rule.correlation_field}\n\n"
        
        if rule.triggers:
            details += "Triggers:\n"
            for trigger in rule.triggers:
                details += f"• {trigger.name}: count={trigger.count}, timeout={trigger.timeout}{trigger.time_unit}\n"
            details += "\n"
        
        if rule.matches:
            details += "Matches:\n"
            for match in rule.matches:
                details += f"• Type: {match.match_type}, Count: {match.count}\n"
                for filter_comp in match.filters:
                    details += f"  - {filter_comp.type} {filter_comp.operator} {filter_comp.value[:50]}\n"
            details += "\n"
        
        if rule.properties:
            details += "Properties:\n"
            for key, value in rule.properties.items():
                details += f"• {key}: {value}\n"
        
        self.rule_details_text.setText(details)

    def view_rule_details(self):
        """View detailed rule information in a dialog"""
        current_index = self.rule_table_view.currentIndex()
        if not current_index.isValid():
            return
        
        row = current_index.row()
        if 0 <= row < len(self.current_rules):
            rule = self.current_rules[row]
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Rule Details - {rule.id}")
            dialog.setMinimumSize(800, 600)
            layout = QVBoxLayout(dialog)
            
            # Tab widget for different views
            tabs = QTabWidget()
            
            # Rule Flow tab
            flow_widget = RuleFlowWidget(rule)
            tabs.addTab(flow_widget, "Rule Flow Visualization")
            
            # Raw XML tab
            raw_xml_text = QTextEdit()
            raw_xml_text.setReadOnly(True)
            raw_xml_text.setPlainText(rule.raw_xml if rule.raw_xml else "No raw XML available")
            tabs.addTab(raw_xml_text, "Raw XML")
            
            layout.addWidget(tabs)
            
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.exec()

    def on_rule_context_menu(self, pos):
        """Show context menu for rules"""
        if not self.rule_table_view.selectionModel().selectedRows():
            return

        menu = QMenu(self)
        generate_alarm_action = menu.addAction("Generate Alarm from Rule")
        view_details_action = menu.addAction("View Rule Details")
        export_selected_action = menu.addAction("Export Selected Rules")
        
        # Add View Alarm action for rules that have alarms
        selected_rows = [index.row() for index in self.rule_table_view.selectionModel().selectedRows()]
        has_alarm = False
        rule_alarm_map = {}
        
        if selected_rows and len(selected_rows) == 1:  # Only add for single selection
            row = selected_rows[0]
            if 0 <= row < len(self.current_rules):
                rule = self.current_rules[row]
                
                # Find the matching alarm
                for alarm in self.alarms:
                    match_value = alarm.get_field("conditionData", "matchValue")
                    if match_value and "|" in match_value:
                        alarm_sigid = match_value.split("|")[1]
                        if alarm_sigid == rule.sigid:
                            has_alarm = True
                            rule_alarm_map[rule.id] = alarm
                            break
                
                # Log alarm mapping for debugging
                if has_alarm:
                    self.logger.debug(f"Found matching alarm for rule ID: {rule.id}, SigID: {rule.sigid}")
                else:
                    self.logger.debug(f"No matching alarm found for rule ID: {rule.id}, SigID: {rule.sigid}")
        
        view_alarm_action = None
        if has_alarm:
            menu.addSeparator()
            view_alarm_action = menu.addAction("View Alarm")
        
        # Add separator and actions for rules without alarms
        if selected_rows:
            # Check if any selected rules don't have alarms
            rules_without_alarms = []
            alarm_sigids = set()
            for alarm in self.alarms:
                match_value = alarm.get_field("conditionData", "matchValue")
                if match_value and "|" in match_value:
                    sigid = match_value.split("|")[1]
                    alarm_sigids.add(sigid)
            
            for row in selected_rows:
                if 0 <= row < len(self.current_rules):
                    rule = self.current_rules[row]
                    if rule.sigid not in alarm_sigids:
                        rules_without_alarms.append(rule)
            
            if rules_without_alarms:
                menu.addSeparator()
                create_missing_alarms_action = menu.addAction(
                    f"Create Alarms for {len(rules_without_alarms)} Rules Without Alarms"
                )
        
        action = menu.exec(self.rule_table_view.mapToGlobal(pos))
        
        if action == generate_alarm_action:
            self.generate_alarm_from_selected_rule()
        elif action == view_details_action:
            self.view_rule_details()
        elif action == export_selected_action:
            self.export_selected_rules()
        elif action == view_alarm_action:
            # Hata kontrolü: Eşleşen alarm var mı kontrol et
            try:
                row = selected_rows[0]
                rule = self.current_rules[row]
                
                # Önce rule.id'nin rule_alarm_map içinde olup olmadığını kontrol et
                if rule.id in rule_alarm_map:
                    self.view_alarm_for_rule(rule_alarm_map[rule.id])
                else:
                    # SigID ile eşleşen alarmı bul
                    for alarm in self.alarms:
                        match_value = alarm.get_field("conditionData", "matchValue")
                        if match_value and "|" in match_value:
                            alarm_sigid = match_value.split("|")[1]
                            if alarm_sigid == rule.sigid:
                                self.view_alarm_for_rule(alarm)
                                return
                    
                    QMessageBox.warning(self, "Warning", f"No matching alarm found for rule ID: {rule.id}")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to view alarm: {str(e)}")
        elif action and action.text().startswith("Create Alarms"):
            self.create_alarms_for_rules_without_alarms(rules_without_alarms)
            
    def view_alarm_for_rule(self, alarm: AlarmModel):
        """View alarm for selected rule"""
        if alarm is None:
            QMessageBox.warning(self, "Warning", "No matching alarm found for this rule")
            return
            
        try:
            # Switch to alarm management tab
            self.main_tab_widget.setCurrentIndex(1)
            
            # Find alarm index
            try:
                alarm_index = self.alarms.index(alarm)
            except ValueError:
                QMessageBox.warning(self, "Warning", f"Alarm '{alarm.name}' is no longer in the alarm list")
                return
            
            # Select the alarm row
            self.alarm_table_view.selectRow(alarm_index)
            
            # Scroll to the alarm
            self.alarm_table_view.scrollTo(
                self.alarm_table_model.index(alarm_index, 0),
                QAbstractItemView.ScrollHint.PositionAtCenter
            )
            
            # Update status bar message
            self.status_bar.showMessage(f"Navigated to alarm: {alarm.name}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to view alarm:\n{str(e)}")

    def create_alarms_for_rules_without_alarms(self, rules: List[RuleData]):
        """Create alarms for rules that don't have alarms"""
        try:
            # Toplu oluşturma için boş template ve use_template=False ile çağır
            alarm_configs = self.rule_alarm_mapper.batch_create_alarms(rules, None, False)
            
            created_count = 0
            for alarm_config in alarm_configs:
                alarm_model = AlarmModel(self)
                alarm_model.name = alarm_config["name"]
                alarm_model.min_version = alarm_config["minVersion"]
                alarm_model.data = alarm_config
                
                self.alarms.append(alarm_model)
                created_count += 1
            
            self.update_alarm_table()
            self.update_rule_table()  # Update to show new alarm status
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Created {created_count} alarms for rules without alarms."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create alarms:\n{str(e)}")

    def generate_alarm_from_selected_rule(self):
        """Düzeltilmiş: Template kullanarak alarm oluştur"""
        selected_rows = [index.row() for index in self.rule_table_view.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select a rule first.")
            return
        
        row = selected_rows[0]
        if 0 <= row < len(self.current_rules):
            rule = self.current_rules[row]
            
            # Template seçimi için dialog göster
            dialog = AlarmTemplateSelectionDialog(self, rule, self.alarms)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                template_alarm = dialog.get_selected_template()
                use_template = dialog.use_template()
                
                try:
                    # Template kullanarak alarm oluştur
                    alarm_config = self.rule_alarm_mapper.create_alarm_from_rule(
                        rule, template_alarm, use_template
                    )
                    
                    # AlarmModel'e dönüştür
                    alarm_model = AlarmModel(self)
                    alarm_model.name = alarm_config["name"]
                    alarm_model.min_version = alarm_config["minVersion"]
                    alarm_model.data = alarm_config
                    
                    # Alarm'ı ekle
                    self.alarms.append(alarm_model)
                    self.alarm_state_manager.mark_as_new(alarm_model)  # Yeni alarm olarak işaretle
                    
                    # Tabloları güncelle
                    self.update_alarm_table()
                    self.update_rule_table()
                    
                    # Alarm Management sekmesine geç
                    self.main_tab_widget.setCurrentIndex(1)
                    
                    # Yeni alarm'ı seç ve property editor'ü güncelle
                    new_alarm_index = len(self.alarms) - 1
                    self.alarm_table_view.selectRow(new_alarm_index)
                    self.property_editor.set_current_alarm(alarm_model)
                    self.property_editor.update_form()
                    
                    # Başarı mesajı
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Alarm created successfully!\n\n"
                        f"Name: {alarm_model.name}\n"
                        f"Template: {'Yes' if use_template else 'No'}\n"
                        f"Severity: {alarm_model.get_field('alarmData', 'severity')}"
                    )
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to generate alarm:\n{str(e)}")

    def generate_alarms_from_selected_rules(self):
        """Düzeltilmiş: Toplu rule'dan alarm oluşturma"""
        selected_rows = [index.row() for index in self.rule_table_view.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select one or more rules.")
            return
        
        selected_rules = [self.current_rules[row] for row in selected_rows if 0 <= row < len(self.current_rules)]
        
        # Template seçimi dialog'u
        dialog = BatchAlarmCreationDialog(self, selected_rules, self.alarms)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template_alarm = dialog.get_selected_template()
            use_template = dialog.use_template()
            
            try:
                # Toplu alarm oluştur
                alarm_configs = self.rule_alarm_mapper.batch_create_alarms(
                    selected_rules, template_alarm, use_template
                )
                
                created_alarms = []
                for alarm_config in alarm_configs:
                    alarm_model = AlarmModel(self)
                    alarm_model.name = alarm_config["name"]
                    alarm_model.min_version = alarm_config["minVersion"]
                    alarm_model.data = alarm_config
                    
                    self.alarms.append(alarm_model)
                    self.alarm_state_manager.mark_as_new(alarm_model)
                    created_alarms.append(alarm_model)
                
                # Tabloları güncelle
                self.update_alarm_table()
                self.update_rule_table()
                
                # Özet dialog göster
                self.show_batch_creation_summary(created_alarms, template_alarm, use_template)
                
                # Alarm Management sekmesine geç
                self.main_tab_widget.setCurrentIndex(1)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate alarms:\n{str(e)}")
    
    def show_batch_creation_summary(self, created_alarms: List[AlarmModel], 
                               template_alarm: Optional[AlarmModel], 
                               use_template: bool):
        """Toplu alarm oluşturma sonuç özeti"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Batch Alarm Creation Summary")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        
        # Başlık
        header = QLabel(f"✅ Successfully Created {len(created_alarms)} Alarms")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #28a745;")
        layout.addWidget(header)
        
        # Template bilgisi
        if use_template and template_alarm:
            template_info = QLabel(f"📋 Template Used: {template_alarm.name}")
            template_info.setStyleSheet("font-size: 10pt; color: #666; padding: 10px;")
            layout.addWidget(template_info)
        else:
            template_info = QLabel("📋 No template used - default values applied")
            template_info.setStyleSheet("font-size: 10pt; color: #666; padding: 10px;")
            layout.addWidget(template_info)
        
        # Oluşturulan alarmlar tablosu
        table = QTableView()
        model = QStandardItemModel(0, 5)
        model.setHorizontalHeaderLabels(["Alarm Name", "Rule SigID", "Severity", "Match Value", "Status"])
        
        for alarm in created_alarms:
            name_item = QStandardItem(alarm.name)
            name_item.setBackground(QBrush(QColor(144, 238, 144, 80)))  # Yeni alarm rengi
            
            sigid = alarm.get_field("conditionData", "matchValue").split("|")[1] if "|" in alarm.get_field("conditionData", "matchValue") else ""
            sigid_item = QStandardItem(sigid)
            
            severity_item = QStandardItem(str(alarm.get_field("alarmData", "severity")))
            match_value_item = QStandardItem(alarm.get_field("conditionData", "matchValue"))
            
            # Validasyon durumu
            validation_errors = self.validator.validate_alarm(alarm)
            if validation_errors:
                status_item = QStandardItem(f"⚠ {len(validation_errors)} warnings")
                status_item.setForeground(QBrush(QColor(255, 193, 7)))
                status_item.setToolTip("\n".join(validation_errors[:3]))
            else:
                status_item = QStandardItem("✓ Valid")
                status_item.setForeground(QBrush(QColor(76, 175, 80)))
            
            model.appendRow([name_item, sigid_item, severity_item, match_value_item, status_item])
        
        table.setModel(model)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # İşlem butonları
        button_layout = QHBoxLayout()
        
        validate_all_btn = QPushButton("Validate All")
        validate_all_btn.clicked.connect(lambda: self.validate_alarms(created_alarms))
        button_layout.addWidget(validate_all_btn)
        
        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(lambda: self.export_creation_report(created_alarms))
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()


    def validate_alarms(self, alarms: List[AlarmModel]):
        """Alarm listesini validate et"""
        all_errors = []
        for alarm in alarms:
            errors = self.validator.validate_alarm(alarm)
            if errors:
                all_errors.append(f"{alarm.name}:\n" + "\n".join(f"  • {e}" for e in errors))
        
        if all_errors:
            msg = "Validation Results:\n\n" + "\n\n".join(all_errors[:10])
            if len(all_errors) > 10:
                msg += f"\n\n... and {len(all_errors) - 10} more alarms with warnings"
            QMessageBox.warning(self, "Validation Warnings", msg)
        else:
            QMessageBox.information(self, "Validation Success", "All alarms are valid!")


    def export_creation_report(self, created_alarms: List[AlarmModel]):
        """Alarm oluşturma raporunu dışa aktar"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Creation Report", "alarm_creation_report.txt", "Text Files (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("ALARM CREATION REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Alarms Created: {len(created_alarms)}\n\n")
                
                for i, alarm in enumerate(created_alarms, 1):
                    f.write(f"{i}. {alarm.name}\n")
                    f.write(f"   Severity: {alarm.get_field('alarmData', 'severity')}\n")
                    f.write(f"   Match Value: {alarm.get_field('conditionData', 'matchValue')}\n")
                    
                    errors = self.validator.validate_alarm(alarm)
                    if errors:
                        f.write(f"   Validation: ⚠ {len(errors)} warnings\n")
                        for error in errors:
                            f.write(f"     - {error}\n")
                    else:
                        f.write(f"   Validation: ✓ Passed\n")
                    f.write("\n")
            
            QMessageBox.information(self, "Export Success", f"Report saved to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{str(e)}")

    # === Mapping Methods ===

    def analyze_rule_alarm_relationships(self):
        """Analyze rule-alarm relationships"""
        if not self.current_customer:
            self.mapping_results_text.setText("No customer selected.")
            return
        
        if not self.current_customer.rule_file_path or not self.current_customer.alarm_file_path:
            self.mapping_results_text.setText("Both rule and alarm files are required for analysis.")
            return

        relationships = self.xml_validator.validate_rule_alarm_relationship(
            self.current_customer.rule_file_path,
            self.current_customer.alarm_file_path
        )
        
        result_text = "🔗 Rule-Alarm Relationship Analysis\n"
        result_text += "=" * 50 + "\n\n"
        
        # Summary
        result_text += f"📊 SUMMARY:\n"
        result_text += f"• Matched Pairs: {len(relationships['matched_pairs'])}\n"
        result_text += f"• Unmatched Rules: {len(relationships['unmatched_rules'])}\n"
        result_text += f"• Unmatched Alarms: {len(relationships['unmatched_alarms'])}\n\n"
        
        # Coverage percentage
        total_rules = len(relationships['matched_pairs']) + len(relationships['unmatched_rules'])
        if total_rules > 0:
            coverage = (len(relationships['matched_pairs']) / total_rules) * 100
            result_text += f"📈 Coverage: {coverage:.1f}%\n\n"
        
        # Detailed results
        if relationships['matched_pairs']:
            result_text += "✅ MATCHED RULE-ALARM PAIRS:\n"
            for pair in relationships['matched_pairs']:
                result_text += f"• SigID {pair['sigid']}: {pair['rule_name']} → {pair['alarm_name']}\n"
            result_text += "\n"
        
        if relationships['unmatched_rules']:
            result_text += "❌ RULES WITHOUT ALARMS:\n"
            for rule in relationships['unmatched_rules']:
                result_text += f"• SigID {rule['sigid']}: {rule['rule_name']}\n"
            result_text += "\n"
        
        if relationships['unmatched_alarms']:
            result_text += "❗ ALARMS WITHOUT RULES:\n"
            for alarm in relationships['unmatched_alarms']:
                result_text += f"• SigID {alarm['sigid']}: {alarm['alarm_name']}\n"
            result_text += "\n"
        
        if relationships['errors']:
            result_text += "🚨 ERRORS:\n"
            for error in relationships['errors']:
                result_text += f"• {error}\n"
        
        self.mapping_results_text.setText(result_text)

    def auto_generate_alarms(self):
        """Auto-generate alarms based on severity filter"""
        if not self.current_rules:
            self.auto_gen_results_text.setText("No rules loaded. Please load a rule file first.")
            return
        
        severity_filter = self.auto_gen_severity_combo.currentText()
        
        # Filter rules by severity
        filtered_rules = []
        for rule in self.current_rules:
            if not rule.sigid:  # Skip rules without sigid
                continue
                
            if severity_filter == "All":
                filtered_rules.append(rule)
            elif severity_filter == "Low (0-39)" and 0 <= rule.severity <= 39:
                filtered_rules.append(rule)
            elif severity_filter == "Medium (40-69)" and 40 <= rule.severity <= 69:
                filtered_rules.append(rule)
            elif severity_filter == "High (70-89)" and 70 <= rule.severity <= 89:
                filtered_rules.append(rule)
            elif severity_filter == "Critical (90-100)" and 90 <= rule.severity <= 100:
                filtered_rules.append(rule)
        
        if not filtered_rules:
            self.auto_gen_results_text.setText(f"No rules found matching criteria: {severity_filter}")
            return
        
        try:
            alarm_configs = self.rule_alarm_mapper.batch_create_alarms(filtered_rules)
            
            generated_count = 0
            for alarm_config in alarm_configs:
                alarm_model = AlarmModel(self)
                alarm_model.name = alarm_config["name"]
                alarm_model.min_version = alarm_config["minVersion"]
                alarm_model.data = alarm_config
                
                self.alarms.append(alarm_model)
                generated_count += 1
            
            self.update_alarm_table()
            
            result_text = f"✅ Auto-Generation Complete!\n\n"
            result_text += f"Filter: {severity_filter}\n"
            result_text += f"Matching Rules: {len(filtered_rules)}\n"
            result_text += f"Generated Alarms: {generated_count}\n\n"
            result_text += "Generated alarms have been added to the Alarm Management tab.\n"
            result_text += "You can now review and modify them as needed."
            
            self.auto_gen_results_text.setText(result_text)
            
            # Show success message
            reply = QMessageBox.question(
                self,
                "Auto-Generation Complete",
                f"Successfully generated {generated_count} alarms.\n\nWould you like to switch to the Alarm Management tab to review them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.main_tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            error_text = f"❌ Auto-Generation Failed!\n\nError: {str(e)}"
            self.auto_gen_results_text.setText(error_text)
            QMessageBox.critical(self, "Error", f"Failed to auto-generate alarms:\n{str(e)}")

    def on_alarm_context_menu(self, pos):
        if not self.alarm_table_view.selectionModel().selectedRows():
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Alarm")
        duplicate_action = menu.addAction("Duplicate Alarm")
        delete_action = menu.addAction("Delete Alarm")
        menu.addSeparator()
        enable_action = menu.addAction("Enable Alarm")
        disable_action = menu.addAction("Disable Alarm")
        menu.addSeparator()
        export_action = menu.addAction("Export Selected Alarms")
        action = menu.exec(self.alarm_table_view.mapToGlobal(pos))

        if action == edit_action:
            self.edit_selected_alarm()
        elif action == duplicate_action:
            self.duplicate_selected_alarm()
        elif action == delete_action:
            self.delete_selected_alarm()
        elif action == enable_action:
            self.toggle_alarm_state(True)
        elif action == disable_action:
            self.toggle_alarm_state(False)
        elif action == export_action:
            self.export_selected_alarms()

    def check_rule_alarm_mapping(self):
        """Rule'ların alarm eşleşmelerini kontrol et"""
        if not self.current_rules or not self.alarms:
            return [], []  # Boş listeler dön
        
        # Alarm sigid'lerini topla
        alarm_sigids = {}
        for alarm in self.alarms:
            match_value = alarm.get_field("conditionData", "matchValue")
            if match_value and "|" in match_value:
                sigid = match_value.split("|")[1]
                alarm_sigids[sigid] = alarm.name
        
        # Rule'ları kontrol et
        unmapped_rules = []
        mapped_rules = []
        
        for rule in self.current_rules:
            if rule.sigid in alarm_sigids:
                mapped_rules.append((rule, alarm_sigids[rule.sigid]))
            else:
                unmapped_rules.append(rule)
        
        # Durum mesajı göster
        if unmapped_rules:
            self.status_bar.showMessage(
                f"⚠ {len(unmapped_rules)} rules without alarms | "
                f"✓ {len(mapped_rules)} rules with alarms"
            )
        else:
            self.status_bar.showMessage(f"✓ All {len(mapped_rules)} rules have alarms")
        
        return mapped_rules, unmapped_rules


    def fix_customer_initialization(self):
        """MainWindow __init__ metodunun sonuna eklenecek"""
        # __init__ metodunun sonunda:
        self._initializing = False
        logger.info("Main window initialization complete")
        
        # Timer kullanarak yükleme - UI tamamen hazır olduktan sonra
        # load_first_customer içinde gerekli kontroller var
        QTimer.singleShot(100, lambda: self.load_first_customer())


    def load_first_customer(self):
        """İlk müşteriyi ve dosyalarını yükle"""
        if self.customer_combo.count() > 0:
            first_item_text = self.customer_combo.itemText(0)
            
            # Check if there are actual customers or just the "No customers" placeholder
            if first_item_text != "No customers available":
                # İlk müşteriyi seç
                self.customer_combo.setCurrentIndex(0)
                # Manuel olarak selection handler'ı çağır
                self.on_customer_selected(self.customer_combo.currentText())
            else:
                self.status_bar.showMessage("No customers available. Create a new customer to begin.")
                # Show customer tab to make it easy to create a new customer
                self.main_tab_widget.setCurrentIndex(0)

    def load_rule_file(self, file_path: str):
        """Load rules from XML file"""
        try:
            logger.info(f"Parsing rule file: {file_path}")
            if self.rule_parser.parse_file(file_path):
                self.rules = self.rule_parser.get_rules()
                self.current_rules = self.rules
                logger.info(f"Successfully loaded {len(self.rules)} rules")
                
                # Update rule table
                self.update_rule_table()

                # Eğer alarm dosyası yüklenmemişse ve kurallar yüklendiyse
                # otomatik olarak alarmları oluştur
                if not self.alarms and self.rules:
                    reply = QMessageBox.question(
                        self,
                        "Auto-generate Alarms",
                        f"No alarms are loaded but {len(self.rules)} rules are found.\n"
                        f"Would you like to automatically generate alarms for these rules with descriptions?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Tüm kurallara alarm oluştur
                        self.create_alarms_for_rules_without_alarms(self.rules)
            else:
                logger.error(f"Failed to parse rule file: {file_path}")
                self.rules = []
                self.current_rules = []
        except Exception as e:
            logger.error(f"Error loading rule file: {str(e)}")
            self.rules = []
            self.current_rules = []
    
    def load_alarm_file(self, file_path: str):
        """Load and parse alarm file"""
        try:
            logger.info(f"Parsing alarm file: {file_path}")
            # Use secure XML parser
            self.original_tree = SecureXMLParser.parse_file(file_path)
            root = self.original_tree.getroot()
            
            if root.tag != "alarms":
                raise XMLParsingError(f"Invalid alarm file: root element is '{root.tag}', expected 'alarms'")
            
            self.alarms.clear()
            alarm_count = 0
            for alarm_elem in root.findall("alarm"):
                alarm_model = AlarmModel(self)
                alarm_model.from_element(alarm_elem)
                self.alarms.append(alarm_model)
                alarm_count += 1
            
            self.current_file = file_path
            logger.info(f"Successfully loaded {alarm_count} alarms")
            
            # Varsayılan template alarm olarak uygun bir alarmı ayarla
            if self.alarms and hasattr(self, 'rule_alarm_mapper'):
                # En yüksek severity değerine sahip alarmı bul
                if len(self.alarms) > 5:  # Eğer yeterli alarm varsa, iyi bir örnek bulmaya çalış
                    template_candidates = sorted(
                        self.alarms, 
                        key=lambda a: int(a.get_field("alarmData", "severity") or "0"), 
                        reverse=True
                    )
                    # En yüksek severity değerli alarm template olarak kullanılacak
                    self.rule_alarm_mapper.set_default_template(template_candidates[0])
                    logger.info(f"Set high-severity alarm '{template_candidates[0].name}' as default template")
                else:
                    # Az sayıda alarm varsa ilkini kullan
                    self.rule_alarm_mapper.set_default_template(self.alarms[0])
                    logger.info(f"Set first alarm '{self.alarms[0].name}' as default template")
                
                # Alarmlar yüklendikten sonra kural-alarm eşleştirmesini güncelle
                if self.rules:
                    self.rule_alarm_mapper.update_mappings(self.rules, self.alarms)
                
                # Eğer daha önce kurallar yüklenmişse ama alarmları yoksa,
                # şimdi örnek alarmları kullanarak eksik kurallar için alarm oluştur
                if self.rules:
                    rules_without_alarms = []
                    mapped_rules, unmapped_rules = self.check_rule_alarm_mapping()
                    
                    if unmapped_rules:
                        reply = QMessageBox.question(
                            self,
                            "Create Alarms from Template",
                            f"Found {len(unmapped_rules)} rules without alarms. "
                            f"Would you like to create alarms for them using the loaded alarm file as a template?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            self.generate_alarms_from_selected_rules_auto(unmapped_rules)
            
        except XMLSecurityError as e:
            logger.error(f"Security error in alarm file: {e}")
            QMessageBox.critical(self, "Security Error", f"Alarm file contains security risks:\n{e}")
            self.alarms = []
        except XMLParsingError as e:
            logger.error(f"XML parsing error in alarm file: {e}")
            QMessageBox.critical(self, "Invalid XML", f"Failed to parse alarm file:\n{e}")
            self.alarms = []
        except Exception as e:
            logger.error(f"Error loading alarm file: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load alarm file:\n{e}")
            self.alarms = []

    def export_selected_rules(self):
        """Export only the selected rules to a file"""
        if not hasattr(self, 'rule_table_view') or not self.rule_table_view.selectionModel():
            QMessageBox.information(self, "Info", "No rules selected.")
            return
            
        selected_indexes = self.rule_table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Info", "No rules selected.")
            return
        
        selected_rules = []
        for index in selected_indexes:
            row = index.row()
            if 0 <= row < len(self.current_rules):
                selected_rules.append(self.current_rules[row])
        
        if not selected_rules:
            QMessageBox.information(self, "Info", "No valid rules selected.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Selected Rules", "selected_rules.xml", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            # Yeni bir XML belgesi oluştur
            root = ET.Element("nitro_policy")
            rules_elem = ET.SubElement(root, "rules", count=str(len(selected_rules)))
            
            # Seçili kuralları ekle
            for rule in selected_rules:
                rule_elem = ET.Element("rule")
                
                # Temel kural bilgilerini ekle
                ET.SubElement(rule_elem, "id").text = rule.id
                ET.SubElement(rule_elem, "normid").text = rule.normid
                ET.SubElement(rule_elem, "revision").text = rule.revision
                ET.SubElement(rule_elem, "sid").text = "0"
                ET.SubElement(rule_elem, "class").text = "0"
                ET.SubElement(rule_elem, "message").text = rule.message
                ET.SubElement(rule_elem, "description").text = rule.description
                ET.SubElement(rule_elem, "origin").text = "1"
                ET.SubElement(rule_elem, "severity").text = str(rule.severity)
                ET.SubElement(rule_elem, "type").text = rule.rule_type
                
                # Varsayılan değerler
                ET.SubElement(rule_elem, "action").text = "255"
                ET.SubElement(rule_elem, "action_initial").text = "255"
                ET.SubElement(rule_elem, "action_disallowed").text = "0"
                ET.SubElement(rule_elem, "other_bits_default").text = "4"
                ET.SubElement(rule_elem, "other_bits_disallowed").text = "0"
                
                # CDATA içeriğini ekle (ElementTree CDATA desteklemediği için normal text olarak ekliyoruz)
                text_elem = ET.SubElement(rule_elem, "text")
                text_elem.text = rule.raw_xml if rule.raw_xml else ""
                
                rules_elem.append(rule_elem)
            
            # XML belgesini string olarak oluştur
            xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            
            # CDATA etiketleri için manuel düzeltme (XML string üzerinde replace)
            xml_str = xml_str.replace(b'<text>', b'<text><![CDATA[')
            xml_str = xml_str.replace(b'</text>', b']]></text>')
            
            # Dosyaya yaz
            with open(file_path, 'wb') as f:
                f.write(xml_str)
            
            QMessageBox.information(self, "Success", f"Selected rules exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export rules:\n{str(e)}")

    def export_selected_alarms(self):
        """Export only the selected alarms to a file"""
        if not hasattr(self, 'alarm_table_view') or not self.alarm_table_view.selectionModel():
            QMessageBox.information(self, "Info", "No alarms selected.")
            return
            
        selected_indexes = self.alarm_table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Info", "No alarms selected.")
            return
        
        selected_alarms = []
        for index in selected_indexes:
            row = index.row()
            if 0 <= row < len(self.alarms):
                selected_alarms.append(self.alarms[row])
        
        if not selected_alarms:
            QMessageBox.information(self, "Info", "No valid alarms selected.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Selected Alarms", "selected_alarms.xml", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            # Yeni bir XML belgesi oluştur
            root = ET.Element("alarms")
            
            # Seçili alarmları ekle
            for alarm in selected_alarms:
                alarm_elem = alarm.to_element()
                root.append(alarm_elem)
            
            # XML belgesini dosyaya yaz
            tree = ET.ElementTree(root)
            with open(file_path, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            
            QMessageBox.information(self, "Success", f"Selected alarms exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export alarms:\n{str(e)}")

    def generate_alarms_from_selected_rules_auto(self, rules: List[RuleData]):
        """Şablonları kullanarak kurallar için otomatik alarm oluşturma"""
        if not rules:
            return
            
        try:
            # Template olarak en yüksek severity değerli alarmı bul
            template_alarm = None
            if self.alarms:
                template_candidates = sorted(
                    self.alarms, 
                    key=lambda a: int(a.get_field("alarmData", "severity") or "0"), 
                    reverse=True
                )
                if template_candidates:
                    template_alarm = template_candidates[0]
                    logger.info(f"Using alarm '{template_alarm.name}' as template for auto-generation")
            
            # Toplu alarm oluştur - şablonu kullan
            alarm_configs = self.rule_alarm_mapper.batch_create_alarms(
                rules, template_alarm, True
            )
            
            created_alarms = []
            for alarm_config in alarm_configs:
                alarm_model = AlarmModel(self)
                alarm_model.name = alarm_config["name"]
                alarm_model.min_version = alarm_config["minVersion"]
                alarm_model.data = alarm_config
                
                self.alarms.append(alarm_model)
                self.alarm_state_manager.mark_as_new(alarm_model)
                created_alarms.append(alarm_model)
            
            # Tabloları güncelle
            self.update_alarm_table()
            self.update_rule_table()
            
            # Özet göster
            if created_alarms:
                template_name = "Default"
                if template_alarm and hasattr(template_alarm, 'name'):
                    template_name = template_alarm.name
                    
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Created {len(created_alarms)} alarms using the template alarm '{template_name}'.\n\n"
                    f"The alarms have been added to the Alarm Management tab."
                )
            else:
                QMessageBox.information(
                    self, 
                    "Info", 
                    "No alarms were created. Please check if rules have valid signature IDs."
                )
                
        except Exception as e:
            logger.error(f"Error auto-generating alarms: {str(e)}")
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to auto-generate alarms:\n{str(e)}"
            )


class BulkEditDialog(QDialog):
    """Enhanced bulk edit dialog with preview table"""
    
    def __init__(self, parent, selected_rows, alarms):
        super().__init__(parent)
        self.parent = parent
        self.selected_rows = selected_rows
        self.alarms = alarms
        self.changes = {}
        
        self.setWindowTitle("Bulk Edit Alarms")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with instructions
        header = QLabel("🔧 Bulk Edit Alarms")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4a90e2;")
        layout.addWidget(header)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(80)
        instructions.setHtml("""
        <p><b>Bulk Edit Instructions:</b></p>
        <ul>
            <li>Select the field you want to edit from the dropdown</li>
            <li>Enter the new value for the selected field</li>
            <li>Preview the changes in the table below</li>
            <li>Click 'Apply Changes' to confirm or 'Cancel' to discard</li>
        </ul>
        """)
        layout.addWidget(instructions)
        
        # Field selection
        field_group = QGroupBox("Field Selection")
        field_layout = QFormLayout(field_group)
        
        self.field_combo = QComboBox()
        editable_fields = sorted(list(self.parent.ALARM_DATA_FIELDS) + list(self.parent.CONDITION_DATA_FIELDS))
        self.field_combo.addItems(editable_fields)
        self.field_combo.currentTextChanged.connect(self.on_field_changed)
        field_layout.addRow("Field to edit:", self.field_combo)
        
        # Value input container
        self.value_container = QWidget()
        self.value_layout = QHBoxLayout(self.value_container)
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.addRow("New value:", self.value_container)
        
        # Field description
        self.field_description = QLabel("")
        self.field_description.setWordWrap(True)
        self.field_description.setStyleSheet("color: #666; font-style: italic;")
        field_layout.addRow("Description:", self.field_description)
        
        layout.addWidget(field_group)
        
        # Preview table
        preview_group = QGroupBox("Preview Changes")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableView()
        self.preview_model = QStandardItemModel(0, 4)
        self.preview_model.setHorizontalHeaderLabels(["Alarm Name", "Field", "Current Value", "New Value"])
        self.preview_table.setModel(self.preview_model)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        
        preview_layout.addWidget(self.preview_table)
        
        # Validation status
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("padding: 10px; border-radius: 4px;")
        preview_layout.addWidget(self.validation_label)
        
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        button_layout.addWidget(self.preview_btn)
        
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self.validate_and_accept)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize with first field
        self.on_field_changed(self.field_combo.currentText())
    
    def on_field_changed(self, field_name):
        """Update value input widget based on field type"""
        # Clear previous widget
        for widget in self.value_container.findChildren(QWidget):
            widget.setParent(None)
        
        # Update field description
        descriptions = {
            "severity": "Alarm severity level (0-100). 0=Low, 50=Medium, 100=Critical",
            "enabled": "Whether the alarm is active (T=True, F=False)",
            "notificationType": "Type of notification (0=Default, 1=Urgent, 2=Info)",
            "matchField": "Field used for matching (DSIDSigID or NormID)",
            "matchValue": "Value to match against (format: XX|SIGID for DSIDSigID)",
            "deviceIDs": "Device IDs in XML format or comma-separated list",
            "xMin": "Minimum number of events required to trigger the alarm"
        }
        self.field_description.setText(descriptions.get(field_name, f"Configure {field_name} value"))
        
        # Create appropriate widget
        if field_name in {"severity", "conditionType", "queryID", "alertRateMin", 
                         "alertRateCount", "pctAbove", "pctBelow", "offsetMin", "xMin",
                         "escSeverity", "escMin"}:
            widget = QSpinBox()
            if field_name in {"severity", "escSeverity"}:
                widget.setRange(0, 100)
            elif field_name in {"pctAbove", "pctBelow"}:
                widget.setRange(0, 100)
            elif field_name in {"alertRateMin", "offsetMin", "escMin"}:
                widget.setRange(0, 1440)
            else:
                widget.setRange(0, 10000)
            self.value_layout.addWidget(widget)
            
        elif field_name in {"enabled", "escEnabled", "useWatchlist", "matchNot"}:
            widget = QComboBox()
            widget.addItems(["T", "F"])
            self.value_layout.addWidget(widget)
            
        elif field_name in {"notificationType", "assigneeType", "escAssigneeType"}:
            widget = QComboBox()
            widget.addItems(["0", "1", "2"])
            self.value_layout.addWidget(widget)
            
        elif field_name == "matchField":
            widget = QComboBox()
            widget.addItems(["DSIDSigID", "NormID"])
            self.value_layout.addWidget(widget)
            
        elif field_name == "deviceIDs":
            widget = QTextEdit()
            widget.setMaximumHeight(60)
            widget.setPlaceholderText("Enter device IDs (XML format or comma-separated)")
            # XML mask değerleri için yardımcı bilgi ekle
            info_label = QLabel("<small>Not: XML format için mask değerleri numerik olmalıdır.</small>")
            info_label.setStyleSheet("color: #6c757d;")
            self.value_layout.addWidget(widget)
            self.value_layout.addWidget(info_label)
        
        else:
            widget = QLineEdit()
            if field_name == "matchValue":
                widget.setPlaceholderText("Format: XX|SIGID (e.g., 47|6000001)")
            self.value_layout.addWidget(widget)
        
        # Clear preview
        self.preview_model.setRowCount(0)
        self.apply_btn.setEnabled(False)
        self.validation_label.setText("")
    
    def preview_changes(self):
        """Preview the changes before applying"""
        self.preview_model.setRowCount(0)
        self.changes.clear()
        
        field_name = self.field_combo.currentText()
        widget = self.value_container.layout().itemAt(0).widget()
        
        if not widget:
            return
        
        # Get new value
        if isinstance(widget, QSpinBox):
            new_value = str(widget.value())
        elif isinstance(widget, QComboBox):
            new_value = widget.currentText()
        elif isinstance(widget, QTextEdit):
            new_value = widget.toPlainText()
        elif isinstance(widget, QLineEdit):
            new_value = widget.text()
        else:
            return
        
        # Determine section
        if field_name in self.parent.ALARM_DATA_FIELDS:
            section = "alarmData"
        else:
            section = "conditionData"
        
        # Ön doğrulama yap - özellikle deviceIDs için
        validation_warnings = []
        if field_name == "deviceIDs" and new_value.strip():
            is_valid, error_msg = DeviceIDValidator.validate(new_value)
            if not is_valid:
                validation_warnings.append(f"Uyarı: {error_msg}")
        
        # Count changes before building table
        change_count = 0
        alarm_names = []
        
        # Build preview table
        for row in sorted(self.selected_rows):
            if row < len(self.alarms):
                alarm = self.alarms[row]
                current_value = str(alarm.get_field(section, field_name) or "")
                
                # Add to preview table
                name_item = QStandardItem(alarm.name)
                field_item = QStandardItem(field_name)
                current_item = QStandardItem(current_value)
                new_item = QStandardItem(new_value)
                
                # Highlight changes
                if current_value != new_value:
                    new_item.setForeground(QBrush(QColor(76, 175, 80)))  # Green for new value
                    current_item.setForeground(QBrush(QColor(220, 53, 69)))  # Red for old value
                    change_count += 1
                    alarm_names.append(alarm.name)
                
                self.preview_model.appendRow([name_item, field_item, current_item, new_item])
                
                # Store change
                self.changes[row] = {
                    "alarm": alarm,
                    "section": section,
                    "field": field_name,
                    "old_value": current_value,
                    "new_value": new_value
                }
        
        # Enable apply button if there are changes
        if change_count > 0:
            self.apply_btn.setEnabled(True)
            # Show detailed information about changes
            detail_msg = f"✓ Ready to apply changes to {change_count} alarms\n\n"
            detail_msg += f"Field: {field_name}\n"
            detail_msg += f"New Value: {new_value}\n\n"
            detail_msg += "Alarms to be modified:\n"
            for i, name in enumerate(alarm_names[:5]):
                detail_msg += f"• {name}\n"
            if len(alarm_names) > 5:
                detail_msg += f"... and {len(alarm_names) - 5} more alarms"
            
            # Eğer doğrulama uyarıları varsa ekle
            if validation_warnings:
                detail_msg += "\n\n⚠️ Validation Warnings:\n"
                for warning in validation_warnings:
                    detail_msg += f"{warning}\n"
                self.validation_label.setText(detail_msg)
                self.validation_label.setStyleSheet("background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 4px;")
                # Uyarıya rağmen düğmeyi etkin bırak ama kullanıcıyı bilgilendir
            else:
                self.validation_label.setText(detail_msg)
                self.validation_label.setStyleSheet("background-color: #d4edda; color: #155724; padding: 10px; border-radius: 4px;")
        else:
            self.validation_label.setText("No changes to apply - all alarms already have this value")
            self.validation_label.setStyleSheet("background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px;")
            self.apply_btn.setEnabled(False)
    
    def validate_and_accept(self):
        """Validate changes before accepting"""
        if not self.changes:
            return
        
        # Validate each change
        errors = []
        field_name = self.field_combo.currentText()
        
        for row, change in self.changes.items():
            alarm = change["alarm"]
            new_value = change["new_value"]
            
            # Field-specific validation
            if field_name == "severity" or field_name == "escSeverity":
                try:
                    sev = int(new_value)
                    if sev < 0 or sev > 100:
                        errors.append(f"{alarm.name}: Severity must be 0-100")
                except:
                    errors.append(f"{alarm.name}: Invalid severity value")
            
            elif field_name == "matchValue" and change["section"] == "conditionData":
                match_field = alarm.get_field("conditionData", "matchField")
                if match_field == "DSIDSigID" and new_value:
                    import re
                    if not re.match(r'^\d+\|\d+$', new_value):
                        errors.append(f"{alarm.name}: Invalid matchValue format. Expected: XX|SIGID")
            
            elif field_name == "deviceIDs":
                # Use DeviceIDValidator for proper validation
                is_valid, error_msg = DeviceIDValidator.validate(new_value)
                if not is_valid:
                    errors.append(f"{alarm.name}: {error_msg}")
        
        if errors:
            # Hata mesajlarını daha detaylı bir şekilde göster
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("Validation Errors")
            error_dialog.setMinimumWidth(600)
            error_dialog.setWindowIcon(QIcon(":/icons/warning.png"))
            
            layout = QVBoxLayout(error_dialog)
            
            # Hata başlığı
            header = QLabel("Please fix the following errors:")
            header.setStyleSheet("font-weight: bold; color: #e74c3c;")
            layout.addWidget(header)
            
            # Hata mesajları için bir text edit widget
            error_text = QTextEdit()
            error_text.setReadOnly(True)
            error_text.setStyleSheet("background-color: #f8f9fa;")
            
            # Hatalar için zengin metin oluştur
            html_errors = "<ul>"
            for error in errors:
                if "mask" in error and "must be numeric" in error:
                    # Özellikle mask hatalarını daha açıklayıcı hale getir
                    html_errors += f'<li>{error.replace("must be numeric", "(must be numeric)")}</li>'
                else:
                    html_errors += f"<li>{error}</li>"
            html_errors += "</ul>"
            
            error_text.setHtml(html_errors)
            layout.addWidget(error_text)
            
            # Tamam butonu
            btn_ok = QPushButton("OK")
            btn_ok.clicked.connect(error_dialog.accept)
            layout.addWidget(btn_ok)
            
            error_dialog.exec_()
            return
        
        self.accept()

class DeviceIDValidator:
    """Validator for device ID field"""
    
    @staticmethod
    def validate(device_id_text: str) -> Tuple[bool, str]:
        """Validate device ID format"""
        if not device_id_text:
            return True, ""
        
        text = device_id_text.strip()
        
        # XML format
        if text.startswith("<") and text.endswith(">"):
            try:
                # Önce geçerli XML olup olmadığını kontrol et
                element = ET.fromstring(f"<root>{text}</root>")
                
                # Şimdi özel kontroller yap - deviceFilter/mask değerinin sayısal olduğunu kontrol et
                device_filters = element.findall(".//deviceFilter")
                for filter_elem in device_filters:
                    mask_elem = filter_elem.find("mask")
                    if mask_elem is not None and mask_elem.text:
                        mask_value = mask_elem.text.strip("'\" ")
                        if not mask_value.isdigit():
                            return False, f"Invalid device ID: mask value '{mask_value}' must be numeric"
                
                return True, ""
            except StdET.ParseError as e:
                return False, f"Invalid XML format: {str(e)}"
        
        # Comma-separated IDs
        elif "," in text or text.isdigit():
            ids = [id.strip() for id in text.split(",") if id.strip()]
            for id in ids:
                if not id.isdigit():
                    return False, f"Invalid device ID: {id} (must be numeric)"
            return True, ""
        
        else:
            return False, "Device IDs must be in XML format or comma-separated numbers"

class RuleFlowWidget(QWidget):
    """Widget to visualize rule flow using a simple diagram"""
    
    def __init__(self, rule_data, parent=None):
        super().__init__(parent)
        self.rule_data = rule_data
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Rule flow visualization using HTML/CSS
        flow_html = self.generate_rule_flow_html()
        
        self.flow_view = QTextEdit()
        self.flow_view.setReadOnly(True)
        self.flow_view.setHtml(flow_html)
        
        layout.addWidget(self.flow_view)
    
    def generate_rule_flow_html(self):
        """Generate HTML representation of rule flow"""
        html = """
        <html>
        <head>
        <style>
            body { 
                font-family: 'Segoe UI', Arial, sans-serif; 
                background: #2d2d2d; 
                padding: 20px; 
                color: #e0e0e0;
                margin: 0;
            }
            .flow-container { 
                background: #3a3a3a; 
                border-radius: 12px; 
                padding: 25px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            }
            h2 {
                color: #ffffff;
                font-weight: 300;
                margin-bottom: 20px;
                font-size: 24px;
            }
            h3 { 
                color: #ffffff; 
                margin-top: 20px;
                margin-bottom: 15px;
                font-size: 18px;
                display: flex;
                align-items: center;
            }
            p {
                margin: 8px 0;
                color: #e0e0e0;
            }
            .label { 
                font-weight: bold; 
                color: #b0b0b0; 
                margin-right: 8px;
            }
            .rule-box { 
                background: #1e88e5; 
                border: 2px solid #1565c0; 
                border-radius: 8px; 
                padding: 15px; 
                margin: 10px 0;
                color: white;
                box-shadow: 0 2px 8px rgba(30, 136, 229, 0.3);
            }
            .trigger-box { 
                background: #f57c00; 
                border: 2px solid #e65100; 
                border-radius: 8px; 
                padding: 15px; 
                margin: 10px 0;
                color: white;
                box-shadow: 0 2px 8px rgba(245, 124, 0, 0.3);
            }
            .filter-box { 
                background: #7b1fa2; 
                border: 2px solid #4a148c; 
                border-radius: 8px; 
                padding: 10px 15px; 
                margin: 8px 0;
                color: white;
                font-size: 14px;
            }
            .arrow { 
                text-align: center; 
                font-size: 32px; 
                color: #4a90e2; 
                margin: 20px 0;
                text-shadow: 0 2px 4px rgba(74, 144, 226, 0.3);
            }
            .property { 
                background: #43a047; 
                padding: 6px 12px; 
                border-radius: 4px; 
                margin: 4px;
                display: inline-block;
                color: white;
                font-size: 14px;
                box-shadow: 0 2px 4px rgba(67, 160, 71, 0.3);
            }
            .section-icon {
                margin-right: 8px;
                font-size: 20px;
            }
            .value-highlight {
                background: rgba(255, 255, 255, 0.1);
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            b {
                color: #ffffff;
            }
        </style>
        </head>
        <body>
        <div class="flow-container">
        """
        
        # Rule header
        html += f"""
        <h2>{self.rule_data.message}</h2>
        <p><span class="label">Rule ID:</span> <span class="value-highlight">{self.rule_data.id}</span></p>
        <p><span class="label">Severity:</span> <span class="value-highlight">{self.rule_data.severity}</span></p>
        <p><span class="label">SigID:</span> <span class="property">{self.rule_data.sigid or 'N/A'}</span></p>
        """
        
        # Triggers
        if self.rule_data.triggers:
            html += '<h3><span class="section-icon">🔔</span>Triggers</h3>'
            for trigger in self.rule_data.triggers:
                html += f"""
                <div class="trigger-box">
                    <b>{trigger.name}</b><br>
                    <span class="label">Count:</span> {trigger.count}<br>
                    <span class="label">Timeout:</span> {trigger.timeout} {trigger.time_unit}<br>
                    <span class="label">Threshold:</span> {trigger.threshold}
                </div>
                """
        
        html += '<div class="arrow">↓</div>'
        
        # Matches and Filters
        if self.rule_data.matches:
            html += '<h3><span class="section-icon">🔍</span>Match Conditions</h3>'
            for match in self.rule_data.matches:
                html += f"""
                <div class="rule-box">
                    <b>Match Type:</b> <span class="value-highlight">{match.match_type}</span> &nbsp;&nbsp; 
                    <b>Count:</b> <span class="value-highlight">{match.count}</span>
                """
                
                if match.filters:
                    html += "<br><br><b>Filters:</b>"
                    for filter_comp in match.filters:
                        filter_value = filter_comp.value[:50]
                        if len(filter_comp.value) > 50:
                            filter_value += "..."
                        html += f"""
                        <div class="filter-box">
                            <b>{filter_comp.type}</b> {filter_comp.operator} <span class="value-highlight">{filter_value}</span>
                        </div>
                        """
                
                html += "</div>"
        
        html += '<div class="arrow">↓</div>'
        
        # Properties
        if self.rule_data.properties:
            html += '<h3><span class="section-icon">📋</span>Properties</h3>'
            html += '<div style="margin-top: 10px;">'
            for key, value in self.rule_data.properties.items():
                html += f'<span class="property"><b>{key}:</b> {value}</span>'
            html += '</div>'
        
        html += """
        </div>
        </body>
        </html>
        """
        
        return html

class AlarmCreationDialog(QDialog):
    """Dialog for configuring alarm creation from rule"""
    
    def __init__(self, parent, rule_data, existing_alarms):
        super().__init__(parent)
        self.rule_data = rule_data
        self.existing_alarms = existing_alarms
        self.reference_alarm = None
        self.use_template = False
        self.setWindowTitle(f"Create Alarm from Rule: {rule_data.message}")
        self.setModal(True)
        self.setMinimumSize(600, 700)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Rule info
        info_group = QGroupBox("Rule Information")
        info_layout = QFormLayout()
        info_layout.addRow("Rule ID:", QLabel(self.rule_data.id))
        info_layout.addRow("SigID:", QLabel(self.rule_data.sigid))
        info_layout.addRow("Severity:", QLabel(str(self.rule_data.severity)))
        info_layout.addRow("Message:", QLabel(self.rule_data.message))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Template selection
        template_group = QGroupBox("Alarm Configuration")
        template_layout = QVBoxLayout()
        
        # Option 1: Use existing alarm as template
        self.use_template_radio = QCheckBox("Use existing alarm as template")
        self.use_template_radio.setChecked(True)
        template_layout.addWidget(self.use_template_radio)
        
        # Alarm template selector
        self.template_combo = QComboBox()
        self.template_combo.addItem("-- Select Template Alarm --")
        for alarm in self.existing_alarms:
            self.template_combo.addItem(f"{alarm.name} (Severity: {alarm.get_field('alarmData', 'severity')})")
        template_layout.addWidget(self.template_combo)
        
        # Option 2: Use default values
        self.use_defaults_radio = QCheckBox("Use default values")
        template_layout.addWidget(self.use_defaults_radio)
        
        # Connect radio buttons
        self.use_template_radio.toggled.connect(self.on_template_option_changed)
        self.use_defaults_radio.toggled.connect(self.on_template_option_changed)
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Preview
        preview_group = QGroupBox("Alarm Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Custom fields
        custom_group = QGroupBox("Custom Fields (Optional)")
        custom_layout = QFormLayout()
        
        self.alarm_name_edit = QLineEdit()
        self.alarm_name_edit.setText(f"Auto: {self.rule_data.message}")
        custom_layout.addRow("Alarm Name:", self.alarm_name_edit)
        
        self.severity_spin = QSpinBox()
        self.severity_spin.setRange(0, 100)
        self.severity_spin.setValue(self.rule_data.severity)
        custom_layout.addRow("Severity:", self.severity_spin)
        
        self.note_edit = QLineEdit()
        self.note_edit.setText(f"Auto-generated from rule {self.rule_data.id}")
        custom_layout.addRow("Note:", self.note_edit)
        
        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initialize preview
        self.update_preview()
        
    def on_template_option_changed(self, checked):
        if self.sender() == self.use_template_radio and checked:
            self.use_defaults_radio.setChecked(False)
            self.template_combo.setEnabled(True)
            self.use_template = True
        elif self.sender() == self.use_defaults_radio and checked:
            self.use_template_radio.setChecked(False)
            self.template_combo.setEnabled(False)
            self.use_template = False
            self.reference_alarm = None
        self.update_preview()
        
    def on_template_selected(self, index):
        if index > 0 and index <= len(self.existing_alarms):
            self.reference_alarm = self.existing_alarms[index - 1]
        else:
            self.reference_alarm = None
        self.update_preview()
        
    def update_preview(self):
        preview = "📋 Alarm Configuration:\n\n"
        
        if self.use_template and self.reference_alarm:
            preview += f"✅ Using template: {self.reference_alarm.name}\n"
            preview += f"   - Severity: {self.reference_alarm.get_field('alarmData', 'severity')}\n"
            preview += f"   - Assignee: {self.reference_alarm.get_field('alarmData', 'assignee')}\n"
            preview += f"   - Actions: {len(self.reference_alarm.data.get('actions', {}).get('actionData', []))} configured\n"
            preview += f"   - Device IDs: {self.reference_alarm.get_field('alarmData', 'deviceIDs') is not None}\n"
        else:
            preview += "✅ Using default values\n"
            preview += "   - Default severity from rule\n"
            preview += "   - Basic logging action\n"
            preview += "   - No device filters\n"
        
        preview += f"\n📝 Custom Settings:\n"
        preview += f"   - Name: {self.alarm_name_edit.text()}\n"
        preview += f"   - Severity: {self.severity_spin.value()}\n"
        preview += f"   - Note: {self.note_edit.text()}\n"
        preview += f"   - Match Value: 47|{self.rule_data.sigid}\n"
        
        self.preview_text.setText(preview)
        
    def get_alarm_config(self):
        """Get the configured alarm data"""
        if self.use_template and self.reference_alarm:
            # Deep copy template alarm data
            alarm_config = {
                "name": self.alarm_name_edit.text(),
                "minVersion": self.reference_alarm.min_version,
                "alarmData": copy.deepcopy(self.reference_alarm.data.get("alarmData", {})),
                "conditionData": copy.deepcopy(self.reference_alarm.data.get("conditionData", {})),
                "actions": copy.deepcopy(self.reference_alarm.data.get("actions", {}))
            }
            
            # Update specific fields
            alarm_config["alarmData"]["severity"] = str(self.severity_spin.value())
            alarm_config["alarmData"]["note"] = self.note_edit.text()
            alarm_config["conditionData"]["matchValue"] = f"47|{self.rule_data.sigid}"
            
        else:
            # Use default configuration
            alarm_config = {
                "name": self.alarm_name_edit.text(),
                "minVersion": DEFAULT_MIN_VERSION,
                "alarmData": {
                    "filters": "",
                    "note": self.note_edit.text(),
                    "notificationType": "0",
                    "severity": str(self.severity_spin.value()),
                    "escEnabled": "F",
                    "escSeverity": str(self.severity_spin.value()),
                    "escMin": "0",
                    "summaryTemplate": "",
                    "assignee": DEFAULT_ASSIGNEE_ID,
                    "assigneeType": "0",
                    "escAssignee": DEFAULT_ESC_ASSIGNEE_ID,
                    "escAssigneeType": "0",
                    "deviceIDs": "",
                    "enabled": "T"
                },
                "conditionData": {
                    "conditionType": "14",
                    "queryID": "0",
                    "alertRateMin": "0",
                    "alertRateCount": "0",
                    "pctAbove": "0",
                    "pctBelow": "0",
                    "offsetMin": "0",
                    "timeFilter": "",
                    "xMin": "10",
                    "useWatchlist": "F",
                    "matchField": "DSIDSigID",
                    "matchValue": f"47|{self.rule_data.sigid}",
                    "matchNot": "F"
                },
                "actions": {
                    "actionData": [
                        {
                            "actionType": "0",
                            "actionProcess": "6",
                            "actionAttributes": {}
                        }
                    ]
                }
            }
            
        return alarm_config

class AlarmTemplateSelectionDialog(QDialog):
    """Alarm template seçimi için geliştirilmiş dialog"""
    
    def __init__(self, parent, rule: RuleData, existing_alarms: List[AlarmModel]):
        super().__init__(parent)
        self.rule = rule
        self.existing_alarms = existing_alarms
        self.selected_template = None
        self._use_template = True
        
        self.setWindowTitle(f"Create Alarm from Rule: {rule.message}")
        self.setMinimumSize(700, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Rule bilgisi
        info_group = QGroupBox("Rule Information")
        info_layout = QFormLayout()
        info_layout.addRow("Rule ID:", QLabel(self.rule.id))
        info_layout.addRow("SigID:", QLabel(self.rule.sigid))
        info_layout.addRow("Severity:", QLabel(str(self.rule.severity)))
        info_layout.addRow("Message:", QLabel(self.rule.message[:100]))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Template seçimi
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout()
        
        # Seçenekler
        self.use_template_check = QCheckBox("Use existing alarm as template")
        self.use_template_check.setChecked(True)
        self.use_template_check.toggled.connect(self.on_template_option_changed)
        template_layout.addWidget(self.use_template_check)
        
        # Alarm listesi
        self.alarm_list = QListWidget()
        self.alarm_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Benzer severity'ye sahip alarm'ları üste koy
        sorted_alarms = sorted(self.existing_alarms, 
                             key=lambda a: abs(int(a.get_field("alarmData", "severity") or 0) - self.rule.severity))
        
        for alarm in sorted_alarms:
            severity = alarm.get_field("alarmData", "severity")
            item_text = f"{alarm.name} (Severity: {severity})"
            self.alarm_list.addItem(item_text)
        
        if self.alarm_list.count() > 0:
            self.alarm_list.setCurrentRow(0)
        
        template_layout.addWidget(self.alarm_list)
        
        # Template detayları
        self.template_details = QTextEdit()
        self.template_details.setReadOnly(True)
        self.template_details.setMaximumHeight(150)
        template_layout.addWidget(QLabel("Template Details:"))
        template_layout.addWidget(self.template_details)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Butonlar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Sinyal bağlantıları
        self.alarm_list.currentRowChanged.connect(self.on_template_selected)
        self.on_template_selected(0)
    
    def on_template_option_changed(self, checked):
        self._use_template = checked
        self.alarm_list.setEnabled(checked)
        self.template_details.setEnabled(checked)
    
    def on_template_selected(self, index):
        if index < 0 or index >= len(self.existing_alarms):
            return
        
        alarm = self.existing_alarms[index]
        self.selected_template = alarm
        
        # Detayları göster
        details = f"Name: {alarm.name}\n"
        details += f"Severity: {alarm.get_field('alarmData', 'severity')}\n"
        details += f"Notification Type: {alarm.get_field('alarmData', 'notificationType')}\n"
        details += f"Assignee: {alarm.get_field('alarmData', 'assignee')}\n"
        details += f"Device IDs: {bool(alarm.get_field('alarmData', 'deviceIDs'))}\n"
        details += f"Actions: {len(alarm.data.get('actions', {}).get('actionData', []))}"
        
        self.template_details.setText(details)
    
    def get_selected_template(self) -> Optional[AlarmModel]:
        return self.selected_template if self._use_template else None
    
    def use_template(self) -> bool:
        return self._use_template


class BatchAlarmCreationDialog(AlarmTemplateSelectionDialog):
    """Toplu alarm oluşturma için dialog"""
    
    def __init__(self, parent, rules: List[RuleData], existing_alarms: List[AlarmModel]):
        # selected_rules değişkenini ilk başta tanımla
        self.selected_rules = rules  # Değişken adı düzeltildi: rules -> selected_rules
        # rule değişkenini ekleme (bu, üst sınıfın setup_ui fonksiyonunda kullanılıyor)
        self.rule = rules[0]
        super().__init__(parent, rules[0], existing_alarms)
        self.setWindowTitle(f"Batch Create Alarms from {len(rules)} Rules")
    
    def setup_ui(self):
        """UI setup override - ekstra kontroller ekle"""
        super().setup_ui()
        
        # Toplu işlem hakkında bilgi ekleyin
        info_label = QLabel(f"<b>⚠️ Bu işlem {len(self.selected_rules)} kural için alarm oluşturacak.</b>")
        info_label.setStyleSheet("color: #e67e22; margin-top: 10px;")
        
        # Rule sayısı bilgisi - öncelik seviyelerine göre sayılar
        low_priority_rules = len([r for r in self.selected_rules if 0 <= r.severity <= 39])
        medium_priority_rules = len([r for r in self.selected_rules if 40 <= r.severity <= 69])
        high_priority_rules = len([r for r in self.selected_rules if 70 <= r.severity <= 100])
        
        rules_info = QLabel(f"<ul>" +
                          f"<li>Düşük öncelikli ({low_priority_rules})</li>" +
                          f"<li>Orta öncelikli ({medium_priority_rules})</li>" +
                          f"<li>Yüksek öncelikli ({high_priority_rules})</li>" +
                          f"</ul>")
        
        # Get the main layout
        main_layout = self.layout()
        
        # Bilgileri ekle
        idx = main_layout.count() - 1  # Son öğeden önce ekle (buttons)
        main_layout.insertWidget(idx, info_label)
        main_layout.insertWidget(idx + 1, rules_info)
        
        # Template filtresi
        template_filter_layout = QHBoxLayout()
        template_filter_layout.addWidget(QLabel("Template Filtrele:"))
        self.template_filter = QLineEdit()
        self.template_filter.setPlaceholderText("Template aramak için metin girin...")
        self.template_filter.textChanged.connect(self.filter_templates)
        template_filter_layout.addWidget(self.template_filter)
        
        # Daha iyi görünüm için ayarlamalar
        self.alarm_list.setMinimumHeight(300)  # Listeyi daha uzun göster
        
        # Filtre kontrolünü ekle
        main_layout.insertLayout(main_layout.indexOf(self.alarm_list), template_filter_layout)
    
    def filter_templates(self, text):
        """Template listesini filtrele"""
        for i in range(self.alarm_list.count()):
            item = self.alarm_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

class SettingsDialog(QDialog):
    """Dialog for editing application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(700, 500)
        
        # Create a backup of settings for cancel operation
        self.settings_backup = copy.deepcopy(app_settings.current)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # General settings tab
        self.general_tab = QWidget()
        self.tab_widget.addTab(self.general_tab, "General")
        
        # XML Security tab
        self.xml_security_tab = QWidget()
        self.tab_widget.addTab(self.xml_security_tab, "XML Security")
        
        # Default Values tab
        self.defaults_tab = QWidget()
        self.tab_widget.addTab(self.defaults_tab, "Default Values")
        
        # Severity tab
        self.severity_tab = QWidget()
        self.tab_widget.addTab(self.severity_tab, "Severity Levels")
        
        # UI Settings tab
        self.ui_tab = QWidget()
        self.tab_widget.addTab(self.ui_tab, "UI Settings")
        
        # Create General tab content
        self.setup_general_tab()
        
        # Create XML Security tab content
        self.setup_xml_security_tab()
        
        # Create Defaults tab content
        self.setup_defaults_tab()
        
        # Create Severity tab content
        self.setup_severity_tab()
        
        # Create UI Settings tab content
        self.setup_ui_tab()
        
        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        
        # Get the restore defaults button and connect it
        restore_btn = self.button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        restore_btn.clicked.connect(self.restore_defaults)
        
        layout.addWidget(self.button_box)
    
    def setup_general_tab(self):
        layout = QFormLayout(self.general_tab)
        
        # Auto backup settings
        self.enable_auto_backup = QCheckBox("Enable automatic backups")
        layout.addRow("Auto Backup:", self.enable_auto_backup)
        
        self.max_backups = QSpinBox()
        self.max_backups.setRange(1, 20)
        layout.addRow("Maximum number of backups:", self.max_backups)
        
        # Auto save settings
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(0, 3600)
        self.auto_save_interval.setSuffix(" seconds")
        self.auto_save_interval.setSpecialValueText("Disabled")
        layout.addRow("Auto-save interval:", self.auto_save_interval)
        
        self.auto_validate_on_save = QCheckBox("Automatically validate on save")
        layout.addRow("Validation:", self.auto_validate_on_save)
    
    def setup_xml_security_tab(self):
        layout = QFormLayout(self.xml_security_tab)
        
        # XML security settings
        self.xml_max_entities = QSpinBox()
        self.xml_max_entities.setRange(10, 1000)
        layout.addRow("Maximum XML entities:", self.xml_max_entities)
        
        self.xml_max_entity_expansion_size = QSpinBox()
        self.xml_max_entity_expansion_size.setRange(1, 100)
        self.xml_max_entity_expansion_size.setSuffix(" MB")
        layout.addRow("Maximum entity expansion size:", self.xml_max_entity_expansion_size)
        
        self.xml_max_entity_expansion_count = QSpinBox()
        self.xml_max_entity_expansion_count.setRange(10, 1000)
        layout.addRow("Maximum entity expansion count:", self.xml_max_entity_expansion_count)
        
        self.max_xml_file_size = QSpinBox()
        self.max_xml_file_size.setRange(1, 1000)
        self.max_xml_file_size.setSuffix(" MB")
        layout.addRow("Maximum XML file size:", self.max_xml_file_size)
    
    def setup_defaults_tab(self):
        layout = QFormLayout(self.defaults_tab)
        
        # Default values
        self.default_assignee_id = QLineEdit()
        layout.addRow("Default Assignee ID:", self.default_assignee_id)
        
        self.default_esc_assignee_id = QLineEdit()
        layout.addRow("Default Escalation Assignee ID:", self.default_esc_assignee_id)
        
        self.default_min_version = QLineEdit()
        layout.addRow("Default Minimum Version:", self.default_min_version)
        
        self.default_device_filter_prefix = QLineEdit()
        layout.addRow("Default Device Filter Prefix:", self.default_device_filter_prefix)
        
        # Alarm Generation Prefix ayarını ekle
        self.alarm_generation_prefix_edit = QLineEdit()
        self.alarm_generation_prefix_edit.setText(str(app_settings.get("alarm_generation_prefix", "47")))
        layout.addRow("Alarm Generation Prefix:", self.alarm_generation_prefix_edit)
        
        # Açıklama ekle
        prefix_info = QLabel("Default prefix for the DSIDSigID match value (e.g. '47|123456')")
        prefix_info.setStyleSheet("color: #666; font-style: italic;")
        layout.addRow("", prefix_info)
    
    def setup_severity_tab(self):
        layout = QVBoxLayout(self.severity_tab)
        
        info_label = QLabel(
            "Set the maximum threshold for each severity level. " +
            "The ranges will be adjusted automatically (Low: 0-X, Medium: X+1-Y, High: Y+1-Z, Critical: Z+1-100)."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        self.severity_low_max = QSpinBox()
        self.severity_low_max.setRange(1, 98)
        form_layout.addRow("Low Maximum (0-X):", self.severity_low_max)
        
        self.severity_medium_max = QSpinBox()
        self.severity_medium_max.setRange(2, 99)
        form_layout.addRow("Medium Maximum (X+1-Y):", self.severity_medium_max)
        
        self.severity_high_max = QSpinBox()
        self.severity_high_max.setRange(3, 99)
        form_layout.addRow("High Maximum (Y+1-Z):", self.severity_high_max)
        
        # Preview
        group_box = QGroupBox("Preview")
        layout.addWidget(group_box)
        
        preview_layout = QVBoxLayout(group_box)
        self.severity_preview = QLabel()
        preview_layout.addWidget(self.severity_preview)
        
        # Connect spinboxes to update preview
        self.severity_low_max.valueChanged.connect(self.update_severity_preview)
        self.severity_medium_max.valueChanged.connect(self.update_severity_preview)
        self.severity_high_max.valueChanged.connect(self.update_severity_preview)
    
    def setup_ui_tab(self):
        layout = QFormLayout(self.ui_tab)
        
        # Theme settings
        self.dark_theme = QCheckBox("Use Dark Theme")
        layout.addRow("Theme:", self.dark_theme)
        
        # Window size
        self.window_width = QSpinBox()
        self.window_width.setRange(800, 3840)
        self.window_width.setSuffix(" px")
        layout.addRow("Window Width:", self.window_width)
        
        self.window_height = QSpinBox()
        self.window_height.setRange(600, 2160)
        self.window_height.setSuffix(" px")
        layout.addRow("Window Height:", self.window_height)
        
        # Table row height
        self.table_row_height = QSpinBox()
        self.table_row_height.setRange(15, 50)
        self.table_row_height.setSuffix(" px")
        layout.addRow("Table Row Height:", self.table_row_height)
        
        # Preview height
        self.preview_max_height = QSpinBox()
        self.preview_max_height.setRange(100, 500)
        self.preview_max_height.setSuffix(" px")
        layout.addRow("Preview Maximum Height:", self.preview_max_height)
        
        # Dialog sizes
        self.dialog_min_width = QSpinBox()
        self.dialog_min_width.setRange(400, 1000)
        self.dialog_min_width.setSuffix(" px")
        layout.addRow("Dialog Minimum Width:", self.dialog_min_width)
        
        self.dialog_min_height = QSpinBox()
        self.dialog_min_height.setRange(300, 1000)
        self.dialog_min_height.setSuffix(" px")
        layout.addRow("Dialog Minimum Height:", self.dialog_min_height)
    
    def update_severity_preview(self):
        """Update the severity preview labels based on current values"""
        low_max = self.severity_low_max.value()
        medium_max = self.severity_medium_max.value()
        high_max = self.severity_high_max.value()
        
        # Ensure valid ranges
        if medium_max <= low_max:
            medium_max = low_max + 1
            self.severity_medium_max.setValue(medium_max)
        
        if high_max <= medium_max:
            high_max = medium_max + 1
            self.severity_high_max.setValue(high_max)
        
        # Create the preview text
        preview_text = (
            f"<b>Low:</b> 0-{low_max}<br>"
            f"<b>Medium:</b> {low_max + 1}-{medium_max}<br>"
            f"<b>High:</b> {medium_max + 1}-{high_max}<br>"
            f"<b>Critical:</b> {high_max + 1}-100"
        )
        
        self.severity_preview.setText(preview_text)
    
    def load_settings(self):
        """Load current settings into UI controls"""
        # General settings
        self.enable_auto_backup.setChecked(app_settings.get("enable_auto_backup"))
        self.max_backups.setValue(app_settings.get("max_backups"))
        self.auto_save_interval.setValue(app_settings.get("auto_save_interval"))
        self.auto_validate_on_save.setChecked(app_settings.get("auto_validate_on_save"))
        
        # XML Security settings
        self.xml_max_entities.setValue(app_settings.get("xml_max_entities"))
        self.xml_max_entity_expansion_size.setValue(
            app_settings.get("xml_max_entity_expansion_size") // (1024 * 1024)  # Convert bytes to MB
        )
        self.xml_max_entity_expansion_count.setValue(app_settings.get("xml_max_entity_expansion_count"))
        self.max_xml_file_size.setValue(
            app_settings.get("max_xml_file_size") // (1024 * 1024)  # Convert bytes to MB
        )
        
        # Default values
        self.default_assignee_id.setText(app_settings.get("default_assignee_id"))
        self.default_esc_assignee_id.setText(app_settings.get("default_esc_assignee_id"))
        self.default_min_version.setText(app_settings.get("default_min_version"))
        self.default_device_filter_prefix.setText(app_settings.get("default_device_filter_prefix"))
        
        # Alarm Generation Prefix
        if hasattr(self, "alarm_generation_prefix_edit"):
            self.alarm_generation_prefix_edit.setText(app_settings.get("alarm_generation_prefix", "47"))
        
        # Severity levels
        self.severity_low_max.setValue(app_settings.get("severity_low_max"))
        self.severity_medium_max.setValue(app_settings.get("severity_medium_max"))
        self.severity_high_max.setValue(app_settings.get("severity_high_max"))
        self.update_severity_preview()
        
        # UI settings
        self.dark_theme.setChecked(app_settings.get("dark_theme"))
        self.window_width.setValue(app_settings.get("window_width"))
        self.window_height.setValue(app_settings.get("window_height"))
        self.table_row_height.setValue(app_settings.get("table_row_height"))
        self.preview_max_height.setValue(app_settings.get("preview_max_height"))
        self.dialog_min_width.setValue(app_settings.get("dialog_min_width"))
        self.dialog_min_height.setValue(app_settings.get("dialog_min_height"))
    
    def save_settings(self):
        """Save settings from UI controls to config"""
        # General settings
        app_settings.set("enable_auto_backup", self.enable_auto_backup.isChecked())
        app_settings.set("max_backups", self.max_backups.value())
        app_settings.set("auto_save_interval", self.auto_save_interval.value())
        app_settings.set("auto_validate_on_save", self.auto_validate_on_save.isChecked())
        
        # XML Security settings
        app_settings.set("xml_max_entities", self.xml_max_entities.value())
        app_settings.set("xml_max_entity_expansion_size", 
                         self.xml_max_entity_expansion_size.value() * 1024 * 1024)  # Convert MB to bytes
        app_settings.set("xml_max_entity_expansion_count", self.xml_max_entity_expansion_count.value())
        app_settings.set("max_xml_file_size", 
                         self.max_xml_file_size.value() * 1024 * 1024)  # Convert MB to bytes
        
        # Default values
        app_settings.set("default_assignee_id", self.default_assignee_id.text())
        app_settings.set("default_esc_assignee_id", self.default_esc_assignee_id.text())
        app_settings.set("default_min_version", self.default_min_version.text())
        app_settings.set("default_device_filter_prefix", self.default_device_filter_prefix.text())
        
        # Alarm Generation Prefix
        if hasattr(self, "alarm_generation_prefix_edit"):
            app_settings.set("alarm_generation_prefix", self.alarm_generation_prefix_edit.text())
        
        # Severity levels
        app_settings.set("severity_low_max", self.severity_low_max.value())
        app_settings.set("severity_medium_max", self.severity_medium_max.value())
        app_settings.set("severity_high_max", self.severity_high_max.value())
        
        # UI settings
        app_settings.set("dark_theme", self.dark_theme.isChecked())
        app_settings.set("window_width", self.window_width.value())
        app_settings.set("window_height", self.window_height.value())
        app_settings.set("table_row_height", self.table_row_height.value())
        app_settings.set("preview_max_height", self.preview_max_height.value())
        app_settings.set("dialog_min_width", self.dialog_min_width.value())
        app_settings.set("dialog_min_height", self.dialog_min_height.value())
        
        # Save to file
        if app_settings.save():
            # Update global variables with new settings
            update_globals_from_settings()
            
            # Notify user
            QMessageBox.information(
                self, 
                "Settings Saved", 
                "Settings have been saved successfully.\n\n"
                "Some changes will take effect the next time you restart the application."
            )
            self.accept()
        else:
            QMessageBox.warning(
                self, 
                "Error", 
                "Failed to save settings. Please check file permissions."
            )
    
    def restore_defaults(self):
        """Restore all settings to default values"""
        if QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            app_settings.reset()
            self.load_settings()
    
    def reject(self):
        """Cancel changes and restore previous settings"""
        app_settings.current = self.settings_backup
        super().reject()

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



