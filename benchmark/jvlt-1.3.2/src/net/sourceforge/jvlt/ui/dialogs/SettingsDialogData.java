package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.ListSelectionModel;
import javax.swing.LookAndFeel;
import javax.swing.SpinnerNumberModel;
import javax.swing.SwingConstants;
import javax.swing.UIManager;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.DefaultTableModel;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.metadata.DefaultAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.AudioFile;
import net.sourceforge.jvlt.multimedia.CustomMultimediaFile;
import net.sourceforge.jvlt.multimedia.ImageFile;
import net.sourceforge.jvlt.multimedia.MultimediaFile;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.ui.components.AttributeSelectionPanel;
import net.sourceforge.jvlt.ui.components.ButtonPanel;
import net.sourceforge.jvlt.ui.components.CustomTabbedPane;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.FontChooserComboBox;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.components.LabeledSpinner;
import net.sourceforge.jvlt.ui.table.SortableTable;
import net.sourceforge.jvlt.ui.table.SortableTableModel;
import net.sourceforge.jvlt.ui.table.SortableTableModel.SortOrder;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.FontInfo;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.FileUtils;
import net.sourceforge.jvlt.utils.Utils;

public class SettingsDialogData extends CustomDialogData implements
		ActionListener {
	private enum FontKey {
		PRINT("print_font"), HTML("html_font"), HTML_ORTH("orth_font"), HTML_PRON(
				"pron_font"), UI("ui_font"), UI_ORTH("ui_orth_font"), UI_PRON(
				"ui_pron_font");

		private String _action_command;

		private FontKey(String action_command) {
			_action_command = action_command;
		}

		public String getActionCommand() {
			return _action_command;
		}
	}

	private final Map<FontKey, Font> _old_fonts = new HashMap<FontKey, Font>();
	private Locale _old_locale;
	private final boolean _old_restore_previously_open;
	private final boolean _old_play_immediately;
	private final LookAndFeel _old_laf;
	private final HashMap<String, Locale> _string_locale_map;
	private final HashMap<String, String> _string_laf_map;
	private final int _old_num_batches;
	private final float _old_expiration_factor;
	private final String _old_expiration_unit;
	private final Attribute[] _old_displayed_attrs;

	private final JVLTModel _model;

	private JCheckBox _restore_chbox;
	private JCheckBox _play_immediately_chbox;
	private LabeledComboBox _locale_cobox;
	private LabeledComboBox _laf_cobox;
	private FileTypePanel _file_type_panel;
	private final Map<FontKey, FontChooserComboBox> _font_boxes = new HashMap<FontKey, FontChooserComboBox>();
	private ExpirationTimePanel _expiration_panel;
	private AttributeSelectionPanel _displayed_attrs_panel;

	public SettingsDialogData(JVLTModel model) {
		_model = model;
		UIConfig config = (UIConfig) JVLT.getConfig();

		_old_fonts.put(FontKey.PRINT, config.getFontProperty("print_font"));
		_old_fonts.put(FontKey.HTML, config.getFontProperty("html_font"));
		_old_fonts.put(FontKey.HTML_ORTH, config.getFontProperty("orth_font"));
		_old_fonts.put(FontKey.HTML_PRON, config.getFontProperty("pron_font"));
		_old_fonts.put(FontKey.UI, config.getFontProperty("ui_font"));
		_old_fonts.put(FontKey.UI_ORTH, config.getFontProperty("ui_orth_font"));
		_old_fonts.put(FontKey.UI_PRON, config.getFontProperty("ui_pron_font"));
		_old_restore_previously_open = config.getBooleanProperty(
				"restore_previously_open_file", false);
		_old_play_immediately = config.getBooleanProperty(
				"play_audio_immediately", false);
		_old_num_batches = config.getIntProperty("num_batches", 7);
		_old_expiration_factor = config.getFloatProperty("expiration_factor",
				3.0f);
		_old_expiration_unit = config.getProperty("expiration_unit",
				Entry.UNIT_DAYS);

		MetaData data = model.getDictModel().getMetaData(Entry.class);
		String[] attr_names;
		Object[] attrs = (Object[]) JVLT.getRuntimeProperties().get(
				"displayed_attributes");
		if (attrs != null) {
			attr_names = Utils.objectArrayToStringArray(attrs);
		} else {
			attr_names = new String[0];
		}
		_old_displayed_attrs = new Attribute[attr_names.length];
		for (int i = 0; i < attr_names.length; i++) {
			_old_displayed_attrs[i] = data.getAttribute(attr_names[i]);
		}

		_old_locale = null;
		Locale locale = config.getLocaleProperty("locale", Locale.getDefault());
		Locale[] locales = JVLT.getSupportedLocales();
		_string_locale_map = new HashMap<String, Locale>();
		for (Locale locale2 : locales) {
			_string_locale_map.put(locale2.getDisplayLanguage(), locale2);
			if (locale2.equals(locale)) {
				_old_locale = locale;
			}
		}
		if (_old_locale == null) {
			_old_locale = Locale.US;
		}

		_old_laf = UIManager.getLookAndFeel();
		_string_laf_map = new HashMap<String, String>();
		String class_name;
		String id;
		try {
			class_name = _old_laf.getClass().getName();
			id = _old_laf.getID();
			_string_laf_map.put(id, class_name);

			class_name = UIManager.getSystemLookAndFeelClassName();
			id = ((LookAndFeel) Class.forName(class_name).newInstance())
					.getID();
			_string_laf_map.put(id, class_name);

			class_name = "javax.swing.plaf.metal.MetalLookAndFeel";
			id = ((LookAndFeel) Class.forName(class_name).newInstance())
					.getID();
			_string_laf_map.put(id, class_name);
		} catch (Exception ex) {
			ex.printStackTrace();
		}

		init();
	}

	@Override
	public void updateData() {
		Locale new_locale = _string_locale_map.get(_locale_cobox
				.getSelectedItem());
		String new_laf_string = _string_laf_map.get(_laf_cobox
				.getSelectedItem());
		Map<FontKey, FontInfo> new_font_infos = new HashMap<FontKey, FontInfo>();
		Map<FontKey, Font> new_fonts = new HashMap<FontKey, Font>();
		for (Map.Entry<FontKey, FontChooserComboBox> e : _font_boxes.entrySet()) {
			new_font_infos.put(e.getKey(), e.getValue().getFontInfo());
		}
		boolean new_restore_previously_open = _restore_chbox.isSelected();
		boolean new_play_immediately = _play_immediately_chbox.isSelected();
		int new_num_batches = _expiration_panel.getNumBatches();
		float new_expiration_factor = _expiration_panel.getExpirationFactor();
		String new_expiration_unit = _expiration_panel.getExpirationUnit();
		Object[] new_displayed_attrs = _displayed_attrs_panel
				.getSelectedObjects();

		for (Map.Entry<FontKey, FontChooserComboBox> e : _font_boxes.entrySet()) {
			new_font_infos.put(e.getKey(), e.getValue().getFontInfo());
		}

		for (Map.Entry<FontKey, FontInfo> e : new_font_infos.entrySet()) {
			new_fonts.put(e.getKey(), e.getValue() == null ? null : e
					.getValue().getFont());
		}

		UIConfig config = (UIConfig) JVLT.getConfig();
		config.setProperty("print_font", new_fonts.get(FontKey.PRINT));
		config.setProperty("html_font", new_fonts.get(FontKey.HTML));
		config.setProperty("ui_font", new_fonts.get(FontKey.UI));
		config.setProperty("ui_orth_font", new_fonts.get(FontKey.UI_ORTH));
		config.setProperty("ui_pron_font", new_fonts.get(FontKey.UI_PRON));
		config.setProperty("orth_font", new_fonts.get(FontKey.HTML_ORTH));
		config.setProperty("pron_font", new_fonts.get(FontKey.HTML_PRON));
		config.setProperty("locale", new_locale);
		config.setProperty("restore_previously_open_file", String
				.valueOf(new_restore_previously_open));
		config.setProperty("look_and_feel", new_laf_string);
		config.setProperty("play_audio_immediately", new_play_immediately);
		config.setProperty("num_batches", new_num_batches);
		config.setProperty("expiration_factor", new_expiration_factor);
		config.setProperty("expiration_unit", new_expiration_unit);
		JVLT.getRuntimeProperties().put("displayed_attributes",
				new_displayed_attrs);

		_file_type_panel.save();

		if (isFontUpdated(FontKey.HTML, new_fonts)
				|| isFontUpdated(FontKey.HTML_ORTH, new_fonts)
				|| isFontUpdated(FontKey.HTML_PRON, new_fonts)
				|| isFontUpdated(FontKey.UI, new_fonts)
				|| isFontUpdated(FontKey.UI_ORTH, new_fonts)
				|| isFontUpdated(FontKey.UI_PRON, new_fonts)
				|| !_old_locale.equals(new_locale)
				|| !_old_laf.getClass().getName().equals(new_laf_string)) {
			MessageDialog.showDialog(_content_pane,
					MessageDialog.WARNING_MESSAGE, I18nService.getString(
							"Messages", "restart"));
		}
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("look_and_feel")) {
			Object item = _laf_cobox.getSelectedItem();
			boolean metal_theme = _string_laf_map.get(item).equals(
					"javax.swing.plaf.metal.MetalLookAndFeel");
			_font_boxes.get(FontKey.UI).setEnabled(metal_theme);
		}
	}

	private void init() {
		_content_pane = new JPanel();

		for (FontKey k : FontKey.values()) {
			FontChooserComboBox b = new FontChooserComboBox();
			_font_boxes.put(k, b);

			Font f = _old_fonts.get(k);
			b.setFontInfo(f == null ? null : new FontInfo(f));
			b.setActionCommand(k.getActionCommand());
		}

		_laf_cobox = new LabeledComboBox();
		_laf_cobox.setLabel("look_and_feel");
		Iterator<String> it = _string_laf_map.keySet().iterator();
		while (it.hasNext()) {
			_laf_cobox.addItem(it.next());
		}
		_laf_cobox.addActionListener(this);
		_laf_cobox.setSelectedItem(_old_laf.getID());

		_locale_cobox = new LabeledComboBox();
		_locale_cobox.setLabel("locale");
		Locale[] locales = JVLT.getSupportedLocales();
		for (Locale locale : locales) {
			_locale_cobox.addItem(locale.getDisplayLanguage());
		}
		_locale_cobox.setSelectedItem(_old_locale.getDisplayLanguage());

		_displayed_attrs_panel = new AttributeSelectionPanel();
		_displayed_attrs_panel.setAllowReordering(true);
		_displayed_attrs_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"displayed_attributes")));
		MetaData data = _model.getDictModel().getMetaData(Entry.class);
		_displayed_attrs_panel.setAvailableObjects(data.getAttributes());
		_displayed_attrs_panel.setSelectedObjects(_old_displayed_attrs);

		_restore_chbox = new JCheckBox(GUIUtils.createTextAction(this,
				"restore_previously_open"));
		_restore_chbox.setSelected(_old_restore_previously_open);

		_file_type_panel = new FileTypePanel();
		_file_type_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"file_types")));
		_play_immediately_chbox = new JCheckBox(GUIUtils.createTextAction(this,
				"play_audio_immediately"));
		_play_immediately_chbox.setSelected(_old_play_immediately);

		JPanel appearance_panel = new JPanel();
		appearance_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		appearance_panel.add(_laf_cobox.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		appearance_panel.add(_laf_cobox, cc);
		cc.update(0, 1, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI).getJLabel(), cc);
		cc.update(1, 1, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI), cc);
		cc.update(0, 2, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI_ORTH).getJLabel(), cc);
		cc.update(1, 2, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI_ORTH), cc);
		cc.update(0, 3, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI_PRON).getJLabel(), cc);
		cc.update(1, 3, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.UI_PRON), cc);
		cc.update(0, 4, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.HTML).getJLabel(), cc);
		cc.update(1, 4, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.HTML), cc);
		cc.update(0, 5, 1.0, 0.0);
		appearance_panel
				.add(_font_boxes.get(FontKey.HTML_ORTH).getJLabel(), cc);
		cc.update(1, 5, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.HTML_ORTH), cc);
		cc.update(0, 6, 1.0, 0.0);
		appearance_panel
				.add(_font_boxes.get(FontKey.HTML_PRON).getJLabel(), cc);
		cc.update(1, 6, 1.0, 0.0);
		appearance_panel.add(_font_boxes.get(FontKey.HTML_PRON), cc);
		cc.update(0, 7, 1.0, 0.0);
		appearance_panel.add(_locale_cobox.getLabel(), cc);
		cc.update(1, 7, 1.0, 0.0);
		appearance_panel.add(_locale_cobox, cc);
		cc.update(0, 8, 1.0, 0.0, 2, 1);
		appearance_panel.add(_displayed_attrs_panel, cc);
		cc.update(0, 9, 0.0, 1.0);
		appearance_panel.add(Box.createVerticalGlue(), cc);

		JPanel printing_panel = new JPanel();
		printing_panel
				.setBorder(new TitledBorder(new EtchedBorder(
						EtchedBorder.LOWERED), I18nService.getString("Labels",
						"printing")));
		printing_panel.setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 0.0);
		printing_panel.add(_font_boxes.get(FontKey.PRINT).getJLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		printing_panel.add(_font_boxes.get(FontKey.PRINT), cc);

		_expiration_panel = new ExpirationTimePanel();
		_expiration_panel.setNumBatches(_old_num_batches);
		_expiration_panel.setExpirationFactor(_old_expiration_factor);
		_expiration_panel.setExpirationUnit(_old_expiration_unit);
		_expiration_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"expiration_time")));

		JPanel general_panel = new JPanel();
		general_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		general_panel.add(_restore_chbox, cc);
		cc.update(0, 1, 1.0, 0.0);
		general_panel.add(printing_panel, cc);
		cc.update(0, 2, 1.0, 0.0);
		general_panel.add(_expiration_panel, cc);
		cc.update(0, 3, 0.0, 1.0);
		general_panel.add(Box.createVerticalGlue(), cc);

		JPanel multimedia_panel = new JPanel();
		multimedia_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		multimedia_panel.add(_play_immediately_chbox, cc);
		cc.update(0, 1, 1.0, 1.0);
		multimedia_panel.add(_file_type_panel, cc);

		CustomTabbedPane tab_pane = new CustomTabbedPane();
		tab_pane.addTab("appearance", appearance_panel);
		tab_pane.addTab("general", general_panel);
		tab_pane.addTab("multimedia_files", multimedia_panel);

		_content_pane.setLayout(new GridLayout());
		_content_pane.add(tab_pane);
	}

	private boolean isFontUpdated(FontKey key, Map<FontKey, Font> new_fonts) {
		if (_old_fonts.get(key) == null) {
			return new_fonts.get(key) == null;
		}
		return _old_fonts.get(key).equals(new_fonts.get(key));
	}
}

