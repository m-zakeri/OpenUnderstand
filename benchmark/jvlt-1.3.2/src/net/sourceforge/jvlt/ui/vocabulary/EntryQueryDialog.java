package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.GregorianCalendar;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.TreeSet;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.ButtonGroup;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JDialog;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JRadioButton;
import javax.swing.JScrollPane;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.border.EtchedBorder;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.EntryAttributeSchema;
import net.sourceforge.jvlt.core.EntryClass;
import net.sourceforge.jvlt.event.ComponentReplacementListener;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.event.ComponentReplacementListener.ComponentReplacementEvent;
import net.sourceforge.jvlt.metadata.ArrayAttribute;
import net.sourceforge.jvlt.metadata.ArrayChoiceAttribute;
import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.metadata.AttributeComparator;
import net.sourceforge.jvlt.metadata.BooleanAttribute;
import net.sourceforge.jvlt.metadata.CalendarAttribute;
import net.sourceforge.jvlt.metadata.ChoiceAttribute;
import net.sourceforge.jvlt.metadata.CustomArrayAttribute;
import net.sourceforge.jvlt.metadata.CustomAttribute;
import net.sourceforge.jvlt.metadata.CustomChoiceAttribute;
import net.sourceforge.jvlt.metadata.DefaultAttribute;
import net.sourceforge.jvlt.metadata.DefaultChoiceAttribute;
import net.sourceforge.jvlt.metadata.EntryMetaData;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.metadata.NumberAttribute;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.query.BitmaskQueryItem;
import net.sourceforge.jvlt.query.BooleanQueryItem;
import net.sourceforge.jvlt.query.CalendarQueryItem;
import net.sourceforge.jvlt.query.ChoiceObjectArrayQueryItem;
import net.sourceforge.jvlt.query.ChoiceQueryItem;
import net.sourceforge.jvlt.query.EntryClassQueryItem;
import net.sourceforge.jvlt.query.NumberQueryItem;
import net.sourceforge.jvlt.query.ObjectArrayQueryItem;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.query.ObjectQueryItem;
import net.sourceforge.jvlt.query.SenseArrayQueryItem;
import net.sourceforge.jvlt.query.StringQueryItem;
import net.sourceforge.jvlt.ui.components.ButtonPanel;
import net.sourceforge.jvlt.ui.components.ChoiceInputComponent;
import net.sourceforge.jvlt.ui.components.ChoiceListPanel;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.DateChooserButton;
import net.sourceforge.jvlt.ui.components.InputComponent;
import net.sourceforge.jvlt.ui.components.ObjectMapEditorPanel;
import net.sourceforge.jvlt.ui.components.StringInputComponent;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.ItemContainer;
import net.sourceforge.jvlt.utils.Utils;

public class EntryQueryDialog extends AbstractDialog {
	private class ComponentReplacementHandler implements
			ComponentReplacementListener {
		public void componentReplaced(ComponentReplacementEvent e) {
			JComponent o = e.getOldComponent();
			JComponent n = e.getNewComponent();
			int i = 0;
			for (Iterator<EntryQueryRow> it = _query_rows.iterator(); it
					.hasNext(); i++) {
				EntryQueryRow row = it.next();
				if (row.getValueField() == n) {
					_query_panel.remove(o);
					CustomConstraints cc = new CustomConstraints();
					cc.update(2, i, 1.0, 0.0);
					_query_panel.add(n, cc);
					_query_panel.revalidate();
					_query_panel.repaint(_query_panel.getVisibleRect());
					break;
				}
			}
		}
	}

	private class PropertyChangeHandler implements PropertyChangeListener {
		public void propertyChange(PropertyChangeEvent ev) {
			if (ev.getPropertyName().equals("filters")) {
				loadFilters();
			}
		}
	}

