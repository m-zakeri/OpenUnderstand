package net.sourceforge.jvlt.ui.quiz;

import java.awt.Font;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.swing.JTable;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.TableCellRenderer;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Entry.Stats.UserFlag;
import net.sourceforge.jvlt.metadata.EntryMetaData.SensesAttribute;
import net.sourceforge.jvlt.ui.table.CustomFontCellRenderer;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;

public class ResultEntryTable extends JTable {
	private static class Model extends AbstractTableModel {
		private static final long serialVersionUID = 1L;

		private static SensesAttribute sensesAttribute = new SensesAttribute();

		private List<Entry> entries = new ArrayList<Entry>();
		private Map<Entry, Integer> flagMap = new HashMap<Entry, Integer>();

		@Override
		public Class<?> getColumnClass(int column) {
			if (column == 0 || column == 1)
				return String.class;
			else if (isUserFlagColumn(column))
				return Boolean.class;
			else
				return null;
		}
		
		public int getColumnCount() { return 2 + UserFlag.values().length - 1; }

		@Override
		public String getColumnName(int column) {
			if (column == 0) {
				return I18nService.getString("Labels", "original");
			} else if (column == 1) {
				return I18nService.getString("Labels", "meanings");
			} else if (isUserFlagColumn(column)) {
				return I18nService.getString("Labels",
						UserFlag.values()[column-2+1].getShortName());
			} else {
				return null;
			}
		}
		
		public int getRowCount() {
			return entries.size();
		}

		public Object getValueAt(int row, int column) {
			if (row < 0 || row >= entries.size())
				return null;
			
			Entry e = entries.get(row);
			if (column == 0) {
				return e.getOrthography();
			} else if (column == 1) {
				return sensesAttribute.getFormattedValue(e);
			} else if (isUserFlagColumn(column)) {
				if (flagMap.containsKey(e)) {
					return (flagMap.get(e)
							& UserFlag.values()[column-2+1].getValue()) != 0;
				} else {
					return (e.getUserFlags()
							& UserFlag.values()[column-2+1].getValue()) != 0;
				}
			} else {
				return null;
			}
		}
		
		@Override
		public boolean isCellEditable(int row, int column) {
			return isUserFlagColumn(column);
		}
		
		@Override
		public void setValueAt(Object object, int row, int column) {
			if (isUserFlagColumn(column)) {
				Entry e = entries.get(row);
				int flags = flagMap.containsKey(e) ? flagMap.get(e)
						: e.getUserFlags();
				if ((Boolean) object) {
					flags |= UserFlag.values()[column-2+1].getValue();
				} else {
					flags &= ~UserFlag.values()[column-2+1].getValue();
				}
				flagMap.put(e, flags);
			}
		}
		
		public void addEntry(Entry entry) {
			entries.add(entry);
			fireTableRowsInserted(entries.size() - 1, entries.size() - 1);
		}
		
		public void removeEntry(Entry entry) {
			int index = entries.indexOf(entry);
			if (index >= 0) {
				entries.remove(index);
				fireTableRowsDeleted(index, index);
			}
		}
		
		public void clear() {
			int entriesSize = entries.size();
			entries.clear();
			if (entriesSize > 0) {
				fireTableRowsDeleted(0, entriesSize - 1);
			}
			
			flagMap.clear();
		}
		
		private boolean isUserFlagColumn(int column) {
			return column >= 2 && column < 2 + UserFlag.values().length - 1;
		}
	}
	
	private static final long serialVersionUID = 1L;
	
	private static final CustomFontCellRenderer originalRenderer;
	private static final CustomFontCellRenderer pronunciationRenderer;
	static {
		Font font;
		originalRenderer = new CustomFontCellRenderer();
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_orth_font");
		if (font != null) {
			originalRenderer.setCustomFont(font);
		}
		pronunciationRenderer = new CustomFontCellRenderer();
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_pron_font");
		if (font != null) {
			pronunciationRenderer.setCustomFont(font);
		}
	}
	
	private Model model;
	
	public ResultEntryTable() {
		model = new Model();
		setModel(model);
//		setFillsViewportHeight(true); Java 1.6
	}
	
	public void addEntry(Entry e) { model.addEntry(e); }
	
	public void setEntries(List<Entry> entries) {
		model.clear();
		for (Entry e: entries)
			addEntry(e);
	}
	
	public void removeEntry(Entry e) { model.removeEntry(e); }
	
	public List<Entry> getEntries() { return model.entries; }
	
	public Entry getSelectedEntry() {
		int selected = getSelectedRow();
		if (selected != -1)
			return model.entries.get(selected);
		else
			return null;
	}
	
	public Map<Entry, Integer> getFlagMap() { return model.flagMap; }
	
	@Override
	public TableCellRenderer getCellRenderer(int row, int column) {
		if (column == 0)
			return originalRenderer;
		else if (column == 1)
			return pronunciationRenderer;
		else
			return super.getCellRenderer(row, column);
	}
}