class FileTypePanel extends JPanel implements ListSelectionListener,
		ActionListener {
	private static final long serialVersionUID = 1L;

	private final TreeMap<String, MultimediaFile> _extensions;
	private final TreeSet<String> _default_extensions;

	private Action _add_action;
	private Action _edit_action;
	private Action _remove_action;
	private SortableTable<MultimediaFile> _table;
	private SortableTableModel<MultimediaFile> _table_model;

	public FileTypePanel() {
		_extensions = new TreeMap<String, MultimediaFile>();
		_default_extensions = new TreeSet<String>();

		load();
		init();
		update();
	}

	public final void load() {
		_extensions.clear();
		_default_extensions.clear();
		String[] exts = MultimediaUtils.AUDIO_FILE_EXTENSIONS;
		for (String ext : exts) {
			_extensions.put(ext, new AudioFile("." + ext));
			_default_extensions.add(ext);
		}

		exts = MultimediaUtils.IMAGE_FILE_EXTENSIONS;
		for (String ext : exts) {
			_extensions.put(ext, new ImageFile("." + ext));
			_default_extensions.add(ext);
		}

		exts = JVLT.getConfig().getStringListProperty("custom_extensions",
				new String[0]);
		for (String ext : exts) {
			String[] ext_prop = JVLT.getConfig().getStringListProperty(
					"extension_" + ext, new String[0]);
			CustomMultimediaFile f = new CustomMultimediaFile("." + ext,
					Integer.parseInt(ext_prop[0]));
			f.setCommand(ext_prop[1]);
			_extensions.put(ext, f);
		}
	}

	public void save() {
		// Remove all extension_* keys from the config file
		for (String s : JVLT.getConfig().getKeys()) {
			if (s.startsWith("extension_")) {
				JVLT.getConfig().remove(s);
			}
		}

		// Insert all custom file types
		Iterator<String> it2 = _extensions.keySet().iterator();
		TreeSet<String> custom_extensions = new TreeSet<String>();
		while (it2.hasNext()) {
			String extension = it2.next();
			MultimediaFile file = _extensions.get(extension);
			if (file instanceof CustomMultimediaFile) {
				CustomMultimediaFile cmf = (CustomMultimediaFile) file;
				JVLT.getConfig().setProperty("extension_" + extension,
						new Object[] { cmf.getType(), cmf.getCommand() });
				custom_extensions.add(extension);
			}
		}
		JVLT.getConfig().setProperty("custom_extensions",
				custom_extensions.toArray());
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting()) {
			update();
		}
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("add")) {
			FileTypeDialogData data = new FileTypeDialogData(
					new CustomMultimediaFile(MultimediaFile.OTHER_FILE),
					_default_extensions);
			int result = CustomDialog.showDialog(data, this, I18nService
					.getString("Labels", "edit_file_type"));
			if (result == AbstractDialog.OK_OPTION) {
				MultimediaFile file = data.getFile();
				_table_model.addObject(file);
				_extensions.put(FileUtils.getFileExtension(file.getFileName()),
						file);
			}
		} else if (ev.getActionCommand().equals("edit")) {
			List<MultimediaFile> objs = _table.getSelectedObjects();
			MultimediaFile file = objs.get(0);
			FileTypeDialogData data = new FileTypeDialogData(file,
					_default_extensions);
			int result = CustomDialog.showDialog(data, this, I18nService
					.getString("Labels", "edit_file_type"));
			if (result == AbstractDialog.OK_OPTION) {
				_table_model.removeObject(file);
				file = data.getFile();
				_table_model.addObject(file);
				_extensions.put(FileUtils.getFileExtension(file.getFileName()),
						file);
			}
		} else if (ev.getActionCommand().equals("remove")) {
			List<MultimediaFile> objs = _table.getSelectedObjects();
			MultimediaFile file = objs.get(0);
			_table_model.removeObject(file);
			_extensions.remove(FileUtils.getFileExtension(file.getFileName()));
		}
	}

	private void init() {
		_add_action = GUIUtils.createTextAction(this, "add");
		_edit_action = GUIUtils.createTextAction(this, "edit");
		_remove_action = GUIUtils.createTextAction(this, "remove");

		MultimediaFileMetaData data = new MultimediaFileMetaData();
		_table_model = new SortableTableModel<MultimediaFile>(data);
		_table_model.setColumnNames(data.getAttributeNames());
		_table_model.setObjects(_extensions.values());
		_table_model.setSortingDirective(new SortableTableModel.Directive(0,
				SortOrder.ASCENDING));
		_table = new SortableTable<MultimediaFile>(_table_model);
		_table.getSelectionModel().addListSelectionListener(this);
		_table.getSelectionModel().setSelectionMode(
				ListSelectionModel.SINGLE_SELECTION);
		_table.setShowTooltips(JVLT.getConfig().getBooleanProperty(
				"Table.showTooltips", true));
		JScrollPane scrpane = new JScrollPane();
		scrpane.getViewport().setView(_table);
		scrpane.setPreferredSize(new Dimension(250, 150));

		ButtonPanel button_panel = new ButtonPanel(SwingConstants.VERTICAL,
				SwingConstants.TOP);
		button_panel.addButtons(new JButton[] { new JButton(_add_action),
				new JButton(_edit_action), new JButton(_remove_action) });

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		add(scrpane, cc);
		cc.update(1, 0, 0.0, 1.0);
		add(button_panel, cc);
	}

	private void update() {
		List<MultimediaFile> objs = _table.getSelectedObjects();
		_edit_action.setEnabled(objs.size() > 0);
		_remove_action.setEnabled(objs.size() > 0);
		if (objs.size() > 0) {
			MultimediaFile file = objs.get(0);
			_remove_action.setEnabled(!_default_extensions.contains(FileUtils
					.getFileExtension(file.getFileName())));
		}
	}
}

