package net.sourceforge.jvlt.ui.table;

import java.awt.Component;
import java.text.NumberFormat;

import javax.swing.JLabel;
import javax.swing.JTable;
import javax.swing.table.DefaultTableCellRenderer;

public class PercentCellRenderer extends DefaultTableCellRenderer {
	private static final long serialVersionUID = 1L;

	@Override
	public Component getTableCellRendererComponent(JTable table, Object value,
			boolean is_selected, boolean has_focus, int row, int column) {
		JLabel cell = (JLabel) super.getTableCellRendererComponent(table,
				value, is_selected, has_focus, row, column);
		NumberFormat formatter = NumberFormat.getPercentInstance();
		formatter.setMaximumFractionDigits(1);
		cell.setText(formatter.format(value));

		return cell;
	}
}