	private class FilterMapEditorPanel extends
			ObjectMapEditorPanel<ObjectQuery> {
		private static final long serialVersionUID = 1L;

		@Override
		protected ObjectQuery getCurrentObject() {
			return EntryQueryDialog.this.getObjectQuery();
		}

		@Override
		protected void removeSelectedItem() {
			super.removeSelectedItem();
			EntryQueryDialog.this.clear();
		}

		@Override
		protected void selectionChanged() {
			Object item = getSelectedItem();
			if (_item_map.containsKey(item)) {
				EntryQueryDialog.this.setObjectQuery(_item_map.get(item));
			}
		}
	}

	private class DictUpdateHandler implements DictUpdateListener {
		public void dictUpdated(DictUpdateEvent event) {
			if (event instanceof NewDictDictUpdateEvent
					|| event instanceof LanguageDictUpdateEvent) {
				for (EntryQueryRow row : _query_rows) {
					row.reset();
				}
			}
		}
	}

	private static final long serialVersionUID = 1L;

	private final JVLTModel _model;
	private final LinkedList<EntryQueryRow> _query_rows;

	private FilterMapEditorPanel _filter_map_panel;
	private JPanel _query_panel;
	private JRadioButton _match_all_button;
	private JRadioButton _match_one_button;

	public EntryQueryDialog(Frame owner, String title, JVLTModel model) {
		this(owner, title, false, model);
	}

	public EntryQueryDialog(Frame owner, String title, boolean modal,
			JVLTModel model) {
		super(owner, title, modal);
		_model = model;
		_query_rows = new LinkedList<EntryQueryRow>();

		_model.getDictModel().addDictUpdateListener(new DictUpdateHandler());
		init();
	}

	public ObjectQuery getObjectQuery() {
		ObjectQuery oq = new ObjectQuery(Entry.class);
		Object selected = _filter_map_panel.getSelectedItem();
		if (selected != null) {
			oq.setName(selected.toString());
		}
		if (_match_all_button.isSelected()) {
			oq.setType(ObjectQuery.MATCH_ALL);
		} else if (_match_one_button.isSelected()) {
			oq.setType(ObjectQuery.MATCH_ONE);
		}

		Iterator<EntryQueryRow> it = _query_rows.iterator();
		while (it.hasNext()) {
			oq.addItem(it.next().getQueryItem());
		}

		return oq;
	}

	public void setObjectQuery(ObjectQuery query) {
		if (query.getType() == ObjectQuery.MATCH_ALL) {
			_match_all_button.setSelected(true);
		} else {
			_match_one_button.setSelected(true);
		}

		Iterator<EntryQueryRow> it = _query_rows.iterator();
		while (it.hasNext()) {
			EntryQueryRow row = it.next();
			_query_panel.remove(row.getNameBox());
			_query_panel.remove(row.getTypeBox());
			_query_panel.remove(row.getValueField());
		}
		_query_rows.clear();

		ObjectQueryItem[] items = query.getItems();
		for (ObjectQueryItem item : items) {
			EntryQueryRow row = new EntryQueryRow(_model);
			row.setQueryItem(item);
			addRow(row);
		}
		_query_panel.revalidate();
		_query_panel.repaint(_query_panel.getVisibleRect());

		// Update filter map panel
		_filter_map_panel.setSelectedItem(query.getName());
	}