class MultimediaFileMetaData extends MetaData {
	public MultimediaFileMetaData() {
		super(MultimediaFile.class);
	}

	@Override
	protected void init() {
		addAttribute(new DefaultAttribute("Extension", String.class) {
			@Override
			public Object getValue(Object o) {
				MultimediaFile m = (MultimediaFile) o;
				return FileUtils.getFileExtension(m.getFileName());
			}
		});
		addAttribute(new DefaultAttribute("Type", String.class) {
			@Override
			public Object getValue(Object o) {
				return getValue(o, "TypeString");
			}
		});
		addAttribute(new DefaultAttribute("Command", String.class) {
			@Override
			public Object getValue(Object o) {
				if (o instanceof CustomMultimediaFile) {
					return getValue(o, "Command");
				}
				return "-";
			}
		});
	}
}

class FileTypeDialogData extends CustomDialogData implements ActionListener {
	private final Set<String> _default_extensions;
	private MultimediaFile _file;

	private Action _browse_action;
	private CustomTextField _extension_field;
	private JCheckBox _jvlt_plays_box;
	private LabeledComboBox _type_box;
	private CustomTextField _command_field;

	public FileTypeDialogData(MultimediaFile file,
			Set<String> default_extensions) {
		_file = file;
		_default_extensions = default_extensions;

		init();
		update();
	}

