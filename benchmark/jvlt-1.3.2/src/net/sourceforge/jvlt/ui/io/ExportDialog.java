package net.sourceforge.jvlt.ui.io;

import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeSet;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.DictException;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.event.StateListener.StateEvent;
import net.sourceforge.jvlt.io.DictCSVWriter;
import net.sourceforge.jvlt.io.DictHtmlWriter;
import net.sourceforge.jvlt.io.DictXMLWriter;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.query.EntryFilter;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.DictFileChooser;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.vocabulary.EntryList;
import net.sourceforge.jvlt.ui.vocabulary.EntryQueryDialog;
import net.sourceforge.jvlt.ui.vocabulary.ExampleList;
import net.sourceforge.jvlt.ui.wizard.DialogWizardModel;
import net.sourceforge.jvlt.ui.wizard.Wizard;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.I18nService;

import org.apache.log4j.Logger;

public class ExportDialog extends JDialog {
	private static final long serialVersionUID = 1L;

	public ExportDialog(Frame parent, JVLTModel model) {
		super(parent, I18nService.getString("Labels", "export"), true);

		final ExportWizardModel ewmodel = new ExportWizardModel(model);
		ewmodel.loadState();
		ewmodel.addStateListener(new StateListener() {
			public void stateChanged(StateEvent ev) {
				ewmodel.saveState();
				dispose();
			}
		});
		Wizard wizard = new Wizard(ewmodel);
		JPanel content = wizard.getContent();
		content.setPreferredSize(new Dimension(600, 400));
		setContentPane(content);
	}
}

class ExportWizardModel extends DialogWizardModel {
	public ExportWizardModel(JVLTModel model) {
		super(model);

		registerPanelDescriptor(new StartExportDescriptor(this));
		registerPanelDescriptor(new FinishExportDescriptor(this));
		registerPanelDescriptor(new ExportSuccessDescriptor(this));

		_current_descriptor = getPanelDescriptor("start");
	}

	@Override
	public String getButtonText(String button_command) {
		if (_current_descriptor instanceof ExportSuccessDescriptor) {
			if (button_command.equals(Wizard.NEXT_COMMAND)) {
				return I18nService.getString("Actions", "finish");
			}
		}
		return super.getButtonText(button_command);
	}

	@Override
	public boolean isButtonEnabled(String button_command) {
		if (_current_descriptor instanceof StartExportDescriptor) {
			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return false;
			}
		} else if (_current_descriptor instanceof ExportSuccessDescriptor) {
			if (button_command.equals(Wizard.BACK_COMMAND)
					|| button_command.equals(Wizard.CANCEL_COMMAND)) {
				return false;
			}
		}

		return super.isButtonEnabled(button_command);
	}

	@Override
	public WizardPanelDescriptor nextPanelDescriptor(String command)
			throws InvalidInputException {
		WizardPanelDescriptor next = _current_descriptor;
		if (_current_descriptor instanceof StartExportDescriptor) {
			if (command.equals(Wizard.NEXT_COMMAND)) {
				next = getPanelDescriptor("finish");
			}
		} else if (_current_descriptor instanceof FinishExportDescriptor) {
			StartExportDescriptor sed = (StartExportDescriptor) getPanelDescriptor("start");
			ExportSuccessDescriptor esd = (ExportSuccessDescriptor) getPanelDescriptor("success");
			FinishExportDescriptor fed = (FinishExportDescriptor) _current_descriptor;
			if (command.equals(Wizard.NEXT_COMMAND)) {
				Dict dict = sed.getDict();
				String file_name = fed.getFileName();

				boolean write_file = true;
				if (new File(file_name).exists()) {
					if (JOptionPane.showConfirmDialog(fed.getPanelComponent(),
							I18nService.getString("Messages", "overwrite"),
							I18nService.getString("Labels", "confirm"),
							JOptionPane.YES_NO_OPTION) != JOptionPane.YES_OPTION) {
						write_file = false;
					}
				}

				if (write_file) {
					fed.setDict(dict);
					fed.setClearStats(sed.getClearStats());
					try {
						fed.export();
						next = esd;
					} catch (IOException e) {
						throw new InvalidInputException(I18nService.getString(
								"Messages", "exporting_failed"), e.getMessage());
					}
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				next = sed;
			}
		} else if (_current_descriptor instanceof ExportSuccessDescriptor) {
			fireStateEvent(new StateEvent(this, FINISH_STATE));
		}

		_current_descriptor = next;
		if (command.equals(Wizard.CANCEL_COMMAND)) {
			fireStateEvent(new StateEvent(this, CANCEL_STATE));
		}

		return next;
	}

	public void loadState() {
		((StartExportDescriptor) getPanelDescriptor("start")).loadState();
		((FinishExportDescriptor) getPanelDescriptor("finish")).loadState();
	}

	public void saveState() {
		((StartExportDescriptor) getPanelDescriptor("start")).saveState();
		((FinishExportDescriptor) getPanelDescriptor("finish")).saveState();
	}
}

