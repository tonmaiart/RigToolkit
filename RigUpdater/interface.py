import os
import importlib

import maya.cmds as cmds

from tmlib.module.PySide import QtCore, QtGui, QtWidgets
from tmlib.ui.interface_template import ToolkitWindow
from tmlib.ui import uitools

from RigUpdater import function

# launch()/launch_toolkit() only reload this interface module, not its
# sibling function.py -- reload it explicitly so scene-logic edits take
# effect without restarting Maya.
importlib.reload(function)

COL_GEO = 0
COL_STATUS = 1

COL_MAP_SOURCE = 0
COL_MAP_UPDATE = 1

UNRESOLVED_TEXT = "Unresolve"


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.source_ref_info = None
        self.update_ref_info = None
        self.source_geo_list = []  # list[str], index-aligned with source info table rows
        self.update_geo_list = []  # list[str], index-aligned with update info/mapping rows
        self.row_sources = []  # list[list[str]], index-aligned with update_geo_list

        for table in (
            self.ui.tableWidget_geo_source_info,
            self.ui.tableWidget_geo_update_info,
            self.ui.tableWidget_mapping_skin,
        ):
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self._configure_table_columns()

        self.connect_signal_ui()
        self.restore_session()

    def _configure_table_columns(self):
        """Give Geo-name columns most of the width -- Resolve Status only
        ever holds "Resolved"/"Unresolved" and doesn't need much room."""
        for table in (
            self.ui.tableWidget_geo_source_info,
            self.ui.tableWidget_geo_update_info,
        ):
            header = table.horizontalHeader()
            header.setSectionResizeMode(COL_GEO, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(COL_STATUS, QtWidgets.QHeaderView.ResizeToContents)

        mapping_header = self.ui.tableWidget_mapping_skin.horizontalHeader()
        mapping_header.setSectionResizeMode(COL_MAP_SOURCE, QtWidgets.QHeaderView.Stretch)
        mapping_header.setSectionResizeMode(COL_MAP_UPDATE, QtWidgets.QHeaderView.Stretch)

        # multiple Source Geo names are shown one-per-line (not comma-joined
        # word-wrap) -- rows grow tall enough via resizeRowToContents instead
        self.ui.tableWidget_mapping_skin.setWordWrap(False)

    def connect_signal_ui(self):
        self.ui.pushButton_load_source_reference.clicked.connect(
            self.load_source_reference
        )
        self.ui.pushButton_update_reference.clicked.connect(self.load_update_reference)
        self.ui.pushButton_add_mapping.clicked.connect(self.add_selected_to_mapping)
        self.ui.pushButton_auto_resolve.clicked.connect(self.auto_resolve)
        self.ui.pushButton_clear_selected.clicked.connect(self.clear_selected)
        self.ui.pushButton_update_rig.clicked.connect(self.update_rig)

        self.ui.tableWidget_geo_source_info.itemSelectionChanged.connect(
            lambda: self._select_geo_in_scene(
                self.ui.tableWidget_geo_source_info, self.source_geo_list
            )
        )
        self.ui.tableWidget_geo_update_info.itemSelectionChanged.connect(
            lambda: self._select_geo_in_scene(
                self.ui.tableWidget_geo_update_info, self.update_geo_list
            )
        )

    def _select_geo_in_scene(self, table, geo_list):
        rows = self._selected_rows(table)
        geos = [geo_list[row] for row in rows if row < len(geo_list)]
        existing = [geo for geo in geos if cmds.objExists(geo)]

        if existing:
            cmds.select(existing, replace=True)
        else:
            cmds.select(clear=True)

    # ------------------------------------------------------------------
    # Load Reference
    # ------------------------------------------------------------------

    def _get_selected_node(self):
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Select a node that belongs to the reference first.")
            return None
        return selection[0]

    def _selected_rows(self, table):
        return sorted({index.row() for index in table.selectedIndexes()})

    def _populate_geo_table(self, table, geo_list):
        table.setRowCount(len(geo_list))
        for row, geo in enumerate(geo_list):
            geo_item = QtWidgets.QTableWidgetItem(geo.split("|")[-1])
            geo_item.setFlags(geo_item.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(row, COL_GEO, geo_item)

            status_item = QtWidgets.QTableWidgetItem("")
            status_item.setFlags(status_item.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(row, COL_STATUS, status_item)

    def load_source_reference(self):
        node = self._get_selected_node()
        if not node:
            return

        info = function.get_reference_info(node)
        if not info:
            cmds.warning(
                "Selected node isn't part of a reference with a '{}' group.".format(
                    function.GEO_GROUP_NAME
                )
            )
            return

        self.source_ref_info = info
        self.ui.lineEdit.setText(info["ref_name"])

        self.source_geo_list = function.list_geo_meshes(info["geo_group"])
        # drop sources that no longer exist in the freshly loaded reference,
        # leaving the rest of each row's mapping untouched
        for row, sources in enumerate(self.row_sources):
            pruned = [source for source in sources if source in self.source_geo_list]
            if pruned != sources:
                self.set_row_sources(row, pruned)

        self._populate_geo_table(self.ui.tableWidget_geo_source_info, self.source_geo_list)
        self.refresh_resolve_status()
        self.save_session()

    def load_update_reference(self):
        node = self._get_selected_node()
        if not node:
            return

        info = function.get_reference_info(node)
        if not info:
            cmds.warning(
                "Selected node isn't part of a reference with a '{}' group.".format(
                    function.GEO_GROUP_NAME
                )
            )
            return

        self.update_ref_info = info
        self.ui.lineEdit_2.setText(info["ref_name"])

        self.update_geo_list = function.list_geo_meshes(info["geo_group"])
        self.row_sources = [[] for _ in self.update_geo_list]

        self._populate_geo_table(self.ui.tableWidget_geo_update_info, self.update_geo_list)
        self.rebuild_mapping_table()
        self.save_session()

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def rebuild_mapping_table(self):
        """(Re)build the preview table with one fixed row per Update Geo.

        Called as soon as the Update Reference loads -- every Update Geo is
        visible up front, Source Geo showing "Unresolve" until mapped.
        """
        table = self.ui.tableWidget_mapping_skin
        table.setRowCount(len(self.update_geo_list))

        for row, update_geo in enumerate(self.update_geo_list):
            update_item = QtWidgets.QTableWidgetItem(update_geo.split("|")[-1])
            update_item.setFlags(update_item.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(row, COL_MAP_UPDATE, update_item)

            source_item = QtWidgets.QTableWidgetItem(UNRESOLVED_TEXT)
            source_item.setFlags(source_item.flags() & ~QtCore.Qt.ItemIsEditable)
            source_item.setForeground(QtGui.QColor("red"))
            table.setItem(row, COL_MAP_SOURCE, source_item)

        table.resizeRowsToContents()
        self.refresh_resolve_status()

    def set_row_sources(self, row, sources):
        self.row_sources[row] = sources
        short_names = [source.split("|")[-1] for source in sources]
        resolved = bool(sources)

        table = self.ui.tableWidget_mapping_skin
        item = table.item(row, COL_MAP_SOURCE)
        # one name per line rather than comma-joined -- wordWrap is off on
        # this table so a name is never broken mid-word, the row just grows
        item.setText("\n".join(short_names) if resolved else UNRESOLVED_TEXT)
        item.setForeground(QtGui.QColor("green") if resolved else QtGui.QColor("red"))
        table.resizeRowToContents(row)

        self.refresh_resolve_status()

    def add_selected_to_mapping(self):
        source_rows = self._selected_rows(self.ui.tableWidget_geo_source_info)
        update_rows = self._selected_rows(self.ui.tableWidget_geo_update_info)

        if not source_rows or not update_rows:
            cmds.warning(
                "Select at least one Geo in Source Reference and Update "
                "Reference before adding to mapping."
            )
            return

        for update_row in update_rows:
            sources = list(self.row_sources[update_row])
            for source_row in source_rows:
                source = self.source_geo_list[source_row]
                if source not in sources:
                    sources.append(source)
            self.set_row_sources(update_row, sources)

        self.save_session()

    def auto_resolve(self):
        if not self.source_ref_info or not self.update_ref_info:
            cmds.warning("Load both Source Reference and Update Reference first.")
            return

        matches = function.auto_match(self.source_geo_list, self.update_geo_list)
        for row, update_geo in enumerate(self.update_geo_list):
            match = matches.get(update_geo)
            if not match:
                continue

            sources = list(self.row_sources[row])
            for source in match:
                if source not in sources:
                    sources.append(source)
            self.set_row_sources(row, sources)

        self.save_session()

    def clear_selected(self):
        rows = self._selected_rows(self.ui.tableWidget_geo_update_info)
        if not rows:
            cmds.warning("Select an Update Geo row to clear its mapping first.")
            return

        for row in rows:
            self.set_row_sources(row, [])

        self.save_session()

    def refresh_resolve_status(self):
        mapped_sources = {source for sources in self.row_sources for source in sources}
        resolved_updates = {
            self.update_geo_list[row]
            for row, sources in enumerate(self.row_sources)
            if sources
        }

        self._set_status_column(
            self.ui.tableWidget_geo_source_info, self.source_geo_list, mapped_sources
        )
        self._set_status_column(
            self.ui.tableWidget_geo_update_info, self.update_geo_list, resolved_updates
        )

    def _set_status_column(self, table, geo_list, mapped_set):
        for row, geo in enumerate(geo_list):
            resolved = geo in mapped_set
            item = table.item(row, COL_STATUS)
            if item is None:
                continue
            item.setText("Resolved" if resolved else "Unresolved")
            item.setForeground(
                QtGui.QColor("green") if resolved else QtGui.QColor("red")
            )

    # ------------------------------------------------------------------
    # RigData session persistence
    # ------------------------------------------------------------------

    def save_session(self):
        data = {
            "source_ref_path": self.source_ref_info["ref_path"]
            if self.source_ref_info
            else None,
            "update_ref_path": self.update_ref_info["ref_path"]
            if self.update_ref_info
            else None,
            "mapping": {
                update_geo: sources
                for update_geo, sources in zip(self.update_geo_list, self.row_sources)
                if sources
            },
            "keep_old_geo": self.ui.checkBox_keep_old_geo.isChecked(),
        }
        function.save_session(data)

    def restore_session(self):
        session = function.load_session()
        if not session:
            return

        source_info = function.get_reference_info_by_path(
            session.get("source_ref_path")
        )
        if source_info:
            self.source_ref_info = source_info
            self.ui.lineEdit.setText(source_info["ref_name"])
            self.source_geo_list = function.list_geo_meshes(source_info["geo_group"])
            self._populate_geo_table(
                self.ui.tableWidget_geo_source_info, self.source_geo_list
            )

        update_info = function.get_reference_info_by_path(
            session.get("update_ref_path")
        )
        if update_info:
            self.update_ref_info = update_info
            self.ui.lineEdit_2.setText(update_info["ref_name"])
            self.update_geo_list = function.list_geo_meshes(update_info["geo_group"])
            self.row_sources = [[] for _ in self.update_geo_list]

            self._populate_geo_table(
                self.ui.tableWidget_geo_update_info, self.update_geo_list
            )
            self.rebuild_mapping_table()

            saved_mapping = session.get("mapping", {})
            for row, update_geo in enumerate(self.update_geo_list):
                sources = [
                    source
                    for source in saved_mapping.get(update_geo, [])
                    if cmds.objExists(source)
                ]
                if sources:
                    self.set_row_sources(row, sources)

        self.ui.checkBox_keep_old_geo.setChecked(bool(session.get("keep_old_geo")))
        self.refresh_resolve_status()

    # ------------------------------------------------------------------
    # Update Rig
    # ------------------------------------------------------------------

    @uitools.undoable
    def update_rig(self):
        if not self.source_ref_info or not self.update_ref_info:
            cmds.warning("Load both Source Reference and Update Reference first.")
            return

        mapping = [
            (update_geo, sources)
            for update_geo, sources in zip(self.update_geo_list, self.row_sources)
            if sources
        ]
        unresolved = [
            update_geo
            for update_geo, sources in zip(self.update_geo_list, self.row_sources)
            if not sources
        ]

        if unresolved:
            result = cmds.confirmDialog(
                title="Unresolved Update Geo",
                message="{} Update Geo have no Source Geo mapped and will be "
                "left without transferred skin weights:\n\n{}".format(
                    len(unresolved),
                    "\n".join(each.split("|")[-1] for each in unresolved),
                ),
                button=["Continue", "Cancel"],
                defaultButton="Cancel",
                cancelButton="Cancel",
                dismissString="Cancel",
            )
            if result != "Continue":
                return

        # transfer skin first, while the source reference's meshes are
        # still live at their currently-known paths
        all_sources = [source for _, sources in mapping for source in sources]
        function.backup_skin(all_sources)

        for update_geo, sources in mapping:
            function.transfer_skin(sources, update_geo)

        if self.ui.checkBox_keep_old_geo.isChecked():
            function.keep_source_reference_as_backup(self.source_ref_info)
        else:
            function.discard_source_reference(self.source_ref_info["ref_path"])

        function.cleanup_materials()
        function.attach_update_geo(self.update_ref_info)

        cmds.inViewMessage(amg="<hl>Rig Updated!</hl>", pos="botCenter", fade=True)

        self.reset_state()

    def reset_state(self):
        self.source_ref_info = None
        self.update_ref_info = None
        self.source_geo_list = []
        self.update_geo_list = []
        self.row_sources = []

        self.ui.lineEdit.clear()
        self.ui.lineEdit_2.clear()
        self.ui.tableWidget_geo_source_info.setRowCount(0)
        self.ui.tableWidget_geo_update_info.setRowCount(0)
        self.ui.tableWidget_mapping_skin.setRowCount(0)

        function.clear_session()