	public MultimediaFile getFile() {
		return _file;
	}

	@Override
	public void updateData() throws InvalidDataException {
		String extension = FileUtils.getFileExtension(_file.getFileName());
		String new_ext = _extension_field.getText();
		boolean default_type = _default_extensions.contains(extension);
		if (!default_type && _default_extensions.contains(new_ext)) {
			throw new InvalidDataException(I18nService.getString("Messages",
					"overwrite_extension", new String[] { new_ext }));
		}

		int type;
		if (_type_box.getSelectedItem().toString().equals(
				I18nService.getString("Labels", "audio_file"))) {
			type = MultimediaFile.AUDIO_FILE;
		} else if (_type_box.getSelectedItem().toString().equals(
				I18nService.getString("Labels", "image_file"))) {
			type = MultimediaFile.IMAGE_FILE;
		} else {
			type = MultimediaFile.OTHER_FILE;
		}

		if (_jvlt_plays_box.isSelected()) {
			if (type == MultimediaFile.AUDIO_FILE) {
				_file = new AudioFile("." + new_ext);
			} else {
				// if (type == MultimediaFile.IMAGE_FILE)
				_file = new ImageFile("." + new_ext);
			}
		} else {
			CustomMultimediaFile file = new CustomMultimediaFile("." + new_ext,
					type);
			file.setCommand(_command_field.getText());
			_file = file;
		}
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("jvlt_plays")) {
			update();
		} else if (ev.getActionCommand().equals("browse")) {
			JFileChooser chooser = new JFileChooser();
			int val = chooser.showOpenDialog(_content_pane);
			if (val == JFileChooser.APPROVE_OPTION) {
				File f = chooser.getSelectedFile();
				_command_field.setText(f.getAbsolutePath());
			}
		}
	}

	private void init() {
		_browse_action = GUIUtils.createTextAction(this, "browse");
		_extension_field = new CustomTextField(20);
		_extension_field.setActionCommand("extension");
		_command_field = new CustomTextField(20);
		_command_field.setActionCommand("command");
		_jvlt_plays_box = new JCheckBox(GUIUtils.createTextAction(this,
				"jvlt_plays"));
		_jvlt_plays_box.addActionListener(this);
		_type_box = new LabeledComboBox();
		_type_box.setLabel("type");

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		_content_pane.add(_extension_field.getLabel(), cc);
		cc.update(1, 0, 0.0, 0.0);
		_content_pane.add(_extension_field, cc);
		cc.update(2, 0, 1.0, 0.0);
		_content_pane.add(Box.createHorizontalGlue(), cc);
		cc.update(0, 1, 0.0, 0.0);
		_content_pane.add(_type_box.getLabel(), cc);
		cc.update(1, 1, 0.0, 0.0);
		_content_pane.add(_type_box, cc);
		cc.update(2, 1, 0.0, 0.0);
		_content_pane.add(Box.createHorizontalGlue(), cc);
		cc.update(0, 2, 0.0, 0.0, 3, 1);
		_content_pane.add(_jvlt_plays_box, cc);
		cc.update(0, 3, 0.0, 0.0, 1, 1);
		_content_pane.add(_command_field.getLabel(), cc);
		cc.update(1, 3, 0.0, 0.0);
		cc.fill = GridBagConstraints.HORIZONTAL;
		_content_pane.add(_command_field, cc);
		cc.update(2, 3, 0.0, 0.0);
		_content_pane.add(new JButton(_browse_action), cc);
		cc.update(0, 4, 0.0, 0.0);
		_content_pane.add(new JLabel(I18nService.getString("Labels",
				"command_description")), cc);

		String extension = FileUtils.getFileExtension(_file.getFileName());
		boolean default_type = _default_extensions.contains(extension);
		_type_box.addItem(I18nService.getString("Labels", "audio_file"));
		_type_box.addItem(I18nService.getString("Labels", "image_file"));
		_type_box.addItem(I18nService.getString("Labels", "other_file"));
		_type_box.setSelectedItem(_file.getTypeString());
		_extension_field.setText(extension);
		_extension_field.setEnabled(!default_type);
		_type_box.setEnabled(!default_type);
		if (!default_type) {
			_jvlt_plays_box.setSelected(false);
			_jvlt_plays_box.setEnabled(false);
		} else {
			_jvlt_plays_box
					.setSelected(!(_file instanceof CustomMultimediaFile));
		}
		if (_file instanceof CustomMultimediaFile) {
			CustomMultimediaFile f = (CustomMultimediaFile) _file;
			_command_field.setText(f.getCommand());
		}
	}

	private void update() {
		_browse_action.setEnabled(!_jvlt_plays_box.isSelected());
		_command_field.setEnabled(!_jvlt_plays_box.isSelected());
	}
}

