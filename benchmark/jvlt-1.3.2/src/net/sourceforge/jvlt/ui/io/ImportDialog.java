package net.sourceforge.jvlt.ui.io;

import java.awt.Component;
import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Collection;
import java.util.TreeSet;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JDialog;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.ImportAction;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.core.SchemaAttribute;
import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.event.StateListener.StateEvent;
import net.sourceforge.jvlt.io.CSVDictReader;
import net.sourceforge.jvlt.io.DictImporter;
import net.sourceforge.jvlt.io.DictReader;
import net.sourceforge.jvlt.io.DictReaderException;
import net.sourceforge.jvlt.io.SAXDictReader;
import net.sourceforge.jvlt.io.VersionException;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.components.CustomTabbedPane;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.dialogs.DictFileChooser;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.vocabulary.EntryList;
import net.sourceforge.jvlt.ui.vocabulary.ExampleList;
import net.sourceforge.jvlt.ui.wizard.DialogWizardModel;
import net.sourceforge.jvlt.ui.wizard.Wizard;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.Config;
import net.sourceforge.jvlt.utils.I18nService;

public class ImportDialog extends JDialog {
	private static final long serialVersionUID = 1L;

	public ImportDialog(Frame parent, JVLTModel model) {
		super(parent, I18nService.getString("Labels", "import"), true);

		final ImportWizardModel iwmodel = new ImportWizardModel(model);
		iwmodel.loadState();
		iwmodel.addStateListener(new StateListener() {
			public void stateChanged(StateEvent ev) {
				iwmodel.saveState();
				dispose();
			}
		});
		Wizard wizard = new Wizard(iwmodel);
		JPanel content = wizard.getContent();
		content.setPreferredSize(new Dimension(600, 400));
		setContentPane(content);
	}
}

class ImportWizardModel extends DialogWizardModel {
	private final DictImporter _importer;

	public ImportWizardModel(JVLTModel model) {
		super(model);
		_importer = new DictImporter(model.getDict());

		registerPanelDescriptor(new StartImportDescriptor(this));
		registerPanelDescriptor(new ImportResultsDescriptor(this));
		registerPanelDescriptor(new ImportSuccessDescriptor(this));

		_current_descriptor = getPanelDescriptor("start");
	}

	@Override
	public String getButtonText(String button_command) {
		if (_current_descriptor instanceof ImportSuccessDescriptor) {
			if (button_command.equals(Wizard.NEXT_COMMAND)) {
				return I18nService.getString("Actions", "finish");
			}
		}

		return super.getButtonText(button_command);
	}

