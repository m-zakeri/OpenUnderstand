package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Container;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSpinner;
import javax.swing.SpinnerNumberModel;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

import net.sourceforge.jvlt.ui.components.TablePrinterPanel;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.utils.TablePrinter;
import net.sourceforge.jvlt.utils.I18nService;

public class PrintPreviewDialog extends JDialog implements ActionListener,
		ChangeListener {
	private static final long serialVersionUID = 1L;

	public static final int PRINT_OPTION = 0;
	public static final int CANCEL_OPTION = 1;

	private int _option;
	private final TablePrinter _printer;
	private SpinnerNumberModel _spinner_model;
	private TablePrinterPanel _printer_panel;

	public PrintPreviewDialog(Frame owner, String title, TablePrinter printer) {
		super(owner, title, true);

		_option = CANCEL_OPTION;
		_printer = printer;
		init();
	}

	public void actionPerformed(ActionEvent e) {
		if (e.getActionCommand().equals("print")) {
			_option = PRINT_OPTION;
			setVisible(false);
		} else if (e.getActionCommand().equals("cancel")) {
			_option = CANCEL_OPTION;
			setVisible(false);
		}
	}

	public int getOption() {
		return _option;
	}

	public void stateChanged(ChangeEvent ev) {
		int page = _spinner_model.getNumber().intValue();
		_printer_panel.setCurrentPage(page - 1);
		_printer_panel.repaint(_printer_panel.getVisibleRect());
	}

	private void init() {
		Action print_action = GUIUtils.createTextAction(this, "print");
		Action cancel_action = GUIUtils.createTextAction(this, "cancel");

		_printer_panel = new TablePrinterPanel(_printer);
		JScrollPane spane = new JScrollPane();
		spane.getViewport().setView(_printer_panel);

		int max_page = _printer.getPageNumber();
		if (max_page == 0) {
			max_page = 1;
		}
		_spinner_model = new SpinnerNumberModel(1, 1, max_page, 1);
		JSpinner spinner = new JSpinner(_spinner_model);
		spinner.addChangeListener(this);
		if (max_page == 0) {
			spinner.setEnabled(false);
		}

		JPanel settings_panel = new JPanel();
		settings_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		settings_panel.add(new JLabel(I18nService.getString("Labels", "page")
				+ ":"), cc);
		cc.update(1, 0, 0.0, 0.0);
		settings_panel.add(spinner, cc);
		cc.update(2, 0, 0.0, 0.0);
		settings_panel.add(new JLabel(I18nService.getString("Labels",
				"total_pages", new Object[] { max_page })), cc);
		cc.update(3, 0, 1.0, 0.0);
		settings_panel.add(Box.createHorizontalGlue(), cc);

		JPanel button_panel = new JPanel();
		button_panel.setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 0.0);
		button_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		button_panel.add(new JButton(print_action), cc);
		cc.update(2, 0, 0.0, 0.0);
		button_panel.add(new JButton(cancel_action), cc);

		Container cpane = getContentPane();
		cpane.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		cpane.add(settings_panel, cc);
		cc.update(0, 1, 1.0, 1.0);
		cpane.add(spane, cc);
		cc.update(0, 2, 1.0, 0.0);
		cpane.add(button_panel, cc);
	}
}