class ExpirationTimePanel extends JPanel {
	private class ActionHandler implements ActionListener, ChangeListener {
		public void actionPerformed(ActionEvent e) {
			updateTable();
		}

		public void stateChanged(ChangeEvent e) {
			updateTable();
		}
	}

	private static final long serialVersionUID = 1L;

	private final DefaultTableModel _table_model;
	private final SpinnerNumberModel _batches_spinner_model;
	private final SpinnerNumberModel _factor_spinner_model;
	private final LabeledComboBox _unit_box;

	public ExpirationTimePanel() {
		// Create table
		_table_model = new DefaultTableModel() {
			private static final long serialVersionUID = 1L;

			@Override
			public boolean isCellEditable(int row, int col) {
				return false;
			}
		};
		_table_model.addColumn(I18nService.getString("Labels", "batch"));
		_table_model.addColumn(I18nService.getString("Labels", "duration"));
		JTable table = new JTable(_table_model);
		table.getTableHeader().setReorderingAllowed(false);
		table.setPreferredScrollableViewportSize(new Dimension(100, 100));
		JScrollPane pane = new JScrollPane(table);

		_batches_spinner_model = new SpinnerNumberModel();
		_batches_spinner_model.setStepSize(1);
		_batches_spinner_model.setMinimum(1);
		_batches_spinner_model.setMaximum(20);
		_batches_spinner_model.setValue(7);
		LabeledSpinner batches_spinner = new LabeledSpinner(
				_batches_spinner_model);
		batches_spinner.addChangeListener(new ActionHandler());
		batches_spinner.setLabel("num_batches");

		_factor_spinner_model = new SpinnerNumberModel();
		_factor_spinner_model.setStepSize(new Double(0.5));
		_factor_spinner_model.setMinimum(new Double(1.0));
		_factor_spinner_model.setMaximum(new Double(10));
		_factor_spinner_model.setValue(new Double(3));
		LabeledSpinner factor_spinner = new LabeledSpinner(
				_factor_spinner_model);
		factor_spinner.addChangeListener(new ActionHandler());
		factor_spinner.setLabel("expiration_factor");

		_unit_box = new LabeledComboBox();
		_unit_box.setLabel("unit");
		_unit_box.addItem(I18nService.getString("Labels", "days"));
		_unit_box.addItem(I18nService.getString("Labels", "hours"));
		_unit_box.addActionListener(new ActionHandler());

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(batches_spinner.getLabel(), cc);
		cc.update(1, 0, 0.0, 0.0);
		add(batches_spinner, cc);
		cc.update(0, 1, 1.0, 0.0);
		add(factor_spinner.getLabel(), cc);
		cc.update(1, 1, 0.0, 0.0);
		add(factor_spinner, cc);
		cc.update(0, 2, 1.0, 0.0);
		add(_unit_box.getLabel(), cc);
		cc.update(1, 2, 0.0, 0.0);
		add(_unit_box, cc);
		cc.update(0, 3, 1.0, 1.0, 2, 1);
		add(pane, cc);

		updateTable();
	}

