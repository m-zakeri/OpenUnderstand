package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.util.ArrayList;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.ButtonGroup;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JRadioButton;
import javax.swing.SwingConstants;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.metadata.ChoiceAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.query.ChoiceObjectArrayQueryItem;
import net.sourceforge.jvlt.query.ChoiceQueryItem;
import net.sourceforge.jvlt.query.ContainerQueryItem;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.ui.components.ButtonPanel;
import net.sourceforge.jvlt.ui.components.ChoiceListPanel;
import net.sourceforge.jvlt.ui.components.CustomTabbedPane;
import net.sourceforge.jvlt.ui.components.StringChooserPanel;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.CustomDialogData;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.Utils;

/**
 * Dialog for selecting the words available during a quiz.
 */
public class EntrySelectionDialogData extends CustomDialogData implements
		ActionListener, DialogListener {
	public static class State {
		public static final int ALL_ENTRIES = 0;
		public static final int SOME_CATEGORIES = 1;
		public static final int SOME_ENTRIES = 2;
		public static final int MULTIPLE_FILTERS = 3;

		private int _type = ALL_ENTRIES;
		private String _language = "";
		private ObjectQuery _query = new ObjectQuery(Entry.class);
		private ObjectQuery[] _queries = new ObjectQuery[0];
		private String[] _allowed_lessons = new String[0];
		private String[] _allowed_categories = new String[0];
		private String[] _disallowed_lessons = new String[0];
		private String[] _disallowed_categories = new String[0];

		public State() {
			this(ALL_ENTRIES);
		}

		public State(int type) {
			_type = type;
		}

		public int getType() {
			return _type;
		}

		public String getLanguage() {
			return _language;
		}

		public ObjectQuery getQuery() {
			return _query;
		}

		public ObjectQuery[] getMultiQuery() {
			return _queries;
		}

		public String[] getAllowedLessons() {
			return _allowed_lessons;
		}

		public String[] getAllowedCategories() {
			return _allowed_categories;
		}

		public String[] getDisallowedLessons() {
			return _disallowed_lessons;
		}

		public String[] getDisallowedCategories() {
			return _disallowed_categories;
		}

		public void setType(int type) {
			_type = type;
		}

		public void setLanguage(String l) {
			_language = l;
		}

		public void setQuery(ObjectQuery query) {
			_query = query;
		}

		public void setMultiQuery(ObjectQuery[] queries) {
			_queries = queries;
		}

		public void setAllowedLessons(String[] lessons) {
			_allowed_lessons = lessons;
		}

		public void setAllowedCategories(String[] categories) {
			_allowed_categories = categories;
		}

		public void setDisallowedLessons(String[] lessons) {
			_disallowed_lessons = lessons;
		}

		public void setDisallowedCategories(String[] categories) {
			_disallowed_categories = categories;
		}
	}

	private class PropertyChangeHandler implements PropertyChangeListener {
		public void propertyChange(PropertyChangeEvent ev) {
			if (ev.getPropertyName().equals("filters")) {
				setFilters((ObjectQuery[]) ev.getNewValue());
			}
		}
	}

	private Action _manage_filters_action;
	private JButton _filter_button;
	private JRadioButton _all_entries_button;
	private JRadioButton _some_entries_button;
	private JRadioButton _some_categories_button;
	private JRadioButton _multiple_filters_button;
	private ChoiceListPanel _contained_lessons_panel;
	private ChoiceListPanel _contained_categories_panel;
	private ChoiceListPanel _not_contained_lessons_panel;
	private ChoiceListPanel _not_contained_categories_panel;
	private SimpleEntryQueryDialog _query_dlg;
	private StringChooserPanel _filter_chooser_panel;

	private final JVLTModel _model;

	public EntrySelectionDialogData(JVLTModel model) {
		_model = model;
		_model.getDictModel().addDictUpdateListener(new DictUpdateListener() {
			public synchronized void dictUpdated(DictUpdateEvent ev) {
				updateComponents();
			}
		});

		init();
		JVLT.getRuntimeProperties().addPropertyChangeListener(
				new PropertyChangeHandler());
	}

	public ObjectQuery[] getObjectQueries() {
		ObjectQuery query = new ObjectQuery(Entry.class);
		if (_all_entries_button.isSelected()) {
			return new ObjectQuery[] { query };
		} else if (_some_categories_button.isSelected()) {
			Object[] categories = _contained_categories_panel
					.getSelectedObjects();
			if (categories.length > 0) {
				query.addItem(new ChoiceObjectArrayQueryItem("Categories",
						ChoiceObjectArrayQueryItem.CONTAINS_ONE_ITEM, Utils
								.objectArrayToStringArray(categories)));
			}
			categories = _not_contained_categories_panel.getSelectedObjects();
			if (categories.length > 0) {
				query.addItem(new ChoiceObjectArrayQueryItem("Categories",
						ChoiceObjectArrayQueryItem.DOES_NOT_CONTAIN_ANY_ITEM,
						Utils.objectArrayToStringArray(categories)));
			}

			Object[] lessons = _contained_lessons_panel.getSelectedObjects();
			if (lessons.length > 0) {
				ContainerQueryItem cqi = new ContainerQueryItem("Lesson",
						ContainerQueryItem.MATCH_ONE);
				for (Object lesson : lessons) {
					cqi.addItem(new ChoiceQueryItem("Lesson",
							ChoiceQueryItem.EQUALS, lesson));
				}
				query.addItem(cqi);
			}
			lessons = _not_contained_lessons_panel.getSelectedObjects();
			if (lessons.length > 0) {
				ContainerQueryItem cqi = new ContainerQueryItem("Lesson",
						ContainerQueryItem.MATCH_ALL);
				for (Object lesson : lessons) {
					cqi.addItem(new ChoiceQueryItem("Lesson",
							ChoiceQueryItem.NOT_EQUAL, lesson));
				}
				query.addItem(cqi);
			}

			return new ObjectQuery[] { query };
		} else if (_some_entries_button.isSelected()) {
			return new ObjectQuery[] { _query_dlg.getObjectQuery() };
		} else { // if (_multiple_filters_button.isSelected())
			ObjectQuery[] oqs = (ObjectQuery[]) JVLT.getRuntimeProperties()
					.get("filters");
			if (oqs == null) {
				return new ObjectQuery[0];
			}

			ArrayList<ObjectQuery> filters = new ArrayList<ObjectQuery>();
			for (ObjectQuery oq : oqs) {
				if (_filter_chooser_panel.isStringSelected(oq.getName())) {
					filters.add(oq);
				}
			}

			return filters.toArray(new ObjectQuery[0]);
		}
	}

	public State getState() {
		int type = State.ALL_ENTRIES;
		if (_some_categories_button.isSelected()) {
			type = State.SOME_CATEGORIES;
		} else if (_some_entries_button.isSelected()) {
			type = State.SOME_ENTRIES;
		} else if (_multiple_filters_button.isSelected()) {
			type = State.MULTIPLE_FILTERS;
		}

		State state = new State(type);
		state.setLanguage(_model.getDict().getLanguage());
		state.setQuery(_query_dlg.getObjectQuery());
		state.setMultiQuery(getObjectQueries());
		state.setAllowedCategories(Utils
				.objectArrayToStringArray(_contained_categories_panel
						.getSelectedObjects()));
		state.setDisallowedCategories(Utils
				.objectArrayToStringArray(_not_contained_categories_panel
						.getSelectedObjects()));
		state.setAllowedLessons(Utils
				.objectArrayToStringArray(_contained_lessons_panel
						.getSelectedObjects()));
		state.setDisallowedLessons(Utils
				.objectArrayToStringArray(_not_contained_lessons_panel
						.getSelectedObjects()));
		return state;
	}

	public void initFromState(State state) {
		if (state == null) {
			return;
		}

		int type = state.getType();
		if (type == State.ALL_ENTRIES) {
			_all_entries_button.setSelected(true);
		} else if (type == State.SOME_CATEGORIES) {
			_some_categories_button.setSelected(true);
		} else if (type == State.SOME_ENTRIES) {
			_some_entries_button.setSelected(true);
		} else {
			// if (type == State.MULTIPLE_FILTERS)
			_multiple_filters_button.setSelected(true);
		}

		_contained_lessons_panel.setSelectedObjects(state.getAllowedLessons());
		_contained_categories_panel.setSelectedObjects(state
				.getAllowedCategories());
		_not_contained_lessons_panel.setSelectedObjects(state
				.getDisallowedLessons());
		_not_contained_categories_panel.setSelectedObjects(state
				.getDisallowedCategories());
		_query_dlg.setObjectQuery(state.getQuery());
		ObjectQuery[] oqs = state.getMultiQuery();
		String[] filter_names = new String[oqs.length];
		for (int i = 0; i < oqs.length; i++) {
			filter_names[i] = oqs[i].getName();
		}
		_filter_chooser_panel.setSelectedStrings(filter_names);

		updateComponents();
	}

	@Override
	public void updateData() {
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("filter")
				|| ev.getActionCommand().equals("manage_filters")) {
			GUIUtils.showDialog(_content_pane, _query_dlg);
		} else {
			updateComponents();
		}
	}

	public void dialogStateChanged(DialogEvent ev) {
		if (ev.getSource() == _query_dlg) {
			_query_dlg.setVisible(false);
		}
	}

	private void init() {
		Action all_entries_action = GUIUtils.createTextAction(this,
				"all_entries");
		Action some_entries_action = GUIUtils.createTextAction(this,
				"some_entries");
		Action multiple_filters_action = GUIUtils.createTextAction(this,
				"multiple_filters");
		Action some_categories_action = GUIUtils.createTextAction(this,
				"some_categories");
		Action filter_action = GUIUtils.createTextAction(this, "filter");
		_manage_filters_action = GUIUtils.createTextAction(this,
				"manage_filters");

		_all_entries_button = new JRadioButton(all_entries_action);
		_all_entries_button.setSelected(true);
		_some_entries_button = new JRadioButton(some_entries_action);
		_multiple_filters_button = new JRadioButton(multiple_filters_action);
		_some_categories_button = new JRadioButton(some_categories_action);
		ButtonGroup bg = new ButtonGroup();
		bg.add(_all_entries_button);
		bg.add(_some_entries_button);
		bg.add(_multiple_filters_button);
		bg.add(_some_categories_button);

		_filter_button = new JButton(filter_action);
		JPanel filter_panel = new JPanel();
		filter_panel.add(_filter_button, BorderLayout.CENTER);

		_contained_lessons_panel = new ChoiceListPanel();
		_contained_lessons_panel.setAllowCustomChoices(false);
		_contained_categories_panel = new ChoiceListPanel();
		_contained_categories_panel.setAllowCustomChoices(false);
		_not_contained_lessons_panel = new ChoiceListPanel();
		_not_contained_lessons_panel.setAllowCustomChoices(false);
		_not_contained_categories_panel = new ChoiceListPanel();
		_not_contained_categories_panel.setAllowCustomChoices(false);
		CustomTabbedPane categories_tab = new CustomTabbedPane();
		categories_tab.add("allowed_lessons", _contained_lessons_panel);
		categories_tab.add("allowed_categories", _contained_categories_panel);
		categories_tab.add("not_allowed_lessons", _not_contained_lessons_panel);
		categories_tab.add("not_allowed_categories",
				_not_contained_categories_panel);

		_filter_chooser_panel = new StringChooserPanel();
		ButtonPanel button_panel = new ButtonPanel(SwingConstants.VERTICAL,
				SwingConstants.TOP);
		button_panel.addButton(new JButton(_manage_filters_action));
		JPanel filter_chooser_panel = new JPanel();
		filter_chooser_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		filter_chooser_panel.add(_filter_chooser_panel, cc);
		cc.update(1, 0, 0.0, 1.0);
		filter_chooser_panel.add(button_panel, cc);

		// Filler item that ensures that the dialog has a minimum width of 400
		Box.Filler filler = new Box.Filler(new Dimension(400, 0),
				new Dimension(400, 0), new Dimension(400, 0));

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		_content_pane.add(_all_entries_button, cc);
		cc.update(0, 1, 1.0, 0.0);
		_content_pane.add(_some_entries_button, cc);
		cc.update(0, 2, 1.0, 0.0);
		_content_pane.add(filter_panel, cc);
		cc.update(0, 3, 1.0, 0.0);
		_content_pane.add(_multiple_filters_button, cc);
		cc.update(0, 4, 1.0, 1.0);
		_content_pane.add(filter_chooser_panel, cc);
		cc.update(0, 5, 1.0, 0.0);
		_content_pane.add(_some_categories_button, cc);
		cc.update(0, 6, 1.0, 1.0);
		_content_pane.add(categories_tab, cc);
		cc.update(0, 7, 1.0, 0.0);
		_content_pane.add(filler, cc);

		// Initialize dialog
		_query_dlg = new SimpleEntryQueryDialog(JOptionPane
				.getFrameForComponent(_content_pane), I18nService.getString(
				"Labels", "advanced_filter"), _model);
		_query_dlg.addDialogListener(this);

		setFilters((ObjectQuery[]) JVLT.getRuntimeProperties().get("filters"));
	}

	private void updateComponents() {
		boolean some_lessons_categories = _some_categories_button.isSelected();

		MetaData data = _model.getDictModel().getMetaData(Entry.class);
		ChoiceAttribute attr = (ChoiceAttribute) data
				.getAttribute("Categories");
		_contained_categories_panel.setAvailableObjects(attr.getValues());
		_contained_categories_panel.setEnabled(some_lessons_categories);
		_not_contained_categories_panel.setAvailableObjects(attr.getValues());
		_not_contained_categories_panel.setEnabled(some_lessons_categories);

		attr = (ChoiceAttribute) data.getAttribute("Lesson");
		_contained_lessons_panel.setAvailableObjects(attr.getValues());
		_contained_lessons_panel.setEnabled(some_lessons_categories);
		_not_contained_lessons_panel.setAvailableObjects(attr.getValues());
		_not_contained_lessons_panel.setEnabled(some_lessons_categories);

		_filter_button.setEnabled(_some_entries_button.isSelected());
		_filter_chooser_panel.setEnabled(_multiple_filters_button.isSelected());
		_manage_filters_action
				.setEnabled(_multiple_filters_button.isSelected());
	}

	private void setFilters(ObjectQuery[] oqs) {
		String[] names;
		if (oqs == null) {
			names = new String[0];
		} else {
			names = new String[oqs.length];
			for (int i = 0; i < oqs.length; i++) {
				names[i] = oqs[i].getName();
			}
		}

		_filter_chooser_panel.setStrings(names);
	}
}

class SimpleEntryQueryDialog extends EntryQueryDialog {
	private static final long serialVersionUID = 1L;

	public SimpleEntryQueryDialog(Frame owner, String title, JVLTModel _model) {
		super(owner, title, true, _model);
		setButtons(new int[] { AbstractDialog.CLOSE_OPTION });
	}
}
