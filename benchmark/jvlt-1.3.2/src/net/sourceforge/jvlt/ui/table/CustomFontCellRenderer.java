package net.sourceforge.jvlt.ui.table;

import java.awt.Component;
import java.awt.Font;

import javax.swing.JTable;
import javax.swing.table.DefaultTableCellRenderer;

public class CustomFontCellRenderer extends DefaultTableCellRenderer {
	private static final long serialVersionUID = 1L;

	private Font _font = null;

	public Font getCustomFont() {
		return _font;
	}

	public void setCustomFont(Font f) {
		_font = f;
	}

	@Override
	public Component getTableCellRendererComponent(JTable table, Object value,
			boolean is_selected, boolean has_focus, int row, int column) {
		Component cell = super.getTableCellRendererComponent(table, value,
				is_selected, has_focus, row, column);
		if (_font != null) {
			cell.setFont(_font);
		}

		return cell;
	}
}