	@Override
	public boolean isButtonEnabled(String button_command) {
		if (_current_descriptor instanceof StartImportDescriptor) {
			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return false;
			}
		} else if (_current_descriptor instanceof ImportSuccessDescriptor) {
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
		if (_current_descriptor instanceof StartImportDescriptor) {
			StartImportDescriptor sid = (StartImportDescriptor) _current_descriptor;
			if (command.equals(Wizard.NEXT_COMMAND)) {
				try {
					prepareImport(sid.getDict());
					next = getPanelDescriptor("results");
				} catch (DictReaderException ex) {
					throw new InvalidInputException(ex.getShortMessage(), ex
							.getLongMessage());
				} catch (IOException ex) {
					throw new InvalidInputException(I18nService.getString(
							"Messages", "loading_failed"), ex.getMessage());
				}
			}
		} else if (_current_descriptor instanceof ImportResultsDescriptor) {
			StartImportDescriptor sid = (StartImportDescriptor) getPanelDescriptor("start");
			ImportResultsDescriptor ird = (ImportResultsDescriptor) getPanelDescriptor("results");
			ImportSuccessDescriptor isd = (ImportSuccessDescriptor) getPanelDescriptor("success");
			if (command.equals(Wizard.NEXT_COMMAND)) {
				_importer.setClearStats(ird.getClearStats());
				try {
					DictImporter.ImportInfo info = _importer.getImportInfo(
							sid.getDict());
					ImportAction ia = new ImportAction(
							info.oldLanguage, info.newLanguage,
							info.entries, info.examples);
					ia.setMessage(I18nService.getString(
							"Actions", "import_dict"));
					_model.getDictModel().executeAction(ia);
					next = isd;
				} catch (Exception ex) {
					throw new InvalidInputException(I18nService.getString(
							"Messages", "importing_failed"), ex.getMessage());
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				next = sid;
			}
		} else if (_current_descriptor instanceof ImportSuccessDescriptor) {
			fireStateEvent(new StateEvent(this, FINISH_STATE));
		}

		_current_descriptor = next;
		if (command.equals(Wizard.CANCEL_COMMAND)) {
			fireStateEvent(new StateEvent(this, CANCEL_STATE));
		}

		return next;
	}

	public void loadState() {
		StartImportDescriptor sid = (StartImportDescriptor) getPanelDescriptor("start");
		sid.loadState();
		ImportResultsDescriptor ird = (ImportResultsDescriptor) getPanelDescriptor("results");
		ird.loadState();
	}

	public void saveState() {
		StartImportDescriptor sid = (StartImportDescriptor) getPanelDescriptor("start");
		sid.saveState();
		ImportResultsDescriptor ird = (ImportResultsDescriptor) getPanelDescriptor("results");
		ird.saveState();
	}

	private void prepareImport(Dict dict) throws InvalidInputException {
		ImportResultsDescriptor ird = (ImportResultsDescriptor) getPanelDescriptor("results");

		// Throw exception if languages of old and new dictionary
		// are not compatible
		String newlang = dict.getLanguage();
		String oldlang = getJVLTModel().getDict().getLanguage();
		if (newlang != null && oldlang != null && !newlang.equals(oldlang)) {
			throw new InvalidInputException(I18nService.getString("Messages",
					"invalid_language"), "Invalid language: " + oldlang + "!="
					+ newlang);
		}

		Collection<Entry> entries = _importer.getImportedEntries(dict);
		TreeSet<Entry> imported_entries = new TreeSet<Entry>();
		imported_entries.addAll(entries);
		TreeSet<Entry> not_imported_entries = new TreeSet<Entry>();
		not_imported_entries.addAll(dict.getEntries());
		not_imported_entries.removeAll(imported_entries);
		ird.setEntries(entries, not_imported_entries);

		TreeSet<Example> imported_examples = new TreeSet<Example>();
		imported_examples.addAll(_importer.getImportedExamples(dict, entries));
		TreeSet<Example> not_imported_examples = new TreeSet<Example>();
		not_imported_examples.addAll(dict.getExamples());
		not_imported_examples.removeAll(imported_examples);
		ird.setExamples(imported_examples, not_imported_examples);
	}
}

class StartImportDescriptor extends WizardPanelDescriptor {
	class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			String csv_file = I18nService.getString("Labels", "csv_file");
			if (e.getActionCommand().equals("open")) {
				DictFileChooser chooser;
				ImportWizardModel iwm = (ImportWizardModel) _model;
				String file = iwm.getJVLTModel().getDictFileName();
				if (_type_box.getSelectedItem().equals(csv_file)) {
					chooser = new DictFileChooser(file,
							DictFileChooser.FileType.CSV_FILES);
				} else {
					chooser = new DictFileChooser(file,
							DictFileChooser.FileType.JVLT_FILES);
				}

				int val = chooser.showOpenDialog(_panel);
				if (val == JFileChooser.APPROVE_OPTION) {
					_file_field.setText(chooser.getSelectedFile().getPath());
				}
			} else if (e.getActionCommand().equals("file_type")) {
				CustomConstraints cc = new CustomConstraints();
				cc.update(0, 3, 1.0, 1.0, 3, 1);
				if (_type_box.getSelectedItem().equals(csv_file)) {
					_panel.remove(_empty_component);
					_panel.add(_csv_panel, cc);
				} else {
					_panel.remove(_csv_panel);
					_panel.add(_empty_component, cc);
				}

				_panel.revalidate();
				_panel.repaint(_panel.getVisibleRect());
			}
		}
	}

	private LabeledComboBox _type_box;
	private CustomTextField _file_field;
	private CSVImportPanel _csv_panel;
	private Component _empty_component;

	private Dict _dict = null;
	private String _type = ""; // Content of _type_box
	private String _file = ""; // Content of _file_field;

	public StartImportDescriptor(ImportWizardModel model) {
		super(model);
		initUI();
	}

	@Override
	public String getID() {
		return "start";
	}

	public Dict getDict() throws DictReaderException, IOException {
		//
		// Save dictionary. When called again, this method will return the
		// saved dictionary if _type and _file haven't changed.
		//
		if (_type != null && _type.equals(_type_box.getSelectedItem())
				&& _file != null && _file.equals(_file_field.getText())
				&& _dict != null) {
			return _dict;
		}

		// Save file type and name
		_type = _type_box.getSelectedItem().toString();
		_file = _file_field.getText();

		File f = new File(_file_field.getText());
		DictReader reader = null;
		String csv_file = I18nService.getString("Labels", "csv_file");
		if (_type_box.getSelectedItem().equals(csv_file)) {
			CSVDictReader csv_reader = new CSVDictReader();
			csv_reader.setTextDelimiter(_csv_panel.getTextDelimiter());
			csv_reader.setFieldDelimiter(_csv_panel.getFieldDelimiter());
			csv_reader.setCharset(_csv_panel.getCharset());
			csv_reader.setNumSenses(_csv_panel.getNumSenses());
			csv_reader.setNumCategories(_csv_panel.getNumCategories());
			csv_reader
					.setNumMultimediaFiles(_csv_panel.getNumMultimediaFiles());
			csv_reader.setNumExamples(_csv_panel.getNumExamples());
			csv_reader.setIgnoreFirstLine(_csv_panel.getIgnoreFirstRow());
			csv_reader.setLanguage(_csv_panel.getLanguage());
			SchemaAttribute[] attrs = _csv_panel.getAttributes();
			String[] attr_names = new String[attrs.length];
			for (int i = 0; i < attrs.length; i++) {
				attr_names[i] = attrs[i].getName();
			}
			csv_reader.setAttributes(attr_names);
			csv_reader.setAttributeColumns(_csv_panel.getAttributeColumns());
			reader = csv_reader;
		} else {
			reader = new SAXDictReader();
		}

		FileInputStream in = new FileInputStream(f);
		try {
			reader.read(in);
			_dict = reader.getDict();
			return _dict;
		} catch (DictReaderException e) {
			if (!(reader instanceof SAXDictReader)) {
				throw e;
			}

			/*
			 * When reading a .jvlt file, a version exception may occur. Try to
			 * handle this exception.
			 */
			Exception ex = e.getException();
			if (ex == null || !(ex instanceof VersionException)) {
				throw e;
			}

			VersionException ve = (VersionException) ex;
			if (ve.getVersion().compareTo(JVLT.getDataVersion()) > 0) {
				throw e;
			}
			String text = I18nService.getString("Messages", "convert_file");
			int result = MessageDialog.showDialog(JOptionPane
					.getFrameForComponent(_panel),
					MessageDialog.WARNING_MESSAGE,
					MessageDialog.OK_CANCEL_OPTION, text);
			if (result == MessageDialog.OK_OPTION) {
				reader = new SAXDictReader(ve.getVersion());
				in.close();
				in = new FileInputStream(f);
				reader.read(in);
				_dict = reader.getDict();
				return _dict;
			}
			throw e;
		} finally {
			in.close();
		}
	}

	public void loadState() {
		Config config = JVLT.getConfig();
		_file_field.setText(config.getProperty("ImportDialog.File", ""));
		String type = config.getProperty("ImportDialog.Type", "jvlt");
		if (type.equals("jvlt")) {
			_type_box
					.setSelectedItem(I18nService.getString("Labels", "jvlt_file"));
		} else {
			_type_box.setSelectedItem(I18nService.getString("Labels", "csv_file"));
		}

		_csv_panel.loadState();
	}

	public void saveState() {
		Config config = JVLT.getConfig();
		config.setProperty("ImportDialog.File", _file_field.getText());
		if (_type_box.getSelectedItem().equals(
				I18nService.getString("Labels", "csv_file"))) {
			config.setProperty("ImportDialog.Type", "csv");
			_csv_panel.saveState();
		} else {
			config.setProperty("ImportDialog.Type", "jvlt");
		}

		_csv_panel.saveState();
	}

	private void initUI() {
		Action open_action = GUIUtils.createTextAction(new ActionHandler(),
				"open");

		_file_field = new CustomTextField(20);
		_file_field.setActionCommand("select_import_file");

		_type_box = new LabeledComboBox();
		_type_box.setLabel("file_type");
		_type_box.addItem(I18nService.getString("Labels", "jvlt_file"));
		_type_box.addItem(I18nService.getString("Labels", "csv_file"));
		_type_box.addActionListener(new ActionHandler());

		_csv_panel = new CSVImportPanel();
		_empty_component = Box.createVerticalGlue();

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0, 3, 1);
		_panel.add(new JLabel(I18nService.getString("Messages", "start_import")),
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
		_panel.add(new JButton(open_action), cc);
		cc.update(0, 3, 0, 1.0);
		_panel.add(_empty_component, cc);
	}
}