	@Override
	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("more")) {
			addRow();
		} else if (ev.getActionCommand().equals("less")) {
			removeRow();
		} else if (ev.getActionCommand().equals("reset")) {
			clear();
		} else { // Either "Close" or "Apply" button has been pressed
			saveFilters();
			super.actionPerformed(ev);
		}
	}

	private void init() {
		Action more_action = GUIUtils.createTextAction(this, "more");
		Action less_action = GUIUtils.createTextAction(this, "less");
		Action reset_action = GUIUtils.createTextAction(this, "reset");

		_filter_map_panel = new FilterMapEditorPanel();

		JPanel type_panel = new JPanel();
		type_panel.setLayout(new GridLayout(2, 1, 5, 5));
		ButtonGroup bg = new ButtonGroup();
		_match_all_button = new JRadioButton(I18nService.getString("Labels",
				"match_all"));
		type_panel.add(_match_all_button);
		bg.add(_match_all_button);
		_match_one_button = new JRadioButton(I18nService.getString("Labels",
				"match_one"));
		type_panel.add(_match_one_button);
		bg.add(_match_one_button);
		_match_all_button.setSelected(true);

		_query_panel = new JPanel();
		_query_panel.setLayout(new GridBagLayout());
		JPanel query_panel = new JPanel();
		query_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		query_panel.add(_query_panel, cc);
		cc.update(0, 1, 1.0, 1.0);
		query_panel.add(Box.createVerticalGlue(), cc);
		JScrollPane query_scrpane = new JScrollPane(query_panel);
		query_scrpane.setPreferredSize(new Dimension(400, 100));

		JPanel more_less_panel = new JPanel();
		more_less_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		more_less_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		more_less_panel.add(new JButton(more_action), cc);
		cc.update(2, 0, 0.0, 0.0);
		more_less_panel.add(new JButton(less_action), cc);
		cc.update(3, 0, 0.0, 0.0);
		more_less_panel.add(new JButton(reset_action), cc);

		JPanel main_panel = new JPanel();
		main_panel.setBorder(new EtchedBorder(EtchedBorder.LOWERED));
		main_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		main_panel.add(_filter_map_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		main_panel.add(type_panel, cc);
		cc.update(0, 2, 1.0, 1.0);
		main_panel.add(query_scrpane, cc);
		cc.update(0, 3, 1.0, 0.0);
		main_panel.add(more_less_panel, cc);

		setContent(main_panel);
		setButtons(new int[] { AbstractDialog.APPLY_OPTION,
				AbstractDialog.CLOSE_OPTION });
		loadFilters();
		JVLT.getRuntimeProperties().addPropertyChangeListener(
				new PropertyChangeHandler());

		// Start with a query that has one row.
		clear();
	}

	private void clear() {
		setObjectQuery(new ObjectQuery(Entry.class));
		addRow();
	}

	private void loadFilters() {
		ObjectQuery[] oqs = (ObjectQuery[]) JVLT.getRuntimeProperties().get(
				"filters");
		HashMap<Object, ObjectQuery> map = new HashMap<Object, ObjectQuery>();
		if (oqs != null) {
			for (ObjectQuery oq : oqs) {
				map.put(oq.getName(), oq);
			}
		}

		_filter_map_panel.setItems(map);
	}

	private void saveFilters() {
		JVLT.getRuntimeProperties().put(
				"filters",
				_filter_map_panel.getItems().values().toArray(
						new ObjectQuery[0]));
	}

	/** Add a single row. Do not repaint afterwards. */
	private void addRow(EntryQueryRow row) {
		row.addComponentReplacementListener(new ComponentReplacementHandler());
		_query_rows.addLast(row);
		int numrows = _query_rows.size();
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, numrows - 1, 1.0, 0.0);
		_query_panel.add(row.getNameBox(), cc);
		cc.update(1, numrows - 1, 1.0, 0.0);
		_query_panel.add(row.getTypeBox(), cc);
		cc.update(2, numrows - 1, 1.0, 0.0);
		_query_panel.add(row.getValueField(), cc);
	}

	private void addRow() {
		EntryQueryRow row = new EntryQueryRow(_model);
		addRow(row);
		_query_panel.revalidate();
		_query_panel.repaint(_query_panel.getVisibleRect());
	}

	private void removeRow() {
		if (_query_rows.size() == 0) {
			return;
		}

		EntryQueryRow row = _query_rows.getLast();
		_query_rows.removeLast();
		_query_panel.remove(row.getNameBox());
		_query_panel.remove(row.getTypeBox());
		_query_panel.remove(row.getValueField());
		_query_panel.revalidate();
		_query_panel.repaint(_query_panel.getVisibleRect());
	}
}

