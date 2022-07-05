package net.sourceforge.jvlt.ui.components;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.TreeSet;

import javax.swing.MutableComboBoxModel;
import javax.swing.event.ListDataEvent;
import javax.swing.event.ListDataListener;

public class SortedComboBoxModel implements MutableComboBoxModel {
	private Object _selected_item = null;
	private final ArrayList<ListDataListener> _listeners = new ArrayList<ListDataListener>();
	private final TreeSet<Object> _items = new TreeSet<Object>();

	public void addElement(Object obj) {
		_items.add(obj);
	}

	/**
	 * Inserts an object
	 * 
	 * The obj argument is ignored.
	 */
	public void insertElementAt(Object obj, int index) {
		_items.add(obj);
	}

	public void removeElement(Object obj) {
		_items.remove(obj);
	}

	public void removeElementAt(int index) {
		Iterator<Object> it = _items.iterator();
		for (int i = 0; it.hasNext(); i++) {
			it.next();
			if (i == index) {
				it.remove();
				break;
			}
		}
	}

	public Object getSelectedItem() {
		return _selected_item;
	}

	public void setSelectedItem(Object item) {
		_selected_item = item;

		synchronized (_listeners) {
			ListDataListener[] listeners = _listeners
					.toArray(new ListDataListener[0]);
			for (ListDataListener listener : listeners) {
				listener.contentsChanged(new ListDataEvent(this,
						ListDataEvent.CONTENTS_CHANGED, 0, 0));
			}
		}
	}

	public void addListDataListener(ListDataListener l) {
		synchronized (_listeners) {
			_listeners.add(l);
		}
	}

	public Object getElementAt(int index) {
		Iterator<Object> it = _items.iterator();
		for (int i = 0; it.hasNext(); i++) {
			Object obj = it.next();
			if (i == index) {
				return obj;
			}
		}

		return null;
	}

	public int getSize() {
		return _items.size();
	}

	public void removeListDataListener(ListDataListener l) {
		synchronized (_listeners) {
			_listeners.remove(l);
		}
	}
}
