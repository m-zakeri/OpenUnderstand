package net.sourceforge.jvlt.ui.components;

import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.HashMap;
import java.util.Map;

import javax.swing.Action;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

public abstract class ObjectMapEditorPanel<T extends Object> extends JPanel {
	private static final long serialVersionUID = 1L;

	protected class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("new_update")) {
				Object item = _name_box.getSelectedItem();
				if (item != null && !item.toString().equals("")) {
					ObjectMapEditorPanel.this.createOrUpdateItem();
				}
			} else if (ev.getActionCommand().equals("remove")) {
				ObjectMapEditorPanel.this.removeSelectedItem();
			} else if (ev.getSource() == _name_box) {
				ObjectMapEditorPanel.this.selectionChanged();
			}
		}
	}

	private class ChangeHandler implements ChangeListener {
		public void stateChanged(ChangeEvent ev) {
			update();
		}
	}

	protected HashMap<Object, T> _item_map = new HashMap<Object, T>();

	protected Action _new_update_action;
	protected Action _remove_action;
	protected ActionHandler _handler;
	protected LabeledComboBox _name_box;

	public ObjectMapEditorPanel() {
		init();
		update();
	}

	public Object getSelectedItem() {
		return _name_box.getSelectedItem();
	}

	public void setSelectedItem(Object o) {
		_name_box.setSelectedItem(o);
	}

	public Map<Object, T> getItems() {
		return _item_map;
	}

	public void setItems(Map<Object, T> items) {
		_name_box.removeActionListener(_handler);
		_item_map.clear();
		Object selected = _name_box.getSelectedItem();
		_name_box.removeAllItems();
		for (Object key : items.keySet()) {
			T value = items.get(key);
			_item_map.put(key, value);
			_name_box.addItem(key);
		}

		if (selected == null || selected.equals("")
				|| _item_map.containsKey(selected)) {
			_name_box.setSelectedItem(selected);
		}

		_name_box.addActionListener(_handler);
	}

	protected abstract T getCurrentObject();

	protected abstract void selectionChanged();

	protected void init() {
		_handler = new ActionHandler();
		_new_update_action = GUIUtils.createTextAction(_handler, "new_update");
		_remove_action = GUIUtils.createTextAction(_handler, "remove");

		_name_box = new LabeledComboBox();
		_name_box.setEditable(true);
		_name_box.addChangeListener(new ChangeHandler());
		_name_box.addActionListener(_handler);

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_name_box, cc);
		cc.update(1, 0, 0.0, 0.0);
		add(new JButton(_new_update_action), cc);
		cc.update(2, 0, 0.0, 0.0);
		add(new JButton(_remove_action), cc);
	}

	protected void update() {
		// Enable/disable the "New/Update" and the "Remove" button
		Object item = _name_box.getEditor().getItem();
		String str = item == null ? "" : item.toString();
		_new_update_action.setEnabled(!str.equals(""));
		_remove_action.setEnabled(_item_map.containsKey(str));
	}

	protected void removeSelectedItem() {
		_item_map.remove(_name_box.getSelectedItem());
		_name_box.removeItem(_name_box.getSelectedItem());
		_name_box.setSelectedItem("");
		update();
	}

	protected void createOrUpdateItem() {
		Object item = _name_box.getSelectedItem();
		if (!_item_map.containsKey(item)) {
			_name_box.addItem(item);
		}

		_item_map.put(item, getCurrentObject());
		_name_box.getEditor().selectAll();
		update();
	}
}