class StartExportDescriptor extends WizardPanelDescriptor {
	private static final Logger logger = Logger
			.getLogger(StartExportDescriptor.class);

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			if (e.getActionCommand().equals("select_words")) {
				GUIUtils.showDialog(JOptionPane.getFrameForComponent(_panel),
						_query_dialog);
			}
		}
	}

	private class DialogHandler implements DialogListener {
		public void dialogStateChanged(DialogEvent ev) {
			if (ev.getSource() == _query_dialog) {
				if (ev.getType() == AbstractDialog.APPLY_OPTION) {
					_query_modified = true;
					updateUI();
				} else {
					_query_dialog.setVisible(false);
				}
			}
		}
	}

	private boolean _query_modified;
	private EntryList _entry_list;
	private ExampleList _example_list;
	private JCheckBox _clear_stats_box;
	private JLabel _entry_label;
	private JLabel _example_label;
	private EntryQueryDialog _query_dialog;

	public StartExportDescriptor(ExportWizardModel model) {
		super(model);
		_query_modified = false;
		initUI();
		updateUI();
	}

	@Override
	public String getID() {
		return "start";
	}

	public Dict getDict() {
		ExportWizardModel model = (ExportWizardModel) _model;
		Dict dict = new Dict();
		try {
			dict.setLanguage(model.getJVLTModel().getDict().getLanguage());
			for (Entry entry : _entry_list.getEntries()) {
				dict.addEntry(entry);
			}
			for (Example example : _example_list.getExamples()) {
				dict.addExample(example);
			}
		} catch (DictException e) {
			logger.error("Failed to set dictionary data", e);
		}

		return dict;
	}

	public boolean getClearStats() {
		return _clear_stats_box.isSelected();
	}

	public void loadState() {
		_clear_stats_box.setSelected(JVLT.getConfig().getBooleanProperty(
				"export_clear_stats", false));
	}

	public void saveState() {
		JVLT.getConfig().setProperty("export_clear_stats",
				_clear_stats_box.isSelected());
	}

	private void setEntries(Collection<Entry> entries) {
		ExportWizardModel model = (ExportWizardModel) _model;
		int n = model.getJVLTModel().getDict().getEntryCount();
		_entry_label.setText(getLabel(entries.size(), n, "num_words"));
		_entry_list.setEntries(entries);
	}

	private void setExamples(Collection<Example> examples) {
		ExportWizardModel model = (ExportWizardModel) _model;
		int n = model.getJVLTModel().getDict().getExampleCount();
		_example_label.setText(getLabel(examples.size(), n, "num_examples"));
		_example_list.setExamples(examples);
	}

	private void initUI() {
		JVLTModel model = ((ExportWizardModel) _model).getJVLTModel();
		_query_dialog = new EntryQueryDialog(JOptionPane
				.getFrameForComponent(_panel), I18nService.getString("Labels",
				"advanced_filter"), true, model);
		_query_dialog.addDialogListener(new DialogHandler());

		_entry_list = new EntryList();
		_example_list = new ExampleList();
		_entry_label = new JLabel();
		_example_label = new JLabel();

		_clear_stats_box = new JCheckBox(GUIUtils
				.createTextAction("clear_stats"));

		Action select_words_action = GUIUtils.createTextAction(
				new ActionHandler(), "select_words");
		JPanel selection_panel = new JPanel();
		selection_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		selection_panel.add(new JLabel(I18nService.getString("Labels",
				"select_exported_words")
				+ ":"), cc);
		cc.update(1, 0, 0.0, 0.0);
		selection_panel.add(new JButton(select_words_action), cc);

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		_panel.add(_clear_stats_box, cc);
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(selection_panel, cc);
		cc.update(0, 2, 1.0, 0.0);
		_panel.add(_entry_label, cc);
		cc.update(0, 3, 1.0, 0.5);
		_panel.add(new JScrollPane(_entry_list), cc);
		cc.update(0, 4, 1.0, 0.0);
		_panel.add(_example_label, cc);
		cc.update(0, 5, 1.0, 0.5);
		_panel.add(new JScrollPane(_example_list), cc);
	}

	private String getLabel(int num, int total, String i18n) {
		ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
				"Labels", i18n));
		String str = formatter.format(total);
		return I18nService.getString("Labels", "exported",
				new Object[] { num, str });
	}

	private void updateUI() {
		ExportWizardModel model = (ExportWizardModel) _model;
		Dict dict = model.getJVLTModel().getDict();
		ObjectQuery query;
		if (_query_modified) {
			query = _query_dialog.getObjectQuery();
		} else {
			query = new ObjectQuery(Entry.class);
		}
		EntryFilter filter = new EntryFilter(query);
		Collection<Entry> entries = filter
				.getMatchingEntries(dict.getEntries());
		TreeSet<Example> examples = new TreeSet<Example>();
		for (Entry entry : entries) {
			examples.addAll(dict.getExamples(entry));
		}
		setEntries(entries);
		setExamples(examples);
	}
}