class EntryQueryRow implements ActionListener {
	private final ItemContainer _container;
	private final JVLTModel _model;
	private final ArrayList<ComponentReplacementListener> _listeners;
	private final HashMap<Class<? extends Attribute>, ObjectQueryItem> _query_items;
	private final HashMap<String, Integer> _translation_type_map;
	private final HashMap<Integer, String> _type_translation_map;
	private final MetaData _data;
	private InputComponent _input_component;
	private JComboBox _name_box = null;
	private JComboBox _type_box = null;

	public EntryQueryRow(JVLTModel model) {
		_container = new ItemContainer();
		_container.setTranslateItems(true);
		_model = model;
		_listeners = new ArrayList<ComponentReplacementListener>();
		_translation_type_map = new HashMap<String, Integer>();
		_type_translation_map = new HashMap<Integer, String>();
		_query_items = new HashMap<Class<? extends Attribute>, ObjectQueryItem>();
		_query_items.put(DefaultChoiceAttribute.class, new ChoiceQueryItem());
		_query_items.put(ArrayAttribute.class, new ObjectArrayQueryItem());
		_query_items.put(ArrayChoiceAttribute.class,
				new ChoiceObjectArrayQueryItem());
		_query_items.put(CalendarAttribute.class, new CalendarQueryItem());
		_query_items.put(NumberAttribute.class, new NumberQueryItem());
		_query_items.put(BooleanAttribute.class, new BooleanQueryItem());
		_query_items.put(DefaultAttribute.class, new StringQueryItem());
		_query_items.put(CustomAttribute.class, new StringQueryItem());
		_query_items.put(CustomChoiceAttribute.class, new ChoiceQueryItem());
		_query_items
				.put(CustomArrayAttribute.class, new ObjectArrayQueryItem());
		_query_items.put(EntryMetaData.SensesAttribute.class,
				new SenseArrayQueryItem());
		_query_items.put(EntryMetaData.EntryClassAttribute.class,
				new EntryClassQueryItem());
		_query_items.put(EntryMetaData.UserFlagsAttribute.class,
				new BitmaskQueryItem());
		_data = _model.getDictModel().getMetaData(Entry.class);

		_name_box = new JComboBox();
		_name_box.addActionListener(this);
		_type_box = new JComboBox();
		_type_box.addActionListener(this);
		_input_component = null;

		updateAttributeBox();
		setAttribute(_data.getAttributes()[0]);
	}

	public void addComponentReplacementListener(ComponentReplacementListener l) {
		_listeners.add(l);
	}

	public JComboBox getNameBox() {
		return _name_box;
	}

	public JComboBox getTypeBox() {
		return _type_box;
	}

	public JComponent getValueField() {
		return _input_component.getComponent();
	}

	public ObjectQueryItem getQueryItem() {
		Attribute attr = (Attribute) _container.getItem(_name_box
				.getSelectedItem());
		ObjectQueryItem item = _query_items.get(attr.getClass());
		item.setName(attr.getName());
		Object type_obj = _type_box.getSelectedItem().toString();
		int type = _translation_type_map.get(type_obj).intValue();
		item.setType(type);
		Object value = _input_component.getInput();
		item.setValue(value);

		return item;
	}

	public void setQueryItem(ObjectQueryItem item) {
		String name = item.getName();
		setAttribute(_data.getAttribute(name));
		Integer type = item.getType();
		if (_type_translation_map.containsKey(type)) {
			_type_box.setSelectedItem(_type_translation_map.get(type));
		}

		_input_component.setInput(item.getValue());
	}

	public void actionPerformed(ActionEvent ev) {
		Object selected = _name_box.getSelectedItem();
		Integer type = _translation_type_map.get(_type_box.getSelectedItem());
		if (ev.getSource() == _name_box) {
			if (selected != null) {
				setAttribute((Attribute) _container.getItem(selected));
			}
		} else if (ev.getSource() == _type_box) {
			if (selected != null && type != null) {
				setType((Attribute) _container.getItem(selected), type
						.intValue());
			}
		}
	}

	public void reset() {
		updateAttributeBox();
	}

