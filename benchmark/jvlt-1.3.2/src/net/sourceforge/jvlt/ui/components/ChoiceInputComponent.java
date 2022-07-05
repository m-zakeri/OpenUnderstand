package net.sourceforge.jvlt.ui.components;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.JComponent;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

import net.sourceforge.jvlt.utils.ItemContainer;

public class ChoiceInputComponent extends ListeningInputComponent {
	protected ItemContainer _container = new ItemContainer();
	protected LabeledComboBox _input_box = null;

	public ChoiceInputComponent() {
		this(new LabeledComboBox(new SortedComboBoxModel()));
	}

	public JComponent getComponent() {
		return _input_box;
	}

	public void reset() {
		if (_input_box.getItemCount() > 0) {
			_input_box.setSelectedIndex(0);
		}
	}

	public Object getInput() {
		// If the input box is editable, it may happen that method
		// getSelectedItem() does not return the current item. If it is not
		// editable getEditor().getItem() may be empty even though the user
		// has entered data.
		Object obj = _input_box.isEditable() ? _input_box.getEditor().getItem()
				: _input_box.getSelectedItem();
		if (obj == null) {
			return null;
		} else if (obj.toString().equals("")) {
			return null;
		} else {
			return _container.getItem(obj);
		}
	}

	public void setInput(Object input) {
		_input_box.setSelectedItem(_container.getTranslation(input));
	}

	public boolean getTranslateItems() {
		return _container.getTranslateItems();
	}

	public void setTranslateItems(boolean translate) {
		_container.setTranslateItems(translate);
		updateInputComponent();
	}

	public void setAllowCustomChoices(boolean allow) {
		_input_box.setEditable(allow);
	}

	public void setChoices(Object[] choices) {
		_container.setItems(choices);
		updateInputComponent();
	}

	protected ChoiceInputComponent(LabeledComboBox input_box) {
		_input_box = input_box;
		_input_box.addChangeListener(new ChangeListener() {
			public void stateChanged(ChangeEvent e) {
				fireChangeEvent();
			}
		});
		_input_box.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent e) {
				fireChangeEvent();
			}
		});
	}

	protected void updateInputComponent() {
		Object[] items = _container.getItems();
		_input_box.removeAllItems();
		for (Object item : items) {
			_input_box.addItem(_container.getTranslation(item));
		}
	}
}