class FinishExportDescriptor extends WizardPanelDescriptor {
	class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			if (e.getActionCommand().equals("select_file")) {
				DictFileChooser.FileType type;
				if (_type_box.getSelectedIndex() == FILE_TYPE_CSV) {
					type = DictFileChooser.FileType.CSV_FILES;
				} else if (_type_box.getSelectedIndex() == FILE_TYPE_HTML) {
					type = DictFileChooser.FileType.HTML_FILES;
				} else {
					type = DictFileChooser.FileType.JVLT_FILES;
				}

				ExportWizardModel ewm = (ExportWizardModel) _model;
				String file = ewm.getJVLTModel().getDictFileName();
				String file_name = DictFileChooser.selectSaveFile(file, type,
						_panel);
				if (file_name != null) {
					_file_names.put(_type_box.getSelectedIndex(), file_name);
					_file_field.setText(file_name);
				}
			} else if (e.getActionCommand().equals("file_type")) {
				_panel.remove(_csv_panel);
				_panel.remove(_html_panel);
				CustomConstraints cc = new CustomConstraints();
				cc.update(0, 3, 1.0, 0.0, 3, 1);
				if (_type_box.getSelectedIndex() == FILE_TYPE_CSV) {
					_panel.add(_csv_panel, cc);
				} else if (_type_box.getSelectedIndex() == FILE_TYPE_HTML) {
					_panel.add(_html_panel, cc);
				}

				updateFileField();

				_panel.revalidate();
				_panel.repaint(_panel.getVisibleRect());
			}
		}
	}

	private static final int FILE_TYPE_JVLT = 0;
	private static final int FILE_TYPE_CSV = 1;
	private static final int FILE_TYPE_HTML = 2;

	private LabeledComboBox _type_box;
	private CustomTextField _file_field;
	private CSVExportPanel _csv_panel;
	private HTMLExportPanel _html_panel;
	private Dict _dict;
	private final Map<Integer, String> _file_names = new HashMap<Integer, String>();
	private boolean _clear_stats = false;

	public FinishExportDescriptor(ExportWizardModel model) {
		super(model);
		initUI();
	}

	@Override
	public String getID() {
		return "finish";
	}

	public String getFileName() {
		return _file_field.getText();
	}

	public void export() throws IOException {
		File f = new File(_file_field.getText());
		FileOutputStream stream = new FileOutputStream(f);
		if (_type_box.getSelectedIndex() == FILE_TYPE_JVLT) {
			DictXMLWriter writer = new DictXMLWriter(_dict, stream);
			writer.setClearStats(_clear_stats);
			writer.write();
		} else if (_type_box.getSelectedIndex() == FILE_TYPE_CSV) {
			DictCSVWriter writer = new DictCSVWriter(_dict, stream);
			writer = new DictCSVWriter(_dict, stream);
			writer.setCharset(_csv_panel.getCharset());
			writer.setTextDelimiter(_csv_panel.getTextDelimiter());
			writer.setFieldDelimiter(_csv_panel.getFieldDelimiter());
			/*
			 * No need to clear entry statistics, since the exporter currently
			 * ignores the statistics fields.
			 */
			writer.write();
		} else if (_type_box.getSelectedIndex() == FILE_TYPE_HTML) {
			DictHtmlWriter writer = new DictHtmlWriter(_dict, stream);
			writer.setAddReverse(_html_panel.isBidirectional());
			writer.write();
		}
	}

	public void setDict(Dict dict) {
		_dict = dict;
	}

	public void setClearStats(boolean clear) {
		_clear_stats = clear;
	}

	public void loadState() {
		_type_box.setSelectedIndex(JVLT.getConfig().getIntProperty(
				"export_file_type", 0));
		_file_names.put(FILE_TYPE_JVLT, JVLT.getConfig().getProperty(
				"export_file_name_jvlt", ""));
		_file_names.put(FILE_TYPE_CSV, JVLT.getConfig().getProperty(
				"export_file_name_csv", ""));
		_file_names.put(FILE_TYPE_HTML, JVLT.getConfig().getProperty(
				"export_file_name_html", ""));
		_html_panel.setBidirectional(JVLT.getConfig().getBooleanProperty(
				"export_html_bidirectional", false));

		_csv_panel.loadState();

		updateFileField();
	}

	public void saveState() {
		JVLT.getConfig().setProperty("export_file_type",
				_type_box.getSelectedIndex());
		JVLT.getConfig().setProperty("export_file_name_jvlt",
				_file_names.get(FILE_TYPE_JVLT));
		JVLT.getConfig().setProperty("export_file_name_csv",
				_file_names.get(FILE_TYPE_CSV));
		JVLT.getConfig().setProperty("export_file_name_html",
				_file_names.get(FILE_TYPE_HTML));
		JVLT.getConfig().setProperty("export_html_bidirectional",
				_html_panel.isBidirectional());

		_csv_panel.saveState();
	}

	private void initUI() {
		Action select_action = GUIUtils.createTextAction(new ActionHandler(),
				"select_file");

		_file_field = new CustomTextField(20);
		_file_field.setEnabled(false);
		_file_field.setActionCommand("select_export_file");

		_type_box = new LabeledComboBox();
		_type_box.setLabel("file_type");
		_type_box.insertItemAt(I18nService.getString("Labels", "jvlt_file"),
				FILE_TYPE_JVLT);
		_type_box.insertItemAt(I18nService.getString("Labels", "csv_file"),
				FILE_TYPE_CSV);
		_type_box.insertItemAt(I18nService.getString("Labels", "html_file"),
				FILE_TYPE_HTML);
		_type_box.addActionListener(new ActionHandler());

		_csv_panel = new CSVExportPanel();
		_html_panel = new HTMLExportPanel();

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0, 3, 1);
		_panel.add(new JLabel(I18nService.getString("Messages", "start_export")),
				cc);
		cc.update(0, 1, 0.5, 0, 1, 1);
		_panel.add(_type_box.getLabel(), cc);
		cc.update(1, 1, 0.5, 0);
		_panel.add(_type_box, cc);
		cc.update(0, 2, 0.5, 0);
		_panel.add(_file_field.getLabel(), cc);
		cc.update(1, 2, 0.5, 0);
		_panel.add(_file_field, cc);
		cc.update(2, 2, 0, 0);
		_panel.add(new JButton(select_action), cc);
		cc.update(0, 4, 0, 1.0);
		_panel.add(Box.createVerticalGlue(), cc);
	}

	private void updateFileField() {
		_file_field.setText(_file_names.get(_type_box.getSelectedIndex()));
	}
}

class ExportSuccessDescriptor extends WizardPanelDescriptor {
	public ExportSuccessDescriptor(ExportWizardModel model) {
		super(model);

		initUI();
	}

	@Override
	public String getID() {
		return "success";
	}

	private void initUI() {
		JLabel label = new JLabel(I18nService.getString("Labels",
				"exporting_successful"));
		label.setHorizontalAlignment(SwingConstants.CENTER);
		label.setVerticalAlignment(SwingConstants.CENTER);
		_panel = label;
	}
}

class HTMLExportPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final JCheckBox _bidirectional_box;

	public HTMLExportPanel() {
		_bidirectional_box = new JCheckBox();
		_bidirectional_box.setText(I18nService.getString("Actions",
				"bidirectional"));

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_bidirectional_box, cc);
		cc.update(0, 1, 0.0, 1.0);
		add(Box.createVerticalGlue(), cc);
	}

	public boolean isBidirectional() {
		return _bidirectional_box.isSelected();
	}

	public void setBidirectional(boolean bidirectional) {
		_bidirectional_box.setSelected(bidirectional);
	}
}
