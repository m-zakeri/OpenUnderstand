package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;

import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.TableColumnModel;
import javax.swing.table.TableModel;

import org.apache.log4j.Logger;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.RemoveEntriesAction;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.event.FilterListener;
import net.sourceforge.jvlt.event.SelectionListener;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.FilterListener.FilterEvent;
import net.sourceforge.jvlt.metadata.EntryMetaData;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.table.CustomFontCellRenderer;
import net.sourceforge.jvlt.ui.table.PercentCellRenderer;
import net.sourceforge.jvlt.ui.table.SortableTable;
import net.sourceforge.jvlt.ui.table.SortableTableModel;
import net.sourceforge.jvlt.ui.table.SortableTableModel.SortOrder;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.vocabulary.entrydialog.AddEntryDialog;
import net.sourceforge.jvlt.ui.vocabulary.entrydialog.EditEntryDialog;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.Utils;

public class EntryPanel extends JPanel implements ActionListener,
		DictUpdateListener, ListSelectionListener, SelectionListener {
	private static final long serialVersionUID = 1L;

	private static final CustomFontCellRenderer ORIGINAL_RENDERER;
	private static final CustomFontCellRenderer PRONUNCIATION_RENDERER;
	private static final PercentCellRenderer MISTAKE_RATIO_RENDERER = new PercentCellRenderer();

	private static Logger logger = Logger.getLogger(ExamplePanel.class);

	static {
		Font font;
		ORIGINAL_RENDERER = new CustomFontCellRenderer();
		PRONUNCIATION_RENDERER = new CustomFontCellRenderer();
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_orth_font");
		if (font != null) {
			ORIGINAL_RENDERER.setCustomFont(font);
		}
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_pron_font");
		if (font != null) {
			PRONUNCIATION_RENDERER.setCustomFont(font);
		}
	}

	private final ArrayList<FilterListener<Entry>> _filter_listeners;
	private final JVLTModel _model;
	private Dict _dict;
	private final SelectionNotifier _notifier;

	private CustomAction _add_action;
	private CustomAction _edit_action;
	private CustomAction _edit_as_new_action;
	private CustomAction _remove_action;
	private SortableTable<Entry> _entry_table;
	private SortableTableModel<Entry> _entry_table_model;
	private EntryInfoPanel _entry_info_panel;
	private AddEntryDialog _add_entry_dialog;
	private EditEntryDialog _edit_entry_dialog;
	private EntryFilterPanel _filter_panel;
	private JPopupMenu _menu;

	public EntryPanel(JVLTModel model, SelectionNotifier notifier) {
		_filter_listeners = new ArrayList<FilterListener<Entry>>();
		_model = model;
		_notifier = notifier;
		_dict = _model.getDict();
		_model.getDictModel().addDictUpdateListener(this);
		_model.getQueryModel().addDictUpdateListener(this);
		notifier.addSelectionListener(this);
		init();
		updateActions();
	}

	public TableModel getTableModel() {
		return _entry_table.getModel();
	}

	public void saveState(UIConfig config) {
		String[] columns = _entry_table_model.getColumnNames();
		config.setProperty("entry_table_column_names", columns);

		Double[] col_widths = new Double[columns.length];
		TableColumnModel col_model = _entry_table.getColumnModel();
		for (int i = 0; i < columns.length; i++) {
			col_widths[i] = new Double(col_model.getColumn(i).getWidth());
		}

		config.setProperty("entry_table_column_widths", col_widths);

		SortableTableModel.Directive dir = _entry_table_model
				.getSortingDirective();
		config.setProperty("entry_table_sorting", Utils
				.arrayToString(new Integer[] { dir.getColumn(),
						dir.getDirection().toInt() }));

		// Save filter panel's state
		_filter_panel.saveState();
	}

	public void loadState(UIConfig config) {
		String[] col_names = config.getStringListProperty(
				"entry_table_column_names", new String[] { "Orthography",
						"Pronunciations", "Senses" });
		_entry_table_model.setColumnNames(col_names);

		SortableTableModel.Directive dir = new SortableTableModel.Directive();
		String[] dir_string = config.getStringListProperty(
				"entry_table_sorting", new String[] {
						String.valueOf(dir.getColumn()),
						String.valueOf(dir.getDirection().toInt()) });
		if (dir_string.length == 2) {
			try {
				int col = Integer.parseInt(dir_string[0]);
				int direction = Integer.parseInt(dir_string[1]);
				dir.setColumn(col);
				dir.setDirection(SortOrder.valueOf(direction));
			} catch (NumberFormatException e) {
				logger.warn("Could not read sorting info for example table", e);
			}
		}
		_entry_table_model.setSortingDirective(dir);

		/*
		 * Load column widths. This must be done after setting the sorting
		 * directive, as otherwise the widths are reset.
		 */
		double[] col_widths = config.getNumberListProperty(
				"entry_table_column_widths", new double[] { 50, 50, 50 });
		if (col_widths.length != _entry_table_model.getColumnCount()) {
			return;
		}

		TableColumnModel col_model = _entry_table.getColumnModel();
		for (int i = 0; i < col_widths.length; i++) {
			col_model.getColumn(i).setPreferredWidth((int) col_widths[i]);
		}

		// Load filter panel's state
		_filter_panel.loadState();
	}

	public void objectSelected(SelectionEvent e) {
		Object obj = e.getElement();
		Entry entry = null;
		if (obj instanceof Sense) {
			Sense sense = (Sense) obj;
			entry = sense.getParent();
		} else if (obj instanceof Entry) {
			entry = (Entry) obj;
		} else {
			return;
		}

		if (!_entry_table_model.containsObject(entry)) {
			String filter = entry.getOrthography();
			_filter_panel.setFilterString(filter);
			_filter_panel.setMode(EntryFilterPanel.FilterMode.MODE_ORIGINAL);
			applyFilter();
		}
		_entry_table.setSelectedObject(entry);
	}

	public void actionPerformed(ActionEvent e) {
		if (e.getSource() == _filter_panel) {
			applyFilter();
		} else if (e.getActionCommand().equals("add")) {
			addEntry(null);
		} else if (e.getActionCommand().equals("edit")) {
			List<Entry> entries = _entry_table.getSelectedObjects();
			if (entries.size() > 0) {
				editEntries(entries);
			}
		} else if (e.getActionCommand().equals("edit_as_new")) {
			List<Entry> entries = _entry_table.getSelectedObjects();
			if (entries.size() == 1) {
				// Use selected entry as template for new entry
				Entry entry = entries.get(0).createDeepCopy();
				entry.setID(_dict.getNextUnusedEntryID());
				addEntry(entry);
				_add_entry_dialog.init(entry);
			}
		} else if (e.getActionCommand().equals("remove")) {
			List<Entry> entries = _entry_table.getSelectedObjects();
			if (entries.size() > 0) {
				removeEntries(entries);
			}
		}
	}

	public synchronized void dictUpdated(DictUpdateEvent event) {
		if (event instanceof EntryDictUpdateEvent) {
			EntryDictUpdateEvent eevent = (EntryDictUpdateEvent) event;
			if (event.getType() == EntryDictUpdateEvent.ENTRIES_ADDED) {
				Collection<Entry> entries = eevent.getEntries();
				Entry entry = null;
				for (Iterator<Entry> it = entries.iterator(); it.hasNext();) {
					entry = it.next();
					if (_filter_panel.getFilter().entryMatches(entry)) {
						_entry_table_model.addObject(entry);
					}
				}
				// Select the last added entry.
				if (entry != null && _entry_table_model.containsObject(entry)) {
					_entry_table.setSelectedObject(entry);
				}

				fireFilterEvent(new FilterEvent<Entry>(this, _entry_table_model
						.getObjects()));
			} else if (eevent.getType() == EntryDictUpdateEvent.ENTRIES_CHANGED) {
				Collection<Entry> entries = eevent.getEntries();
				if (entries.size() < 1) {
					return;
				}

				List<Entry> objs = _entry_table.getSelectedObjects();
				applyFilter();
				if (objs.size() > 0
						&& _entry_table_model.containsObject(objs.get(0))) {
					_entry_table.setSelectedObject(objs.get(0));
				}
			} else if (eevent.getType() == EntryDictUpdateEvent.ENTRIES_REMOVED) {
				Collection<Entry> entries = eevent.getEntries();
				for (Entry entry : entries) {
					_entry_table_model.removeObject(entry);
				}

				fireFilterEvent(new FilterEvent<Entry>(this, _entry_table_model
						.getObjects()));
			}
		} else if (event instanceof ExampleDictUpdateEvent) {
			updateEntryInfoPanel();
		} else if (event instanceof NewDictDictUpdateEvent
				|| event instanceof LanguageDictUpdateEvent) {
			if (event instanceof NewDictDictUpdateEvent) {
				_dict = ((NewDictDictUpdateEvent) event).getDict();
			}

			applyFilter();
			updateEntryInfoPanel();
		}
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting()) {
			updateEntryInfoPanel();
			updateActions();
		}
	}

	public void addFilterListener(FilterListener<Entry> fl) {
		_filter_listeners.add(fl);
	}

	public void removeFilterListener(FilterListener<Entry> fl) {
		_filter_listeners.remove(fl);
	}

	private void fireFilterEvent(FilterEvent<Entry> ev) {
		Iterator<FilterListener<Entry>> it = _filter_listeners.iterator();
		while (it.hasNext()) {
			it.next().filterApplied(ev);
		}
	}

	private void init() {
		_add_action = GUIUtils.createTextAction(this, "add");
		_edit_action = GUIUtils.createTextAction(this, "edit");
		_edit_as_new_action = GUIUtils.createTextAction(this, "edit_as_new");
		_remove_action = GUIUtils.createTextAction(this, "remove");

		_filter_panel = new EntryFilterPanel(_model);
		_filter_panel.addActionListener(this);

		MetaData data = _model.getDictModel().getMetaData(Entry.class);
		_entry_table_model = new SortableTableModel<Entry>(data);
		_entry_table_model.setFormatValue(
				EntryMetaData.UserFlagsAttribute.class, true);
		_entry_table = new SortableTable<Entry>(_entry_table_model);
		_entry_table.setShowTooltips(JVLT.getConfig().getBooleanProperty(
				"Table.showTooltips", true));
		_entry_table.setArrowDirectionReversed(JVLT.getConfig()
				.getBooleanProperty("entry_table_arrow_direction_reversed",
						false));

		_entry_table.addMouseListener(new MouseAdapter() {
			@Override
			public void mouseClicked(MouseEvent e) {
				EntryPanel.this.handleTableMouseEvent(e);
			}
		});
		JScrollPane entry_scrpane = new JScrollPane();
		entry_scrpane.getViewport().setView(_entry_table);
		_entry_table.getSelectionModel().addListSelectionListener(this);
		_entry_table.setCellRenderer("Original", ORIGINAL_RENDERER);
		_entry_table.setCellRenderer("Pronunciations", PRONUNCIATION_RENDERER);
		_entry_table.setCellRenderer("MistakeRatio", MISTAKE_RATIO_RENDERER);

		JPanel button_panel = new JPanel();
		button_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		button_panel.add(new JButton(_add_action), cc);
		cc.update(0, 1);
		button_panel.add(new JButton(_edit_action), cc);
		cc.update(0, 2);
		button_panel.add(new JButton(_edit_as_new_action), cc);
		cc.update(0, 3);
		button_panel.add(new JButton(_remove_action), cc);
		cc.update(0, 4, 0.0, 1.0);
		button_panel.add(Box.createVerticalGlue(), cc);

		JPanel entry_list_panel = new JPanel();
		entry_list_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0, 2, 1);
		entry_list_panel.add(_filter_panel, cc);
		cc.update(0, 1, 1.0, 1.0, 1, 1);
		entry_list_panel.add(entry_scrpane, cc);
		cc.update(1, 1, 0.0, 1.0);
		entry_list_panel.add(button_panel, cc);

		_entry_info_panel = new EntryInfoPanel(_model, _notifier);

		JSplitPane split_pane = new JSplitPane(JSplitPane.VERTICAL_SPLIT,
				entry_list_panel, _entry_info_panel);
		split_pane.setDividerLocation(0.7);
		entry_scrpane.setPreferredSize(new Dimension(600, 150));
		_entry_info_panel.setPreferredSize(new Dimension(600, 250));

		this.setLayout(new GridLayout());
		this.add(split_pane);

		// Initialize dialogs
		Frame frame = JOptionPane.getFrameForComponent(this);
		_add_entry_dialog = new AddEntryDialog(frame, I18nService.getString(
				"Labels", "add_entry"), _model);
		_edit_entry_dialog = new EditEntryDialog(frame, "", _model);

		// Initialize popup menu
		_menu = new JPopupMenu();
		_menu.add(_edit_action);
		_menu.add(_edit_as_new_action);
		_menu.add(_remove_action);
	}

	private void applyFilter() {
		Collection<Entry> entries = _dict.getEntries();
		List<Entry> el = _filter_panel.getFilter().getMatchingEntries(entries);
		_entry_table_model.setObjects(el);
		fireFilterEvent(new FilterEvent<Entry>(this, el));
	}

	private void updateActions() {
		boolean element_selected = (_entry_table.getSelectedObjects().size() != 0);

		_edit_action.setEnabled(element_selected);
		_edit_as_new_action
				.setEnabled(_entry_table.getSelectedObjects().size() == 1);
		_remove_action.setEnabled(element_selected);
	}

	private void updateEntryInfoPanel() {
		// Change displayed attributes
		Object[] displayedattrs = (Object[]) JVLT.getRuntimeProperties().get(
				"displayed_attributes");
		if (displayedattrs == null) {
			displayedattrs = _model.getDictModel().getMetaData(Entry.class)
					.getAttributeNames();
		}
		_entry_info_panel.setDisplayedEntryAttributes(Utils
				.objectArrayToStringArray(displayedattrs));
		MetaData example_data = _model.getDictModel()
				.getMetaData(Example.class);
		_entry_info_panel.setDisplayedExampleAttributes(example_data
				.getAttributeNames());

		List<Entry> objs = _entry_table.getSelectedObjects();
		if (objs.size() == 0) {
			return;
		}

		Entry entry = objs.get(0);
		_entry_info_panel.setEntry(entry);
		boolean play = JVLT.getConfig().getBooleanProperty(
				"play_audio_immediately", false);
		if (play) {
			try {
				MultimediaUtils.playAudioFiles(entry);
			} catch (IOException ex) {
				String msg = I18nService.getString("Messages", "loading_failed");
				MessageDialog.showDialog(this, MessageDialog.ERROR_MESSAGE,
						msg, ex.getMessage());
			}
		} // if (entry != null && play)
	}

	private void editEntries(List<Entry> entries) {
		String title = entries.size() == 1 ? I18nService.getString("Labels",
				"edit_entry") : I18nService.getString("Labels", "edit_entries");
		_edit_entry_dialog.loadState((UIConfig) JVLT.getConfig());
		_edit_entry_dialog.setTitle(title);
		_edit_entry_dialog.init(entries);
		GUIUtils.showDialog(JOptionPane.getFrameForComponent(this),
				_edit_entry_dialog);
		_edit_entry_dialog.saveState((UIConfig) JVLT.getConfig());
	}

	private void removeEntries(List<Entry> entries) {
		RemoveEntriesAction action = new RemoveEntriesAction(_dict, entries);
		int num_removed_examples = action.getRemovedExamples().size();
		int num_modified_examples = action.getModifiedExamples().size();

		int result;
		if (num_modified_examples + num_removed_examples > 0) {
			ChoiceFormatter formatter = new ChoiceFormatter();
			formatter.applyPattern(I18nService.getString("Labels", "words"));
			String s1 = formatter.format(entries.size());
			Integer n1 = num_modified_examples;
			Integer n2 = num_removed_examples;
			String msg = I18nService.getString("Messages",
					"confirm_entry_deletion", new Object[] { s1, n1, n2 });
			result = MessageDialog.showDialog(this,
					MessageDialog.WARNING_MESSAGE,
					MessageDialog.OK_CANCEL_OPTION, msg);
			if (result != MessageDialog.OK_OPTION) {
				return;
			}
		} else {
			result = MessageDialog.showDialog(this,
					MessageDialog.WARNING_MESSAGE,
					MessageDialog.OK_CANCEL_OPTION, I18nService.getString(
							"Messages", "remove_entry"));
		}

		if (result == MessageDialog.OK_OPTION) {
			action.setMessage(I18nService.getString("Actions", "remove_entries"));
			_model.getDictModel().executeAction(action);
		}
	}

	private void handleTableMouseEvent(MouseEvent e) {
		int index = _entry_table.rowAtPoint(e.getPoint());
		if (index < 0) {
			return;
		}

		if (e.getButton() == MouseEvent.BUTTON1) {
			if (e.getClickCount() != 2) {
				return;
			}

			Entry entry = _entry_table_model.getObjectAt(index);
			ArrayList<Entry> list = new ArrayList<Entry>();
			list.add(entry);
			editEntries(list);
		} else if (e.getButton() == MouseEvent.BUTTON3) {
			_menu.show(e.getComponent(), e.getX(), e.getY());
		}
	}

	private void addEntry(Entry template) {
		_add_entry_dialog.loadState((UIConfig) JVLT.getConfig());

		if (template != null) {
			_add_entry_dialog.init(template);
		} else {
			_add_entry_dialog.init();
		}

		GUIUtils.showDialog(JOptionPane.getFrameForComponent(this),
				_add_entry_dialog);

		_add_entry_dialog.saveState((UIConfig) JVLT.getConfig());
	}
}
