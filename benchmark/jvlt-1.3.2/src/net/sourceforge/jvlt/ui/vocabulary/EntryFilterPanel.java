package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JOptionPane;
import javax.swing.JPanel;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.query.EntryFilter;
import net.sourceforge.jvlt.query.ObjectArrayQueryItem;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.query.ObjectQueryItem;
import net.sourceforge.jvlt.query.SenseArrayQueryItem;
import net.sourceforge.jvlt.query.SimpleEntryFilter;
import net.sourceforge.jvlt.query.StringEntryFilter;
import net.sourceforge.jvlt.query.StringPairQueryItem;
import net.sourceforge.jvlt.query.StringQueryItem;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

public class EntryFilterPanel extends JPanel {
	enum FilterMode {
		MODE_MULTI("filter_all"), MODE_ORIGINAL("original"), MODE_PRONUNCIATION(
				"pronunciation"), MODE_TRANSLATION("translation"), MODE_DEFINITION(
				"definition"), MODE_CATEGORY("category"), MODE_CUSTOM_FIELD(
				"custom_field"), MODE_LESSON("lesson"), MODE_ADVANCED(
				"filter_advanced");

		private String _value;

		private FilterMode(String value) {
			_value = value;
		}

		@Override
		public String toString() {
			return I18nService.getString("Labels", _value);
		}
	}

	private static final long serialVersionUID = 1L;

	private static class BasicEntryFilter extends EntryFilter implements
			StringEntryFilter {
		private ObjectQueryItem _item = null;

		public BasicEntryFilter(ObjectQueryItem item) {
			_item = item;
			if (item instanceof StringQueryItem) {
				((StringQueryItem) item).setMatchCase(false);
			} else if (item instanceof ObjectArrayQueryItem) {
				((ObjectArrayQueryItem) item).setMatchCase(false);
			} else if (item instanceof SenseArrayQueryItem) {
				((SenseArrayQueryItem) item).setMatchCase(false);
			}

			_query = new ObjectQuery(Entry.class);
			_query.setType(ObjectQuery.MATCH_ONE);
			_query.addItem(item);
		}

		public String getFilterString() {
			return (String) _item.getValue();
		}

		public void setFilterString(String str) {
			_item.setValue(str);
		}
	}