	private void updateAttributeBox() {
		/*
		 * Remove action listener. Otherwise ActionEvents are generated while
		 * updating the name combo box which results in NullPointerExceptions.
		 */
		_name_box.removeActionListener(this);

		/*
		 * Save attribute in order to restore it after the name box has been
		 * updated
		 */
		Attribute attr = (Attribute) _container.getItem(_name_box
				.getSelectedItem());

		_name_box.removeAllItems();
		Attribute[] attrs = _data.getAttributes();
		boolean found = false;
		if (attrs != null && attrs.length > 0) {
			_container.setItems(attrs);
			TreeSet<Object> set = new TreeSet<Object>(new AttributeComparator(
					_container));
			set.addAll(Arrays.asList(attrs));
			for (Object object : set) {
				_name_box.addItem(_container.getTranslation(object));
			}

			/*
			 * If the name box does not contain the original name, use the
			 * default name (the first one in the array). Otherwise, restore the
			 * original name.
			 */
			if (attr != null) {
				for (Attribute attr2 : attrs) {
					if (attr2.getName().equals(attr.getName())) {
						found = true;
						break;
					}
				}
			}

			if (found) {
				_name_box.setSelectedItem(_container.getTranslation(attr));
			}
		}

		_name_box.addActionListener(this);

		if (!found) {
			/*
			 * - Do not call _name_box.setSelectedItem() as the other values in
			 * the row probably also have to be updated. - Call setAttribute()
			 * after the action listener has been added so the action listener
			 * will not be added twice
			 */
			setAttribute(attrs[0]);
		}
	}

	private void setAttribute(Attribute attr) {
		/*
		 * Remove action listeners from combo boxes so actionPerformed() will
		 * not called during the update
		 */
		_name_box.removeActionListener(this);
		_type_box.removeActionListener(this);

		_name_box.setSelectedItem(_container.getTranslation(attr));

		ObjectQueryItem item = _query_items.get(attr.getClass());
		String[] types = item.getTypeNames();
		_type_box.removeAllItems();
		_translation_type_map.clear();
		_type_translation_map.clear();
		for (String type : types) {
			String translation = I18nService.getString("Labels", type);
			_type_box.addItem(translation);
			try {
				Field field = item.getClass().getField(type);
				int type_value = field.getInt(item);
				_translation_type_map.put(translation, type_value);
				_type_translation_map.put(type_value, translation);
			} catch (Exception ex) {
				ex.printStackTrace();
			}
		}

		/* Re-add action listeners */
		_name_box.addActionListener(this);
		_type_box.addActionListener(this);

		setType(attr, item.getTypes()[0]);
	}