	public int getNumBatches() {
		return _batches_spinner_model.getNumber().intValue();
	}

	public void setNumBatches(int num) {
		_batches_spinner_model.setValue(num);
	}

	public float getExpirationFactor() {
		return _factor_spinner_model.getNumber().floatValue();
	}

	public void setExpirationFactor(float factor) {
		_factor_spinner_model.setValue(new Double(factor));
	}

	public String getExpirationUnit() {
		if (_unit_box.getSelectedItem().equals(
				I18nService.getString("Labels", "hours"))) {
			return Entry.UNIT_HOURS;
		}
		return Entry.UNIT_DAYS;
	}

	public void setExpirationUnit(String unit) {
		if (unit.equals(Entry.UNIT_HOURS)) {
			_unit_box.setSelectedItem(I18nService.getString("Labels", "hours"));
		} else {
			_unit_box.setSelectedItem(I18nService.getString("Labels", "days"));
		}
	}

	private void updateTable() {
		int num_batches = _batches_spinner_model.getNumber().intValue();
		double factor = _factor_spinner_model.getNumber().doubleValue();
		Object[][] new_data = new Object[num_batches][2];
		for (int i = 0; i < num_batches; i++) {
			new_data[i][0] = String.valueOf(i + 1);
			if (_unit_box.getSelectedItem().equals(
					I18nService.getString("Labels", "hours"))) {
				new_data[i][1] = getFormattedDuration(Math.pow(factor, i));
			} else {
				new_data[i][1] = getFormattedDuration(Math.pow(factor, i) * 24);
			}
		}

		Object[] columns = { I18nService.getString("Labels", "batch"),
				I18nService.getString("Labels", "duration") };

		_table_model.setDataVector(new_data, columns);
	}

	private String getFormattedDuration(double hours) {
		ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
				"Labels", "num_days"));
		int num_days = (int) hours / 24;
		String days_str = formatter.format(num_days);
		formatter.applyPattern(I18nService.getString("Labels", "num_hours"));
		int num_hours = (int) (hours - 24 * num_days);
		if (num_hours > 0) {
			return days_str + " " + formatter.format(num_hours);
		}
		return days_str;
	}
}