class ImportResultsDescriptor extends WizardPanelDescriptor {
	private EntryList _imported_entries_list;
	private EntryList _not_imported_entries_list;
	private ExampleList _imported_examples_list;
	private ExampleList _not_imported_examples_list;
	private JCheckBox _clear_stats_box;
	private JLabel _entry_label;
	private JLabel _example_label;

	public ImportResultsDescriptor(ImportWizardModel model) {
		super(model);
		initUI();
	}

	@Override
	public String getID() {
		return "results";
	}

	public boolean getClearStats() {
		return _clear_stats_box.isSelected();
	}

	public void setEntries(Collection<Entry> imported,
			Collection<Entry> not_imported) {
		_entry_label.setText(getLabel(imported.size(), imported.size()
				+ not_imported.size(), "num_words"));
		_imported_entries_list.setEntries(imported);
		_not_imported_entries_list.setEntries(not_imported);
	}

	public void setExamples(Collection<Example> imported,
			Collection<Example> not_imported) {
		_example_label.setText(getLabel(imported.size(), imported.size()
				+ not_imported.size(), "num_examples"));
		_imported_examples_list.setExamples(imported);
		_not_imported_examples_list.setExamples(not_imported);
	}

	public void loadState() {
		_clear_stats_box.setSelected(JVLT.getConfig().getBooleanProperty(
				"import_clear_stats", false));
	}

