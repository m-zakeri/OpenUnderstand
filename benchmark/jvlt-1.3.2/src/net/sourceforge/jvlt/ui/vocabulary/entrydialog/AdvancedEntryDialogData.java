package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Dimension;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.DefaultListModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JFileChooser;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.ListSelectionModel;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.EntryAttributeSchema;
import net.sourceforge.jvlt.core.EntryClass;
import net.sourceforge.jvlt.core.StringPair;
import net.sourceforge.jvlt.metadata.ChoiceAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.ui.components.ChoiceListPanel;
import net.sourceforge.jvlt.ui.components.CustomTabbedPane;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.dialogs.CustomDialogData;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.FileUtils;
import net.sourceforge.jvlt.utils.SimpleFileFilter;
import net.sourceforge.jvlt.utils.Utils;

import org.apache.log4j.Logger;

public class AdvancedEntryDialogData extends CustomDialogData {
	private static final Logger logger = Logger
			.getLogger(AdvancedEntryDialogData.class);

	private final JVLTModel _model;
	private final List<Entry> _entries;

	private EntryClass _orig_class;
	private String[] _orig_categories;
	private StringPair[] _orig_custom_fields;
	private String[] _orig_mmfiles;

	private ChoiceListPanel _category_selection_panel;
	private CustomFieldPanel _custom_field_panel;
	private EntryAttributeSchemaPanel _schema_panel;
	private FileSelectionPanel _file_selection_panel;
	private FlagSelectionPanel _flag_selection_panel;

	public AdvancedEntryDialogData(List<Entry> entries, JVLTModel model) {
		_entries = entries;
		_model = model;
		init();
	}

	@Override
	public void updateData() {
		/* Entry class */
		if (_schema_panel != null) {
			EntryClass ec = _schema_panel.getValue();
			if (_entries.size() == 1) {
				_entries.get(0).setEntryClass(ec);
			} else {
				if (ec == null) {
					if (_orig_class != null) {
						Iterator<Entry> it = _entries.iterator();
						for (; it.hasNext();) {
							it.next().setEntryClass(null);
						}
					}
				} else if (!ec.equals(_orig_class)) {
					/*
					 * Currently, only when the new entry class has another name
					 * as the old one, the entry class is updated. TODO: Update
					 * also if only attributes have changed
					 */
					for (Entry entry : _entries) {
						entry.setEntryClass(ec);
					}
				}
			}
		}

		/* Categories */
		String[] categories = Utils
				.objectArrayToStringArray(_category_selection_panel
						.getSelectedObjects());
		if (!Utils.arraysEqual(categories, _orig_categories)) {
			for (Entry entry : _entries) {
				entry.setCategories(categories);
			}
		}

		/* Custom fields */
		_custom_field_panel.updateData();
		StringPair[] custom_fields = _custom_field_panel.getKeyValuePairs();
		if (!Arrays.equals(custom_fields, _orig_custom_fields)) {
			for (Entry e : _entries) {
				e.setCustomFields(custom_fields);
			}
		}

		/* Multimedia files */
		String[] files = _file_selection_panel.getFiles();
		if (!Utils.arraysEqual(files, _orig_mmfiles)) {
			for (Entry entry : _entries) {
				entry.setMultimediaFiles(files);
			}
		}

		if (files.length > 0) {
			try {
				if (FileUtils.isPathRelative(files[files.length - 1])) {
					JVLT.getConfig().setProperty("use_relative_path", true);
				} else {
					JVLT.getConfig().setProperty("use_relative_path", false);
				}
			} catch (IOException e) {
				logger.error("Could not determine canonical path for '"
						+ files[files.length - 1] + "'", e);
			}
		}

		/* Set flags */
		_flag_selection_panel.apply();
	}

	@Override
	protected void loadState(UIConfig config) {
		if (config.containsKey("AdvancedEntryDialog.size")) {
			_content_pane.setPreferredSize(config.getDimensionProperty(
					"AdvancedEntryDialog.size", new Dimension(300, 200)));
		}
	}

	@Override
	protected void saveState(UIConfig config) {
		config.setProperty("AdvancedEntryDialog.size", _content_pane.getSize());
	}

