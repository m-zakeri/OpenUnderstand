package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Component;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.TreeMap;

import javax.swing.Box;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;

import net.sourceforge.jvlt.core.ArraySchemaAttribute;
import net.sourceforge.jvlt.core.AttributeChoice;
import net.sourceforge.jvlt.core.ChoiceSchemaAttribute;
import net.sourceforge.jvlt.core.EntryAttributeSchema;
import net.sourceforge.jvlt.core.EntryClass;
import net.sourceforge.jvlt.core.SchemaAttribute;
import net.sourceforge.jvlt.ui.components.AttributeChoiceInputComponent;
import net.sourceforge.jvlt.ui.components.AttributeChoiceListPanel;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.IndentedComboBox;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.I18nService;

public class EntryAttributeSchemaPanel extends JPanel {
	private static final long serialVersionUID = 1L;
	private static final String NOT_SPECIFIED = "not_specified";

	private final TreeMap<String, EntryClass> _string_class_map;
	private final TreeMap<EntryClass, EntryClassPanel> _class_panel_map;
	private final IndentedComboBox _class_box;
	private JPanel _current_panel;
	private final JScrollPane _scroll_pane;
	private final Component _empty_panel;

	public EntryAttributeSchemaPanel(EntryAttributeSchema schema) {
		_string_class_map = new TreeMap<String, EntryClass>();
		_class_panel_map = new TreeMap<EntryClass, EntryClassPanel>();
		_current_panel = null;
		_scroll_pane = new JScrollPane();
		_empty_panel = Box.createVerticalGlue();
		_class_box = new IndentedComboBox();
		_class_box.setLabel("class");
		_class_box.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent ev) {
				update();
			}
		});

		_class_box.setTranslateItems(true);
		_class_box.addItem(NOT_SPECIFIED, 0);
		EntryClass[] entry_classes = schema.getEntryClasses();
		ArrayList<EntryClass> root_attrs = new ArrayList<EntryClass>();
		for (int i = 0; i < entry_classes.length; i++) {
			if (entry_classes[i].getParentClass() == null
					&& !root_attrs.contains(entry_classes[i])) {
				root_attrs.add(entry_classes[i]);
			}
		}
		for (EntryClass entryClass : root_attrs) {
			insertEntryClass(entryClass, 0);
		}

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		add(_class_box.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_class_box, cc);
		cc.update(0, 1, 1.0, 1.0, 2, 1);
		add(_empty_panel, cc);

		update();
	}

	public EntryClass getValue() {
		Object selected = _class_box.getSelectedItem();
		if (selected.equals(NOT_SPECIFIED)) {
			return null;
		}
		EntryClass cl = _string_class_map.get(selected);
		EntryClassPanel p = _class_panel_map.get(cl);
		return p.getValue();
	}

	public void setValue(EntryClass cl) {
		if (cl == null) {
			_class_box.setSelectedItem(NOT_SPECIFIED);
		} else {
			EntryClassPanel p = _class_panel_map.get(cl);
			p.setValue(cl);
			_class_box.setSelectedItem(cl.getName());
		}
	}

	private void update() {
		if (_current_panel != null) {
			remove(_scroll_pane);
		} else {
			remove(_empty_panel);
		}

		Object item = _class_box.getSelectedItem();
		JPanel p = null;
		if (item != null && !item.equals(NOT_SPECIFIED)) {
			p = _class_panel_map.get(_string_class_map.get(item));
		}

		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 1, 1.0, 1.0, 2, 1);
		if (p != null) {
			_scroll_pane.getViewport().setView(p);
			add(_scroll_pane, cc);
		} else {
			add(_empty_panel, cc);
		}

		revalidate();
		repaint(getVisibleRect());
		_current_panel = p;
	}

	private void insertEntryClass(EntryClass cl, int indent_level) {
		EntryClassPanel p = new EntryClassPanel(cl);
		_class_panel_map.put(cl, p);
		_class_box.addItem(cl.getName(), indent_level);
		_string_class_map.put(cl.getName(), cl);

		EntryClass[] children = cl.getChildClasses();
		for (EntryClass element : children) {
			insertEntryClass(element, indent_level + 1);
		}
	}
}

class EntryClassPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final TreeMap<SchemaAttribute, SchemaAttributeInput> _input_panels;
	private final EntryClass _entry_class;
	private final AttributeResources _resources;

	public EntryClassPanel(EntryClass cl) {
		_entry_class = cl;
		_input_panels = new TreeMap<SchemaAttribute, SchemaAttributeInput>();
		_resources = new AttributeResources();

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		String[] groups = cl.getGroups();
		for (int i = 0; i < groups.length; i++) {
			cc.update(0, i, 1.0, 0.0);
			cc.insets = new Insets(0, 0, 0, 0);
			add(createPanel(groups[i]), cc);
		}
	}

	public EntryClass getValue() {
		EntryClass ec = new EntryClass(_entry_class.getName());
		SchemaAttribute[] atts = _entry_class.getAttributes();
		for (SchemaAttribute att2 : atts) {
			SchemaAttribute att = getAttributeValue(att2);
			if (att != null) {
				ec.addAttribute(att);
			}
		}
		return ec;
	}

	public void setValue(EntryClass cl) {
		SchemaAttribute[] atts = cl.getAttributes();
		for (SchemaAttribute att : atts) {
			updateInputPanel(att);
		}
	}

	private SchemaAttribute getAttributeValue(SchemaAttribute att) {
		SchemaAttributeInput input = _input_panels.get(att);
		Object value = input.getValue();
		if (value == null) {
			return null;
		}
		SchemaAttribute cloned = (SchemaAttribute) att.clone();
		cloned.setValue(value);
		return cloned;
	}

	private void updateInputPanel(SchemaAttribute att) {
		SchemaAttributeInput input = _input_panels.get(att);
		if (input != null) {
			/*
			 * The input panel may be null if the attribute cannot be found
			 * because the dictionary changed.
			 */
			input.setValue(att.getValue());
		}
	}

	private JPanel createPanel(String group) {
		JPanel panel = new JPanel();
		panel.setLayout(new GridBagLayout());
		if (!group.equals("")) {
			panel.setBorder(new TitledBorder(new EtchedBorder(
					EtchedBorder.LOWERED), _resources.getString(group)));
		}

		CustomConstraints cc = new CustomConstraints();
		SchemaAttribute[] atts = _entry_class.getAttributes(group);
		for (int i = 0; i < atts.length; i++) {
			cc.update(0, i, 1.0, 0.0);
			cc.insets = new Insets(0, 0, 0, 0);
			panel.add(createPanel(atts[i]), cc);
		}

		return panel;
	}

	private JPanel createPanel(SchemaAttribute attr) {
		if (attr instanceof ArraySchemaAttribute) {
			ArraySchemaAttribute asa = (ArraySchemaAttribute) attr;
			ArrayAttributeInput aai = new ArrayAttributeInput(asa);
			_input_panels.put(asa, aai);
			return aai;
		} else if (attr instanceof ChoiceSchemaAttribute) {
			ChoiceSchemaAttribute csa = (ChoiceSchemaAttribute) attr;
			ChoiceAttributeInput cai = new ChoiceAttributeInput(csa);
			_input_panels.put(csa, cai);
			return cai;
		} else {
			SimpleAttributeInput sai = new SimpleAttributeInput(attr);
			_input_panels.put(attr, sai);
			return sai;
		}
	}
}

abstract class SchemaAttributeInput extends JPanel {
	private static final long serialVersionUID = 1L;

	protected SchemaAttribute _attribute;
	protected AttributeResources _resources;

	public SchemaAttributeInput(SchemaAttribute att) {
		_attribute = att;
		_resources = new AttributeResources();
	}

	public abstract Object getValue();

	public abstract void setValue(Object o);
}

class SimpleAttributeInput extends SchemaAttributeInput {
	private static final long serialVersionUID = 1L;

	private final CustomTextField _input_field;

	public SimpleAttributeInput(SchemaAttribute att) {
		super(att);

		_input_field = new CustomTextField(20);

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		add(new JLabel(_resources.getString(att.getName()) + ":"), cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_input_field, cc);
	}

	@Override
	public Object getValue() {
		String text = _input_field.getText();
		if (text == null || text.length() == 0) {
			return null;
		}
		return text;
	}

	@Override
	public void setValue(Object o) {
		if (o == null) {
			_input_field.setText("");
		} else {
			_input_field.setText(o.toString());
		}
	}
}

class ChoiceAttributeInput extends SchemaAttributeInput {
	private static final long serialVersionUID = 1L;

	protected AttributeChoice _not_specified;
	protected AttributeChoiceInputComponent _input_component;

	public ChoiceAttributeInput(ChoiceSchemaAttribute att) {
		super(att);
		_not_specified = new AttributeChoice(I18nService.getString("Labels",
				"not_specified"));
		initUI();
	}

	@Override
	public Object getValue() {
		AttributeChoice val = (AttributeChoice) _input_component.getInput();
		return val == null || val.equals(_not_specified) ? null : val;
	}

	@Override
	public void setValue(Object o) {
		if (o == null) {
			_input_component.setInput(_not_specified);
		} else {
			_input_component.setInput(o);
		}
	}

	protected void initUI() {
		_input_component = new AttributeChoiceInputComponent();
		ArrayList<AttributeChoice> list = new ArrayList<AttributeChoice>();
		list.addAll(Arrays.asList(((ChoiceSchemaAttribute) _attribute)
				.getChoices()));
		list.add(0, _not_specified);
		_input_component.setChoices(list.toArray(new AttributeChoice[0]));

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		add(new JLabel(_resources.getString(_attribute.getName()) + ":"), cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_input_component.getComponent(), cc);
	}
}

class ArrayAttributeInput extends ChoiceAttributeInput {
	private static final long serialVersionUID = 1L;

	private AttributeChoiceListPanel _input_panel;

	public ArrayAttributeInput(ArraySchemaAttribute attr) {
		super(attr);
	}

	@Override
	public Object getValue() {
		return _input_panel.getSelectedAttributeChoices();
	}

	@Override
	public void setValue(Object obj) {
		_input_panel.setSelectedObjects((Object[]) obj);
	}

	@Override
	protected void initUI() {
		_input_panel = new AttributeChoiceListPanel();
		_input_panel.setAvailableObjects(((ChoiceSchemaAttribute) _attribute)
				.getChoices());

		setLayout(new GridLayout());
		add(_input_panel);
		setBorder(new TitledBorder(new EtchedBorder(EtchedBorder.LOWERED),
				_resources.getString(_attribute.getName())));
	}
}