	public void saveState() {
		JVLT.getConfig().setProperty("import_clear_stats",
				_clear_stats_box.isSelected());
	}

	private void initUI() {
		_imported_entries_list = new EntryList();
		_not_imported_entries_list = new EntryList();
		_imported_examples_list = new ExampleList();
		_not_imported_examples_list = new ExampleList();
		_entry_label = new JLabel();
		_example_label = new JLabel();

		_clear_stats_box = new JCheckBox(GUIUtils
				.createTextAction("clear_stats"));

		CustomTabbedPane entry_panel = new CustomTabbedPane();
		JScrollPane sp = new JScrollPane(_imported_entries_list);
		entry_panel.addTab("imported_entries", sp);
		sp = new JScrollPane(_not_imported_entries_list);
		entry_panel.addTab("not_imported_entries", sp);

		CustomTabbedPane example_panel = new CustomTabbedPane();
		sp = new JScrollPane(_imported_examples_list);
		example_panel.addTab("imported_examples", sp);
		sp = new JScrollPane(_not_imported_examples_list);
		example_panel.addTab("not_imported_examples", sp);

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		_panel.add(_clear_stats_box, cc);
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(_entry_label, cc);
		cc.update(0, 2, 1.0, 0.5);
		_panel.add(entry_panel, cc);
		cc.update(0, 3, 1.0, 0.0);
		_panel.add(_example_label, cc);
		cc.update(0, 4, 1.0, 0.5);
		_panel.add(example_panel, cc);
	}

	private String getLabel(int num, int total, String i18n) {
		ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
				"Labels", i18n));
		String str = formatter.format(total);
		return I18nService.getString("Labels", "imported",
				new Object[] { num, str });
	}
}

class ImportSuccessDescriptor extends WizardPanelDescriptor {
	public ImportSuccessDescriptor(ImportWizardModel model) {
		super(model);

		initUI();
	}

	@Override
	public String getID() {
		return "success";
	}

	private void initUI() {
		JLabel label = new JLabel(I18nService.getString("Labels",
				"importing_successful"));
		label.setHorizontalAlignment(SwingConstants.CENTER);
		label.setVerticalAlignment(SwingConstants.CENTER);
		_panel = label;
	}
}