	private void init() {
		_category_selection_panel = new ChoiceListPanel();
		_category_selection_panel.setAllowCustomChoices(true);

		_custom_field_panel = new CustomFieldPanel();

		_file_selection_panel = new FileSelectionPanel();
		String dict_file_name = _model.getDictFileName();
		if (dict_file_name != null && !dict_file_name.equals("")) {
			File file = new File(dict_file_name);
			File parent = file.getParentFile();
			if (parent != null) {
				try {
					_file_selection_panel.setPath(parent.getCanonicalPath());
				} catch (IOException e) {
					logger.error("Could not determine canonical path for '"
							+ parent + "'", e);
				}
			}
		}
		_file_selection_panel.setUseRelativePath(JVLT.getConfig()
				.getBooleanProperty("use_relative_path", false));
		SimpleFileFilter filter = new SimpleFileFilter(I18nService.getString(
				"Labels", "audio_files"));
		filter.setExtensions(MultimediaUtils.AUDIO_FILE_EXTENSIONS);
		_file_selection_panel.addFileFilter(filter);
		filter = new SimpleFileFilter(I18nService.getString("Labels",
				"image_files"));
		filter.setExtensions(MultimediaUtils.IMAGE_FILE_EXTENSIONS);
		_file_selection_panel.addFileFilter(filter);

		EntryAttributeSchema schema = _model.getDict()
				.getEntryAttributeSchema();
		if (schema == null) {
			_schema_panel = null;
		} else {
			_schema_panel = new EntryAttributeSchemaPanel(schema);
		}

		_flag_selection_panel = new FlagSelectionPanel(_entries);

		CustomTabbedPane tpane = new CustomTabbedPane();
		if (_schema_panel != null) {
			tpane.addTab("details", _schema_panel);
		}
		tpane.addTab("categories", _category_selection_panel);
		tpane.addTab("custom_fields", _custom_field_panel);
		tpane.addTab("multimedia_files", _file_selection_panel);
		tpane.addTab("flags", _flag_selection_panel);

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridLayout());
		_content_pane.add(tpane);

		// -----
		// Init data
		// -----
		MetaData data = _model.getDictModel().getMetaData(Entry.class);
		ChoiceAttribute choices_attr = (ChoiceAttribute) data
				.getAttribute("Categories");
		_category_selection_panel.setAvailableObjects(choices_attr.getValues());

		ChoiceAttribute custom_field_attr = (ChoiceAttribute) data
				.getAttribute("CustomFields");
		_custom_field_panel.setChoices(custom_field_attr.getValues());

		_orig_categories = _entries.get(0).getCategories();
		_orig_custom_fields = _entries.get(0).getCustomFields();
		_orig_mmfiles = _entries.get(0).getMultimediaFiles();
		_orig_class = _entries.get(0).getEntryClass();
		for (int i = 1; i < _entries.size(); i++) {
			if (_orig_categories.length > 0
					&& !Utils.arraysEqual(_orig_categories, _entries.get(i)
							.getCategories())) {
				_orig_categories = new String[0];
			}
			if (!Arrays.equals(_orig_custom_fields, _entries.get(i)
					.getCustomFields())) {
				_orig_custom_fields = null;
			}
			if (_orig_mmfiles.length > 0
					&& !Utils.arraysEqual(_orig_mmfiles, _entries.get(i)
							.getMultimediaFiles())) {
				_orig_mmfiles = new String[0];
			}
			if (_orig_class != null
					&& !_orig_class.equals(_entries.get(i).getEntryClass())) {
				_orig_class = null;
			}
		}

		_category_selection_panel.setSelectedObjects(_orig_categories);
		_custom_field_panel.setKeyValuePairs(_orig_custom_fields);
		_file_selection_panel.setFiles(_orig_mmfiles);
		if (schema != null) {
			_schema_panel.setValue(_orig_class);
		}
	}
}

class FileSelectionPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private static final Logger logger = Logger
			.getLogger(FileSelectionPanel.class);

	private class ChangeHandler implements ChangeListener {
		public void stateChanged(ChangeEvent e) {
			update();
		}
	}

	private class ListSelectionHandler implements ListSelectionListener {
		public void valueChanged(ListSelectionEvent ev) {
			if (!ev.getValueIsAdjusting()) {
				update();
			}
		}
	}

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("add")) {
				String value = _field.getText();
				if (!"".equals(value) && !_list_model.contains(value)) {
					_list_model.addElement(value);
					_list.setSelectedIndex(_list_model.size() - 1);
				}
			} else if (ev.getActionCommand().equals("remove")) {
				int index = _list.getSelectedIndex();
				if (index >= 0) {
					_list_model.remove(index);
					update();
				}
			} else if (ev.getActionCommand().equals("browse")) {
				JFileChooser chooser = new JFileChooser();
				Iterator<SimpleFileFilter> it = _file_filters.iterator();
				while (it.hasNext()) {
					chooser.addChoosableFileFilter(it.next());
				}

				File file = new File(_path);
				chooser.setCurrentDirectory(file);

				int val = chooser.showOpenDialog(FileSelectionPanel.this);
				if (val == JFileChooser.APPROVE_OPTION) {
					File f = chooser.getSelectedFile();
					if (_relative_path_box.isSelected()) {
						_field.setText(FileUtils.getRelativePath(
								new File(_path), f));
					} else {
						try {
							_field.setText(f.getCanonicalPath());
						} catch (IOException e) {
							logger.error("Could not determine canonical path "
									+ "for '" + f + "'", e);
						}
					}
				}
			} else if (ev.getActionCommand().equals("relative_path")) {
				int index = _list.getSelectedIndex();
				if (index < 0) {
					return;
				}

				String path = _list_model.get(index).toString();
				File f;
				try {
					if (FileUtils.isPathRelative(path)) {
						f = new File(_path + File.separator + path);
					} else {
						f = new File(path);
					}

					if (_relative_path_box.isSelected()) {
						_list_model.set(index, FileUtils.getRelativePath(
								new File(_path), f));
					} else {
						_list_model.set(index, f.getCanonicalPath());
					}
				} catch (IOException e) {
					logger.error("Could not determine canonical path for '"
							+ path + "'", e);
				}
			} else if (ev.getActionCommand().equals("up")
					|| ev.getActionCommand().equals("down")) {
				int index = _list.getSelectedIndex();
				Object item = _list_model.remove(index);
				index = ev.getActionCommand().equals("up") ? index - 1
						: index + 1;
				_list_model.insertElementAt(item, index);
				_list.setSelectedIndex(index);
			}
		}
	}

	private final List<SimpleFileFilter> _file_filters;
	private String _path;
	private boolean _use_relative_path;

	private Action _add_action;
	private Action _browse_action;
	private Action _remove_action;
	private Action _up_action;
	private Action _down_action;
	private CustomTextField _field;
	private DefaultListModel _list_model;
	private JCheckBox _relative_path_box;
	private JList _list;

	public FileSelectionPanel() {
		_path = System.getProperty("user.home");
		_use_relative_path = false;
		_file_filters = new ArrayList<SimpleFileFilter>();

		init();
	}

	public String getPath() {
		return _path;
	}

	public String[] getFiles() {
		return Utils.objectArrayToStringArray(_list_model.toArray());
	}

	public void addFileFilter(SimpleFileFilter filter) {
		_file_filters.add(filter);
	}

	public void setPath(String path) {
		_path = path;
	}

	public void setFiles(String[] files) {
		_list_model.clear();
		for (String file : files) {
			_list_model.addElement(file);
		}
	}

	public void setUseRelativePath(boolean relative) {
		_use_relative_path = relative;
		_relative_path_box.setSelected(relative);
	}

	private void init() {
		ActionHandler handler = new ActionHandler();
		_add_action = GUIUtils.createTextAction(handler, "add");
		_browse_action = GUIUtils.createTextAction(handler, "browse");
		_remove_action = GUIUtils.createTextAction(handler, "remove");
		_up_action = GUIUtils.createIconAction(handler, "up");
		_down_action = GUIUtils.createIconAction(handler, "down");
		Action relative_path_action = GUIUtils.createTextAction(handler,
				"relative_path");

		_list_model = new DefaultListModel();
		_list = new JList(_list_model);
		_list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
		_list.addListSelectionListener(new ListSelectionHandler());

		_field = new CustomTextField(20);
		_field.addChangeListener(new ChangeHandler());

		_relative_path_box = new JCheckBox(relative_path_action);
		_relative_path_box.setSelected(_use_relative_path);

		JScrollPane list_scrpane = new JScrollPane();
		list_scrpane.setPreferredSize(new Dimension(100, 50));
		list_scrpane.getViewport().setView(_list);

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_field, cc);
		cc.update(1, 0, 0.0, 0.0);
		add(new JButton(_browse_action), cc);
		cc.update(0, 1, 1.0, 1.0, 1, 5);
		add(list_scrpane, cc);
		cc.update(1, 1, 0.0, 0.0, 1, 1);
		add(new JButton(_add_action), cc);
		cc.update(1, 2, 0.0, 0.0);
		add(new JButton(_remove_action), cc);
		cc.update(1, 3, 0.0, 0.0);
		add(new JButton(_up_action), cc);
		cc.update(1, 4, 0.0, 0.0);
		add(new JButton(_down_action), cc);
		cc.update(1, 5, 0.0, 1.0);
		add(Box.createVerticalGlue(), cc);
		cc.update(0, 6, 1.0, 0.0, 2, 1);
		add(_relative_path_box, cc);

		update();
	}

	protected void update() {
		String path = getCurrentPath();

		_add_action.setEnabled(_field.getText().length() > 0);
		_remove_action.setEnabled(path != null);
		_relative_path_box.setEnabled(path != null);
		if (path != null) {
			try {
				_relative_path_box.setSelected(FileUtils.isPathRelative(path));
			} catch (IOException e) {
				logger.error("Could not determine canonical path for '" + path
						+ "'", e);
			}
		}

		_up_action.setEnabled(_list.getSelectedIndex() > 0);
		_down_action.setEnabled(_list.getSelectedIndex() >= 0
				&& _list.getSelectedIndex() < _list_model.getSize() - 1);
	}

	private String getCurrentPath() {
		String path = null;
		int index = _list.getSelectedIndex();
		if (index >= 0) {
			path = _list_model.get(index).toString();
		}

		return path;
	}
}
