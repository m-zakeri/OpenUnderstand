package net.sourceforge.jvlt.ui.components;

import java.awt.Dimension;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Iterator;
import java.util.TreeSet;

import javax.swing.Action;
import javax.swing.DefaultListModel;
import javax.swing.JButton;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.ListSelectionModel;
import javax.swing.SwingConstants;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.ItemContainer;

public class ObjectSelectionPanel extends JPanel {
	protected class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("up")) {
				int index = _selection_list.getSelectedIndex();
				Object obj = _selected_objects.remove(index);
				_selected_objects.add(index - 1, obj);
				updateLists();
				_selection_list.setSelectedValue(
						_container.getTranslation(obj), true);
			} else if (ev.getActionCommand().equals("down")) {
				int index = _selection_list.getSelectedIndex();
				Object obj = _selected_objects.remove(index);
				_selected_objects.add(index + 1, obj);
				updateLists();
				_selection_list.setSelectedValue(
						_container.getTranslation(obj), true);
			} else if (ev.getActionCommand().equals("left")) {
				int index = _choice_list.getSelectedIndex();
				Object obj = _container
						.getItem(_choice_list.getSelectedValue());
				_selected_objects.add(obj);
				updateLists();
				if (index < _choice_list_model.size()) {
					_choice_list.setSelectedIndex(index);
				} else if (index == _choice_list_model.size()
						&& _choice_list_model.size() > 0) {
					_choice_list.setSelectedIndex(index - 1);
				}
			} else if (ev.getActionCommand().equals("right")) {
				int index = _selection_list.getSelectedIndex();
				Object obj = _container.getItem(_selection_list
						.getSelectedValue());
				_selected_objects.remove(obj);
				updateLists();
				if (index < _selection_list_model.size()) {
					_selection_list.setSelectedIndex(index);
				} else if (index == _selection_list_model.size()
						&& _selection_list_model.size() > 0) {
					_selection_list.setSelectedIndex(index - 1);
				}
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

	private static final long serialVersionUID = 1L;

	protected ItemContainer _container = new ItemContainer();
	protected Comparator<Object> _comparator = null;
	protected boolean _allow_reordering = true;
	// _selected_objects and _available_objects contain the original objects,
	// while _selection_list_model contains the translations
	protected ArrayList<Object> _selected_objects = new ArrayList<Object>();
	protected ArrayList<Object> _available_objects = new ArrayList<Object>();

	protected Action _up_action;
	protected Action _down_action;
	protected Action _left_action;
	protected Action _right_action;
	protected ButtonPanel _button_panel;
	protected JList _selection_list;
	protected JList _choice_list;
	protected DefaultListModel _selection_list_model;
	protected DefaultListModel _choice_list_model;

	public ObjectSelectionPanel() {
		init();
		update();
	}

	public Object[] getSelectedObjects() {
		return _selected_objects.toArray();
	}

	/**
	 * Adds the set of selected objects. Call {@link #setSelectedObjects} after
	 * {@link #setAvailableObjects}.
	 */
	public void setSelectedObjects(Object[] values) {
		_selected_objects.clear();
		_selected_objects.addAll(Arrays.asList(values));

		updateLists();
	}

	public void addAvailableObjects(Object[] values) {
		_container.addItems(values);
		_available_objects.addAll(Arrays.asList(values));
		updateLists();
	}

	public void setAvailableObjects(Object[] values) {
		_container.removeAllItems();
		_available_objects.clear();
		addAvailableObjects(values);
	}

	public void setTranslateItems(boolean translate) {
		_container.setTranslateItems(translate);
		updateLists();
	}

	public void setAllowReordering(boolean allow) {
		_allow_reordering = allow;
		updateButtonPanel();
		_button_panel.revalidate();
		_button_panel.repaint(_button_panel.getVisibleRect());
	}

	protected void init() {
		ActionHandler action_handler = new ActionHandler();
		_up_action = GUIUtils.createIconAction(action_handler, "up");
		_down_action = GUIUtils.createIconAction(action_handler, "down");
		_left_action = GUIUtils.createIconAction(action_handler, "left");
		_right_action = GUIUtils.createIconAction(action_handler, "right");

		ListSelectionHandler listhandler = new ListSelectionHandler();
		_selection_list_model = new DefaultListModel();
		_selection_list = new JList(_selection_list_model);
		_selection_list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
		_selection_list.addListSelectionListener(listhandler);
		JScrollPane selection_scrpane = new JScrollPane();
		selection_scrpane.setPreferredSize(new Dimension(150, 100));
		selection_scrpane.getViewport().setView(_selection_list);

		_choice_list_model = new DefaultListModel();
		_choice_list = new JList(_choice_list_model);
		_choice_list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
		_choice_list.addListSelectionListener(listhandler);
		JScrollPane choice_scrpane = new JScrollPane();
		choice_scrpane.setPreferredSize(new Dimension(150, 100));
		choice_scrpane.getViewport().setView(_choice_list);

		_button_panel = new ButtonPanel(SwingConstants.VERTICAL,
				SwingConstants.TOP);
		updateButtonPanel();

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(GUIUtils.getLabel("selected", _selection_list), cc);
		cc.update(0, 1, 1.0, 1.0);
		add(selection_scrpane, cc);
		cc.update(1, 0, 0.0, 1.0, 1, 2);
		add(_button_panel, cc);
		cc.update(2, 0, 1.0, 0.0, 1, 1);
		add(GUIUtils.getLabel("available", _choice_list), cc);
		cc.update(2, 1, 1.0, 1.0, 1, 1);
		add(choice_scrpane, cc);
	}

	protected void update() {
		int selection_list_index = _selection_list.getSelectedIndex();
		int choice_list_index = _choice_list.getSelectedIndex();
		_left_action.setEnabled(choice_list_index >= 0);
		_right_action.setEnabled(selection_list_index >= 0);
		_up_action.setEnabled(selection_list_index > 0);
		_down_action.setEnabled(selection_list_index >= 0
				&& selection_list_index < _selection_list_model.size() - 1);
	}

	protected void updateButtonPanel() {
		if (_allow_reordering) {
			_button_panel.setButtons(new JButton[] { new JButton(_up_action),
					new JButton(_down_action), new JButton(_left_action),
					new JButton(_right_action) });
		} else {
			_button_panel.setButtons(new JButton[] { new JButton(_left_action),
					new JButton(_right_action) });
		}
	}

	protected void updateLists() {
		Iterator<Object> it;
		TreeSet<Object> set;

		// Update list of selected items
		if (_comparator != null && !_allow_reordering) {
			set = new TreeSet<Object>(_comparator);
			set.addAll(_selected_objects);
			it = set.iterator();
		} else {
			it = _selected_objects.iterator();
		}
		_selection_list_model.clear();
		while (it.hasNext()) {
			_selection_list_model.addElement(_container.getTranslation(it
					.next()));
		}

		// Update list of available items
		if (_comparator != null) {
			set = new TreeSet<Object>(_comparator);
			set.addAll(_available_objects);
			it = set.iterator();
		} else {
			it = _available_objects.iterator();
		}
		_choice_list_model.clear();
		while (it.hasNext()) {
			Object o = it.next();
			if (!_selected_objects.contains(o)) {
				_choice_list_model.addElement(_container.getTranslation(o));
			}
		}
	}

	protected void setComparator(Comparator<Object> comparator) {
		_comparator = comparator;
	}
}