	private static class CustomFieldFilter extends EntryFilter implements
			StringEntryFilter {
		private final StringPairQueryItem _key_item;
		private final StringPairQueryItem _value_item;

		public CustomFieldFilter() {
			_key_item = new StringPairQueryItem("CustomFields",
					StringPairQueryItem.KEY_CONTAINS, "");
			_key_item.setMatchCase(false);

			_value_item = new StringPairQueryItem("CustomFields",
					StringPairQueryItem.VALUE_CONTAINS, "");
			_value_item.setMatchCase(false);

			_query.setType(ObjectQuery.MATCH_ONE);
			_query.addItem(_key_item);
			_query.addItem(_value_item);
		}

		public String getFilterString() {
			return (String) _key_item.getValue();
		}

		public void setFilterString(String str) {
			_key_item.setValue(str);
			_value_item.setValue(str);
		}
	}

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			if (e.getSource() == _advanced_button) {
				if (_query_dialog.isVisible()) {
					_query_dialog.setVisible(false);
				} else {
					Frame f = JOptionPane
							.getFrameForComponent(EntryFilterPanel.this);
					GUIUtils.showDialog(f, _query_dialog);
				}
			} else if (e.getSource() == _filter_field) {
				setFilterString(_filter_field.getText());

				fireActionEvent(new ActionEvent(EntryFilterPanel.this, e
						.getID(), null));
			} else if (e.getSource() == _mode_box) {
				setMode((FilterMode) _mode_box.getSelectedItem());

				if (_mode != FilterMode.MODE_ADVANCED) {
					setFilterString(_filter_field.getText());
				}

				fireActionEvent(new ActionEvent(EntryFilterPanel.this, e
						.getID(), null));
			} else if (e.getActionCommand().equals("ok")) {
				if (_mode != FilterMode.MODE_ADVANCED) {
					setFilterString(_filter_field.getText());
				}

				fireActionEvent(new ActionEvent(EntryFilterPanel.this, e
						.getID(), null));
			} else if (e.getActionCommand().equals("cancel")) {
				if (_mode == FilterMode.MODE_ADVANCED) {
					ObjectQuery empty_query = new ObjectQuery();
					_query_dialog.setObjectQuery(empty_query);
					_filters.get(FilterMode.MODE_ADVANCED)
							.setQuery(empty_query);
					updateAdvancedFilterField();
				} else {
					setFilterString("");
				}

				fireActionEvent(new ActionEvent(EntryFilterPanel.this, e
						.getID(), null));
			}
		}
	}

	private class DialogHandler implements DialogListener {
		public void dialogStateChanged(DialogEvent e) {
			if (e.getSource() == _query_dialog) {
				if (e.getType() == AbstractDialog.APPLY_OPTION) {
					ObjectQuery oq = _query_dialog.getObjectQuery();
					_filters.get(FilterMode.MODE_ADVANCED).setQuery(oq);
					updateAdvancedFilterField();
					fireActionEvent(new ActionEvent(EntryFilterPanel.this,
							ActionEvent.ACTION_PERFORMED, null));
				} else if (e.getType() == AbstractDialog.CLOSE_OPTION) {
					_query_dialog.setVisible(false);
				}
			}
		}
	}

	private FilterMode _mode;
	private final JVLTModel _model;
	private final Map<FilterMode, EntryFilter> _filters;
	private final Set<ActionListener> _listeners;
	private final ActionHandler _action_handler;

	private final CustomTextField _filter_field;
	private final EntryQueryDialog _query_dialog;
	private final JButton _advanced_button;
	private final JButton _ok_button;
	private final JButton _cancel_button;
	private final JComboBox _mode_box;

	public EntryFilterPanel(JVLTModel model) {
		_mode = FilterMode.MODE_MULTI;
		_model = model;
		_listeners = new HashSet<ActionListener>();

		//
		// Create entry filters
		//
		_filters = new HashMap<FilterMode, EntryFilter>();
		EntryFilter filter = new SimpleEntryFilter();
		((SimpleEntryFilter) filter).setMatchCase(false);
		_filters.put(FilterMode.MODE_MULTI, filter);
		_filters.put(FilterMode.MODE_ORIGINAL,
				new BasicEntryFilter(new StringQueryItem("Orthography",
						StringQueryItem.CONTAINS, "")));
		_filters.put(FilterMode.MODE_PRONUNCIATION, new BasicEntryFilter(
				new ObjectArrayQueryItem("Pronunciations",
						ObjectArrayQueryItem.ITEM_CONTAINS, "")));
		_filters.put(FilterMode.MODE_TRANSLATION, new BasicEntryFilter(
				new SenseArrayQueryItem(
						SenseArrayQueryItem.TRANSLATION_CONTAINS, "")));
		_filters.put(FilterMode.MODE_DEFINITION, new BasicEntryFilter(
				new SenseArrayQueryItem(
						SenseArrayQueryItem.DEFINITION_CONTAINS, "")));
		_filters.put(FilterMode.MODE_CATEGORY, new BasicEntryFilter(
				new ObjectArrayQueryItem("Categories",
						ObjectArrayQueryItem.ITEM_CONTAINS, "")));
		_filters.put(FilterMode.MODE_CUSTOM_FIELD, new CustomFieldFilter());
		_filters.put(FilterMode.MODE_LESSON, new BasicEntryFilter(
				new StringQueryItem("Lesson", StringQueryItem.CONTAINS, "")));
		_filters.put(FilterMode.MODE_ADVANCED, new EntryFilter());

		//
		// Create UI
		//
		_query_dialog = new EntryQueryDialog(JOptionPane
				.getFrameForComponent(this), I18nService.getString("Labels",
				"advanced_filter"), _model);
		_query_dialog.addDialogListener(new DialogHandler());

		_action_handler = new ActionHandler();

		_filter_field = new CustomTextField();
		_filter_field.setActionCommand("filter");
		_filter_field.addActionListener(_action_handler);

		_advanced_button = new JButton("...");
		_advanced_button.addActionListener(_action_handler);

		_ok_button = new JButton(GUIUtils.createIconAction(_action_handler,
				"ok"));

		_cancel_button = new JButton(GUIUtils.createIconAction(_action_handler,
				"cancel"));

		_mode_box = new JComboBox();
		_mode_box.addActionListener(_action_handler);
		_mode_box.setModel(new DefaultComboBoxModel(FilterMode.values()));

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		add(_filter_field.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_filter_field, cc);
		cc.update(2, 0, 0.0, 0.0);
		add(_cancel_button, cc);
		cc.update(3, 0, 0.0, 0.0);
		add(_ok_button, cc);
		cc.update(4, 0, 0.0, 0.0);
		add(_mode_box, cc);
	}

	public FilterMode getMode() {
		return _mode;
	}

	public void setMode(FilterMode mode) {
		if (mode == _mode) {
			return;
		}

		FilterMode oldmode = _mode;
		_mode = mode;

		CustomConstraints cc = new CustomConstraints();
		cc.update(3, 0, 0.0, 0.0);
		if (mode == FilterMode.MODE_ADVANCED) {
			// Update filter field text
			updateAdvancedFilterField();

			// Remove ok button, add button for advanced dialog
			remove(_ok_button);
			add(_advanced_button, cc);
			revalidate();
		} else {
			// Update filter field text
			_filter_field.setEnabled(true);
			if (oldmode == FilterMode.MODE_ADVANCED) {
				_filter_field.setText("");
			}

			// Remove button for advanced dialog, add ok button
			remove(_advanced_button);
			add(_ok_button, cc);
			revalidate();
		}

		// Update mode box
		FilterMode current_mode = (FilterMode) _mode_box.getSelectedItem();
		if (!current_mode.equals(mode)) {
			_mode_box.setSelectedItem(mode);
		}
	}

	public EntryFilter getFilter() {
		return _filters.get(_mode);
	}

	public String getFilterString() {
		EntryFilter filter = _filters.get(_mode);
		if (filter instanceof StringEntryFilter) {
			return ((StringEntryFilter) filter).getFilterString();
		}
		return null;
	}

	public void setFilterString(String str) {
		EntryFilter filter = _filters.get(_mode);
		if (filter instanceof StringEntryFilter) {
			((StringEntryFilter) filter).setFilterString(str);
		}

		_filter_field.setText(str);
	}

	public void addActionListener(ActionListener l) {
		_listeners.add(l);
	}

	public void loadState() {
		int selected = JVLT.getConfig().getIntProperty("filter_mode",
				FilterMode.MODE_MULTI.ordinal());

		// Set the mode that has been read from the configuration. The
		// action listener has to be removed temporarily to prevent an
		// action event from being emitted.
		_mode_box.removeActionListener(_action_handler);
		setMode(FilterMode.values()[selected]);
		_mode_box.addActionListener(_action_handler);
	}

	public void saveState() {
		JVLT.getConfig().setProperty("filter_mode", getMode().ordinal());
	}

	private void fireActionEvent(ActionEvent e) {
		for (ActionListener actionListener : _listeners) {
			actionListener.actionPerformed(new ActionEvent(this, e.getID(), e
					.getActionCommand()));
		}
	}

	private void updateAdvancedFilterField() {
		_filter_field.setEnabled(false);
		ObjectQuery oq = _filters.get(_mode).getQuery();
		if (oq.getName() == null || oq.getName().equals("")) {
			_filter_field.setText(I18nService
					.getString("Labels", "filter_unnamed"));
		} else {
			_filter_field.setText(oq.getName());
		}
	}
}
