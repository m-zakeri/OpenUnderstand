package net.sourceforge.jvlt.ui.io;

import java.awt.GridBagLayout;

import javax.swing.JLabel;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.I18nService;

public class CSVExportPanel extends CSVPanel {
	private static final long serialVersionUID = 1L;

	public void loadState() {
		_text_delim_box.setSelectedItem(JVLT.getConfig().getProperty(
				"CSVExport.TextDelimiter", "\""));
		_field_delim_box.setSelectedItem(JVLT.getConfig().getProperty(
				"CSVExport.FieldDelimiter", ","));
		_charset_box.setSelectedItem(JVLT.getConfig().getProperty(
				"CSVExport.Charset", "UTF-8"));
	}

	public void saveState() {
		JVLT.getConfig().setProperty("CSVImport.TextDelimiter",
				String.valueOf(getTextDelimiter()));
		JVLT.getConfig().setProperty("CSVImport.FieldDelimiter",
				String.valueOf(getFieldDelimiter()));
		JVLT.getConfig().setProperty("CSVImport.Charset",
				String.valueOf(getCharset()));
	}

	@Override
	protected void initLayout() {
		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0, 2, 1);
		add(new JLabel(I18nService.getString("Messages", "csv_export")), cc);
		cc.update(0, 1, 0.5, 0.0, 1, 1);
		add(_charset_box.getLabel(), cc);
		cc.update(1, 1, 0.5, 0.0);
		add(_charset_box, cc);
		cc.update(0, 2, 0.5, 0.0);
		add(_field_delim_box.getLabel(), cc);
		cc.update(1, 2, 0.5, 0.0);
		add(_field_delim_box, cc);
		cc.update(0, 3, 0.5, 0.0);
		add(_text_delim_box.getLabel(), cc);
		cc.update(1, 3, 0.5, 0.0);
		add(_text_delim_box, cc);
	}
}