	private void setType(Attribute attr, int type) {
		/*
		 * Update the type combo box. Remove action listener before updating in
		 * order to prevent actionPerformed() from being called.
		 */
		_type_box.removeActionListener(this);
		_type_box.setSelectedItem(_type_translation_map.get(type));
		_type_box.addActionListener(this);

		JComponent old_component = null;
		if (_input_component != null) {
			old_component = _input_component.getComponent();
		}

		ObjectQueryItem item = _query_items.get(attr.getClass());
		if (item instanceof ChoiceQueryItem) {
			if (type == ChoiceQueryItem.CONTAINS) {
				_input_component = new StringInputComponent();
			} else if (type == ChoiceQueryItem.EMPTY
					|| type == ChoiceQueryItem.NOT_EMPTY) {
				_input_component = new EmptyInputComponent();
			} else {
				ChoiceInputComponent cic = new ChoiceInputComponent();
				if (attr.getClass().equals(CustomChoiceAttribute.class)) {
					CustomChoiceAttribute cca = (CustomChoiceAttribute) attr;
					cic.setTranslateItems(true);

					Object[] values = cca.getValues();
					String[] strvals = new String[values.length];
					for (int i = 0; i < values.length; i++) {
						strvals[i] = values[i].toString();
					}

					cic.setChoices(strvals);
				} else if (attr.getClass().equals(DefaultChoiceAttribute.class)) {
					DefaultChoiceAttribute dca = (DefaultChoiceAttribute) attr;
					cic.setChoices(dca.getValues());
				}
				_input_component = cic;
			}
		} else if (item instanceof ObjectArrayQueryItem) {
			if (type == ObjectArrayQueryItem.EMPTY
					|| type == ObjectArrayQueryItem.CONTAINS_AT_LEAST_ONE_ITEM) {
				_input_component = new EmptyInputComponent();
			} else if (type == ObjectArrayQueryItem.ITEM_CONTAINS) {
				_input_component = new StringInputComponent();
			} else { // item is a ChoiceObjectArrayQueryItem
				ChoiceListInputComponent clic = new ChoiceListInputComponent();
				_input_component = clic;
				if (attr instanceof ChoiceAttribute) {
					clic.setChoices(((ChoiceAttribute) attr).getValues());
				}
				if (attr instanceof CustomArrayAttribute) {
					clic.setTranslateItems(true);
				}
			}
		} else if (item instanceof CalendarQueryItem) {
			_input_component = new DateInputComponent();
		} else if (item instanceof NumberQueryItem) {
			_input_component = new NumberInputComponent();
		} else if (item instanceof BooleanQueryItem) {
			_input_component = new EmptyInputComponent();
		} else if (item instanceof StringQueryItem) {
			_input_component = new StringInputComponent();
		} else if (item instanceof SenseArrayQueryItem) {
			_input_component = new StringInputComponent();
		} else if (item instanceof EntryClassQueryItem) {
			EntryClassInputComponent ecic = new EntryClassInputComponent();
			if (_model.getDict() != null) {
				ecic.setSchema(_model.getDict().getEntryAttributeSchema());
			}

			_input_component = ecic;
		} else if (item instanceof BitmaskQueryItem) {
			_input_component = new UserFlagsInputComponent();
		} else {
			_input_component = null;
		}

		// Notify listeners
		for (ComponentReplacementListener componentReplacementListener : _listeners) {
			componentReplacementListener
					.componentReplaced(new ComponentReplacementEvent(
							old_component, _input_component.getComponent()));
		}
	}
}

class EmptyInputComponent implements InputComponent {
	private final JPanel _input_panel = new JPanel();

	public JComponent getComponent() {
		return _input_panel;
	}

	public void reset() {
		// nothing to do - it's empty
	}

	public Object getInput() {
		return null;
	}

	public void setInput(Object input) {
		// nothing to do - it's empty
	}
}

class DateInputComponent implements InputComponent {
	private final DateChooserButton _input_panel = new DateChooserButton();

	public JComponent getComponent() {
		return _input_panel;
	}

	public void reset() {
		_input_panel.setDate(new GregorianCalendar());
	}

	public Object getInput() {
		return _input_panel.getDate();
	}

	public void setInput(Object input) {
		_input_panel.setDate((Calendar) input);
	}
}

class NumberInputComponent implements InputComponent {
	private final CustomTextField _input_panel = new CustomTextField(10);

	public JComponent getComponent() {
		return _input_panel;
	}

	public void reset() {
		_input_panel.setText("");
	}

	public Object getInput() {
		String text = _input_panel.getText();
		if (text == null || "".equals(text)) {
			_input_panel.setText("0");
			return new Double(0.0);
		}
		return new Double(_input_panel.getText());
	}

	public void setInput(Object input) {
		_input_panel.setText(input.toString());
	}
}

class ChoiceListInputComponent extends ChoiceInputComponent {
	private final StringListInput _input_component = new StringListInput();

	@Override
	public JComponent getComponent() {
		return _input_component;
	}

	@Override
	public void reset() {
		_input_component.setStrings(new String[0]);
	}

	@Override
	public Object getInput() {
		return _container.getItems(_input_component.getStrings());
	}

	@Override
	public void setInput(Object input) {
		_input_component.setStrings(_container
				.getTranslations((Object[]) input));
	}

	@Override
	protected void updateInputComponent() {
		_input_component.setAvailableStrings(_container.getTranslations());
	}
}

