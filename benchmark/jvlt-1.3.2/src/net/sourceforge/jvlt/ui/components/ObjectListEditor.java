package net.sourceforge.jvlt.ui.components;

import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;

import javax.swing.Action;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;

import net.sourceforge.jvlt.event.ComponentReplacementListener;
import net.sourceforge.jvlt.event.ComponentReplacementListener.ComponentReplacementEvent;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

public abstract class ObjectListEditor {
	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			if (e.getActionCommand().equals("more_items")) {
				// Make sure that _multi_input_field contains the value
				// from _single_input_field
				setSelectedItems(getSelectedItems());
				replaceComponents(_single_input_field, _multi_input_field);
			}
		}
	}

	protected ArrayList<ComponentReplacementListener> _listeners;

	protected JLabel _single_item_label = null;
	protected JLabel _multi_item_label = null;
	protected JPanel _single_item_panel = null;
	protected JPanel _multi_item_panel = null;
	protected Action _more_action = null;
	protected InputComponent _single_input_field = null;
	protected InputComponent _multi_input_field = null;
	/* Either _single_input_field or _multi_input_field */
	protected InputComponent _input_field = null;

	public ObjectListEditor(String label) {
		_listeners = new ArrayList<ComponentReplacementListener>();

		_more_action = GUIUtils.createTextAction(new ActionHandler(),
				"more_items");

		_single_input_field = createSingleInputComponent();
		_single_item_panel = new JPanel();
		_single_item_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.fill = GridBagConstraints.HORIZONTAL;
		cc.update(1, 0, 1.0, 0.0);
		_single_item_panel.add(_single_input_field.getComponent(), cc);
		cc.update(2, 0, 0.0, 0.0);
		_single_item_panel.add(new JButton(_more_action), cc);

		_multi_input_field = createMultiInputComponent();
		_multi_item_panel = new JPanel();
		_multi_item_panel.setLayout(new GridBagLayout());
		cc.update(0, 1, 1.0, 1.0);
		_multi_item_panel.add(_multi_input_field.getComponent(), cc);

		_input_field = _single_input_field;

		setLabel(label);
	}

	public void setFont(Font font) {
		_multi_input_field.getComponent().setFont(font);
		_single_input_field.getComponent().setFont(font);
	}

	public void setSelectedItems(Object[] items) {
		_multi_input_field.setInput(items);
		_single_input_field.setInput(items.length == 0 ? null : items[0]);

		if (items.length < 2 && _input_field != _single_input_field) {
			replaceComponents(_multi_input_field, _single_input_field);
		} else if (items.length >= 2 && _input_field != _multi_input_field) {
			replaceComponents(_single_input_field, _multi_input_field);
		}
	}

	public Object[] getSelectedItems() {
		if (_input_field == _single_input_field) {
			Object o = _input_field.getInput();
			if (o == null) {
				return new Object[0];
			}
			return new Object[] { o };
		}
		return (Object[]) _input_field.getInput();
	}

	public void addComponentReplacementListener(ComponentReplacementListener l) {
		_listeners.add(l);
	}

	public void removeComponentReplacementListener(
			ComponentReplacementListener l) {
		_listeners.remove(l);
	}

	public JComponent getInputComponent() {
		return _input_field == _single_input_field ? _single_item_panel
				: _multi_item_panel;
	}

	public void setLabel(String label) {
		if (_single_item_label != null) {
			_single_item_panel.remove(_single_item_label);
		}
		if (_multi_item_label != null) {
			_multi_item_panel.remove(_multi_item_label);
		}

		_single_item_label = GUIUtils.getLabel(label, _single_input_field
				.getComponent());
		_multi_item_label = GUIUtils.getLabel(label, _multi_input_field
				.getComponent());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		_single_item_panel.add(_single_item_label, cc);
		_multi_item_panel.add(_multi_item_label, cc);
	}

	public void setEnabled(boolean enable) {
		_more_action.setEnabled(enable);
		_single_input_field.getComponent().setEnabled(enable);
		_multi_input_field.getComponent().setEnabled(enable);
	}

	protected void replaceComponents(InputComponent old_component,
			InputComponent new_component) {
		_input_field = new_component;
		for (ComponentReplacementListener l : _listeners) {
			JPanel old_panel = old_component == _single_input_field ? _single_item_panel
					: _multi_item_panel;
			JPanel new_panel = new_component == _single_input_field ? _single_item_panel
					: _multi_item_panel;
			l.componentReplaced(new ComponentReplacementEvent(old_panel,
					new_panel));
		}
	}

	protected abstract InputComponent createSingleInputComponent();

	protected abstract InputComponent createMultiInputComponent();
}
