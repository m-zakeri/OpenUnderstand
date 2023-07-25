package net.sourceforge.jvlt.ui.components;

import java.awt.Dimension;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.print.PageFormat;
import java.awt.print.PrinterException;

import javax.swing.JPanel;

import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.utils.TablePrinter;

public class TablePrinterPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private int _current_page = 0;
	private TablePrinter _printer = null;

	public TablePrinterPanel(TablePrinter printer) {
		_printer = printer;
		PageFormat format = _printer.getPageFormat();
		setPreferredSize(new Dimension((int) format.getWidth(), (int) format
				.getHeight()));
	}

	@Override
	public void paint(Graphics graphics) {
		super.paint(graphics);

		try {
			_printer.paintPage((Graphics2D) graphics, _current_page);
		} catch (PrinterException ex) {
			MessageDialog.showDialog(this, MessageDialog.WARNING_MESSAGE, ex
					.getMessage());
		}
	}

	public void setCurrentPage(int page) {
		_current_page = page;
	}
}