class EntryClassInputComponent extends ChoiceInputComponent {
	public EntryClassInputComponent() {
		super();
		setTranslateItems(true);
	}

	public void setSchema(EntryAttributeSchema s) {
		if (s == null) {
			setChoices(new Object[0]);
		} else {
			EntryClass[] entry_classes = s.getEntryClasses();
			String[] choices = new String[entry_classes.length];
			for (int i = 0; i < entry_classes.length; i++) {
				choices[i] = entry_classes[i].getName();
			}

			setChoices(choices);
		}
	}
}

class StringListInput extends JPanel {
	public static class StringListDialog extends JDialog {
		private static final long serialVersionUID = 1L;

		public ChoiceListPanel choicePanel;

		public StringListDialog(Frame owner, String title) {
			super(owner, title, true);
			choicePanel = new ChoiceListPanel();
			choicePanel.setAllowCustomChoices(false);

			ActionListener listener = new ActionListener() {
				public void actionPerformed(ActionEvent ev) {
					dispose();
				}
			};
			Action ok = GUIUtils.createTextAction(listener, "ok");
			ButtonPanel button_panel = new ButtonPanel(
					SwingConstants.HORIZONTAL, SwingConstants.RIGHT);
			button_panel.addButtons(new JButton[] { new JButton(ok) });
			JPanel panel = new JPanel();
			panel.setLayout(new GridBagLayout());
			CustomConstraints cc = new CustomConstraints();
			cc.update(0, 0, 1.0, 1.0);
			panel.add(this.choicePanel, cc);
			cc.update(0, 1, 1.0, 0.0);
			panel.add(button_panel, cc);
			setContentPane(panel);
		}
	}

	private static final long serialVersionUID = 1L;

	private final JTextField _display;
	private final StringListDialog _dialog;

	public StringListInput() {
		_display = new JTextField(10);
		_display.setEditable(false);
		_dialog = new StringListDialog(JOptionPane.getFrameForComponent(this),
				I18nService.getString("Labels", "select_categories"));
		JButton button = new JButton("...");
		ActionListener listener = new ActionListener() {
			public void actionPerformed(ActionEvent ev) {
				GUIUtils.showDialog(StringListInput.this, _dialog);
				setStrings(getStrings());
			}
		};
		button.addActionListener(listener);
		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.insets = new Insets(0, 0, 0, 0);
		cc.update(0, 0, 0.0, 0.0);
		add(button, cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_display, cc);
	}

	public void setAvailableStrings(String[] strings) {
		_dialog.choicePanel.setAvailableObjects(strings);
	}

	public void setStrings(String[] strings) {
		_dialog.choicePanel.setSelectedObjects(strings);
		String text = Utils.arrayToString(strings, ", ");
		_display.setText(text);
		_display.setCaretPosition(0);
		_display.setToolTipText(text);
	}

	public String[] getStrings() {
		Object[] values = _dialog.choicePanel.getSelectedObjects();
		return Utils.objectArrayToStringArray(values);
	}
}

class UserFlagsInputComponent extends ChoiceListInputComponent {
	public UserFlagsInputComponent() {
		List<Entry.Stats.UserFlag> flags = Arrays.asList(Entry.Stats.UserFlag
				.values());
		setChoices(flags.subList(1, flags.size()).toArray());
		setTranslateItems(true);
	}

	@Override
	public Object getInput() {
		int input = 0;
		Object[] items = (Object[]) super.getInput();
		for (Object item : items) {
			input |= ((Entry.Stats.UserFlag) item).getValue();
		}

		return input;
	}

	@Override
	public void setInput(Object input) {
		Integer value = (Integer) input;
		List<Entry.Stats.UserFlag> items = new ArrayList<Entry.Stats.UserFlag>();
		for (Entry.Stats.UserFlag f : Entry.Stats.UserFlag.values()) {
			if ((f.getValue() & value) != 0) {
				items.add(f);
			}
		}

		super.setInput(items.toArray());
	}
}
