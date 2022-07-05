package net.sourceforge.jvlt.ui.components;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.DefaultListModel;
import javax.swing.JButton;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.ListSelectionModel;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

/**
 * A panel that allows to manage lists of objects.
 */
public class ObjectListPanel extends JPanel {
	protected class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("add")) {
				Object o = ObjectListPanel.this.toString(_input_component
						.getInput());
				if (o != null && !_list_model.contains(o)) {
					_list_model.addElement(o);
					_list.setSelectedIndex(_list_model.size() - 1);
				}
			} else if (ev.getActionCommand().equals("remove")) {
				int index = _list.getSelectedIndex();
				if (index >= 0) {
					_list_model.remove(index);

					if (index < _list_model.getSize()) {
						_list.setSelectedIndex(index);
					} else if (index - 1 >= 0) {
						_list.setSelectedIndex(index - 1);
					}
				}
			} else if (ev.getActionCommand().equals("up")) {
				int index = _list.getSelectedIndex();
				Object obj = _list_model.remove(index);
				_list_model.add(index - 1, obj);
				_list.setSelectedIndex(index - 1);
			} else if (ev.getActionCommand().equals("down")) {
				int index = _list.getSelectedIndex();
				Object obj = _list_model.remove(index);
				_list_model.add(index + 1, obj);
				_list.setSelectedIndex(index + 1);
			}
		}
	}

	protected class ListSelectionHandler implements ListSelectionListener {
		public void valueChanged(ListSelectionEvent ev) {
			if (!ev.getValueIsAdjusting()) {
				update();
			}
		}
	}

	protected class ChangeHandler implements ChangeListener {
		public void stateChanged(ChangeEvent ev) {
			update();
		}
	}

	private static final long serialVersionUID = 1L;

	protected ArrayList<ListSelectionListener> _selection_listeners;
	protected ChangeHandler _change_handler = new ChangeHandler();

	protected Action _add_action;
	protected Action _remove_action;
	protected Action _move_up_action;
	protected Action _move_down_action;
	protected DefaultListModel _list_model;
	protected JList _list = null;
	protected ListeningInputComponent _input_component = null;

	public ObjectListPanel() {
		this(new StringInputComponent());
	}

	@Override
	public void setFont(Font font) {
		super.setFont(font);

		if (_list != null) {
			_list.setFont(font);
		}

		if (_input_component != null) {
			_input_component.getComponent().setFont(font);
		}
	}

	public Object[] getSelectedObjects() {
		return _list_model.toArray();
	}

	public void setSelectedObjects(Object[] objects) {
		Object[] vals = objects == null ? new Object[0] : objects;

		_list_model.clear();
		for (Object val : vals) {
			String s = toString(val);
			if (s != null) {
				_list_model.addElement(s);
			}
		}

		update();
	}

	@Override
	public void setEnabled(boolean enabled) {
		super.setEnabled(enabled);
		_add_action.setEnabled(enabled);
		_remove_action.setEnabled(enabled);
		_input_component.getComponent().setEnabled(enabled);
		_list.setEnabled(enabled);
		if (enabled) {
			update();
		}
	}

	protected ObjectListPanel(ListeningInputComponent c) {
		_selection_listeners = new ArrayList<ListSelectionListener>();

		_input_component = c;
		_input_component.addChangeListener(_change_handler);

		init();
		update();
	}

	protected void init() {
		ActionHandler handler = new ActionHandler();
		_add_action = GUIUtils.createTextAction(handler, "add");
		_remove_action = GUIUtils.createTextAction(handler, "remove");
		_move_up_action = GUIUtils.createIconAction(handler, "up");
		_move_down_action = GUIUtils.createIconAction(handler, "down");

		_list_model = new DefaultListModel();
		_list = new JList(_list_model);
		_list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
		_list.addListSelectionListener(new ListSelectionHandler());
		_list.setFont(getFont());

		_input_component.getComponent().setFont(getFont());

		JScrollPane list_scrpane = new JScrollPane();
		list_scrpane.setPreferredSize(new Dimension(100, 100));
		list_scrpane.getViewport().setView(_list);

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_input_component.getComponent(), cc);
		cc.update(1, 0, 0.0, 0.0);
		add(new JButton(_add_action), cc);
		cc.update(0, 1, 1.0, 1.0, 1, 4);
		add(list_scrpane, cc);
		cc.update(1, 1, 0.0, 0.0, 1, 1);
		add(new JButton(_remove_action), cc);
		cc.update(1, 2, 0.0, 0.0, 1, 1);
		add(new JButton(_move_up_action), cc);
		cc.update(1, 3, 0.0, 0.0, 1, 1);
		add(new JButton(_move_down_action), cc);
		cc.update(1, 4, 0.0, 1.0, 1, 1);
		add(Box.createVerticalGlue(), cc);
	}

	protected void update() {
		int index = _list.getSelectedIndex();
		String s = toString(_input_component.getInput());
		_add_action.setEnabled(s != null && !_list_model.contains(s));
		_remove_action.setEnabled(index >= 0);
		_move_up_action.setEnabled(index >= 1);
		_move_down_action.setEnabled(index >= 0
				&& index < _list_model.size() - 1);
	}

	protected String toString(Object o) {
		return o == null ? null : o.toString();
	}
}
