package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EventObject;
import java.util.List;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.DefaultCellEditor;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.event.TableModelEvent;
import javax.swing.event.TableModelListener;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;

import net.sourceforge.jvlt.core.StringPair;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

/**
 * Panel for setting custom fields (used in the advanced entry dialog)
 */
public class CustomFieldPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private static class CustomFieldCellRenderer extends
			DefaultTableCellRenderer {
		private static final long serialVersionUID = 1L;

		@Override
		public Component getTableCellRendererComponent(JTable table,
				Object value, boolean isSelected, boolean hasFocus, int row,
				int column) {
			JLabel label = (JLabel) super.getTableCellRendererComponent(table,
					value, isSelected, hasFocus, row, column);
			if (value == null) {
				label.setText(I18nService.getString("Labels",
						"double_click_to_edit"));
			}

			return label;
		}
	}

	private static class CustomFieldTableModel extends AbstractTableModel {
		private static final long serialVersionUID = 1L;

		private final List<String> keys = new ArrayList<String>();
		private final List<String> values = new ArrayList<String>();

		public int getColumnCount() {
			return 2;
		}

		public int getRowCount() {
			return keys.size() + 1;
		}

		public Object getValueAt(int rowIndex, int columnIndex) {
			if (rowIndex < 0 || rowIndex >= keys.size()) {
				return null;
			}

			if (columnIndex == 0) {
				return keys.get(rowIndex);
			} else if (columnIndex == 1) {
				return values.get(rowIndex);
			} else {
				return null;
			}
		}

		@Override
		public boolean isCellEditable(int rowIndex, int columnIndex) {
			return columnIndex == 0 || columnIndex == 1;
		}

		@Override
		public Class<? extends Object> getColumnClass(int column) {
			return String.class;
		}

		@Override
		public void setValueAt(Object value, int rowIndex, int columnIndex) {
			if (columnIndex == 0) {
				if (rowIndex == keys.size()) {
					/* Add new key-value pair */
					keys.add((String) value);
					values.add(null);
					fireTableRowsUpdated(rowIndex, rowIndex);
					fireTableRowsInserted(rowIndex + 1, rowIndex + 1);
				} else {
					/* Replace a key */
					keys.set(rowIndex, (String) value);
					fireTableRowsUpdated(rowIndex, rowIndex);
				}
			} else if (columnIndex == 1) {
				if (rowIndex < values.size()) {
					/* Set/replace a value */
					values.set(rowIndex, (String) value);
					fireTableRowsUpdated(rowIndex, rowIndex);
				}
			}
		}

		@Override
		public String getColumnName(int columnIndex) {
			if (columnIndex == 0) {
				return I18nService.getString("Labels", "field_name");
			}
			return I18nService.getString("Labels", "field_value");
		}

		public void removeRow(int row) {
			if (row < 0 || row >= keys.size()) {
				return;
			}

			keys.remove(row);
			values.remove(row);
			fireTableRowsDeleted(row, row);
		}

		public void insertRow(int row, String key, String value) {
			if (row < 0 || row > keys.size()) {
				return;
			}

			keys.add(row, key);
			values.add(row, value);
			fireTableRowsInserted(row, row);
		}
	}

	private static class CustomFieldCellEditor extends DefaultCellEditor {
		private static final long serialVersionUID = 1L;

		public CustomFieldCellEditor(JComboBox box) {
			super(box);
		}

		public CustomFieldCellEditor(JTextField field) {
			super(field);
		}

		@Override
		public boolean isCellEditable(EventObject evt) {
			if (evt instanceof MouseEvent)
				return ((MouseEvent) evt).getClickCount() >= 2;
			else
				return false;
		}
	}

	private final CustomFieldTableModel tableModel;
	private int popupRow = -1; // Row on which popup menu was opened

	private final JTable table;
	private final JComboBox keyBox;
	private final JTextField valueField;
	private final CustomFieldCellEditor keyCellEditor;
	private final CustomFieldCellEditor valueCellEditor;
	private final JPopupMenu menu;
	private final Action upAction;
	private final Action downAction;

	public CustomFieldPanel() {
		CustomConstraints cc = new CustomConstraints();

		ActionListener upDownListener = new ActionListener() {
			public void actionPerformed(ActionEvent e) {
				if (e.getActionCommand().equals("up")) {
					moveElement(table.getSelectedRow(), true);
				} else if (e.getActionCommand().equals("down")) {
					moveElement(table.getSelectedRow(), false);
				}
			}
		};
		upAction = GUIUtils.createIconAction(upDownListener, "up");
		downAction = GUIUtils.createIconAction(upDownListener, "down");

		keyBox = new JComboBox();
		keyBox.setEditable(true);

		valueField = new JTextField();

		tableModel = new CustomFieldTableModel();

		ActionListener remove_listener = new ActionListener() {
			public void actionPerformed(ActionEvent e) {
				removeRow(popupRow);
			}
		};
		menu = new JPopupMenu();
		menu.add(GUIUtils.createTextAction(remove_listener, "remove"));

		keyCellEditor = new CustomFieldCellEditor(keyBox);
		valueCellEditor = new CustomFieldCellEditor(valueField);

		table = new JTable(tableModel);
		table.getColumnModel().getColumn(0).setCellEditor(keyCellEditor);
		table.getColumnModel().getColumn(1).setCellEditor(valueCellEditor);
		table.getColumnModel().getColumn(0).setCellRenderer(
				new CustomFieldCellRenderer());
		table.getColumnModel().getColumn(1).setCellRenderer(
				new CustomFieldCellRenderer());
		table.setRowHeight(table.getFontMetrics(getFont()).getHeight() + 5);
		table.addMouseListener(new MouseAdapter() {
			@Override
			public void mousePressed(MouseEvent e) {
				maybeShowPopup(e);
			}

			@Override
			public void mouseReleased(MouseEvent e) {
				maybeShowPopup(e);
			}
		});

		ListSelectionListener selectionListener = new ListSelectionListener() {
			public void valueChanged(ListSelectionEvent e) {
				if (!e.getValueIsAdjusting()) {
					updateActions();
				}
			}
		};
		table.getSelectionModel().addListSelectionListener(selectionListener);
		
		TableModelListener modelListener = new TableModelListener() {
			public void tableChanged(TableModelEvent e) {
				updateActions();
			}
		};
		tableModel.addTableModelListener(modelListener);

		JScrollPane scrollPane = new JScrollPane(table);
		scrollPane.setPreferredSize(new Dimension(400, 200));

		JPanel buttonPanel = new JPanel();
		buttonPanel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		buttonPanel.add(new JButton(upAction), cc);
		cc.update(0, 1, 1.0, 0.0);
		buttonPanel.add(new JButton(downAction), cc);
		cc.update(0, 2, 1.0, 1.0);
		buttonPanel.add(Box.createVerticalGlue(), cc);

		setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 1.0);
		add(scrollPane, cc);
		cc.update(1, 0, 0.0, 1.0);
		add(buttonPanel, cc);

		updateActions();
	}

	public void setChoices(Object[] choices) {
		Arrays.sort(choices);
		for (Object o : choices) {
			keyBox.addItem(o.toString());
		}
	}

	public StringPair[] getKeyValuePairs() {
		ArrayList<StringPair> valueList = new ArrayList<StringPair>();
		for (int i = 0; i < tableModel.keys.size(); i++) {
			if (tableModel.keys.get(i) != null
					&& !tableModel.keys.get(i).equals("")
					&& tableModel.values.get(i) != null) {
				valueList.add(new StringPair(tableModel.keys.get(i),
						tableModel.values.get(i)));
			}
		}

		return valueList.toArray(new StringPair[0]);
	}

	public void setKeyValuePairs(StringPair[] pairs) {
		if (pairs == null) {
			return;
		}

		for (StringPair p : pairs) {
			tableModel.keys.add(p.getFirst());
			tableModel.values.add(p.getSecond());
		}
	}

	public void updateData() {
		// Save data
		keyCellEditor.stopCellEditing();
		valueCellEditor.stopCellEditing();
	}

	private void maybeShowPopup(MouseEvent e) {
		if (e.isPopupTrigger()) {
			popupRow = table.rowAtPoint(e.getPoint());
			if (tableModel.getValueAt(popupRow, 0) != null) {
				menu.show(e.getComponent(), e.getX(), e.getY());
			}
		}
	}

	private void moveElement(int row, boolean up) {
		String key = (String) tableModel.getValueAt(row, 0);
		String value = (String) tableModel.getValueAt(row, 1);

		removeRow(row);

		int newRow = up ? row - 1 : row + 1;
		tableModel.insertRow(newRow, key, value);

		table.getSelectionModel().setSelectionInterval(newRow, newRow);
	}

	private void updateActions() {
		int index = table.getSelectedRow();
		upAction.setEnabled(index > 0
				&& tableModel.getValueAt(index, 0) != null);
		downAction.setEnabled(tableModel.getValueAt(index, 0) != null
				&& tableModel.getValueAt(index + 1, 0) != null);
	}

	private void removeRow(int index) {
		// Discard entered data
		keyCellEditor.cancelCellEditing();
		valueCellEditor.cancelCellEditing();
		tableModel.removeRow(index);
	}
}
